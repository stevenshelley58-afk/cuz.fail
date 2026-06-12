from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):

    def _visit_jsonb(self, type_, **kw):  # type: ignore[misc]
        return "JSON"

    SQLiteTypeCompiler.visit_JSONB = _visit_jsonb  # type: ignore[attr-defined]

import draftcheck.db.models as _models_mod  # noqa: E402

for _tbl in _models_mod.Base.metadata.tables.values():
    for _idx in list(_tbl.indexes):
        if _idx.name in {"ix_documents_sha256", "ix_document_facts_check_key"} and len(_idx.columns) == 1:
            _idx.table.indexes.discard(_idx)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from draftcheck.api.auth import get_current_session  # noqa: E402
from draftcheck.api.deps import get_db_session  # noqa: E402
from draftcheck.api.main import create_app  # noqa: E402
from draftcheck.db.models import (  # noqa: E402
    Base,
    CheckResult,
    Clause,
    Org,
    Rule,
    Source,
    SourceVersion,
    User,
    UserStatus,
)
from draftcheck.domain.identity import (  # noqa: E402
    ActiveSession,
    IdentityRole,
    InMemoryIdentityStore,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "golden"
ORIGIN_HEADERS = {"origin": "http://localhost:5173"}


def test_golden_fixture_e2e_reaches_cited_advisory_compliance_results(tmp_path, monkeypatch) -> None:
    fixtures = _load_golden_fixtures()
    expected_scope = set(fixtures["manifest"]["canary_scope"]["tier_1_check_keys"])
    expected_result_keys = {
        item["check_key"]
        for item in fixtures["expected_compliance"]["expected_results"]
        if item["check_key"] in expected_scope
    }

    app, db, active_session = _make_app()
    _seed_identity_rows(db, active_session)
    _seed_approved_rules(db, active_session.org.id)
    db.commit()

    import draftcheck.api.documents as documents_module

    monkeypatch.setattr(documents_module, "STORAGE_ROOT", tmp_path / "storage")

    client = TestClient(app, headers=ORIGIN_HEADERS)

    address = fixtures["address_resolution"]["address_resolution"]["input"]["single_line"]
    project_payload = fixtures["project"]["project"]
    project = client.post(
        "/api/v1/projects",
        json={
            "name": project_payload["name"],
            "council_scope": "Demo Bay Local Government",
        },
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    resolved = client.post(
        f"/api/v1/projects/{project_id}/resolve-address",
        json={
            "address": address,
            "manual_override": {
                "entered_by": "golden-fixture",
                "reason": "M1 golden fixture address confirmation.",
                "address": address,
                "facts": [
                    {
                        "fact_type": "address",
                        "value": {"single_line": address},
                        "source_note": "tests/fixtures/golden/address_resolution.json",
                    }
                ],
            },
        },
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["address"] == address
    assert resolved.json()["resolution_status"] == "needs_more_info"

    proposal_payload = fixtures["proposal"]["proposal"]
    proposal = client.post(
        f"/api/v1/projects/{project_id}/proposal",
        json={
            "proposal_type": proposal_payload["proposal_type"],
            "dwelling_type": proposal_payload["dwelling_type"],
            "building_class": proposal_payload["building_class"],
            "work_type": proposal_payload["work_type"],
            "new_or_existing": proposal_payload["new_or_existing"],
            "lot_type": proposal_payload["lot_type"],
            "primary_street_confirmed": proposal_payload["primary_street_confirmed"],
            "secondary_street_confirmed": proposal_payload["secondary_street_confirmed"],
            "source": proposal_payload["source"],
            "confidence": proposal_payload["confidence"],
        },
    )
    assert proposal.status_code == 200, proposal.text

    dxf_payload = _golden_dxf_payload(fixtures["document_facts"])
    upload = client.post(
        "/api/v1/documents/upload",
        params={"project_id": project_id},
        files={
            "file": (
                "m1_canary_site_plan_rev_a.dxf",
                dxf_payload.encode("utf-8"),
                "application/dxf",
            )
        },
    )
    assert upload.status_code == 200, upload.text
    upload_body = upload.json()
    assert upload_body["media_type"] == "application/dxf"
    assert upload_body["chunk_count"] >= 1
    assert upload_body["review_required"] is True

    document_id = upload_body["document_id"]
    facts_by_key = {fact["fact_key"]: fact for fact in upload_body["extracted_facts"]}
    expected_fact_keys = {
        "proposed_site_cover_pct",
        "proposed_setback_front_m",
        "proposed_open_space_pct",
        "proposed_garage_width_m",
        "proposed_boundary_wall_length_m",
    }
    assert expected_fact_keys <= set(facts_by_key)

    for fact_key in expected_fact_keys:
        fact_id = facts_by_key[fact_key]["fact_id"]
        reviewed = client.patch(
            f"/api/v1/documents/{document_id}/facts/{fact_id}",
            json={"status": "confirmed"},
        )
        assert reviewed.status_code == 200, reviewed.text
        promoted = client.post(f"/api/v1/documents/{document_id}/facts/{fact_id}/promote")
        assert promoted.status_code == 200, promoted.text
        assert promoted.json()["review_status"] == "confirmed"
        assert "not a legal or compliance certification" in promoted.json()["advisory_notice"].lower()

    compliance = client.post(f"/api/v1/compliance/projects/{project_id}/run")
    assert compliance.status_code == 201, compliance.text
    body = compliance.json()
    assert body["project_id"] == project_id
    assert "advisory only" in body["advisory_disclaimer"]
    assert "not final legal" in body["advisory_disclaimer"]

    results_by_key = {result["check_key"]: result for result in body["results"]}
    api_scope = {
        "site_cover",
        "setback_front",
        "open_space",
        "garage_dominance",
        "boundary_wall_length",
    }
    assert api_scope <= set(results_by_key)

    for check_key in api_scope:
        result = results_by_key[check_key]
        assert result["display_name"]
        assert result["rule_id"]
        assert result["rule_quote"]
        assert result["citation"]
        assert "source_version:" in result["citation"]
        assert result["status"] in {"likely_pass", "likely_fail", "needs_more_info"}
        assert "missing_info_reason" in result
        assert "drawing_evidence" in result

    site_cover_result = results_by_key["site_cover"]
    assert site_cover_result["missing_info_reason"] is None
    assert site_cover_result["drawing_evidence"]["fact_type"] == "proposed_site_cover_pct"
    assert site_cover_result["drawing_evidence"]["method"] == "document_extraction_promoted"
    assert site_cover_result["drawing_evidence"]["document_fact_id"]

    persisted_site_cover = db.query(CheckResult).filter(CheckResult.check_key == "site_cover").one()
    assert persisted_site_cover.drawing_evidence_json["fact_type"] == "proposed_site_cover_pct"
    assert persisted_site_cover.drawing_evidence_json["method"] == "document_extraction_promoted"
    assert persisted_site_cover.drawing_evidence_json["document_fact_id"]
    assert persisted_site_cover.decision_trace_json["missing_info_reason"] is None

    assert expected_result_keys == {
        "site_cover",
        "primary_street_setback",
        "open_space",
        "garage_dominance",
        "boundary_wall_length",
    }


def _load_golden_fixtures() -> dict[str, object]:
    manifest = json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))
    return {
        "manifest": manifest,
        **{
            key: json.loads((FIXTURE_DIR / relative_path).read_text(encoding="utf-8"))
            for key, relative_path in manifest["files"].items()
        },
    }


def _make_app() -> tuple[object, Session, ActiveSession]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    needed_tables = [
        "orgs",
        "users",
        "projects",
        "properties",
        "property_facts",
        "proposals",
        "source_documents",
        "source_versions",
        "clauses",
        "rules",
        "documents",
        "document_pages",
        "document_chunks",
        "document_facts",
        "check_runs",
        "resolved_rules",
        "check_results",
    ]
    Base.metadata.create_all(
        engine,
        tables=[Base.metadata.tables[name] for name in needed_tables],
    )
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    db = session_factory()

    def override_db() -> Iterator[Session]:
        try:
            yield db
            db.flush()
        except Exception:
            db.rollback()
            raise

    store = InMemoryIdentityStore()
    org = store.get_or_create_org(slug="golden-e2e")
    user = store.get_or_create_user(org=org, email="owner@golden-e2e.test", role=IdentityRole.OWNER)
    session_issue = store.create_session(user=user, org=org)
    active_session = ActiveSession(
        session=session_issue.session,
        user=session_issue.user,
        org=session_issue.org,
    )

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_current_session] = lambda: active_session
    return app, db, active_session


