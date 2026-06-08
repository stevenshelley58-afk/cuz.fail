from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from draftcheck.api.auth import get_current_session, require_reviewer_session
from draftcheck.api.main import app, create_app
from draftcheck.api import v1 as v1_api
from draftcheck.api.v1 import create_v1_router
from draftcheck.domain.sources import InMemorySourceLibrary, LicenceStatus
from draftcheck.domain.identity import ActiveSession, IdentityRole, InMemoryIdentityStore

ORIGIN_HEADERS = {"origin": "http://localhost:5173"}


def test_v3_health_and_ready_are_mounted_only_under_api_v1() -> None:
    client = TestClient(app)

    health = client.get("/api/v1/health")
    ready = client.get("/api/v1/ready")

    assert health.status_code == 200
    assert ready.status_code == 200
    assert health.headers["x-request-id"]
    assert health.json() == {"status": "ok", "service": "draftcheck-api", "version": "0.1.0"}
    ready_body = ready.json()
    assert ready_body["status"] == "ok"
    assert ready_body["service"] == "draftcheck-api"
    assert ready_body["checks"]["app"]["status"] == "ok"
    assert ready_body["checks"]["config"]["status"] == "ok"
    assert ready_body["checks"]["database"]["status"] == "warning"
    assert ready_body["checks"]["queue"]["status"] == "warning"
    assert ready_body["checks"]["storage"]["status"] in {"ok", "warning"}
    assert ready_body["checks"]["source_store"]["status"] == "warning"
    assert client.get("/v1/health").status_code == 404
    assert client.get("/api/health").status_code == 404


