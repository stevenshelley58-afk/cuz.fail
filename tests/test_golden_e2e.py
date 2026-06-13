from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

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
    AuditEvent,
    Base,
    CheckResult,
    CheckRun,
    Clause,
    Document,
    Org,
    Project,
    PropertyFact,
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
FIXTURE_TO_API_CHECK_KEY = {
    "primary_street_setback": "setback_front",
}


def test_document_upload_commits_before_async_parse_enqueue(tmp_path, monkeypatch) -> None:
    app, db, active_session = _make_app()
    _seed_identity_rows(db, active_session)
    db.commit()

    import draftcheck.api.documents as documents_module
    import draftcheck.jobs.documents as document_jobs

    monkeypatch.setattr(documents_module, "STORAGE_ROOT", tmp_path / "storage")
    client = TestClient(app, headers=ORIGIN_HEADERS)
    project = client.post(
        "/api/v1/projects",
        json={"name": "Async parse project", "council_scope": "Demo Bay Local Government"},
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    events: list[str] = []
    original_commit = db.commit

    def commit_spy() -> None:
        events.append("commit")
        original_commit()

    def enqueue_spy(document_id: UUID) -> dict[str, object]:
        events.append("enqueue")
        assert db.get(Document, document_id) is not None
        return {"enqueued": True, "job_id": "job-123", "queue": "default"}

    monkeypatch.setattr(db, "commit", commit_spy)
    monkeypatch.setattr(document_jobs, "enqueue_document_parse", enqueue_spy)

    upload = client.post(
        "/api/v1/documents/upload",
        params={"project_id": project_id},
        files={"file": ("async-site-plan.txt", b"Front setback: 4.5 m", "text/plain")},
    )

    assert upload.status_code == 200, upload.text
    body = upload.json()
    assert body["parse_status"] == "parse_pending"
    assert body["parse_job"] == {"enqueued": True, "job_id": "job-123", "queue": "default"}
    assert body["fact_count"] == 0
    assert events[:2] == ["commit", "enqueue"]


def test_drawing_dimension_requires_calibration_before_promotion(tmp_path, monkeypatch) -> None:
    app, db, active_session = _make_app()
    _seed_identity_rows(db, active_session)
    db.commit()

    import draftcheck.api.documents as documents_module

    monkeypatch.setattr(documents_module, "STORAGE_ROOT", tmp_path / "storage")
    client = TestClient(app, headers=ORIGIN_HEADERS)
    project = client.post(
        "/api/v1/projects",
        json={"name": "Calibrated DXF project", "council_scope": "Demo Bay Local Government"},
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]
    dxf_payload = "\n".join(
        [
            "0",
            "SECTION",
            "2",
            "HEADER",
            "9",
            "$INSUNITS",
            "70",
            "6",
            "0",
            "ENDSEC",
            "0",
            "SECTION",
            "2",
            "ENTITIES",
            "0",
            "DIMENSION",
            "5",
            "D-CAL-1",
            "8",
            "A-DIMENSIONS",
            "42",
            "4.5",
            "0",
            "ENDSEC",
            "0",
            "EOF",
        ]
    )

    upload = client.post(
        "/api/v1/documents/upload",
        params={"project_id": project_id},
        files={"file": ("calibrated-setback.dxf", dxf_payload.encode(), "application/dxf")},
    )
    assert upload.status_code == 200, upload.text
    db.commit()
    body = upload.json()
    document_id = body["document_id"]
    fact = body["extracted_facts"][0]
    assert fact["fact_kind"] == "drawing_dimension"
    assert fact["unit"] == "m"
    assert "calibration_ref" not in fact["metadata"]
    fact_id = fact["fact_id"]

    blocked = client.post(f"/api/v1/documents/{document_id}/facts/{fact_id}/promote")
    assert blocked.status_code == 422
    assert "calibration_ref" in blocked.text

    calibrated = client.patch(
        f"/api/v1/documents/{document_id}/facts/{fact_id}",
        json={"calibration_ref": "scale-bar:A101:1:100", "calibration_note": "Checked against title block scale."},
    )
    assert calibrated.status_code == 200, calibrated.text
    calibrated_body = calibrated.json()
    assert calibrated_body["metadata"]["calibration_ref"] == "scale-bar:A101:1:100"
    assert calibrated_body["metadata"]["calibration_status"] == "human_confirmed"

    promoted = client.post(f"/api/v1/documents/{document_id}/facts/{fact_id}/promote")
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["promoted_to_measurement"] is True
    property_fact = next(
        fact
        for fact in db.query(PropertyFact).all()
        if fact.value_json.get("document_fact_id") == fact_id
    )
    assert property_fact.value_json["calibration_ref"] == "scale-bar:A101:1:100"
    assert property_fact.provenance_json["calibration_ref"] == "scale-bar:A101:1:100"


def test_compliance_result_review_annotation_preserves_deterministic_status() -> None:
    app, db, active_session = _make_app()
    _seed_identity_rows(db, active_session)
    project_id = uuid4()
    run_id = uuid4()
    result_id = uuid4()
    db.add(
        Project(
            id=project_id,
            org_id=active_session.org.id,
            created_by_user_id=active_session.user.id,
            name="Human review project",
            status="draft",
        )
    )
    db.add(
        CheckRun(
            id=run_id,
            org_id=active_session.org.id,
            project_id=project_id,
            as_of_date=datetime.now(UTC),
            status="complete",
            engine_version="test-engine",
        )
    )
    db.add(
        CheckResult(
            id=result_id,
            org_id=active_session.org.id,
            project_id=project_id,
            check_run_id=run_id,
            check_key="site_cover",
            status="likely_fail",
            requirement_json={"threshold_value": 50, "threshold_unit": "%", "rule_id": "rule-fixture"},
            proposed_json={"measured_value": 58},
            why_this_applies="Fixture review rule quote.",
            citations_json=["source_version:fixture#clause:1"],
            drawing_evidence_json={"fact_type": "proposed_site_cover_pct"},
            decision_trace_json={"note": "Fixture deterministic trace."},
        )
    )
    db.commit()
    client = TestClient(app, headers=ORIGIN_HEADERS)

    reviewed = client.post(
        f"/api/v1/compliance/results/{result_id}/override",
        json={"action": "operator_note", "reason": "Planner asked for a boundary survey check."},
    )

    assert reviewed.status_code == 200, reviewed.text
    body = reviewed.json()
    assert body["result_id"] == str(result_id)
    assert body["status"] == "likely_fail"
    assert body["review_reason"] == "Planner asked for a boundary survey check."
    assert body["human_override"]["action"] == "operator_note"
    assert body["human_override"]["status_unchanged"] == "likely_fail"
    assert body["reviewed_by_user_id"] == str(active_session.user.id)
    assert body["reviewed_at"]

    persisted = db.get(CheckResult, result_id)
    assert persisted is not None
    assert persisted.status == "likely_fail"
    assert persisted.requirement_json["threshold_value"] == 50
    assert persisted.proposed_json["measured_value"] == 58
    assert persisted.drawing_evidence_json["fact_type"] == "proposed_site_cover_pct"

    audit = db.query(AuditEvent).filter(AuditEvent.subject_id == result_id).one()
    assert audit.event_type == "check_result.human_override_recorded"
    assert audit.action == "operator_note"
    assert audit.before_json["status"] == "likely_fail"
    assert audit.after_json["status"] == "likely_fail"
    assert audit.metadata_json["deterministic_status_preserved"] is True

    empty_reason = client.post(
        f"/api/v1/compliance/results/{result_id}/override",
        json={"action": "operator_note", "reason": "   "},
    )
    assert empty_reason.status_code == 422

    active_session.user.role = IdentityRole.GUEST
    blocked = client.post(
        f"/api/v1/compliance/results/{result_id}/override",
        json={"action": "operator_note", "reason": "Guest should not be able to annotate."},
    )
    assert blocked.status_code == 403
    active_session.user.role = IdentityRole.OWNER


def test_golden_fixture_e2e_reaches_cited_advisory_compliance_results(tmp_path, monkeypatch) -> None:
    fixtures = _load_golden_fixtures()
    expected_scope = set(fixtures["manifest"]["canary_scope"]["tier_1_check_keys"])
    expected_result_keys = {
        _api_expectation(item)["check_key"]
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

    dxf_artifact = FIXTURE_DIR / fixtures["manifest"]["artifacts"]["site_plan_dxf"]
    upload = client.post(
        "/api/v1/documents/upload",
        params={"project_id": project_id},
        files={
            "file": (
                dxf_artifact.name,
                dxf_artifact.read_bytes(),
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
        assert "not a legal or compliance determination" in promoted.json()["advisory_notice"].lower()

    compliance = client.post(f"/api/v1/compliance/projects/{project_id}/run")
    assert compliance.status_code == 201, compliance.text
    body = compliance.json()
    assert body["project_id"] == project_id
    for expected_text in fixtures["expected_compliance"]["run"]["advisory_disclaimer_contains"]:
        assert expected_text in body["advisory_disclaimer"]

    results_by_key = {result["check_key"]: result for result in body["results"]}
    api_scope = expected_result_keys
    assert api_scope <= set(results_by_key)
    expected_by_api_key = {
        _api_expectation(item)["check_key"]: item
        for item in fixtures["expected_compliance"]["expected_results"]
        if item["check_key"] in expected_scope
    }
    seeded_source_version_fragment = f"source_version:{_uuid('source-version:golden-rcodes')}"

    for check_key in api_scope:
        result = results_by_key[check_key]
        expected_result = expected_by_api_key[check_key]
        api_expectation = _api_expectation(expected_result)
        assert result["display_name"]
        assert result["rule_id"]
        assert result["rule_quote"]
        assert result["citation"]
        for citation_fragment in api_expectation["citation_contains"]:
            assert citation_fragment in result["citation"]
        assert seeded_source_version_fragment in result["citation"]
        assert result["status"] == expected_result["status"]
        assert result["threshold_value"] == api_expectation["threshold_value"]
        assert result["threshold_unit"] == api_expectation["threshold_unit"]
        assert result["measured_value"] == api_expectation["measured_value"]
        assert result["missing_info_reason"] is None
        assert "drawing_evidence" in result
        assert result["drawing_evidence"]["fact_type"] == api_expectation["drawing_fact_type"]
        assert result["drawing_evidence"]["method"] == "document_extraction_promoted"
        assert result["drawing_evidence"]["document_fact_id"]
        assert result["result_id"]
        assert result["review_reason"] is None
        assert result["human_override"] == {}
        assert result["reviewed_by_user_id"] is None
        assert result["reviewed_at"] is None

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

    assert api_scope == {
        "site_cover",
        "setback_front",
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
        "audit_events",
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


def _api_check_key(fixture_check_key: str) -> str:
    return FIXTURE_TO_API_CHECK_KEY.get(fixture_check_key, fixture_check_key)


def _api_expectation(expected_result: dict[str, object]) -> dict[str, object]:
    api_expectation = dict(expected_result["api_expectation"])
    api_expectation.setdefault("check_key", _api_check_key(str(expected_result["check_key"])))
    return api_expectation


def _uuid(value: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"draftcheck-golden-e2e:{value}")
