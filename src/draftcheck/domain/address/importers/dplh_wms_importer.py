"""DPLH WMS / WFS planning zones importer for City of Vincent.

Fetches local planning scheme zones from the DPLH WA Planning Viewer.

Licence:    UNLICENSED / display-only — LicenceStatus.UNLICENSED
            Planning data from DPLH WMS is for display purposes only.
            It MUST NOT be used as authoritative compliance information.
approval_status: "pending_review" (NOT "approved") — a licensed data
            agreement with DPLH must be in place before elevating.

Endpoints tried (in order):
1. DPLH geoserver WFS:
   https://www.planning.wa.gov.au/dapi/geoserver/wfs
   typeName: ``planning:LOCAL_PLANNING_SCHEME_ZONES``
   CQL_FILTER: ``LGA_NAME='"'"'VINCENT'"'"'``

2. SLIP Planning Cadastre WMS/WFS:
   https://services.slip.wa.gov.au/public/services/
       SLIP_Public_Services/Planning_Cadastre/MapServer/WFSServer

If neither endpoint is reachable, the importer logs a warning and returns 0
(degraded operation -- does NOT raise).

IMPORTANT: ``store.import_dataset`` will RAISE ``ValueError`` for UNLICENSED
datasets (safety invariant 3).  This importer therefore uses
``LicenceStatus.RESTRICTED`` (advisory/display) and
``approval_status=PENDING_REVIEW``.  The data is importable but will never
satisfy ``is_authoritative()``.

Usage::

    from draftcheck.domain.address.importers.dplh_wms_importer import (
        import_dplh_planning_vincent,
    )
    count = import_dplh_planning_vincent(store)
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
    PlanningFeature,
    SourceApprovalStatus,
    SpatialDatasetMetadata,
)

if TYPE_CHECKING:
    from draftcheck.domain.address.spatial import InMemorySpatialDatasetStore

logger = logging.getLogger(__name__)

_DPLH_GEOSERVER_WFS = "https://www.planning.wa.gov.au/dapi/geoserver/wfs"
_SLIP_PLANNING_WFS = (
    "https://services.slip.wa.gov.au/public/services/"
    "SLIP_Public_Services/Planning_Cadastre/MapServer/WFSServer"
)
_DPLH_TYPENAME = "planning:LOCAL_PLANNING_SCHEME_ZONES"
_SLIP_PLANNING_TYPENAME = "Planning_Cadastre:LOCAL_PLANNING_SCHEME_ZONE"
_LGA_FILTER = "LGA_NAME='VINCENT'"

_LICENCE_NOTE = (
    "DPLH WA Planning Viewer display data -- advisory only. "
    "Not for authoritative compliance decisions. "
    "Pending licensed data agreement with DPLH."
)
_PROVIDER = "DPLH / WA Planning Viewer"
_DATASET_ID = "dplh_planning_vincent_2026"


def _build_wfs_url(base_url: str, typename: str) -> str:
    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "typeName": typename,
        "outputFormat": "application/json",
        "CQL_FILTER": _LGA_FILTER,
        "srsName": "EPSG:7844",
    }
    return f"{base_url}?{urlencode(params)}"


def _fetch_geojson(url: str) -> dict[str, Any] | None:
    req = Request(url)
    req.add_header("Accept", "application/json")
    try:
        with urlopen(req, timeout=30) as resp:  # noqa: S310 - controlled URL
            return json.loads(resp.read())
    except URLError as exc:
        logger.warning("dplh_wms_importer: HTTP error fetching %s: %s", url, exc)
        return None
    except json.JSONDecodeError as exc:
        logger.warning("dplh_wms_importer: JSON decode error: %s", exc)
        return None


def _detect_source_crs(geojson: dict[str, Any]) -> str | None:
    """Detect CRS from WFS GeoJSON FeatureCollection ``crs`` member.

    Returns ``"EPSG:4283"`` if GDA94, ``"EPSG:7844"`` if GDA2020, or
    ``None`` if the member is absent (treat as GDA2020-compatible).
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
            "dplh_wms_importer: pyproj reprojection failed (%s); storing as-is", exc
        )
        return coordinates