def test_v3_ready_reports_durable_runtime_when_database_and_queue_are_configured(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://fixture:fixture@localhost/fixture")
    monkeypatch.setenv("PROCRASTINATE_DB_URI", "postgresql://fixture:fixture@localhost/fixture")
    monkeypatch.setenv("OBJECT_STORAGE_ROOT", str(Path.cwd()))

    class _FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def execute(self, statement) -> None:
            assert statement is not None

    class _FakeEngine:
        dialect = type("Dialect", (), {"name": "postgresql"})()

        def connect(self) -> _FakeConnection:
            return _FakeConnection()

        def dispose(self) -> None:
            return None

    monkeypatch.setattr(v1_api, "create_runtime_engine", lambda _url: _FakeEngine())
    test_app = FastAPI()
    test_app.include_router(create_v1_router(), prefix="/api/v1")

    ready = TestClient(test_app).get("/api/v1/ready")

    assert ready.status_code == 200
    ready_body = ready.json()
    assert ready_body["status"] == "ok"
    assert ready_body["checks"]["database"] == {
        "status": "ok",
        "detail": "postgresql connection ok",
    }
    assert ready_body["checks"]["queue"]["status"] == "ok"
    assert ready_body["checks"]["storage"]["status"] == "ok"
    assert ready_body["checks"]["source_store"]["status"] == "ok"


def test_v3_ready_degrades_when_database_probe_fails(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://fixture:fixture@localhost/fixture")
    monkeypatch.delenv("PROCRASTINATE_DB_URI", raising=False)
    monkeypatch.setattr(
        v1_api,
        "create_runtime_engine",
        lambda _url: (_ for _ in ()).throw(RuntimeError("db offline")),
    )

    client = TestClient(create_app())
    ready = client.get("/api/v1/ready")

    assert ready.status_code == 200
    ready_body = ready.json()
    assert ready_body["status"] == "degraded"
    assert ready_body["checks"]["database"]["status"] == "error"
    assert "db offline" in ready_body["checks"]["database"]["detail"]


def test_v3_contract_stub_uses_problem_json() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/projects")

    assert response.status_code == 501
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == "Not Implemented"


def test_v3_app_emits_cors_headers_for_configured_frontend_origin() -> None:
    client = TestClient(app)

    response = client.options(
        "/api/v1/health",
        headers={
            "origin": "http://localhost:5173",
            "access-control-request-method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_v3_openapi_contains_required_surface_without_legacy_aliases() -> None:
    client = TestClient(app)
    assert client.get("/openapi.json").status_code == 404
    paths = set(client.get("/api/v1/openapi.json").json()["paths"])

    required_paths = {
        "/api/v1/auth/magic-link/request",
        "/api/v1/projects/{project_id}/resolve-address",
        "/api/v1/documents/projects/{project_id}/upload",
        "/api/v1/sources/import",
        "/api/v1/sources/ingestion-status",
        "/api/v1/sources/review-worklist",
        "/api/v1/sources/quality-report",
        "/api/v1/sources/{source_id}/versions/{source_version_id}/review-packet",
        "/api/v1/rules/candidates/{candidate_id}/promote",
        "/api/v1/search/ask",
        "/api/v1/assistant",
        "/api/v1/compliance/projects/{project_id}/run",
        "/api/v1/compliance/projects/{project_id}/matrix",
        "/api/v1/rfi/projects/{project_id}/parse",
        "/api/v1/agent/jobs",
        "/api/v1/ops/dashboard",
    }

    assert required_paths <= paths
    assert not any(path.startswith("/v1/") for path in paths)
    assert not any(path.startswith("/api/") and not path.startswith("/api/v1/") for path in paths)


def test_wave3_sources_and_address_routes_are_live_in_central_app() -> None:
    client = _authenticated_client()

    ask = client.post("/api/v1/search/ask", json={"query": "site cover"})
    resolved = client.post(
        "/api/v1/projects/project-central/resolve-address",
        json={"address": "1 Example Street, Spearwood WA 6163"},
    )

    assert ask.status_code == 200
    assert ask.json()["status"] == "unsupported"
    assert ask.json()["citations"] == []

    assert resolved.status_code == 200
    assert resolved.json()["resolution_status"] == "resolved"
    assert resolved.json()["target_crs"] == "EPSG:7844"


def test_v3_assistant_accepts_message_payload_and_returns_chat_shape() -> None:
    client = _authenticated_client()

    response = client.post("/api/v1/assistant", json={"message": "How does LotFile work?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"]
    assert body["citations"] == []
    assert body["grounded"] is False
    assert body["provider"] == "mock"
    assert body["used_fallback"] is True


def test_cockburn_ops_dashboard_reports_canary_and_hermes_state() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/ops/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mode"] == "v3_cockburn_build"
    assert body["canary"]["address"] == "3 Black Swan Rise, Beeliar WA 6164"
    assert body["canary"]["local_government"] == "City of Cockburn"
    assert body["canary"]["property_resolution"] == (
        "address_known_parcel_pending_authoritative_import"
    )
    assert body["canary"]["beta_status"] == "not_beta_accurate_yet"
    assert set(body["canary"]["blocked_outputs"]) >= {
        "final_compliance_claims",
        "uncited_regulatory_answers",
        "unpromoted_measurement_verdicts",
    }
    assert body["source_library"]["status"] in {"not_started", "ingestion_in_progress"}
    assert body["source_library"]["answer_policy"] == "cite_or_refuse"
    assert {
        "sources",
        "versions",
        "pending_review_versions",
        "approved_citable_versions",
        "metadata_only_versions",
        "chunks",
        "citations",
        "pending_fetches",
        "review_ready_versions",
        "low_signal_versions",
        "parse_repair_ready_versions",
        "parse_repair_missing_raw_artifact_versions",
        "raw_source_artifact_versions",
        "repaired_text_artifact_versions",
    } <= set(body["source_library"]["counts"])
    assert isinstance(body["source_library"]["quality_gates"], list)
    assert {
        "pending_lawful_fetch",
        "parse_quality_review_required",
        "source_review_ready",
        "citable_search_ready",
    } <= set(body["source_library"]["readiness_counts"])
    assert isinstance(body["source_library"]["source_type_counts"], dict)
    assert isinstance(body["source_library"]["pending_action_counts"], dict)
    assert {"requested_at", "successful_at"} <= set(body["source_library"]["latest_fetch_summary"])
    assert set(body["source_library"]["active_scope"]) >= {
        "City of Cockburn source anchors",
        "WA planning source anchors",
        "NCC public/licensed source anchors",
        "Standards Australia metadata only",
    }
    assert "approved citable Cockburn source versions" in body["source_library"]["pending"]
    if body["source_library"]["counts"]["pending_review_versions"] > 0:
        assert "Cockburn document fetch and human source approval" in body["source_library"]["pending"]
    assert body["hermes"]["trace_required"] is True
    assert body["hermes"]["skill_version_required"] is True
    assert body["hermes"]["spend_capped"] is True
    assert "compliance verdicts" in body["hermes"]["forbidden_outputs"]


def test_ops_dashboard_uses_live_router_source_library_counts() -> None:
    library = InMemorySourceLibrary()
    library.import_source(
        title="Cockburn Fixture",
        content="Fixture text for Cockburn source status.",
        source_id="src_cockburn_fixture",
        publisher="City of Cockburn",
        uri="https://example.test/cockburn-fixture",
        licence_status=LicenceStatus.OPEN,
    )
    test_app = FastAPI()
    test_app.include_router(create_v1_router(library=library), prefix="/api/v1")

    response = TestClient(test_app).get("/api/v1/ops/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["source_library"]["counts"]["sources"] == 1
    assert body["source_library"]["counts"]["versions"] == 1
    assert body["source_library"]["counts"]["pending_review_versions"] == 1
    assert body["source_library"]["counts"]["approved_citable_versions"] == 0
    assert body["source_library"]["counts"]["low_signal_versions"] == 1
    assert body["source_library"]["readiness_counts"]["parse_quality_review_required"] == 1
    assert body["source_library"]["source_type_counts"]["source_document"] == 1
    assert body["source_library"]["pending_action_counts"]["human_source_review"] == 1
    assert body["source_library"]["latest_fetch_summary"]["requested_at"] is None
    assert "Cockburn document fetch and human source approval" in body["source_library"]["pending"]


def test_source_ingestion_status_reports_cite_or_refuse_until_reviewed() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/sources/ingestion-status?local_government=Cockburn")

    assert response.status_code == 200
    body = response.json()
    assert body["answer_policy"] == "cite_or_refuse"
    assert body["beta_status"] == "not_beta_accurate_yet"
    assert "uncited_regulatory_answers" in body["blocked_outputs"]
    assert {
        "sources",
        "versions",
        "pending_review_versions",
        "approved_citable_versions",
        "metadata_only_versions",
        "chunks",
        "citations",
        "pending_fetches",
        "review_ready_versions",
        "low_signal_versions",
        "parse_repair_ready_versions",
        "parse_repair_missing_raw_artifact_versions",
        "raw_source_artifact_versions",
        "repaired_text_artifact_versions",
    } <= set(body["counts"])
    assert isinstance(body["quality_gates"], list)
    assert {
        "pending_lawful_fetch",
        "parse_quality_review_required",
        "source_review_ready",
        "citable_search_ready",
    } <= set(body["readiness_counts"])
    assert isinstance(body["source_type_counts"], dict)
    assert isinstance(body["pending_action_counts"], dict)
    assert {"requested_at", "successful_at"} <= set(body["latest_fetch_summary"])


def test_create_app_instances_do_not_share_default_source_library_state() -> None:
    first_app = create_app()
    second_app = create_app()
    _override_reviewer(first_app)
    _override_reviewer(second_app)
    first_client = TestClient(first_app, headers=ORIGIN_HEADERS)
    second_client = TestClient(second_app, headers=ORIGIN_HEADERS)

    imported = first_client.post(
        "/api/v1/sources/import",
        json={
            "title": "Isolated Source Fixture",
            "content": "This source should remain in the first app instance.",
            "licence_status": "open",
        },
    )
    first_sources = first_client.get("/api/v1/sources")
    second_sources = second_client.get("/api/v1/sources")

    assert imported.status_code == 200
    assert first_sources.json()["count"] == 1
    assert second_sources.json()["count"] == 0


def _authenticated_client() -> TestClient:
    test_app = create_app()
    _override_session(test_app)
    return TestClient(test_app, headers=ORIGIN_HEADERS)


def _override_session(test_app) -> None:
    store = InMemoryIdentityStore()
    org = store.get_or_create_org(slug="fixture")
    user = store.get_or_create_user(org=org, email="owner@example.test")
    session_issue = store.create_session(user=user, org=org)
    test_app.dependency_overrides[get_current_session] = lambda: ActiveSession(
        session=session_issue.session,
        user=session_issue.user,
        org=session_issue.org,
    )


def _override_reviewer(test_app) -> None:
    store = InMemoryIdentityStore()
    org = store.get_or_create_org(slug="fixture")
    user = store.get_or_create_user(
        org=org,
        email="reviewer@example.test",
        role=IdentityRole.REVIEWER,
    )
    session_issue = store.create_session(user=user, org=org)
    active_session = ActiveSession(
        session=session_issue.session,
        user=session_issue.user,
        org=session_issue.org,
    )
    test_app.dependency_overrides[get_current_session] = lambda: active_session
    test_app.dependency_overrides[require_reviewer_session] = lambda: active_session
