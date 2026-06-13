"""WP-G: synthesise engine-consumable PropertyFact rows from spatial data.

The compliance engine (``draftcheck.checks.engine.ComplianceEngine``) only reads
``PropertyFact`` rows whose ``review_status == 'confirmed'``.  The async
resolve-address path writes facts as ``pending_review`` / ``accepted``, so those
synthesised facts never reach the engine.  This module closes that gap: for a
project whose ``properties`` row already resolves to a parcel, it writes a fresh
set of ``confirmed`` measurement facts the engine can consume directly.

Design rules (locked by the product spec):

* **Idempotent** — every run first deletes the project's existing
  ``method='spatial_derived'`` facts, then inserts a fresh set.  Running twice
  yields the same fact set, never duplicates.
* **No fabricated measurements** — lot width/depth are emitted ONLY when they are
  deterministically computable from the parcel geometry via PostGIS.  When the
  backing store cannot compute them (e.g. SQLite in tests, or a NULL result),
  they are omitted entirely.  Absent/ambiguous measurement => missing info.
* **Advisory only** — every fact carries
  ``provenance_json={'method': 'spatial_derived', 'advisory_only': True}``.
* **Schema is owned by Alembic** — this module never creates tables or columns.

The function uses the same synchronous :class:`sqlalchemy.orm.Session` the engine
uses, and operates purely through the ORM models plus one guarded raw-SQL probe
for the oriented bounding box.
"""

from __future__ import annotations

import logging
import math
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from draftcheck.db.models import (
    Parcel,
    PlanningFeature,
    Property,
    PropertyFact,
)

logger = logging.getLogger(__name__)

SYNTH_METHOD = "spatial_derived"
SYNTH_CONFIDENCE = 0.9
# Projected CRS used for planar bbox dimensions (matches the resolver's
# ``postgis_st_area_epsg3112`` convention: GDA94 / Geoscience Australia Lambert).
_BBOX_SRID = 3112

# Planning layer types treated as overlays (bushfire / heritage / etc.).  Zone
# and r_code are handled explicitly; anything else intersecting the parcel that
# carries a code is surfaced as an overlay presence fact.
_NON_OVERLAY_LAYERS = {"zone", "r_code", "rcode", "lga", "local_government"}