def _seed_identity_rows(db: Session, active_session: ActiveSession) -> None:
    db.add(
        Org(
            id=active_session.org.id,
            slug=active_session.org.slug,
            name=active_session.org.name,
            status="active",
        )
    )
    db.add(
        User(
            id=active_session.user.id,
            org_id=active_session.org.id,
            email=active_session.user.email,
            role=active_session.user.role,
            status=UserStatus.ACTIVE,
        )
    )
    db.flush()


def _seed_approved_rules(db: Session, org_id: UUID) -> None:
    source = Source(
        id=_uuid("source:golden-rcodes"),
        org_id=org_id,
        title="Artificial R-Codes Rule Paraphrase Fixture",
        jurisdiction="WA",
        authority="DraftCheck fixture seed",
        local_government="Demo Bay Local Government",
        source_type="synthetic_fixture",
        canonical_url="https://example.test/draftcheck-fixtures/rcodes-paraphrase",
        access_type="fixture",
        status="active",
        metadata_json={"fixture_only": True},
    )
    source_version = SourceVersion(
        id=_uuid("source-version:golden-rcodes"),
        source_id=source.id,
        version_label="2026 artificial paraphrase fixture",
        sha256="e27150ad7c473fa7e06d26db107914f6d2f8455ea1e84c54308da04fdeee3cd5",
        storage_manifest_json={"fixture": "tests/fixtures/golden/approved_sources.json"},
        licence="approved_fixture_only",
        licence_status="approved_fixture_only",
        review_status="approved",
        metadata_json={"approval_scope": "M1 canary fixture only"},
    )
    db.add_all([source, source_version])

    rule_specs = [
        ("site_cover", "site_cover", "lte", 50.0, "%", "Fixture site-cover rule atom."),
        ("primary_street_setback", "primary_street_setback", "gte", 4.0, "m", "Fixture primary-street setback rule atom."),
        ("open_space", "open_space", "gte", 35.0, "%", "Fixture open-space rule atom."),
        ("garage_dominance", "garage_dominance", "lte", 6.0, "m", "Fixture garage-dominance rule atom."),
        ("boundary_wall_length", "boundary_wall_length", "lte", 9.0, "m", "Fixture boundary-wall length rule atom."),
    ]
    for rule_key, base_rule_key, operator, value, unit, quote in rule_specs:
        clause = Clause(
            id=_uuid(f"clause:{rule_key}"),
            source_version_id=source_version.id,
            clause_key=f"fixture.{rule_key}",
            clause_path=f"fixture/{rule_key}",
            clause_type="rule_atom",
            title=quote,
            section_ref=f"FIX-{rule_key}",
            disposition="approved",
            text=quote,
            quote=quote,
            metadata_json={"fixture_only": True},
        )
        rule = Rule(
            id=_uuid(f"rule:{rule_key}"),
            org_id=org_id,
            source_version_id=source_version.id,
            clause_id=clause.id,
            rule_key=rule_key,
            rule_type="requirement",
            pathway="none",
            lifecycle_status="approved",
            operator=operator,
            value_json={"value": value, "base_rule_key": base_rule_key},
            unit=unit,
            condition_json={},
            quote=quote,
            metadata_json={"fixture_only": True},
            council_scope="Demo Bay Local Government",
        )
        db.add_all([clause, rule])
    db.flush()


