"""SLIP cadastre (WA parcel boundaries) importer.

Fetches parcel geometries from the SLIP public WFS for the City of Vincent and
loads them into the spatial store.

Licence:    CC BY 4.0 (Landgate / SLIP free tier) -- LicenceStatus.LICENSED
CRS:        SLIP free WFS returns GDA2020 (EPSG:7844) GeoJSON; if the response
            CRS member indicates GDA94 (EPSG:4283), coordinates are reprojected
            to EPSG:7844 via pyproj before storage.
approval_status: "approved"

Endpoints tried (in order):
1. SLIP public WFS (no authentication required):
   https://services.slip.wa.gov.au/public/services/SLIP_Public_Services/
       Cadastral_Boundaries/MapServer/WFSServer
   typeName: ``Cadastral_Boundaries:WA_CADASTRE_POLYGON``
   CQL_FILTER: ``LGA_NAME='VINCENT'``

2. SLIP authenticated WFS (credentials from env ``SLIP_USERNAME`` /
   ``SLIP_PASSWORD``):
   https://services.slip.wa.gov.au/private/WFS

If neither endpoint is reachable, the importer logs a warning and returns 0
(degraded operation -- does NOT raise).

Usage::

    from draftcheck.domain.address.importers.slip_cadastre_importer import (
        import_slip_cadastre_vincent,
    )
    count = import_slip_cadastre_vincent(store)
"""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError

from draftcheck.domain.address.spatial import (
    GDA2020_TARGET_CRS,
    LicenceStatus,
    Parcel,
    SourceApprovalStatus,
    SpatialDatasetMetadata,
)

if TYPE_CHECKING:
    from draftcheck.domain.address.spatial import InMemorySpatialDatasetStore

logger = logging.getLogger(__name__)

_SLIP_PUBLIC_WFS = (
    "https://services.slip.wa.gov.au/public/services/"
    "SLIP_Public_Services/Cadastral_Boundaries/MapServer/WFSServer"
)
_SLIP_PRIVATE_WFS = "https://services.slip.wa.gov.au/private/WFS"
_TYPENAME = "Cadastral_Boundaries:WA_CADASTRE_POLYGON"
_LGA_FILTER = "LGA_NAME='VINCENT'"

_LICENCE = "CC BY 4.0 (Landgate SLIP)"
_PROVIDER = "Landgate / SLIP"
_DATASET_ID = "slip_cadastre_vincent_2026"


def _build_wfs_url(base_url: str, *, auth: tuple[str, str] | None = None) -> str:
    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "typeName": _TYPENAME,
        "outputFormat": "application/json",
        "CQL_FILTER": _LGA_FILTER,
        "srsName": "EPSG:7844",
    }
    return f"{base_url}?{urlencode(params)}"


def _fetch_geojson(url: str, *, username: str = "", password: str = "") -> dict[str, Any] | None:
    """Fetch GeoJSON from a WFS URL.  Returns parsed dict or None on failure."""
    import base64

    req = Request(url)
    if username and password:
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        req.add_header("Authorization", f"Basic {credentials}")
    req.add_header("Accept", "application/json")
    try:
        with urlopen(req, timeout=30) as resp:  # noqa: S310 - controlled URL
            return json.loads(resp.read())
    except URLError as exc:
        logger.warning("slip_cadastre_importer: HTTP error fetching %s: %s", url, exc)
        return None
    except json.JSONDecodeError as exc:
        logger.warning("slip_cadastre_importer: JSON decode error: %s", exc)
        return None


def _detect_source_crs(geojson: dict[str, Any]) -> str | None:
    """Detect the CRS from a WFS GeoJSON FeatureCollection ``crs`` member.

    Returns ``"EPSG:4283"`` if GDA94, ``"EPSG:7844"`` if GDA2020, or
    ``None`` if the member is absent.
    """
    crs_member = geojson.get("crs")
    if not crs_member or not isinstance(crs_member, dict):
        return None
    props = crs_member.get("properties") or {}
    name = str(props.get("name") or "")
    if "4283" in name:
        return "EPSG:4283"
    if "7844" in name:
        return "EPSG:7844"
    if name.upper().startswith("EPSG:"):
        return name.upper()
    return None


def _reproject_ring(ring: list, transformer: Any) -> list:
    return [list(transformer.transform(x, y)) for x, y in ring]


def _maybe_reproject_coords(coordinates: list, source_crs: str | None) -> list:
    """Reproject coordinates from GDA94 (EPSG:4283) to GDA2020 (EPSG:7844).

    No-op if ``source_crs`` is not GDA94.  Uses pyproj (available via the
    shapely dependency).
    """
    if not source_crs or "4283" not in source_crs:
        return coordinates
    try:
        from pyproj import Transformer

        transformer = Transformer.from_crs("EPSG:4283", "EPSG:7844", always_xy=True)

        def _reproject_depth(coords: list, depth: int) -> list:
            if depth == 0:
                return _reproject_ring(coords, transformer)
            return [_reproject_depth(item, depth - 1) for item in coords]

        return _reproject_depth(coordinates, depth=1)
    except Exception as exc:  # pragma: no cover
        logger.warning(
            "slip_cadastre_importer: pyproj reprojection failed (%s); storing as-is", exc
        )
        return coordinates


