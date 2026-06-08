from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from draftcheck_core.address_service import AddressResolutionService
from draftcheck_core.database import Base
from draftcheck_core.json_utils import hash_text, to_json
from draftcheck_core.models import (
    AddressPoint,
    LocalGovernmentBoundary,
    LocalGovernmentFact,
    Parcel,
    PlanningLayerFeature,
    Project,
    ReviewQueueItem,
    SourceDocument,
    SourceVersion,
    SpatialDataset,
)
from draftcheck_shared.schemas import AddressResolveRequest


def test_address_resolution_uses_stored_spatial_rows_to_resolve_profile():
    db = _session()
    try:
        source_version, dataset = _spatial_source(db)
        parcel = Parcel(
            lot_plan="Lot 1 on P12345",
            local_government="Cockburn",
            area_m2=500,
            spatial_dataset_id=dataset.id,
            source_version_id=source_version.id,
            geom_wkt="POLYGON ((115.0 -32.0, 115.01 -32.0, 115.01 -31.99, 115.0 -31.99, 115.0 -32.0))",
        )
        db.add(parcel)
        db.flush()
        db.add_all(
            [
                AddressPoint(
                    gnaf_pid="GNAF-1",
                    address="1 Example Street, Spearwood WA",
                    lon=115.005,
                    lat=-31.995,
                    parcel_id=parcel.id,
                    spatial_dataset_id=dataset.id,
                    source_version_id=source_version.id,
                    geom_wkt="POINT (115.005 -31.995)",
                ),
                LocalGovernmentBoundary(
                    name="Cockburn",
                    spatial_dataset_id=dataset.id,
                    source_version_id=source_version.id,
                    geom_wkt="POLYGON ((114.99 -32.01, 115.02 -32.01, 115.02 -31.98, 114.99 -31.98, 114.99 -32.01))",
                ),
                PlanningLayerFeature(
                    layer_type="zone",
                    code="R40",
                    label="Residential",
                    spatial_dataset_id=dataset.id,
                    source_version_id=source_version.id,
                    geom_wkt="POLYGON ((114.99 -32.01, 115.02 -32.01, 115.02 -31.98, 114.99 -31.98, 114.99 -32.01))",
                    metadata_json=to_json({"effective_from": "2026-01-01"}),
                ),
                PlanningLayerFeature(
                    layer_type="bushfire_prone_area",
                    label="Bushfire prone area",
                    spatial_dataset_id=dataset.id,
                    source_version_id=source_version.id,
                    geom_wkt="POLYGON ((114.99 -32.01, 115.02 -32.01, 115.02 -31.98, 114.99 -31.98, 114.99 -32.01))",
                    metadata_json="{}",
                ),
            ]
        )
        db.flush()

        service = AddressResolutionService(db)
        suggestions = service.suggest_addresses("1 Example", limit=5)
        assert len(suggestions) == 1
        assert suggestions[0].formatted_address == "1 Example Street, Spearwood WA"
        assert suggestions[0].local_government == "Cockburn"
        assert suggestions[0].confidence == "medium"

        profile = service.resolve_address(
            AddressResolveRequest(address="1 Example Street, Spearwood WA", as_of_date="2026-06-06")
        )

        assert profile.resolution_status == "resolved"
        assert profile.confidence == "high"
        assert profile.parcel_id == parcel.id
        assert profile.local_government == "Cockburn"
        assert profile.lot_plan == "Lot 1 on P12345"
        assert profile.issues == []
        assert dataset.id in profile.dataset_version_ids
        assert profile.planning is not None
        assert profile.planning["zone"] == "Residential R40"
        assert profile.planning["bushfire_prone"] is True
        fact_types = {fact.fact_type for fact in profile.facts}
        assert {"parcel", "lot_area_m2", "local_government", "zone", "bushfire_prone"}.issubset(fact_types)

        lga_fact = db.scalar(select(LocalGovernmentFact).where(LocalGovernmentFact.address_profile_id == profile.id))
        assert lga_fact is not None
        assert lga_fact.local_government == "Cockburn"

        partial_profile = service.resolve_address(
            AddressResolveRequest(address="1 Example", as_of_date="2026-06-06")
        )
        assert partial_profile.resolution_status == "needs_human_review"
        assert partial_profile.confidence == "medium"
        assert "address_match_requires_human_review" in partial_profile.issues
        assert partial_profile.parcel_id is None
        assert partial_profile.facts == []
    finally:
        db.close()