def _provenance(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    base: dict[str, Any] = {"method": SYNTH_METHOD, "advisory_only": True}
    if extra:
        base.update(extra)
    return base


def _finite_positive(value: Any) -> float | None:
    """Return ``value`` as a positive finite float, or ``None`` if unusable."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out) or out <= 0:
        return None
    return out


def _bbox_dimensions(session: Session, parcel_id: UUID) -> tuple[float, float] | None:
    """Return planar ``(width_m, depth_m)`` of the parcel's bbox, or ``None``.

    Uses PostGIS to project the geometry to a planar CRS and measure the axis
    extents of its envelope.  Returns ``None`` (so the caller omits the facts)
    whenever the backing store is not PostGIS or the values are not finite,
    positive numbers — never guesses.
    """
    try:
        row = session.execute(
            text(
                """
                SELECT
                    ST_XMax(env) - ST_XMin(env) AS width_m,
                    ST_YMax(env) - ST_YMin(env) AS depth_m
                FROM (
                    SELECT ST_Envelope(ST_Transform(geom, :srid)) AS env
                    FROM parcels
                    WHERE id = :pid
                ) AS bbox
                """
            ),
            {"srid": _BBOX_SRID, "pid": str(parcel_id)},
        ).first()
    except Exception as exc:  # noqa: BLE001 - non-PostGIS store / missing func
        logger.debug("bbox dimensions unavailable for parcel %s: %s", parcel_id, exc)
        return None

    if row is None:
        return None
    width = _finite_positive(row[0])
    depth = _finite_positive(row[1])
    if width is None or depth is None:
        return None
    return (round(width, 2), round(depth, 2))


def _extract_r_code(feature: PlanningFeature) -> tuple[str, str] | None:
    """Return ``(code, label)`` for an r_code, preferring stamped metadata."""
    metadata = feature.metadata_json if isinstance(feature.metadata_json, dict) else {}
    code = metadata.get("r_code") or feature.code
    if not code:
        return None
    label = feature.label or str(code)
    return (str(code), str(label))


def synth_property_facts(
    session: Session,
    *,
    org_id: str,
    project_id: str,
) -> dict[str, Any]:
    """Synthesise confirmed spatial PropertyFacts for a resolved project.

    Parameters
    ----------
    session:
        Open synchronous SQLAlchemy session (same type the engine uses).  The
        caller owns the transaction; this function flushes but does NOT commit.
    org_id, project_id:
        UUID strings.

    Returns
    -------
    dict
        ``{"written": int, "fact_types": [...]}``.  ``written == 0`` when the
        project has no resolved parcel (no-op).
    """
    try:
        org_uuid = UUID(str(org_id))
        project_uuid = UUID(str(project_id))
    except (ValueError, AttributeError, TypeError):
        return {"written": 0, "fact_types": []}

    # ------------------------------------------------------------------
    # Idempotency: clear this project's prior spatial_derived facts first.
    # ------------------------------------------------------------------
    session.query(PropertyFact).filter(
        PropertyFact.project_id == project_uuid,
        PropertyFact.method == SYNTH_METHOD,
    ).delete(synchronize_session=False)

    # ------------------------------------------------------------------
    # Resolve the property -> parcel.  No parcel => no-op.
    # ------------------------------------------------------------------
    prop: Property | None = (
        session.query(Property)
        .filter(
            Property.org_id == org_uuid,
            Property.project_id == project_uuid,
        )
        .one_or_none()
    )
    if prop is None or prop.parcel_id is None:
        session.flush()
        return {"written": 0, "fact_types": []}

    parcel: Parcel | None = session.get(Parcel, prop.parcel_id)
    if parcel is None:
        session.flush()
        return {"written": 0, "fact_types": []}

    spatial_dataset_id = parcel.spatial_dataset_id
    new_facts: list[PropertyFact] = []

    def _add(
        fact_type: str,
        value: dict[str, Any],
        *,
        planning_feature_id: UUID | None = None,
        provenance_extra: dict[str, Any] | None = None,
    ) -> None:
        new_facts.append(
            PropertyFact(
                org_id=org_uuid,
                project_id=project_uuid,
                property_id=prop.id,
                fact_type=fact_type,
                value_json=value,
                confidence=SYNTH_CONFIDENCE,
                method=SYNTH_METHOD,
                provenance_json=_provenance(provenance_extra),
                spatial_dataset_id=spatial_dataset_id,
                parcel_id=parcel.id,
                planning_feature_id=planning_feature_id,
                review_status="confirmed",
            )
        )

    # ------------------------------------------------------------------
    # lot_area_m2 (only when a positive area is stored on the parcel).
    # ------------------------------------------------------------------
    area = _finite_positive(parcel.area_m2)
    if area is not None:
        _add("lot_area_m2", {"value": round(area, 2), "unit": "m2"})

    # ------------------------------------------------------------------
    # lot_width_m / lot_depth_m — ONLY if deterministically computable.
    # ------------------------------------------------------------------
    dims = _bbox_dimensions(session, parcel.id)
    if dims is not None:
        width_m, depth_m = dims
        _add(
            "lot_width_m",
            {"value": width_m, "unit": "m"},
            provenance_extra={"derivation": "oriented_bbox_epsg3112"},
        )
        _add(
            "lot_depth_m",
            {"value": depth_m, "unit": "m"},
            provenance_extra={"derivation": "oriented_bbox_epsg3112"},
        )

    # ------------------------------------------------------------------
    # local_government from the parcel.
    # ------------------------------------------------------------------
    if parcel.local_government:
        _add("local_government", {"name": str(parcel.local_government)})

    # ------------------------------------------------------------------
    # Planning features intersecting the parcel: zone, r_code, overlays.
    # ------------------------------------------------------------------
    features = _intersecting_features(session, parcel.id, spatial_dataset_id)

    zone_done = False
    rcode_done = False
    for feature in features:
        layer = (feature.layer_type or "").strip().lower()
        metadata = feature.metadata_json if isinstance(feature.metadata_json, dict) else {}

        if layer == "zone" and not zone_done:
            value: dict[str, Any] = {}
            if feature.code:
                value["code"] = str(feature.code)
            if feature.label:
                value["name"] = str(feature.label)
            if value:
                _add("zone", value, planning_feature_id=feature.id)
                zone_done = True
            # A zone feature may also carry a stamped r_code.
            if not rcode_done:
                rc = _extract_r_code(feature)
                if rc is not None:
                    code, label = rc
                    _add("r_code", {"code": code, "label": label}, planning_feature_id=feature.id)
                    rcode_done = True
            continue

        if layer in {"r_code", "rcode"} and not rcode_done:
            rc = _extract_r_code(feature)
            if rc is not None:
                code, label = rc
                _add("r_code", {"code": code, "label": label}, planning_feature_id=feature.id)
                rcode_done = True
            continue

        if layer not in _NON_OVERLAY_LAYERS:
            # Overlay presence fact (bushfire / heritage / etc.).
            overlay_value: dict[str, Any] = {"present": True}
            code = metadata.get("code") or feature.code
            if code:
                overlay_value["code"] = str(code)
            if feature.label:
                overlay_value["label"] = str(feature.label)
            _add(feature.layer_type, overlay_value, planning_feature_id=feature.id)

    for fact in new_facts:
        session.add(fact)
    session.flush()

    fact_types = sorted({f.fact_type for f in new_facts})
    return {"written": len(new_facts), "fact_types": fact_types}


def _intersecting_features(
    session: Session,
    parcel_id: UUID,
    spatial_dataset_id: UUID | None,
) -> list[PlanningFeature]:
    """Planning features whose geometry intersects the parcel geometry.

    Tries a PostGIS ``ST_Intersects`` spatial join first.  If that is
    unavailable (non-PostGIS store), returns an empty list rather than guessing
    — measurement/overlay facts are simply omitted in that case.
    """
    try:
        rows = session.execute(
            text(
                """
                SELECT pf.id
                FROM planning_features pf
                JOIN parcels p ON p.id = :pid
                WHERE ST_Intersects(pf.geom, p.geom)
                """
            ),
            {"pid": str(parcel_id)},
        ).all()
    except Exception as exc:  # noqa: BLE001 - non-PostGIS store / missing func
        logger.debug("planning-feature intersection unavailable for parcel %s: %s", parcel_id, exc)
        return []

    ids = [r[0] for r in rows]
    if not ids:
        return []
    return (
        session.query(PlanningFeature)
        .filter(PlanningFeature.id.in_(ids))
        .order_by(PlanningFeature.layer_type, PlanningFeature.id)
        .all()
    )