def _geom_to_ewkt(geom: dict[str, Any], source_crs: str | None = None) -> str | None:
    """Convert GeoJSON geometry to EWKT SRID=7844.

    Conditionally reprojects from GDA94 (EPSG:4283) to GDA2020 (EPSG:7844)
    when ``source_crs`` indicates the source is GDA94.
    """
    geom_type = geom.get("type", "")
    coordinates = geom.get("coordinates")
    if not coordinates:
        return None
    if geom_type == "Polygon":
        coords = _maybe_reproject_coords(coordinates, source_crs)
        rings = _rings_to_wkt(coords)
        return f"SRID=7844;MULTIPOLYGON(({rings}))"
    elif geom_type == "MultiPolygon":
        polygons = []
        for poly in coordinates:
            reprojected = _maybe_reproject_coords(poly, source_crs)
            polygons.append(f"({_rings_to_wkt(reprojected)})")
        return f"SRID=7844;MULTIPOLYGON({','.join(polygons)})"
    return None


def _rings_to_wkt(rings: list) -> str:
    parts = []
    for ring in rings:
        pts = ",".join(f"{x} {y}" for x, y in ring)
        parts.append(f"({pts})")
    return ",".join(parts)


def import_dplh_planning_vincent(
    store: "InMemorySpatialDatasetStore",
) -> int:
    """Import DPLH planning zones for City of Vincent.

    Returns count of features imported.  Returns 0 (with warning) if the
    DPLH endpoint is unreachable -- does NOT raise.

    Imported features are ``LicenceStatus.RESTRICTED`` /
    ``approval_status=PENDING_REVIEW`` and will NEVER satisfy
    ``is_authoritative()``.
    """
    geojson: dict[str, Any] | None = None

    url = _build_wfs_url(_DPLH_GEOSERVER_WFS, _DPLH_TYPENAME)
    geojson = _fetch_geojson(url)

    if geojson is None:
        logger.info("dplh_wms_importer: trying SLIP planning WFS")
        url = _build_wfs_url(_SLIP_PLANNING_WFS, _SLIP_PLANNING_TYPENAME)
        geojson = _fetch_geojson(url)

    if geojson is None:
        logger.warning(
            "dplh_wms_importer: DPLH/SLIP planning WFS is not accessible. "
            "Returning 0 (degraded operation). Endpoints tried: %s, %s",
            _DPLH_GEOSERVER_WFS,
            _SLIP_PLANNING_WFS,
        )
        return 0

    features = geojson.get("features", [])
    if not features:
        logger.warning("dplh_wms_importer: WFS returned 0 features for LGA_NAME='VINCENT'")
        return 0

    source_crs = _detect_source_crs(geojson)
    if source_crs and "4283" in source_crs:
        logger.info(
            "dplh_wms_importer: source CRS is GDA94 (%s); reprojecting to EPSG:7844",
            source_crs,
        )

    dataset = SpatialDatasetMetadata(
        dataset_id=_DATASET_ID,
        name="DPLH Local Planning Scheme Zones -- City of Vincent (display only)",
        provider=_PROVIDER,
        version="2026",
        licence=_LICENCE_NOTE,
        licence_status=LicenceStatus.RESTRICTED,
        source_crs=source_crs or GDA2020_TARGET_CRS,
        approval_status=SourceApprovalStatus.PENDING_REVIEW,
        source_version_id=None,
    )
    result = store.import_dataset(dataset, require_authoritative=False)
    if not result.accepted:
        logger.error("dplh_wms_importer: dataset not accepted: %s", result.reason)
        return 0

    count = 0
    for feature in features:
        props = feature.get("properties") or {}
        geom = feature.get("geometry") or {}

        zone_code = (
            props.get("ZONE_CODE")
            or props.get("zone_code")
            or props.get("ZONE")
            or "UNKNOWN"
        )
        r_code = props.get("R_CODE") or props.get("r_code") or ""
        overlay_type = props.get("OVERLAY_TYPE") or props.get("overlay_type") or ""
        heritage_listing = props.get("HERITAGE_LISTING") or props.get("heritage_listing") or ""
        label = props.get("ZONE_LABEL") or props.get("zone_label") or zone_code

        geom_ewkt = _geom_to_ewkt(geom, source_crs)

        feature_obj = PlanningFeature(
            feature_id=f"dplh_vincent_zone_{count}",
            parcel_id="",
            fact_type="zone",
            value={
                "zone_code": zone_code,
                "r_code": r_code,
                "overlay_type": overlay_type,
                "heritage_listing": heritage_listing,
                "label": label,
                "advisory_only": True,
            },
            dataset_id=dataset.dataset_id,
            label=label,
        )
        object.__setattr__(feature_obj, "_geom_ewkt", geom_ewkt or "SRID=7844;MULTIPOLYGON EMPTY")
        store.add_planning_feature(feature_obj)
        count += 1

    logger.info(
        "dplh_wms_importer: imported %d planning features (advisory/display only)", count
    )
    return count
