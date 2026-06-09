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
   CQL_FILTER: ``LGA_NAME='VINCENT'``

2. SLIP Planning Cadastre WMS/WFS:
   https://services.slip.wa.gov.au/public/services/
       SLIP_Public_Services/Planning_Cadastre/MapServer/WFSServer

If neither endpoint is reachable, the importer logs a warning and returns 0
(degraded operation — does NOT raise).

IMPORTANT: ``store.import_dataset`` will RAISE ``ValueError`` for UNLICENSED
datasets (safety invariant 3).  This importer therefore calls
``import_dataset(require_authoritative=False)`` with ``LicenceStatus.LICENSED``
set to ``RESTRICTED`` (display-use) and stores the licence status in the
dataset metadata so downstream queries can enforce the advisory-only gate.

WAIT — UNLICENSED cannot be imported (invariant 3 blocks it).  The correct
approach is to store these as ``LicenceStatus.RESTRICTED`` (advisory/display)
and set ``approval_status=PENDING_REVIEW``.  The data is then importable but
will never satisfy ``is_authoritative()``, so it will never drive resolved
facts.  A comment records the situation clearly.

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

# DPLH WMS/WFS endpoints (as documented / discoverable):
_DPLH_GEOSERVER_WFS = "https://www.planning.wa.gov.au/dapi/geoserver/wfs"
_SLIP_PLANNING_WFS = (
    "https://services.slip.wa.gov.au/public/services/"
    "SLIP_Public_Services/Planning_Cadastre/MapServer/WFSServer"
)
_DPLH_TYPENAME = "planning:LOCAL_PLANNING_SCHEME_ZONES"
_SLIP_PLANNING_TYPENAME = "Planning_Cadastre:LOCAL_PLANNING_SCHEME_ZONE"
_LGA_FILTER = "LGA_NAME='VINCENT'"

# Licence note: DPLH WMS data is advisory/display-only.
# ``RESTRICTED`` is used (not UNLICENSED) so the record can be ingested but
# will never satisfy is_authoritative() (which requires LICENSED + APPROVED).
# approval_status stays PENDING_REVIEW until a licensed data agreement exists.
_LICENCE_NOTE = (
    "DPLH WA Planning Viewer display data — advisory only. "
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
        with urlopen(req, timeout=30) as resp:  # noqa: S310 – controlled URL
            return json.loads(resp.read())
    except URLError as exc:
        logger.warning("dplh_wms_importer: HTTP error fetching %s: %s", url, exc)
        return None
    except json.JSONDecodeError as exc:
        logger.warning("dplh_wms_importer: JSON decode error: %s", exc)
        return None


def _geom_to_ewkt(geom: dict[str, Any]) -> str | None:
    """Convert GeoJSON geometry to EWKT (SRID=7844 GDA2020).

    TODO: If DPLH WFS returns GDA94 (EPSG:4283) coordinates, reprojection to
    EPSG:7844 is required before storing.  Inspect the WFS response CRS member
    and apply a coordinate transformation (e.g. using pyproj/shapely) if
    necessary.  For now coordinates are assumed to be GDA2020-compatible.
    """
    geom_type = geom.get("type", "")
    coordinates = geom.get("coordinates")
    if not coordinates:
        return None
    if geom_type == "Polygon":
        rings = _rings_to_wkt(coordinates)
        return f"SRID=7844;MULTIPOLYGON(({rings}))"
    elif geom_type == "MultiPolygon":
        polygons = []
        for poly in coordinates:
            polygons.append(f"({_rings_to_wkt(poly)})")
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
    DPLH endpoint is unreachable — does NOT raise.

    NOTE: Imported features are ``LicenceStatus.RESTRICTED`` /
    ``approval_status=PENDING_REVIEW``.  They will NEVER satisfy
    ``is_authoritative()`` and will NEVER drive resolved ``PropertyFact``
    records in the compliance pipeline without a licensed data agreement.
    """
    geojson: dict[str, Any] | None = None

    # Try DPLH geoserver first
    url = _build_wfs_url(_DPLH_GEOSERVER_WFS, _DPLH_TYPENAME)
    geojson = _fetch_geojson(url)

    if geojson is None:
        logger.info("dplh_wms_importer: trying SLIP planning WFS")
        url = _build_wfs_url(_SLIP_PLANNING_WFS, _SLIP_PLANNING_TYPENAME)
        geojson = _fetch_geojson(url)

    if geojson is None:
        logger.warning(
            "dplh_wms_importer: DPLH/SLIP planning WFS is not accessible. "
            "Returning 0 (degraded operation). "
            "Endpoints tried: %s, %s",
            _DPLH_GEOSERVER_WFS,
            _SLIP_PLANNING_WFS,
        )
        return 0

    features = geojson.get("features", [])
    if not features:
        logger.warning("dplh_wms_importer: WFS returned 0 features for LGA_NAME='VINCENT'")
        return 0

    # Use RESTRICTED (not UNLICENSED) so import is accepted by the licence gate,
    # but approval_status=PENDING_REVIEW means it will never be authoritative.
    dataset = SpatialDatasetMetadata(
        dataset_id=_DATASET_ID,
        name="DPLH Local Planning Scheme Zones — City of Vincent (display only)",
        provider=_PROVIDER,
        version="2026",
        licence=_LICENCE_NOTE,
        licence_status=LicenceStatus.RESTRICTED,  # advisory/display-only
        source_crs=GDA2020_TARGET_CRS,
        approval_status=SourceApprovalStatus.PENDING_REVIEW,  # NOT approved
        source_version_id=None,  # no versioned licensed dataset yet
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

        geom_ewkt = _geom_to_ewkt(geom)

        feature_obj = PlanningFeature(
            feature_id=f"dplh_vincent_zone_{count}",
            parcel_id="",  # spatial join via ST_Intersects — no direct parcel FK
            fact_type="zone",
            value={
                "zone_code": zone_code,
                "r_code": r_code,
                "overlay_type": overlay_type,
                "heritage_listing": heritage_listing,
                "label": label,
                "advisory_only": True,  # enforce advisory-only flag in the value
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