def test_address_resolution_refuses_to_auto_pick_ambiguous_partial_match():
    db = _session()
    try:
        source_version, dataset = _spatial_source(db)
        db.add_all(
            [
                AddressPoint(
                    address="1 Example Street, Spearwood WA",
                    lon=115.005,
                    lat=-31.995,
                    spatial_dataset_id=dataset.id,
                    source_version_id=source_version.id,
                ),
                AddressPoint(
                    address="1 Example Street, Hamilton Hill WA",
                    lon=115.78,
                    lat=-32.08,
                    spatial_dataset_id=dataset.id,
                    source_version_id=source_version.id,
                ),
            ]
        )
        db.flush()

        profile = AddressResolutionService(db).resolve_address(
            AddressResolveRequest(address="1 Example Street", as_of_date="2026-06-06")
        )

        assert profile.resolution_status == "needs_human_review"
        assert profile.confidence == "medium"
        assert "multiple_address_points_match" in profile.issues
        assert profile.parcel_id is None
        assert profile.facts == []
    finally:
        db.close()


def test_address_resolution_enqueues_blocking_spatial_review_for_human_review_profile():
    db = _session()
    try:
        source_version, dataset = _spatial_source(db)
        project = Project(
            project_name="Spatial review project",
            address="1 Example Street",
            local_government="Cockburn",
            project_type="single_house",
            stage="concept",
            as_of_date="2026-06-06",
            assessment_basis="current_rules",
        )
        db.add_all(
            [
                project,
                AddressPoint(
                    address="1 Example Street, Spearwood WA",
                    lon=115.005,
                    lat=-31.995,
                    spatial_dataset_id=dataset.id,
                    source_version_id=source_version.id,
                ),
                AddressPoint(
                    address="1 Example Street, Hamilton Hill WA",
                    lon=115.78,
                    lat=-32.08,
                    spatial_dataset_id=dataset.id,
                    source_version_id=source_version.id,
                ),
            ]
        )
        db.flush()

        profile = AddressResolutionService(db).resolve_address(
            AddressResolveRequest(address="1 Example Street", as_of_date="2026-06-06"),
            project_id=project.id,
        )

        item = db.scalar(select(ReviewQueueItem).where(ReviewQueueItem.target_id == profile.id))
        assert item is not None
        assert item.queue == "spatial_ambiguity_review"
        assert item.project_id == project.id
        assert item.target_type == "address_profile"
        assert item.blocking_level == "blocking"
        assert item.status == "open"
        assert item.priority == "high"
        assert item.reason == "Address resolution requires human review: needs_human_review"
        assert "multiple_address_points_match" in item.evidence_json
    finally:
        db.close()


def test_address_resolution_refuses_parcel_geometry_conflict():
    db = _session()
    try:
        source_version, dataset = _spatial_source(db)
        parcel = Parcel(
            lot_plan="Lot 1 on P12345",
            local_government="Cockburn",
            area_m2=500,
            spatial_dataset_id=dataset.id,
            source_version_id=source_version.id,
            geom_wkt="POLYGON ((115.0 -32.0, 115.01 -32.0, 115.01 -31.99, 115.0 -31.99, 115.0 -32.0))",
        )
        db.add(parcel)
        db.flush()
        db.add(
            AddressPoint(
                address="1 Conflict Street, Spearwood WA",
                lon=116.0,
                lat=-31.995,
                parcel_id=parcel.id,
                spatial_dataset_id=dataset.id,
                source_version_id=source_version.id,
            )
        )
        db.flush()

        profile = AddressResolutionService(db).resolve_address(
            AddressResolveRequest(address="1 Conflict Street, Spearwood WA", as_of_date="2026-06-06")
        )

        assert profile.resolution_status == "missing_info"
        assert "parcel_geometry_conflict" in profile.issues
        assert "planning_layers_not_found" in profile.issues
    finally:
        db.close()


def _session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return session_factory()


def _spatial_source(db):
    source = SourceDocument(
        title="WA Spatial Fixture",
        authority="Authoritative spatial fixture",
        source_type="spatial_dataset",
        canonical_url="https://example.test/spatial-fixture",
    )
    version = SourceVersion(
        source_document=source,
        version_label="2026-06",
        effective_date="2026-06-01",
        content_sha256=hash_text("wa-spatial-fixture"),
        raw_text="Spatial fixture metadata only.",
    )
    db.add_all([source, version])
    db.flush()
    dataset = SpatialDataset(
        name="WA spatial fixture",
        provider="fixture",
        version_label="2026-06",
        source_version_id=version.id,
    )
    db.add(dataset)
    db.flush()
    return version, dataset
