from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from draftcheck.api.blockwise_property_check import get_address_service, router
from draftcheck.domain.address import (
    AddressPoint,
    AddressResolutionService,
    Confidence,
    GDA2020_TARGET_CRS,
    InMemorySpatialDatasetStore,
    LicenceStatus,
    PropertyFact,
    PropertyProfile,
    ProvenanceKind,
    ResolutionProvenance,
    ResolutionStatus,
    SourceApprovalStatus,
    SpatialDatasetMetadata,
)


TOKEN = "test-token"
REQUEST = {
    "workspaceId": "workspace-1",
    "userId": "user-1",
    "address": "1 Example Street, Spearwood WA 6163",
    "clientSituation": "seller_appraisal",
    "notes": "Seller asked about renovation and subdivision indicators.",
}


def test_agent_property_check_returns_cited_preliminary_result(monkeypatch) -> None:
    client = _client(monkeypatch, AddressResolutionService())

    response = client.post(
        "/api/v1/agent-property-check",
        headers=_auth_headers(),
        json=REQUEST,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["confidence"] == "high"
    assert body["normalizedFacts"]["sourceCoverage"] == "source_cited"
    assert body["normalizedFacts"]["facts"]["zone"] == {"label": "Residential", "code": "R40"}
    assert body["citations"]
    citation_ids = {citation["id"] for citation in body["citations"]}
    for item in [*body["signals"], *body["likelyConstraints"]]:
        assert item["citationIds"]
        assert set(item["citationIds"]).issubset(citation_ids)
    assert body["talkingPoints"]
    assert body["engineRequestId"]


def test_agent_property_check_ensures_uuid_workspace_org_before_resolution(monkeypatch) -> None:
    service = AddressResolutionService()
    calls: list[dict[str, str]] = []

    def ensure_org(*, org_id: str, slug: str, name: str) -> None:
        calls.append({"org_id": org_id, "slug": slug, "name": name})

    setattr(service.store, "ensure_org", ensure_org)
    client = _client(monkeypatch, service)
    workspace_id = "00000000-0000-4000-8000-000000000001"

    response = client.post(
        "/api/v1/agent-property-check",
        headers=_auth_headers(),
        json={**REQUEST, "workspaceId": workspace_id},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert calls == [
        {
            "org_id": workspace_id,
            "slug": "blockwise-00000000000040008000000000000001",
            "name": f"Blockwise workspace {workspace_id}",
        }
    ]


def test_agent_property_check_response_avoids_customer_facing_internal_brand_and_unsafe_copy(
    monkeypatch,
) -> None:
    client = _client(monkeypatch, AddressResolutionService())

    response = client.post(
        "/api/v1/agent-property-check",
        headers=_auth_headers(),
        json=REQUEST,
    )

    text = json.dumps(response.json()).lower()
    forbidden = (
        "draftcheck",
        "guaranteed",
        "compliant",
        "legal advice",
        "full da assessment",
        "everything you need",
        "certain",
        "definitive",
        "council-approved",
    )
    for term in forbidden:
        assert term not in text


def test_agent_property_check_requires_bearer_token(monkeypatch) -> None:
    client = _client(monkeypatch, AddressResolutionService())

    response = client.post("/api/v1/agent-property-check", json=REQUEST)

    assert response.status_code == 401


def test_agent_property_check_rejects_invalid_bearer_token(monkeypatch) -> None:
    client = _client(monkeypatch, AddressResolutionService())

    response = client.post(
        "/api/v1/agent-property-check",
        headers={"Authorization": "Bearer wrong-token"},
        json=REQUEST,
    )

    assert response.status_code == 403


def test_agent_property_check_accepts_api_auth_keys_alias(monkeypatch) -> None:
    monkeypatch.delenv("BLOCKWISE_ENGINE_TOKEN", raising=False)
    monkeypatch.delenv("DRAFTCHECK_ENGINE_TOKEN", raising=False)
    monkeypatch.setenv("API_AUTH_KEYS", f"blockwise:{TOKEN}")
    client = _client(monkeypatch, AddressResolutionService(), set_token=False)

    response = client.post(
        "/api/v1/agent-property-check",
        headers=_auth_headers(),
        json=REQUEST,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_agent_property_check_rejects_invalid_address(monkeypatch) -> None:
    client = _client(monkeypatch, AddressResolutionService())

    response = client.post(
        "/api/v1/agent-property-check",
        headers=_auth_headers(),
        json={**REQUEST, "address": "ab"},
    )

    assert response.status_code == 422


def test_agent_property_check_rejects_invalid_client_situation(monkeypatch) -> None:
    client = _client(monkeypatch, AddressResolutionService())

    response = client.post(
        "/api/v1/agent-property-check",
        headers=_auth_headers(),
        json={**REQUEST, "clientSituation": "valuation"},
    )

    assert response.status_code == 422


def test_agent_property_check_returns_no_source_for_unresolved_address(monkeypatch) -> None:
    client = _client(monkeypatch, AddressResolutionService())

    response = client.post(
        "/api/v1/agent-property-check",
        headers=_auth_headers(),
        json={**REQUEST, "address": "999 Missing Road, Perth WA"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "no_source"
    assert body["signals"] == []
    assert body["likelyConstraints"] == []
    assert body["citations"] == []


def test_agent_property_check_returns_unsupported_without_source_coverage(monkeypatch) -> None:
    client = _client(monkeypatch, AddressResolutionService(store=_unsupported_store()))

    response = client.post(
        "/api/v1/agent-property-check",
        headers=_auth_headers(),
        json={**REQUEST, "address": "7 Unsupported Street, Perth WA 6000"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "unsupported"


def test_agent_property_check_fails_closed_when_citations_are_missing(monkeypatch) -> None:
    client = _client(monkeypatch, _MissingCitationService())

    response = client.post(
        "/api/v1/agent-property-check",
        headers=_auth_headers(),
        json=REQUEST,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "no_source"
    assert body["citations"] == []


def test_agent_property_check_returns_error_when_engine_layer_raises(monkeypatch) -> None:
    client = _client(monkeypatch, _RaisingService())

    response = client.post(
        "/api/v1/agent-property-check",
        headers=_auth_headers(),
        json=REQUEST,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert "boom" not in json.dumps(body).lower()


def test_vps_compose_passes_blockwise_engine_token_to_api_container() -> None:
    compose_text = Path("infra/v3/compose.yml").read_text(encoding="utf-8")
    api_service = compose_text.split("  api:", 1)[1].split("\n  worker:", 1)[0]

    assert "BLOCKWISE_ENGINE_TOKEN: ${BLOCKWISE_ENGINE_TOKEN:-}" in api_service
    assert "DRAFTCHECK_ENGINE_TOKEN: ${DRAFTCHECK_ENGINE_TOKEN:-}" in api_service
    assert "API_AUTH_KEYS: ${API_AUTH_KEYS:-}" in api_service


def _client(
    monkeypatch,
    service: Any,
    *,
    set_token: bool = True,
) -> TestClient:
    monkeypatch.delenv("DRAFTCHECK_ENGINE_TOKEN", raising=False)
    if set_token:
        monkeypatch.delenv("API_AUTH_KEYS", raising=False)
        monkeypatch.setenv("BLOCKWISE_ENGINE_TOKEN", TOKEN)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_address_service] = lambda: service
    return TestClient(app)


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def _unsupported_store() -> InMemorySpatialDatasetStore:
    store = InMemorySpatialDatasetStore()
    metadata = SpatialDatasetMetadata(
        dataset_id="unsupported-fixture",
        name="Unsupported fixture",
        provider="fixture",
        version="2026-Q2",
        licence="review fixture",
        licence_status=LicenceStatus.RESTRICTED,
        source_crs=GDA2020_TARGET_CRS,
        source_version_id=None,
        approval_status=SourceApprovalStatus.PENDING_REVIEW,
    )
    store.import_dataset(metadata, require_authoritative=False)
    store.add_address_point(
        AddressPoint(
            address_id="unsupported-address",
            formatted_address="7 Unsupported Street, Perth WA 6000",
            lon=115.86,
            lat=-31.95,
            parcel_id="unsupported-parcel",
            dataset_id=metadata.dataset_id,
        )
    )
    return store


class _MissingCitationService:
    store = InMemorySpatialDatasetStore()

    def resolve_address(
        self,
        org_id: str,
        project_id: str,
        address: str | None,
        manual_override: Any | None = None,
    ) -> PropertyProfile:
        provenance = ResolutionProvenance(
            kind=ProvenanceKind.SPATIAL_DATASET,
            method="fixture",
            dataset_id="fixture-without-source-version",
            source_version_id=None,
            created_at=datetime.now(UTC),
        )
        return PropertyProfile(
            org_id=org_id,
            project_id=project_id,
            resolution_status=ResolutionStatus.RESOLVED,
            confidence=Confidence.HIGH,
            address=address,
            local_government="City of Cockburn",
            facts=(
                PropertyFact(
                    fact_id=f"{project_id}:zone",
                    fact_type="zone",
                    value={"label": "Residential", "code": "R40"},
                    provenance=provenance,
                    confidence=Confidence.HIGH,
                    review_status="accepted",
                ),
            ),
            provenance=(provenance,),
        )


class _RaisingService:
    store = InMemorySpatialDatasetStore()

    def resolve_address(
        self,
        org_id: str,
        project_id: str,
        address: str | None,
        manual_override: Any | None = None,
    ) -> PropertyProfile:
        raise RuntimeError("boom")
