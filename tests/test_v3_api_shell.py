from __future__ import annotations

from fastapi.testclient import TestClient

from draftcheck.api.auth import get_current_session, require_reviewer_session
from draftcheck.api.main import app, create_app
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
    assert ready.json() == {
        "status": "ok",
        "service": "draftcheck-api",
        "checks": {"app": "ok", "config": "ok"},
    }
    assert client.get("/v1/health").status_code == 404
    assert client.get("/api/health").status_code == 404


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
        "/api/v1/rules/candidates/{candidate_id}/promote",
        "/api/v1/search/ask",
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
    assert body["source_library"]["status"] == "ingestion_in_progress"
    assert body["source_library"]["answer_policy"] == "cite_or_refuse"
    assert set(body["source_library"]["active_scope"]) >= {
        "City of Cockburn source anchors",
        "WA planning source anchors",
        "NCC public/licensed source anchors",
        "Standards Australia metadata only",
    }
    assert "Cockburn document fetch and human source approval" in body["source_library"]["pending"]
    assert body["hermes"]["trace_required"] is True
    assert body["hermes"]["skill_version_required"] is True
    assert body["hermes"]["spend_capped"] is True
    assert "compliance verdicts" in body["hermes"]["forbidden_outputs"]


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
    } <= set(body["counts"])


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
