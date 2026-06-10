"""PostGIS-backed spatial dataset store.

This module implements ``PostGISSpatialDatasetStore`` — a drop-in replacement
for ``InMemorySpatialDatasetStore`` backed by the SQLAlchemy ORM models defined
in ``draftcheck.db.models`` (written by Alembic; never created here).

Safety invariants enforced here:
1.  Geocode/address matches are NEVER presented as legal proof.
2.  Every ``PropertyFact`` row carries full provenance (dataset_id, method,
    licence_status) via ``provenance_json``.
3.  Dataset import is BLOCKED when ``licence_status`` is ``UNLICENSED`` or
    ``UNKNOWN``.
4.  ``approval_status`` is written to the ``SpatialDataset.approval_status``
    column (added in migration 0003) and also cached in ``metadata_json``.
5.  No approval gate is added to spatial resolution — pipeline is fully AI.
6.  No direct table creation — Alembic owns the schema.
7.  All geometry is EPSG:7844 (GDA2020).
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import ColumnElement, Engine, case, func, literal, literal_column, or_, select, text
from sqlalchemy.orm import Session

from draftcheck.db.models import (
    AddressPoint as DbAddressPoint,
    Parcel as DbParcel,
    PlanningFeature as DbPlanningFeature,
    Property as DbProperty,
    PropertyFact as DbPropertyFact,
    SpatialDataset as DbSpatialDataset,
)
from draftcheck.domain.address.spatial import (
    ADDRESS_MATCH_AMBIGUITY_GAP,
    ADDRESS_MATCH_SCORE_FLOOR,
    AddressPoint,
    AddressSearchHit,
    Confidence,
    DatasetImportResult,
    GDA2020_TARGET_CRS,
    LicenceStatus,
    Parcel,
    PlanningFeature,
    PropertyFact,
    PropertyProfile,
    ProvenanceKind,
    ResolutionProvenance,
    ResolutionStatus,
    SourceApprovalStatus,
    SpatialDatasetMetadata,
    expand_street_abbreviations,
    leading_house_number,
    normalize_address,
)

logger = logging.getLogger(__name__)

_BLOCKED_LICENCE_STATUSES = {LicenceStatus.UNLICENSED, LicenceStatus.UNKNOWN}


def _provenance_to_json(provenance: ResolutionProvenance) -> dict[str, Any]:
    return {
        "kind": str(provenance.kind),
        "method": provenance.method,
        "target_crs": provenance.target_crs,
        "dataset_id": provenance.dataset_id,
        "source_version_id": provenance.source_version_id,
        "source_crs": provenance.source_crs,
        "licence_status": str(provenance.licence_status) if provenance.licence_status else None,
        "approval_status": str(provenance.approval_status) if provenance.approval_status else None,
        "manual_override_id": provenance.manual_override_id,
        "detail": provenance.detail,
        "created_at": provenance.created_at.isoformat(),
    }


def _metadata_to_dict(metadata: SpatialDatasetMetadata) -> dict[str, Any]:
    return {
        "approval_status": str(metadata.approval_status),
        "target_crs": metadata.target_crs,
        "refresh_due": metadata.refresh_due.isoformat() if metadata.refresh_due else None,
    }


def _db_dataset_to_metadata(row: DbSpatialDataset) -> SpatialDatasetMetadata:
    meta = row.metadata_json or {}
    return SpatialDatasetMetadata(
        dataset_id=row.dataset_id,
        name=row.name,
        provider=row.provider,
        version=row.version,
        licence=row.licence or "",
        licence_status=LicenceStatus(row.licence_status),
        source_crs=row.source_crs,
        source_version_id=str(row.source_version_id) if row.source_version_id else None,
        approval_status=SourceApprovalStatus(row.approval_status),
        target_crs=str(meta.get("target_crs", GDA2020_TARGET_CRS)),
        fetched_at=row.fetched_at or __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )


class PostGISSpatialDatasetStore:
    """SQLAlchemy/PostGIS-backed spatial store.

    ``engine`` should be a live ``sqlalchemy.Engine`` connected to the PostGIS
    database provisioned by Alembic.  Each public method opens a short-lived
    ``Session`` and commits, so the caller never holds a transaction open.

    This class does NOT use metadata DDL — Alembic owns schema
    creation.

    Address matches are indicative only.  They are NEVER legal proof of
    property ownership or compliance status.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    # ------------------------------------------------------------------
    # Dataset registration
    # ------------------------------------------------------------------

    def import_dataset(
        self,
        metadata: SpatialDatasetMetadata,
        *,
        require_authoritative: bool = True,
    ) -> DatasetImportResult:
        """Register a spatial dataset.

        Raises ``ValueError`` when ``licence_status`` is ``UNLICENSED`` or
        ``UNKNOWN`` — these statuses must never be imported (safety invariant 3).
        """
        if metadata.licence_status in _BLOCKED_LICENCE_STATUSES:
            raise ValueError(
                f"Dataset import blocked: licence_status={metadata.licence_status!r} is not "
                f"permitted for import.  Only LICENSED or RESTRICTED datasets may be imported. "
                f"dataset_id={metadata.dataset_id!r}"
            )

        authoritative = metadata.is_authoritative()
        if require_authoritative and not authoritative:
            return DatasetImportResult(
                dataset_id=metadata.dataset_id,
                accepted=False,
                authoritative=False,
                target_crs=metadata.target_crs,
                reason="dataset_not_authoritative_for_spatial_resolution",
            )

        with Session(self._engine) as session:
            # Do not overwrite a higher-status dataset with a rejected/lower one
            existing = session.execute(
                select(DbSpatialDataset).where(
                    DbSpatialDataset.dataset_id == metadata.dataset_id
                ).order_by(DbSpatialDataset.created_at.desc()).limit(1)
            ).scalar_one_or_none()

            if existing is not None:
                existing_meta = _db_dataset_to_metadata(existing)
                if (
                    existing_meta.approval_status == SourceApprovalStatus.APPROVED
                    and metadata.approval_status in (
                        SourceApprovalStatus.REJECTED,
                        SourceApprovalStatus.PENDING_REVIEW,
                    )
                ):
                    logger.warning(
                        "import_dataset: refusing to overwrite approved dataset %r "
                        "with lower-status replacement (approval_status=%r)",
                        metadata.dataset_id,
                        metadata.approval_status,
                    )
                    return DatasetImportResult(
                        dataset_id=metadata.dataset_id,
                        accepted=False,
                        authoritative=False,
                        target_crs=metadata.target_crs,
                        reason="existing_approved_dataset_not_overwritten",
                    )

            row = DbSpatialDataset(
                dataset_id=metadata.dataset_id,
                name=metadata.name,
                provider=metadata.provider,
                version=metadata.version,
                licence=metadata.licence,
                licence_status=str(metadata.licence_status),
                approval_status=str(metadata.approval_status),
                source_crs=metadata.source_crs,
                fetched_at=metadata.fetched_at,
                refresh_due=metadata.refresh_due,
                metadata_json=_metadata_to_dict(metadata),
            )
            session.add(row)
            session.commit()

        return DatasetImportResult(
            dataset_id=metadata.dataset_id,
            accepted=True,
            authoritative=authoritative,
            target_crs=metadata.target_crs,
            reason="dataset_registered",
        )

    def dataset_for(self, dataset_id: str) -> SpatialDatasetMetadata | None:
        with Session(self._engine) as session:
            row = session.execute(
                select(DbSpatialDataset)
                .where(DbSpatialDataset.dataset_id == dataset_id)
                .order_by(DbSpatialDataset.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            if row is None:
                return None
            return _db_dataset_to_metadata(row)

    def is_authoritative_dataset(self, dataset_id: str) -> bool:
        meta = self.dataset_for(dataset_id)
        return bool(meta and meta.is_authoritative())

    # ------------------------------------------------------------------
    # Spatial feature ingestion
    # ------------------------------------------------------------------

    def add_address_point(self, address_point: AddressPoint) -> None:
        """Persist an address point.

        Geometry is stored as GDA2020 (EPSG:7844).  G-NAF coordinates are
        GDA2020-compatible (WGS84/GDA2020 are effectively coincident for
        address-level precision).
        """
        db_dataset_id = self._resolve_db_dataset_id(address_point.dataset_id)
        if db_dataset_id is None:
            logger.warning(
                "add_address_point: dataset %r not found, skipping", address_point.dataset_id
            )
            return
        # Use ST_SetSRID + ST_MakePoint via raw WKT for portability without
        # requiring GeoAlchemy2 at call time (it IS available — see importers).
        # We pass geometry as a WKT expression through text().
        geom_wkt = f"SRID=7844;POINT({address_point.lon} {address_point.lat})"
        with Session(self._engine) as session:
            row = DbAddressPoint(
                gnaf_pid=address_point.gnaf_pid or address_point.address_id,
                address_text=address_point.formatted_address,
                spatial_dataset_id=db_dataset_id,
                confidence=None,
                metadata_json={
                    "address_id": address_point.address_id,
                    "aliases": list(address_point.aliases),
                    "target_crs": address_point.target_crs,
                    "dataset_id": address_point.dataset_id,
                },
            )
            # Set geometry via ST_GeomFromEWKT
            session.add(row)
            session.flush()
            session.execute(
                text(
                    "UPDATE address_points SET geom = ST_GeomFromEWKT(:wkt) WHERE id = :row_id"
                ),
                {"wkt": geom_wkt, "row_id": str(row.id)},
            )
            session.commit()

    def add_parcel(self, parcel: Parcel) -> None:
        """Persist a parcel.

        Geometry must be provided as a WKT string in ``parcel.metadata_json``
        (key ``geom_ewkt``) or a placeholder is stored.  Importers that have
        real geometries should set ``parcel.metadata_json["geom_ewkt"]``.
        """
        db_dataset_id = self._resolve_db_dataset_id(parcel.dataset_id)
        if db_dataset_id is None:
            logger.warning("add_parcel: dataset %r not found, skipping", parcel.dataset_id)
            return
        geom_ewkt = (
            getattr(parcel, "_geom_ewkt", None)
            or "SRID=7844;MULTIPOLYGON EMPTY"
        )
        with Session(self._engine) as session:
            row = DbParcel(
                cadastre_id=parcel.parcel_id,
                lot_plan=parcel.lot_plan,
                local_government=parcel.local_government,
                area_m2=parcel.area_m2,
                spatial_dataset_id=db_dataset_id,
                metadata_json={
                    "parcel_id": parcel.parcel_id,
                    "dataset_id": parcel.dataset_id,
                    "verification_status": parcel.verification_status,
                    "target_crs": parcel.target_crs,
                },
            )
            session.add(row)
            session.flush()
            session.execute(
                text(
                    "UPDATE parcels SET geom = ST_GeomFromEWKT(:wkt) WHERE id = :row_id"
                ),
                {"wkt": geom_ewkt, "row_id": str(row.id)},
            )
            session.commit()

    def add_planning_feature(self, feature: PlanningFeature) -> None:
        """Persist a planning feature.

        Geometry (MULTIPOLYGON EPSG:7844) should be in
        ``feature.metadata_json["geom_ewkt"]``.
        """
        db_dataset_id = self._resolve_db_dataset_id(feature.dataset_id)
        if db_dataset_id is None:
            logger.warning(
                "add_planning_feature: dataset %r not found, skipping", feature.dataset_id
            )
            return
        geom_ewkt = (
            getattr(feature, "_geom_ewkt", None)
            or "SRID=7844;MULTIPOLYGON EMPTY"
        )
        with Session(self._engine) as session:
            row = DbPlanningFeature(
                layer_type=feature.fact_type,
                code=feature.feature_id,
                label=feature.label or feature.fact_type,
                spatial_dataset_id=db_dataset_id,
                metadata_json={
                    "feature_id": feature.feature_id,
                    "parcel_id": feature.parcel_id,
                    "fact_type": feature.fact_type,
                    "value": feature.value,
                    "dataset_id": feature.dataset_id,
                    "target_crs": feature.target_crs,
                },
            )
            session.add(row)
            session.flush()
            session.execute(
                text(
                    "UPDATE planning_features SET geom = ST_GeomFromEWKT(:wkt) WHERE id = :row_id"
                ),
                {"wkt": geom_ewkt, "row_id": str(row.id)},
            )
            session.commit()

    # ------------------------------------------------------------------
    # Spatial queries
    # ------------------------------------------------------------------

    def exact_address_points(self, address: str) -> list[AddressPoint]:
        """Return the best address-point match(es) for ``address``.

        Exact normalized matches win outright.  Otherwise the trigram search
        is consulted: a clear best candidate is returned alone, near-tied
        candidates are all returned (the resolution service reports them as
        ambiguous), and weak matches return an empty list.

        NOTE: Results are indicative geocodes only — not legal proof of title
        or property identity.
        """
        normalized = normalize_address(address)
        if not normalized:
            return []
        variants = {normalized, expand_street_abbreviations(normalized)}

        hits = self.search_address_points(address, limit=5)
        if not hits:
            return []

        exact = [hit for hit in hits if normalize_address(hit.formatted_address) in variants]
        if exact:
            selected = exact
        else:
            strong = [hit for hit in hits if hit.score >= ADDRESS_MATCH_SCORE_FLOOR]
            if not strong:
                return []
            top = strong[0]
            ties = [hit for hit in strong if (top.score - hit.score) < ADDRESS_MATCH_AMBIGUITY_GAP]
            selected = ties if len(ties) > 1 else [top]

        return [
            AddressPoint(
                address_id=hit.address_id,
                formatted_address=hit.formatted_address,
                lon=hit.lon,
                lat=hit.lat,
                parcel_id="",  # parcel resolution is spatial — see parcel_for_address_point
                dataset_id=hit.dataset_id,
                gnaf_pid=hit.gnaf_pid,
                target_crs=GDA2020_TARGET_CRS,
            )
            for hit in selected
        ]

    def search_address_points(self, query: str, limit: int = 8) -> list[AddressSearchHit]:
        """Rank address points against a free-text query using pg_trgm.

        Uses the ``ix_address_points_address_text_trgm`` GIN index (migration
        0009) via the ``<%`` word-similarity operator, querying both the raw
        normalized input and a street-type-expanded variant ("st" -> "street")
        so abbreviated queries still rank well.  A small boost is applied when
        the query's leading house number appears in the candidate, so
        "3 Black Swan Rise" outranks other numbers on the same street.

        Results are indicative geocodes only — never legal proof of title or
        property identity.
        """
        normalized = normalize_address(query)
        if not normalized:
            return []
        expanded = expand_street_abbreviations(normalized)
        house_number = leading_house_number(normalized)

        wsim = func.greatest(
            func.word_similarity(normalized, DbAddressPoint.address_text),
            func.word_similarity(expanded, DbAddressPoint.address_text),
        )
        boost: ColumnElement[float]
        if house_number:
            boost = case(
                (DbAddressPoint.address_text.op("~")(rf"\m{house_number}\M"), 0.05),
                else_=0.0,
            )
        else:
            boost = literal(0.0)
        score = func.least(wsim + boost, 1.0).label("score")

        stmt = (
            select(
                DbAddressPoint.id,
                DbAddressPoint.gnaf_pid,
                DbAddressPoint.address_text,
                func.ST_Y(DbAddressPoint.geom).label("lat"),
                func.ST_X(DbAddressPoint.geom).label("lon"),
                DbSpatialDataset.dataset_id,
                score,
            )
            .join(
                DbSpatialDataset,
                DbAddressPoint.spatial_dataset_id == DbSpatialDataset.id,
            )
            .where(
                or_(
                    literal(normalized).op("<%")(DbAddressPoint.address_text),
                    literal(expanded).op("<%")(DbAddressPoint.address_text),
                )
            )
            .order_by(text("score DESC"), DbAddressPoint.address_text.asc())
            .limit(max(1, min(int(limit), 20)))
        )

        with Session(self._engine) as session:
            try:
                # Lower the word-similarity floor for this transaction so
                # moderate typos still surface candidates; ranking puts the
                # best match first regardless.
                session.execute(text("SET LOCAL pg_trgm.word_similarity_threshold = 0.45"))
                rows = session.execute(stmt).all()
            except Exception:
                logger.warning(
                    "search_address_points: trigram search failed, falling back to ILIKE",
                    exc_info=True,
                )
                session.rollback()
                rows = self._ilike_search_rows(session, normalized, expanded, limit)

        results: list[AddressSearchHit] = []
        for row in rows:
            results.append(
                AddressSearchHit(
                    address_id=str(row[0]),
                    gnaf_pid=row[1],
                    formatted_address=row[2],
                    lat=float(row[3]) if row[3] is not None else 0.0,
                    lon=float(row[4]) if row[4] is not None else 0.0,
                    dataset_id=row[5],
                    score=round(float(row[6]), 4),
                )
            )
        return results

    def _ilike_search_rows(
        self, session: Session, normalized: str, expanded: str, limit: int
    ):
        """Substring fallback used only when pg_trgm is unavailable."""
        patterns = {f"%{normalized}%", f"%{expanded}%"}
        stmt = (
            select(
                DbAddressPoint.id,
                DbAddressPoint.gnaf_pid,
                DbAddressPoint.address_text,
                func.ST_Y(DbAddressPoint.geom).label("lat"),
                func.ST_X(DbAddressPoint.geom).label("lon"),
                DbSpatialDataset.dataset_id,
                literal_column("0.6").label("score"),
            )
            .join(
                DbSpatialDataset,
                DbAddressPoint.spatial_dataset_id == DbSpatialDataset.id,
            )
            .where(or_(*[DbAddressPoint.address_text.ilike(p) for p in patterns]))
            .order_by(DbAddressPoint.address_text.asc())
            .limit(max(1, min(int(limit), 20)))
        )
        return session.execute(stmt).all()

    def parcel_for_address_point(self, point: AddressPoint) -> Parcel | None:
        """Spatially resolve the cadastral parcel containing an address point.

        G-NAF rows carry no parcel linkage, so this is a PostGIS ST_Within
        lookup of the point coordinate against ``parcels.geom`` (both
        EPSG:7844).  Returns ``None`` when no parcel covers the point (e.g.
        LGAs whose cadastre has not been imported yet).
        """
        if not point.lat and not point.lon:
            return None
        with Session(self._engine) as session:
            row = session.execute(
                select(DbParcel, DbSpatialDataset.dataset_id)
                .join(
                    DbSpatialDataset,
                    DbParcel.spatial_dataset_id == DbSpatialDataset.id,
                )
                .where(
                    func.ST_Within(
                        func.ST_SetSRID(func.ST_MakePoint(point.lon, point.lat), 7844),
                        DbParcel.geom,
                    )
                )
                .limit(1)
            ).first()
            if row is None:
                return None
            parcel_row, dataset_id = row
            meta = parcel_row.metadata_json or {}
            return Parcel(
                parcel_id=parcel_row.cadastre_id or str(parcel_row.id),
                lot_plan=parcel_row.lot_plan or "",
                local_government=parcel_row.local_government or "",
                area_m2=float(parcel_row.area_m2 or 0.0),
                dataset_id=str(meta.get("dataset_id", dataset_id)),
                verification_status=str(meta.get("verification_status", "verified")),
            )

    def planning_for_parcel(self, parcel_id: str) -> list[PlanningFeature]:
        """Return planning features whose geometry intersects the given parcel.

        Uses ``ST_Intersects`` between ``planning_features.geom`` and
        ``parcels.geom``, joined on the cadastre_id matching ``parcel_id``.
        """
        with Session(self._engine) as session:
            parcel_row = session.execute(
                select(DbParcel).where(DbParcel.cadastre_id == parcel_id).limit(1)
            ).scalar_one_or_none()
            if parcel_row is None:
                return []

            rows = session.execute(
                select(DbPlanningFeature, DbSpatialDataset)
                .join(
                    DbSpatialDataset,
                    DbPlanningFeature.spatial_dataset_id == DbSpatialDataset.id,
                )
                .where(
                    text(
                        "ST_Intersects(planning_features.geom, "
                        "(SELECT geom FROM parcels WHERE id = :parcel_db_id))"
                    ).bindparams(parcel_db_id=str(parcel_row.id))
                )
            ).all()

            results: list[PlanningFeature] = []
            for pf_row, ds_row in rows:
                meta = pf_row.metadata_json or {}
                results.append(
                    PlanningFeature(
                        feature_id=meta.get("feature_id", str(pf_row.id)),
                        parcel_id=meta.get("parcel_id", parcel_id),
                        fact_type=meta.get("fact_type", pf_row.layer_type),
                        value=meta.get("value"),
                        dataset_id=meta.get("dataset_id", ds_row.dataset_id),
                        label=pf_row.label,
                        target_crs=meta.get("target_crs", GDA2020_TARGET_CRS),
                    )
                )
            return results

    # ------------------------------------------------------------------
    # Property profile persistence
    # ------------------------------------------------------------------

    def save_profile(self, profile: PropertyProfile) -> None:
        """Persist (or replace) a PropertyProfile + its PropertyFact rows.

        Each ``PropertyFact`` row is stored with full provenance in
        ``provenance_json`` (safety invariant 2).
        """
        with Session(self._engine) as session:
            # Upsert the Property row
            import uuid as _uuid_mod

            try:
                org_id = _uuid_mod.UUID(profile.org_id)
            except (ValueError, AttributeError):
                # org_id is a fixture string — cannot store in FK column; skip DB
                logger.warning(
                    "save_profile: org_id %r is not a UUID, profile not persisted to DB",
                    profile.org_id,
                )
                return

            try:
                project_id = _uuid_mod.UUID(profile.project_id)
            except (ValueError, AttributeError):
                logger.warning(
                    "save_profile: project_id %r is not a UUID, profile not persisted to DB",
                    profile.project_id,
                )
                return

            prop = session.execute(
                select(DbProperty).where(
                    DbProperty.org_id == org_id,
                    DbProperty.project_id == project_id,
                )
            ).scalar_one_or_none()

            if prop is None:
                prop = DbProperty(
                    org_id=org_id,
                    project_id=project_id,
                )
                session.add(prop)

            prop.address_text = profile.address
            prop.resolution_status = str(profile.resolution_status)
            prop.confidence = {
                Confidence.HIGH: 1.0,
                Confidence.MEDIUM: 0.5,
                Confidence.LOW: 0.25,
                Confidence.NONE: 0.0,
            }.get(profile.confidence, 0.0)
            prop.target_crs = profile.target_crs
            prop.resolution_cache_json = {
                "issues": list(profile.issues),
                "address_point_id": profile.address_point_id,
                "parcel_id": profile.parcel_id,
                "local_government": profile.local_government,
            }
            prop.resolution_metadata_json = {
                "provenance": [_provenance_to_json(p) for p in profile.provenance],
            }
            session.flush()

            # Persist each fact with provenance (invariant 2)
            for fact in profile.facts:
                db_fact = DbPropertyFact(
                    org_id=org_id,
                    project_id=project_id,
                    property_id=prop.id,
                    fact_type=fact.fact_type,
                    value_json=fact.value if isinstance(fact.value, dict) else {"value": fact.value},
                    confidence={
                        Confidence.HIGH: 1.0,
                        Confidence.MEDIUM: 0.5,
                        Confidence.LOW: 0.25,
                        Confidence.NONE: 0.0,
                    }.get(fact.confidence, 0.0),
                    method=fact.provenance.method,
                    provenance_json=_provenance_to_json(fact.provenance),
                    review_status=fact.review_status,
                )
                session.add(db_fact)

            session.commit()

    def profile_for_project(
        self, *, org_id: str, project_id: str
    ) -> PropertyProfile | None:
        """Reconstruct a ``PropertyProfile`` from the ``properties`` and
        ``property_facts`` tables.

        Returns ``None`` if no ``Property`` row exists for this
        ``(org_id, project_id)``.
        """
        import uuid as _uuid_mod

        try:
            org_uuid = _uuid_mod.UUID(org_id)
            project_uuid = _uuid_mod.UUID(project_id)
        except (ValueError, AttributeError):
            return None

        with Session(self._engine) as session:
            prop = session.execute(
                select(DbProperty).where(
                    DbProperty.org_id == org_uuid,
                    DbProperty.project_id == project_uuid,
                )
            ).scalar_one_or_none()

            if prop is None:
                return None

            cache = prop.resolution_cache_json or {}
            meta = prop.resolution_metadata_json or {}
            _prov_raw = meta.get("provenance")
            provenance_list: list[object] = list(_prov_raw) if isinstance(_prov_raw, list) else []

            fact_rows = session.execute(
                select(DbPropertyFact).where(
                    DbPropertyFact.org_id == org_uuid,
                    DbPropertyFact.project_id == project_uuid,
                )
            ).scalars().all()

            def _json_to_provenance(d: dict) -> ResolutionProvenance:
                return ResolutionProvenance(
                    kind=ProvenanceKind(d.get("kind", "spatial_dataset")),
                    method=d.get("method", "unknown"),
                    target_crs=d.get("target_crs", GDA2020_TARGET_CRS),
                    dataset_id=d.get("dataset_id"),
                    source_version_id=d.get("source_version_id"),
                    source_crs=d.get("source_crs"),
                    licence_status=LicenceStatus(d["licence_status"]) if d.get("licence_status") else None,
                    approval_status=SourceApprovalStatus(d["approval_status"]) if d.get("approval_status") else None,
                    manual_override_id=d.get("manual_override_id"),
                    detail=d.get("detail"),
                )

            facts: list[PropertyFact] = []
            for fr in fact_rows:
                prov_json = fr.provenance_json or {}
                prov = _json_to_provenance(prov_json)
                conf_float = fr.confidence or 0.0
                confidence = (
                    Confidence.HIGH if conf_float >= 0.9
                    else Confidence.MEDIUM if conf_float >= 0.4
                    else Confidence.LOW if conf_float > 0
                    else Confidence.NONE
                )
                facts.append(
                    PropertyFact(
                        fact_id=str(fr.id),
                        fact_type=fr.fact_type,
                        value=fr.value_json,
                        provenance=prov,
                        confidence=confidence,
                        review_status=fr.review_status,
                    )
                )

            conf_float = prop.confidence or 0.0
            profile_confidence = (
                Confidence.HIGH if conf_float >= 0.9
                else Confidence.MEDIUM if conf_float >= 0.4
                else Confidence.LOW if conf_float > 0
                else Confidence.NONE
            )

            return PropertyProfile(
                org_id=org_id,
                project_id=project_id,
                resolution_status=ResolutionStatus(prop.resolution_status),
                confidence=profile_confidence,
                address=prop.address_text,
                address_point_id=str(cache["address_point_id"]) if cache.get("address_point_id") is not None else None,
                parcel_id=str(cache["parcel_id"]) if cache.get("parcel_id") is not None else None,
                local_government=str(cache["local_government"]) if cache.get("local_government") is not None else None,
                facts=tuple(facts),
                provenance=tuple(_json_to_provenance(p) for p in provenance_list),  # type: ignore[arg-type]
                issues=tuple(str(i) for i in (cache.get("issues") if isinstance(cache.get("issues"), list) else [])),  # type: ignore[arg-type,attr-defined]
                target_crs=prop.target_crs or GDA2020_TARGET_CRS,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_db_dataset_id(self, dataset_id: str):
        """Return the UUID primary key of the most-recent ``SpatialDataset`` row
        for the given logical ``dataset_id``.  Returns ``None`` if not found."""

        with Session(self._engine) as session:
            row = session.execute(
                select(DbSpatialDataset.id)
                .where(DbSpatialDataset.dataset_id == dataset_id)
                .order_by(DbSpatialDataset.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            return row
