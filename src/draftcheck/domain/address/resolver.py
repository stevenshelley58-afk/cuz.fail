"""Address resolver orchestration for DraftCheck WA v3.

Converts a free-text address into ``Property`` and ``PropertyFact`` rows via
the PostGIS spatial pipeline:

  free-text address
    -> G-NAF trigram/LIKE lookup  (address_points table)
    -> PostGIS parcel intersection (parcels table, ST_Within)
    -> LGA intersection            (lg_areas table, ST_Intersects)
    -> planning features           (planning_features table, ST_Intersects)
    -> lot_area (ST_Area EPSG:3112), frontage, corner_lot heuristics
    -> upsert Property + PropertyFact rows
    -> ResolverResult

All outputs are advisory.  They are never legal proof of planning compliance.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# EPSG:3112 — GDA94/Geoscience Australia Lambert — used for area in m^2.
# PostGIS ST_Area on EPSG:3112 returns square metres for Australian coordinates.
_AREA_CRS_SRID = 3112


@dataclass
class GnafResult:
    """Result of a G-NAF address lookup."""

    address_point_id: str
    gnaf_pid: str | None
    formatted_address: str
    lat: float
    lon: float
    confidence: float  # 0.0-1.0


@dataclass
class ParcelResult:
    """Parcel row resolved from a coordinate point."""

    parcel_db_id: str  # UUID primary key of parcels row
    cadastre_id: str
    lot_plan: str | None
    local_government: str | None
    area_m2: float
    geom_ewkt: str | None  # raw EWKT for downstream queries


@dataclass
class ZoneFact:
    feature_db_id: str
    layer_type: str
    code: str
    label: str | None
    metadata: dict[str, Any]


@dataclass
class OverlayFact:
    feature_db_id: str
    layer_type: str
    code: str
    label: str | None
    metadata: dict[str, Any]


@dataclass
class ResolverResult:
    """Outcome of ``AddressResolver.resolve``."""

    property_id: str | None
    resolution_status: str
    confidence: float  # 0.0-1.0
    facts_count: int
    warnings: list[str] = field(default_factory=list)
    address: str | None = None
    parcel_id: str | None = None
    local_government: str | None = None
    lot_area_m2: float | None = None
    frontage_m: float | None = None
    corner_lot: bool | None = None
    zone_code: str | None = None
    overlays: list[str] = field(default_factory=list)


class AddressResolver:
    """Orchestrates the address -> property_facts pipeline.

    Uses raw SQLAlchemy ``text()`` queries against a PostGIS-enabled database.
    All geometry is EPSG:7844 (GDA2020) on disk; area calculations use
    ST_Transform to EPSG:3112 (Geoscience Australia Lambert) for m^2.

    Outputs are advisory only.  Never claim legal or certification compliance.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def resolve(
        self,
        raw_address: str,
        project_id: str,
        org_id: str,
        session: Any,
    ) -> ResolverResult:
        """Resolve ``raw_address`` into property facts and persist them.

        Parameters
        ----------
        raw_address:
            Free-text address string supplied by the user.
        project_id:
            UUID string of the project record.
        org_id:
            UUID string of the organisation.
        session:
            An open ``sqlalchemy.ext.asyncio.AsyncSession`` (or sync Session).

        Returns
        -------
        ResolverResult
            Advisory result.  ``resolution_status`` is one of:
            ``"resolved"``, ``"partial"``, ``"no_data"``, ``"not_found"``.
        """
        warnings: list[str] = []

        # Step 1: G-NAF lookup
        gnaf = await self._gnaf_lookup(raw_address, session)
        if gnaf is None:
            return ResolverResult(
                property_id=None,
                resolution_status="no_data",
                confidence=0.0,
                facts_count=0,
                warnings=["address_point_not_found_in_gnaf_table"],
                address=raw_address,
            )

        # Step 2: Parcel from point
        parcel = await self._parcel_from_point(gnaf.lat, gnaf.lon, session)
        if parcel is None:
            warnings.append("parcel_not_found_for_gnaf_point")
            return ResolverResult(
                property_id=None,
                resolution_status="partial",
                confidence=gnaf.confidence * 0.3,
                facts_count=0,
                warnings=warnings,
                address=gnaf.formatted_address,
            )

        # Step 3: LGA
        lga_name = await self._lga_from_point(gnaf.lat, gnaf.lon, session)
        if lga_name is None and parcel.local_government:
            lga_name = parcel.local_government
        if lga_name is None:
            warnings.append("lga_not_resolved")

        # Step 4: Zone facts
        zones = await self._zone_from_parcel(parcel.parcel_db_id, session)
        if not zones:
            warnings.append("zone_not_found_for_parcel")

        # Step 5: Overlay facts
        overlays = await self._overlays_from_parcel(parcel.parcel_db_id, session)

        # Step 6: Lot area (prefer DB value, fallback ST_Area)
        lot_area_m2: float | None = parcel.area_m2 if parcel.area_m2 > 0 else None
        if lot_area_m2 is None:
            lot_area_m2 = await self._area_from_parcel(parcel.parcel_db_id, session)
            if lot_area_m2 is not None:
                warnings.append("lot_area_calculated_from_geometry_not_cadastre_record")

        # Step 7: Frontage heuristic
        frontage_m = await self._frontage_from_parcel(parcel.parcel_db_id, session)
        if frontage_m is None:
            warnings.append("frontage_not_calculable")

        # Step 8: Corner lot heuristic
        corner_lot = await self._corner_lot_from_parcel(parcel.parcel_db_id, session)

        # Step 9: Upsert Property + PropertyFact rows
        property_id = await self._upsert_property(
            org_id=org_id,
            project_id=project_id,
            address=gnaf.formatted_address,
            confidence=gnaf.confidence,
            resolution_status="resolved" if not warnings else "partial",
            parcel_cadastre_id=parcel.cadastre_id,
            local_government=lga_name,
            session=session,
        )

        facts_written = await self._upsert_facts(
            org_id=org_id,
            project_id=project_id,
            property_id=property_id,
            gnaf=gnaf,
            parcel=parcel,
            lga_name=lga_name,
            zones=zones,
            overlays=overlays,
            lot_area_m2=lot_area_m2,
            frontage_m=frontage_m,
            corner_lot=corner_lot,
            session=session,
        )

        zone_code = zones[0].code if zones else None
        overlay_codes = [o.code for o in overlays]

        return ResolverResult(
            property_id=property_id,
            resolution_status="resolved" if not warnings else "partial",
            confidence=gnaf.confidence,
            facts_count=facts_written,
            warnings=warnings,
            address=gnaf.formatted_address,
            parcel_id=parcel.cadastre_id,
            local_government=lga_name,
            lot_area_m2=lot_area_m2,
            frontage_m=frontage_m,
            corner_lot=corner_lot,
            zone_code=zone_code,
            overlays=overlay_codes,
        )

    # ------------------------------------------------------------------
    # Internal steps
    # ------------------------------------------------------------------

    async def _gnaf_lookup(self, address: str, session: Any) -> GnafResult | None:
        """Query address_points using trigram similarity, falling back to LIKE.

        Returns the best match or ``None`` if the table is empty or no match
        is found.
        """
        from sqlalchemy import text

        # First check if the table has any rows at all
        count_result = await _execute(
            session,
            text("SELECT COUNT(*) FROM address_points"),
        )
        row = count_result.fetchone()
        if row is None or row[0] == 0:
            logger.info("_gnaf_lookup: address_points table is empty")
            return None

        # Try trigram similarity (pg_trgm extension)
        try:
            result = await _execute(
                session,
                text(
                    "SELECT id, gnaf_pid, address_text, "
                    "ST_Y(ST_Transform(geom, 4326)) AS lat, "
                    "ST_X(ST_Transform(geom, 4326)) AS lon, "
                    "similarity(address_text, :addr) AS sim "
                    "FROM address_points "
                    "WHERE similarity(address_text, :addr) > 0.3 "
                    "ORDER BY sim DESC "
                    "LIMIT 1"
                ),
                {"addr": address},
            )
            row = result.fetchone()
            if row:
                return GnafResult(
                    address_point_id=str(row[0]),
                    gnaf_pid=row[1],
                    formatted_address=row[2],
                    lat=float(row[3]),
                    lon=float(row[4]),
                    confidence=min(float(row[5]), 1.0),
                )
        except Exception:
            logger.debug("_gnaf_lookup: pg_trgm not available, falling back to LIKE")

        # LIKE fallback
        like_pattern = f"%{address.strip()}%"
        result = await _execute(
            session,
            text(
                "SELECT id, gnaf_pid, address_text, "
                "ST_Y(ST_Transform(geom, 4326)) AS lat, "
                "ST_X(ST_Transform(geom, 4326)) AS lon "
                "FROM address_points "
                "WHERE address_text ILIKE :pat "
                "LIMIT 1"
            ),
            {"pat": like_pattern},
        )
        row = result.fetchone()
        if row is None:
            logger.info("_gnaf_lookup: no match for address %r", address)
            return None
        return GnafResult(
            address_point_id=str(row[0]),
            gnaf_pid=row[1],
            formatted_address=row[2],
            lat=float(row[3]),
            lon=float(row[4]),
            confidence=0.5,  # LIKE match — lower confidence than trigram
        )

    async def _parcel_from_point(
        self, lat: float, lon: float, session: Any
    ) -> ParcelResult | None:
        """ST_Within lookup on the parcels table for the given (lat, lon)."""
        from sqlalchemy import text

        result = await _execute(
            session,
            text(
                "SELECT id, cadastre_id, lot_plan, local_government, area_m2 "
                "FROM parcels "
                "WHERE ST_Within("
                "  ST_SetSRID(ST_Point(:lon, :lat), 7844), "
                "  geom"
                ") "
                "LIMIT 1"
            ),
            {"lat": lat, "lon": lon},
        )
        row = result.fetchone()
        if row is None:
            return None
        return ParcelResult(
            parcel_db_id=str(row[0]),
            cadastre_id=str(row[1]),
            lot_plan=row[2],
            local_government=row[3],
            area_m2=float(row[4]) if row[4] else 0.0,
            geom_ewkt=None,
        )

    async def _lga_from_point(
        self, lat: float, lon: float, session: Any
    ) -> str | None:
        """ST_Intersects lookup on lg_areas for the given point."""
        from sqlalchemy import text

        result = await _execute(
            session,
            text(
                "SELECT name FROM lg_areas "
                "WHERE ST_Intersects("
                "  geom, "
                "  ST_SetSRID(ST_Point(:lon, :lat), 7844)"
                ") "
                "LIMIT 1"
            ),
            {"lat": lat, "lon": lon},
        )
        row = result.fetchone()
        return str(row[0]) if row else None

    async def _zone_from_parcel(
        self, parcel_db_id: str, session: Any
    ) -> list[ZoneFact]:
        """ST_Intersects query on planning_features WHERE layer_type='zone'."""
        from sqlalchemy import text

        result = await _execute(
            session,
            text(
                "SELECT pf.id, pf.layer_type, pf.code, pf.label, pf.metadata_json "
                "FROM planning_features pf "
                "WHERE pf.layer_type = 'zone' "
                "AND ST_Intersects("
                "  pf.geom, "
                "  (SELECT geom FROM parcels WHERE id = :pid)"
                ")"
            ),
            {"pid": parcel_db_id},
        )
        rows = result.fetchall()
        return [
            ZoneFact(
                feature_db_id=str(r[0]),
                layer_type=r[1],
                code=str(r[2]),
                label=r[3],
                metadata=r[4] or {},
            )
            for r in rows
        ]

    async def _overlays_from_parcel(
        self, parcel_db_id: str, session: Any
    ) -> list[OverlayFact]:
        """ST_Intersects on planning_features for overlay/bushfire/heritage."""
        from sqlalchemy import text

        result = await _execute(
            session,
            text(
                "SELECT pf.id, pf.layer_type, pf.code, pf.label, pf.metadata_json "
                "FROM planning_features pf "
                "WHERE pf.layer_type IN ('overlay', 'bushfire', 'heritage', 'special_control') "
                "AND ST_Intersects("
                "  pf.geom, "
                "  (SELECT geom FROM parcels WHERE id = :pid)"
                ")"
            ),
            {"pid": parcel_db_id},
        )
        rows = result.fetchall()
        return [
            OverlayFact(
                feature_db_id=str(r[0]),
                layer_type=r[1],
                code=str(r[2]),
                label=r[3],
                metadata=r[4] or {},
            )
            for r in rows
        ]

    async def _area_from_parcel(
        self, parcel_db_id: str, session: Any
    ) -> float | None:
        """Calculate lot area using ST_Area with EPSG:3112 for m^2."""
        from sqlalchemy import text

        result = await _execute(
            session,
            text(
                "SELECT ST_Area(ST_Transform(geom, :srid)) "
                "FROM parcels WHERE id = :pid"
            ),
            {"pid": parcel_db_id, "srid": _AREA_CRS_SRID},
        )
        row = result.fetchone()
        if row is None or row[0] is None:
            return None
        return float(row[0])

    async def _frontage_from_parcel(
        self, parcel_db_id: str, session: Any
    ) -> float | None:
        """Estimate frontage as the longest exterior ring edge in metres.

        This is a geometric heuristic -- the longest edge of the parcel's
        exterior ring is used as an approximation of the primary street
        frontage.  It does not account for rear lanes or battle-axe lots.
        """
        from sqlalchemy import text

        result = await _execute(
            session,
            text(
                "WITH pts AS ("
                "  SELECT "
                "    ST_PointN(ST_ExteriorRing(ST_Transform("
                "      (CASE WHEN ST_GeometryType(geom) = 'ST_MultiPolygon'"
                "            THEN ST_GeometryN(geom, 1)"
                "            ELSE geom END), :srid)), i) AS p1, "
                "    ST_PointN(ST_ExteriorRing(ST_Transform("
                "      (CASE WHEN ST_GeometryType(geom) = 'ST_MultiPolygon'"
                "            THEN ST_GeometryN(geom, 1)"
                "            ELSE geom END), :srid)), i + 1) AS p2 "
                "  FROM parcels, "
                "    generate_series(1, "
                "      ST_NPoints(ST_ExteriorRing(ST_Transform("
                "        (CASE WHEN ST_GeometryType(geom) = 'ST_MultiPolygon'"
                "              THEN ST_GeometryN(geom, 1)"
                "              ELSE geom END), :srid))) - 1) AS i "
                "  WHERE id = :pid"
                ") "
                "SELECT MAX(ST_Distance(p1, p2)) FROM pts"
            ),
            {"pid": parcel_db_id, "srid": _AREA_CRS_SRID},
        )
        row = result.fetchone()
        if row is None or row[0] is None:
            return None
        return float(row[0])

    async def _corner_lot_from_parcel(
        self, parcel_db_id: str, session: Any
    ) -> bool | None:
        """Corner lot heuristic: parcel exterior ring has 2+ long edges.

        A corner lot typically has two frontages of similar length.  This
        heuristic considers a lot a corner lot if the two longest exterior-ring
        edges are both >= 60% of the longest edge length.

        Returns ``None`` if geometry is not available.
        """
        from sqlalchemy import text

        result = await _execute(
            session,
            text(
                "WITH edges AS ("
                "  SELECT ST_Distance("
                "    ST_Transform(ST_PointN(ST_ExteriorRing("
                "      (CASE WHEN ST_GeometryType(geom) = 'ST_MultiPolygon'"
                "            THEN ST_GeometryN(geom, 1)"
                "            ELSE geom END)), i), :srid),"
                "    ST_Transform(ST_PointN(ST_ExteriorRing("
                "      (CASE WHEN ST_GeometryType(geom) = 'ST_MultiPolygon'"
                "            THEN ST_GeometryN(geom, 1)"
                "            ELSE geom END)), i + 1), :srid)"
                "  ) AS edge_len "
                "  FROM parcels, "
                "    generate_series(1, "
                "      ST_NPoints(ST_ExteriorRing("
                "        (CASE WHEN ST_GeometryType(geom) = 'ST_MultiPolygon'"
                "              THEN ST_GeometryN(geom, 1)"
                "              ELSE geom END))) - 1) AS i "
                "  WHERE id = :pid "
                "  ORDER BY edge_len DESC "
                "  LIMIT 2"
                ") "
                "SELECT "
                "  COUNT(*) AS cnt, "
                "  MAX(edge_len) AS max_len, "
                "  MIN(edge_len) AS second_len "
                "FROM edges"
            ),
            {"pid": parcel_db_id, "srid": _AREA_CRS_SRID},
        )
        row = result.fetchone()
        if row is None or row[0] is None or int(row[0]) < 2:
            return None
        max_len = float(row[1])
        second_len = float(row[2])
        if max_len == 0:
            return None
        # Corner lot if the second-longest edge is >= 60% of the longest
        return (second_len / max_len) >= 0.60

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    async def _upsert_property(
        self,
        *,
        org_id: str,
        project_id: str,
        address: str,
        confidence: float,
        resolution_status: str,
        parcel_cadastre_id: str | None,
        local_government: str | None,
        session: Any,
    ) -> str:
        """Upsert a Property row and return its UUID primary key as a string."""
        from sqlalchemy import text

        try:
            org_uuid = uuid.UUID(org_id)
            project_uuid = uuid.UUID(project_id)
        except (ValueError, AttributeError):
            logger.warning(
                "_upsert_property: org_id %r or project_id %r is not a valid UUID; "
                "using placeholder property_id",
                org_id,
                project_id,
            )
            return str(uuid.uuid4())

        # Check for existing Property row
        result = await _execute(
            session,
            text(
                "SELECT id FROM properties "
                "WHERE org_id = :org_id AND project_id = :project_id "
                "LIMIT 1"
            ),
            {"org_id": str(org_uuid), "project_id": str(project_uuid)},
        )
        row = result.fetchone()
        if row:
            property_id = str(row[0])
            await _execute(
                session,
                text(
                    "UPDATE properties SET "
                    "address_text = :address, "
                    "resolution_status = :status, "
                    "confidence = :confidence, "
                    "resolution_cache_json = :cache "
                    "WHERE id = :prop_id"
                ),
                {
                    "address": address,
                    "status": resolution_status,
                    "confidence": confidence,
                    "cache": {
                        "parcel_id": parcel_cadastre_id,
                        "local_government": local_government,
                    },
                    "prop_id": property_id,
                },
            )
        else:
            property_id = str(uuid.uuid4())
            await _execute(
                session,
                text(
                    "INSERT INTO properties "
                    "(id, org_id, project_id, address_text, resolution_status, "
                    "confidence, target_crs, resolution_cache_json) "
                    "VALUES (:id, :org_id, :project_id, :address, :status, "
                    ":confidence, 'EPSG:7844', :cache)"
                ),
                {
                    "id": property_id,
                    "org_id": str(org_uuid),
                    "project_id": str(project_uuid),
                    "address": address,
                    "status": resolution_status,
                    "confidence": confidence,
                    "cache": {
                        "parcel_id": parcel_cadastre_id,
                        "local_government": local_government,
                    },
                },
            )
        await _commit(session)
        return property_id

    async def _upsert_facts(
        self,
        *,
        org_id: str,
        project_id: str,
        property_id: str,
        gnaf: GnafResult,
        parcel: ParcelResult,
        lga_name: str | None,
        zones: list[ZoneFact],
        overlays: list[OverlayFact],
        lot_area_m2: float | None,
        frontage_m: float | None,
        corner_lot: bool | None,
        session: Any,
    ) -> int:
        """Delete existing facts for this (org_id, project_id) then insert new ones."""
        from sqlalchemy import text

        try:
            org_uuid = uuid.UUID(org_id)
            project_uuid = uuid.UUID(project_id)
        except (ValueError, AttributeError):
            return 0

        await _execute(
            session,
            text(
                "DELETE FROM property_facts "
                "WHERE org_id = :org_id AND project_id = :project_id"
            ),
            {"org_id": str(org_uuid), "project_id": str(project_uuid)},
        )

        facts: list[dict] = []

        facts.append(
            _make_fact(
                org_uuid, project_uuid, property_id,
                fact_type="address",
                value={"formatted_address": gnaf.formatted_address, "gnaf_pid": gnaf.gnaf_pid},
                confidence=gnaf.confidence,
                method="gnaf_trigram_or_like_match",
            )
        )
        facts.append(
            _make_fact(
                org_uuid, project_uuid, property_id,
                fact_type="parcel",
                value={
                    "cadastre_id": parcel.cadastre_id,
                    "lot_plan": parcel.lot_plan,
                },
                confidence=0.9,
                method="postgis_st_within",
            )
        )
        if lga_name:
            facts.append(
                _make_fact(
                    org_uuid, project_uuid, property_id,
                    fact_type="local_government",
                    value={"name": lga_name},
                    confidence=0.9,
                    method="postgis_st_intersects_lga",
                )
            )
        if lot_area_m2 is not None:
            facts.append(
                _make_fact(
                    org_uuid, project_uuid, property_id,
                    fact_type="lot_area_m2",
                    value={"value": lot_area_m2, "unit": "m2"},
                    confidence=0.85,
                    method="postgis_st_area_epsg3112",
                )
            )
        if frontage_m is not None:
            facts.append(
                _make_fact(
                    org_uuid, project_uuid, property_id,
                    fact_type="frontage",
                    value={"value": round(frontage_m, 2), "unit": "m", "method": "longest_edge_heuristic"},
                    confidence=0.6,
                    method="longest_exterior_edge_heuristic",
                )
            )
        if corner_lot is not None:
            facts.append(
                _make_fact(
                    org_uuid, project_uuid, property_id,
                    fact_type="corner_lot",
                    value={"value": corner_lot, "method": "two_long_edges_heuristic"},
                    confidence=0.6,
                    method="two_long_edges_heuristic",
                )
            )
        for zone in zones:
            facts.append(
                _make_fact(
                    org_uuid, project_uuid, property_id,
                    fact_type="zone",
                    value={
                        "code": zone.code,
                        "label": zone.label,
                        "layer_type": zone.layer_type,
                        "metadata": zone.metadata,
                    },
                    confidence=0.85,
                    method="postgis_st_intersects_zone",
                )
            )
        for overlay in overlays:
            facts.append(
                _make_fact(
                    org_uuid, project_uuid, property_id,
                    fact_type=overlay.layer_type,
                    value={
                        "code": overlay.code,
                        "label": overlay.label,
                        "layer_type": overlay.layer_type,
                        "metadata": overlay.metadata,
                    },
                    confidence=0.85,
                    method="postgis_st_intersects_overlay",
                )
            )

        for fact in facts:
            await _execute(
                session,
                text(
                    "INSERT INTO property_facts "
                    "(id, org_id, project_id, property_id, fact_type, value_json, "
                    "confidence, method, provenance_json, review_status) "
                    "VALUES (:id, :org_id, :project_id, :property_id, :fact_type, "
                    ":value_json, :confidence, :method, :provenance_json, :review_status)"
                ),
                fact,
            )
        await _commit(session)
        return len(facts)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _make_fact(
    org_uuid: uuid.UUID,
    project_uuid: uuid.UUID,
    property_id: str,
    *,
    fact_type: str,
    value: dict,
    confidence: float,
    method: str,
) -> dict:
    import json as _json
    return {
        "id": str(uuid.uuid4()),
        "org_id": str(org_uuid),
        "project_id": str(project_uuid),
        "property_id": property_id,
        "fact_type": fact_type,
        "value_json": _json.dumps(value),
        "confidence": confidence,
        "method": method,
        "provenance_json": _json.dumps({"method": method, "advisory_only": True}),
        "review_status": "pending_review",
    }


async def _execute(session: Any, stmt: Any, params: dict | None = None):
    """Execute a statement on either a sync or async SQLAlchemy session."""
    if hasattr(session, "execute"):
        result = session.execute(stmt, params or {})
        # For async sessions the result is a coroutine
        if hasattr(result, "__await__"):
            result = await result
        return result
    raise TypeError(f"Unsupported session type: {type(session)}")


async def _commit(session: Any) -> None:
    """Commit a sync or async session."""
    result = session.commit()
    if hasattr(result, "__await__"):
        await result
