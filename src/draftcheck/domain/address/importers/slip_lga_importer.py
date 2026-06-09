"""SLIP LGA boundary importer — City of Vincent.

Fetches the City of Vincent LGA boundary polygon from the SLIP LGA boundaries
layer and loads it as an ``LgArea`` record.

Licence:    CC BY 4.0 (Landgate SLIP) — LicenceStatus.LICENSED
CRS:        SLIP returns GDA2020 (EPSG:7844).
approval_status: "approved"

Endpoint:
    SLIP public WFS — LGA boundaries layer:
    https://services.slip.wa.gov.au/public/services/
        SLIP_Public_Services/Administrative_Boundaries/MapServer/WFSServer
    typeName: ``Administrative_Boundaries:WA_LOCAL_GOVERNMENT_AREA``
    CQL_FILTER: ``LGA_NAME='VINCENT'``

If the endpoint is unreachable, logs a warning and returns 0 (degraded).

Usage::

    from draftcheck.domain.address.importers.slip_lga_importer import (
        import_slip_lga_vincent,
    )
    count = import_slip_lga_vincent(store)
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError

from draftcheck.domain.address.spatial import (
    GDA2020_TARGET_CRS,
    LicenceStatus,
    SourceApprovalStatus,
    SpatialDatasetMetadata,
)

if TYPE_CHECKING:
    from draftcheck.domain.address.spatial import InMemorySpatialDatasetStore
    from draftcheck.domain.address.postgis_store import PostGISSpatialDatasetStore

logger = logging.getLogger(__name__)

_SLIP_ADMIN_WFS = (
    "https://services.slip.wa.gov.au/public/services/"
    "SLIP_Public_Services/Administrative_Boundaries/MapServer/WFSServer"
)
_TYPENAME = "Administrative_Boundaries:WA_LOCAL_GOVERNMENT_AREA"
_LGA_FILTER = "LGA_NAME='VINCENT'"

_LICENCE = "CC BY 4.0 (Landgate SLIP)"
_PROVIDER = "Landgate / SLIP"
_DATASET_ID = "slip_lga_vincent_2026"

_LGA_NAME = "City of Vincent"
_STATE = "WA"


def _build_url() -> str:
    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "typeName": _TYPENAME,
        "outputFormat": "application/json",
        "CQL_FILTER": _LGA_FILTER,
        "srsName": "EPSG:7844",
    }
    return f"{_SLIP_ADMIN_WFS}?{urlencode(params)}"


def _fetch_geojson(url: str) -> dict[str, Any] | None:
    req = Request(url)
    req.add_header("Accept", "application/json")
    try:
        with urlopen(req, timeout=30) as resp:  # noqa: S310 – controlled URL
            return json.loads(resp.read())
    except URLError as exc:
        logger.warning("slip_lga_importer: HTTP error: %s", exc)
        return None
    except json.JSONDecodeError as exc:
        logger.warning("slip_lga_importer: JSON decode error: %s", exc)
        return None


def _geom_to_ewkt(geom: dict[str, Any]) -> str | None:
    """Convert GeoJSON geometry to EWKT SRID=7844.

    TODO: If SLIP returns GDA94 (EPSG:4283) instead of GDA2020 (EPSG:7844),
    reprojection is required before storing.  Check the CRS member in the WFS
    response FeatureCollection.
    """
    geom_type = geom.get("type", "")
    coordinates = geom.get("coordinates")
    if not coordinates:
        return None
    if geom_type == "Polygon":
        rings = _rings_to_wkt(coordinates)
        return f"SRID=7844;MULTIPOLYGON(({rings}))"
    elif geom_type == "MultiPolygon":
        polygons = [f"({_rings_to_wkt(poly)})" for poly in coordinates]
        return f"SRID=7844;MULTIPOLYGON({','.join(polygons)})"
    return None


def _rings_to_wkt(rings: list) -> str:
    parts = []
    for ring in rings:
        pts = ",".join(f"{x} {y}" for x, y in ring)
        parts.append(f"({pts})")
    return ",".join(parts)


def import_slip_lga_vincent(
    store: "InMemorySpatialDatasetStore | PostGISSpatialDatasetStore",
) -> int:
    """Import the City of Vincent LGA boundary from SLIP.

    For ``PostGISSpatialDatasetStore`` this inserts an ``LgArea`` row.
    For ``InMemorySpatialDatasetStore`` this is a no-op (no LgArea concept)
    but the dataset is still registered.

    Returns 1 on success, 0 on failure.
    """
    geojson = _fetch_geojson(_build_url())
    if geojson is None:
        logger.warning(
            "slip_lga_importer: SLIP administrative WFS is not accessible. "
            "Returning 0 (degraded operation)."
        )
        return 0

    features = geojson.get("features", [])
    if not features:
        logger.warning("slip_lga_importer: no LGA features returned for VINCENT")
        return 0

    dataset = SpatialDatasetMetadata(
        dataset_id=_DATASET_ID,
        name=f"WA LGA Boundary — {_LGA_NAME} (SLIP)",
        provider=_PROVIDER,
        version="2026",
        licence=_LICENCE,
        licence_status=LicenceStatus.LICENSED,
        source_crs=GDA2020_TARGET_CRS,
        approval_status=SourceApprovalStatus.APPROVED,
        source_version_id=f"slip:wa-lga:{_LGA_NAME.lower().replace(' ', '-')}:2026",
    )
    result = store.import_dataset(dataset)
    if not result.accepted:
        logger.error("slip_lga_importer: dataset not accepted: %s", result.reason)
        return 0

    # For PostGIS store — insert an LgArea row directly via SQLAlchemy
    from draftcheck.domain.address.postgis_store import PostGISSpatialDatasetStore

    if isinstance(store, PostGISSpatialDatasetStore):
        return _insert_lg_area_postgis(store, dataset, features)

    # For in-memory store — dataset is registered; no LgArea concept exists
    logger.info(
        "slip_lga_importer: LGA dataset registered in in-memory store "
        "(no LgArea persistence for InMemorySpatialDatasetStore)"
    )
    return 1


def _insert_lg_area_postgis(
    store: "PostGISSpatialDatasetStore",
    dataset: SpatialDatasetMetadata,
    features: list[dict[str, Any]],
) -> int:
    from sqlalchemy.orm import Session
    from sqlalchemy import text
    from draftcheck.db.models import LgArea as DbLgArea, SpatialDataset as DbSpatialDataset
    from sqlalchemy import select

    db_dataset_id = store._resolve_db_dataset_id(dataset.dataset_id)
    if db_dataset_id is None:
        logger.error("slip_lga_importer: could not resolve DB dataset ID")
        return 0

    feature = features[0]
    props = feature.get("properties") or {}
    geom = feature.get("geometry") or {}
    geom_ewkt = _geom_to_ewkt(geom) or "SRID=7844;MULTIPOLYGON EMPTY"
    lg_code = props.get("LGA_CODE") or props.get("lga_code") or ""

    with Session(store._engine) as session:
        row = DbLgArea(
            name=_LGA_NAME,
            lg_code=lg_code,
            spatial_dataset_id=db_dataset_id,
            metadata_json={
                "state": _STATE,
                "dataset_id": dataset.dataset_id,
                "lga_name": _LGA_NAME,
            },
        )
        session.add(row)
        session.flush()
        session.execute(
            text("UPDATE lg_areas SET geom = ST_GeomFromEWKT(:wkt) WHERE id = :row_id"),
            {"wkt": geom_ewkt, "row_id": str(row.id)},
        )
        session.commit()

    logger.info("slip_lga_importer: LgArea inserted for %s", _LGA_NAME)
    return 1