def _geom_to_ewkt(geom: dict[str, Any], source_crs: str | None = None) -> str | None:
    """Convert a GeoJSON geometry dict to an EWKT string (SRID=7844).

    Only handles Polygon and MultiPolygon (parcel geometries).
    Conditionally reprojects from GDA94 (EPSG:4283) to GDA2020 (EPSG:7844)
    when ``source_crs`` indicates the WFS response is GDA94.
    """
    geom_type = geom.get("type", "")
    coordinates = geom.get("coordinates")
    if not coordinates:
        return None

    if geom_type == "Polygon":
        coords = _maybe_reproject_coords(coordinates, source_crs)
        rings = _coords_to_wkt_rings(coords)
        return f"SRID=7844;MULTIPOLYGON(({rings}))"
    elif geom_type == "MultiPolygon":
        polygons = []
        for poly in coordinates:
            reprojected = _maybe_reproject_coords(poly, source_crs)
            rings = _coords_to_wkt_rings(reprojected)
            polygons.append(f"({rings})")
        return f"SRID=7844;MULTIPOLYGON({','.join(polygons)})"
    else:
        logger.debug("slip_cadastre_importer: unsupported geometry type %r", geom_type)
        return None


def _coords_to_wkt_rings(rings: list) -> str:
    parts = []
    for ring in rings:
        pts = ",".join(f"{x} {y}" for x, y in ring)
        parts.append(f"({pts})")
    return ",".join(parts)


def import_slip_cadastre_vincent(
    store: "InMemorySpatialDatasetStore",
) -> int:
    """Import City of Vincent parcel boundaries from SLIP WFS.

    Returns count of parcels imported.  Returns 0 (with a logged warning) if
    SLIP is unreachable -- does NOT raise.
    """
    slip_username = os.environ.get("SLIP_USERNAME", "")
    slip_password = os.environ.get("SLIP_PASSWORD", "")

    geojson: dict[str, Any] | None = None
    public_url = _build_wfs_url(_SLIP_PUBLIC_WFS)
    geojson = _fetch_geojson(public_url)

    if geojson is None and slip_username:
        logger.info("slip_cadastre_importer: trying authenticated SLIP WFS")
        private_url = _build_wfs_url(_SLIP_PRIVATE_WFS, auth=(slip_username, slip_password))
        geojson = _fetch_geojson(private_url, username=slip_username, password=slip_password)

    if geojson is None:
        logger.warning(
            "slip_cadastre_importer: SLIP WFS is not accessible. "
            "Returning 0 (degraded operation). Set SLIP_USERNAME/SLIP_PASSWORD env vars "
            "or check network connectivity to services.slip.wa.gov.au"
        )
        return 0

    features = geojson.get("features", [])
    if not features:
        logger.warning("slip_cadastre_importer: WFS returned 0 features for LGA_NAME='VINCENT'")
        return 0

    source_crs = _detect_source_crs(geojson)
    if source_crs and "4283" in source_crs:
        logger.info(
            "slip_cadastre_importer: source CRS is GDA94 (%s); reprojecting to EPSG:7844",
            source_crs,
        )

    dataset = SpatialDatasetMetadata(
        dataset_id=_DATASET_ID,
        name="WA Cadastre -- City of Vincent parcels (SLIP)",
        provider=_PROVIDER,
        version="2026",
        licence=_LICENCE,
        licence_status=LicenceStatus.LICENSED,
        source_crs=source_crs or GDA2020_TARGET_CRS,
        approval_status=SourceApprovalStatus.APPROVED,
        source_version_id="slip:wa-cadastre:vincent:2026",
    )
    result = store.import_dataset(dataset)
    if not result.accepted:
        logger.error(
            "slip_cadastre_importer: dataset not accepted: %s", result.reason
        )
        return 0

    count = 0
    for feature in features:
        props = feature.get("properties") or {}
        geom = feature.get("geometry") or {}

        lot_number = (
            props.get("LOT_NUMBER")
            or props.get("lot_number")
            or props.get("CADASTRE_NO")
            or str(count)
        )
        plan_number = props.get("PLAN_NUMBER") or props.get("plan_number") or ""
        lot_plan = f"Lot {lot_number} {plan_number}".strip() if plan_number else f"Lot {lot_number}"
        area_m2 = float(props.get("AREA_METRES2") or props.get("area_m2") or 0.0)

        geom_ewkt = _geom_to_ewkt(geom, source_crs)

        parcel = Parcel(
            parcel_id=f"slip_vincent_{lot_number}_{count}",
            lot_plan=lot_plan,
            local_government="City of Vincent",
            area_m2=area_m2,
            dataset_id=dataset.dataset_id,
        )
        object.__setattr__(parcel, "_geom_ewkt", geom_ewkt or "SRID=7844;MULTIPOLYGON EMPTY")
        store.add_parcel(parcel)
        count += 1

    logger.info("slip_cadastre_importer: imported %d parcels for City of Vincent", count)
    return count
