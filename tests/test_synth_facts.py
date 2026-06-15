"""Unit tests for WP-G spatial fact synthesis (synth_property_facts).

The DB-facing parts (PostGIS bbox dimensions, ST_Intersects feature join) are
PostGIS-only, so under the in-memory SQLite engine they degrade gracefully and
are exercised via a monkeypatched ``_intersecting_features`` seam.  The tests
focus on the contract the compliance engine depends on: confirmed,
spatial_derived facts that are idempotent across runs and a no-op without a
resolved parcel.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):

    def _visit_jsonb(self, type_, **kw):  # type: ignore[misc]
        return "JSON"

    SQLiteTypeCompiler.visit_JSONB = _visit_jsonb  # type: ignore[attr-defined]

import draftcheck.db.models as models  # noqa: E402

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from draftcheck.db.models import (  # noqa: E402
    Base,
    Org,
    Parcel,
    PlanningFeature,
    Project,
    Property,
    PropertyFact,
    SpatialDataset,
)
from draftcheck.domain.spatial import synth_facts  # noqa: E402
from draftcheck.domain.spatial.synth_facts import synth_property_facts  # noqa: E402

_NEEDED_TABLES = [
    "orgs",
    "projects",
    "spatial_datasets",
    "parcels",
    "planning_features",
    "properties",
    "property_facts",
]


@pytest.fixture
def session(monkeypatch) -> Iterator[Session]:
    # geoalchemy Geometry renders ``geometry(...)`` DDL that SQLite rejects.
    # Render it as TEXT for THIS engine only — monkeypatch auto-reverts after the
    # test so we never pollute Base.metadata for the schema-contract tests.
    monkeypatch.setattr(
        models.Geometry, "get_col_spec", lambda self, **kw: "TEXT", raising=False
    )
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(
        engine,
        tables=[Base.metadata.tables[name] for name in _NEEDED_TABLES],
    )
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False, future=True)
    db = factory()
    try:
        yield db
    finally:
        db.close()


def _seed_resolved_project(
    db: Session,
    *,
    area_m2: float | None = 540.0,
    local_government: str | None = "City of Cockburn",
    with_parcel: bool = True,
) -> tuple[str, str, Property, Parcel | None]:
    org = Org(id=uuid4(), name="Org", slug=f"org-{uuid4().hex[:8]}")
    project = Project(id=uuid4(), org_id=org.id, name="Beeliar lot", status="draft")
    dataset = SpatialDataset(
        id=uuid4(),
        dataset_id="cadastre",
        name="cadastre",
        provider="Landgate",
        source_crs="EPSG:7844",
        version="2026.1",
    )
    db.add_all([org, project, dataset])
    db.flush()

    parcel: Parcel | None = None
    parcel_id = None
    if with_parcel:
        parcel = Parcel(
            id=uuid4(),
            cadastre_id="CAD-1",
            lot_plan="12/DP345",
            local_government=local_government,
            area_m2=area_m2,
            spatial_dataset_id=dataset.id,
            geom="GEOM",  # TEXT placeholder under SQLite; not exercised by PostGIS here
        )
        db.add(parcel)
        db.flush()
        parcel_id = parcel.id

    prop = Property(
        id=uuid4(),
        org_id=org.id,
        project_id=project.id,
        address_text="1 Beeliar Dr",
        resolution_status="resolved",
        parcel_id=parcel_id,
    )
    db.add(prop)
    db.flush()
    return str(org.id), str(project.id), prop, parcel


def _zone_feature(db: Session, parcel: Parcel, *, r_code: str = "R20") -> PlanningFeature:
    feature = PlanningFeature(
        id=uuid4(),
        layer_type="zone",
        code="R20/30",
        label="Residential",
        spatial_dataset_id=parcel.spatial_dataset_id,
        metadata_json={"r_code": r_code, "density_code": r_code},
        geom="GEOM",  # TEXT placeholder under SQLite
    )
    db.add(feature)
    db.flush()
    return feature


def test_no_parcel_is_noop(session: Session) -> None:
    org_id, project_id, _prop, _parcel = _seed_resolved_project(session, with_parcel=False)

    result = synth_property_facts(session, org_id=org_id, project_id=project_id)

    assert result == {"written": 0, "fact_types": []}
    assert session.query(PropertyFact).count() == 0


def test_writes_confirmed_spatial_derived_facts(session: Session, monkeypatch) -> None:
    org_id, project_id, _prop, parcel = _seed_resolved_project(session)
    assert parcel is not None
    feature = _zone_feature(session, parcel, r_code="R20")
    monkeypatch.setattr(synth_facts, "_intersecting_features", lambda *a, **k: [feature])

    result = synth_property_facts(session, org_id=org_id, project_id=project_id)
    session.flush()

    facts = session.query(PropertyFact).all()
    assert facts, "expected synthesised facts"
    # Engine contract: every fact confirmed + spatial_derived + advisory.
    for fact in facts:
        assert fact.review_status == "confirmed"
        assert fact.method == "spatial_derived"
        assert fact.provenance_json["method"] == "spatial_derived"
        assert fact.provenance_json["advisory_only"] is True
        assert fact.confidence and fact.confidence > 0

    fact_types = {f.fact_type for f in facts}
    assert "lot_area_m2" in fact_types
    assert "local_government" in fact_types
    assert "zone" in fact_types
    assert "r_code" in fact_types
    assert set(result["fact_types"]) == fact_types
    assert result["written"] == len(facts)

    # r_code value comes from stamped metadata.
    rcode = next(f for f in facts if f.fact_type == "r_code")
    assert rcode.value_json["code"] == "R20"
    # lot_area uses the parcel's stored area.
    area = next(f for f in facts if f.fact_type == "lot_area_m2")
    assert area.value_json == {"value": 540.0, "unit": "m2"}
    local_government = next(f for f in facts if f.fact_type == "local_government")
    assert local_government.value_json == {"name": "City of Cockburn"}


def test_normalizes_bbox_local_government_label(session: Session, monkeypatch) -> None:
    org_id, project_id, _prop, parcel = _seed_resolved_project(
        session,
        local_government="City of Cockburn (bbox extent)",
    )
    assert parcel is not None
    monkeypatch.setattr(synth_facts, "_intersecting_features", lambda *a, **k: [])

    synth_property_facts(session, org_id=org_id, project_id=project_id)

    local_government = next(
        f for f in session.query(PropertyFact).all() if f.fact_type == "local_government"
    )
    assert local_government.value_json == {"name": "City of Cockburn"}


def test_idempotent_across_runs(session: Session, monkeypatch) -> None:
    org_id, project_id, _prop, parcel = _seed_resolved_project(session)
    assert parcel is not None
    feature = _zone_feature(session, parcel, r_code="R30")
    monkeypatch.setattr(synth_facts, "_intersecting_features", lambda *a, **k: [feature])

    first = synth_property_facts(session, org_id=org_id, project_id=project_id)
    count_after_first = session.query(PropertyFact).count()
    second = synth_property_facts(session, org_id=org_id, project_id=project_id)
    count_after_second = session.query(PropertyFact).count()

    assert first == second
    assert count_after_first == count_after_second == first["written"]
    # No duplicates: one fact per type.
    types = [f.fact_type for f in session.query(PropertyFact).all()]
    assert len(types) == len(set(types))


def test_omits_area_when_not_positive(session: Session, monkeypatch) -> None:
    org_id, project_id, _prop, parcel = _seed_resolved_project(session, area_m2=0.0)
    assert parcel is not None
    monkeypatch.setattr(synth_facts, "_intersecting_features", lambda *a, **k: [])

    synth_property_facts(session, org_id=org_id, project_id=project_id)

    fact_types = {f.fact_type for f in session.query(PropertyFact).all()}
    assert "lot_area_m2" not in fact_types
    # local_government still synthesised from the parcel.
    assert "local_government" in fact_types
    # width/depth omitted (no PostGIS) — never fabricated.
    assert "lot_width_m" not in fact_types
    assert "lot_depth_m" not in fact_types


def test_preserves_non_spatial_facts(session: Session, monkeypatch) -> None:
    """Idempotent delete must only remove spatial_derived rows."""
    org_id, project_id, prop, parcel = _seed_resolved_project(session)
    assert parcel is not None
    monkeypatch.setattr(synth_facts, "_intersecting_features", lambda *a, **k: [])

    keeper = PropertyFact(
        id=uuid4(),
        org_id=prop.org_id,
        project_id=prop.project_id,
        property_id=prop.id,
        fact_type="proposed_plot_ratio",
        value_json={"value": 0.5},
        method="document_extraction",
        review_status="confirmed",
    )
    session.add(keeper)
    session.flush()

    synth_property_facts(session, org_id=org_id, project_id=project_id)

    survivors = {
        (f.fact_type, f.method) for f in session.query(PropertyFact).all()
    }
    assert ("proposed_plot_ratio", "document_extraction") in survivors