def _golden_dxf_payload(document_fixture: dict[str, object]) -> str:
    promoted = {
        item["measurement_type"]: item
        for item in document_fixture["promoted_measurements"]
    }
    lot_area = float(promoted["lot_area"]["value"])
    covered_area = float(promoted["site_cover_area"]["value"])
    open_space_area = float(promoted["open_space_area"]["value"])
    site_cover_pct = round((covered_area / lot_area) * 100, 2)
    open_space_pct = round((open_space_area / lot_area) * 100, 2)
    return "\n".join(
        [
            "0",
            "SECTION",
            "2",
            "ENTITIES",
            "8",
            "A-LOT-BOUNDARY",
            f"Lot area: {lot_area} m2",
            "8",
            "A-BUILDING-FOOTPRINT",
            f"Footprint: {covered_area} m2",
            f"Site coverage: {site_cover_pct}%",
            "8",
            "A-OPEN-SPACE",
            f"Open space: {open_space_area} m2",
            f"Open space percentage: {open_space_pct}%",
            "8",
            "A-DIMENSIONS",
            f"Front setback: {promoted['primary_street_setback']['value']} m",
            f"Garage width: {promoted['garage_width']['value']} m",
            "8",
            "A-WALLS",
            f"Boundary wall length: {promoted['boundary_wall_length']['value']} m",
            "0",
            "ENDSEC",
        ]
    )


def _uuid(value: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"draftcheck-golden-e2e:{value}")
