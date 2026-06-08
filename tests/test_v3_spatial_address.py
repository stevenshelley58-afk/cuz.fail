from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from draftcheck.api.address import get_address_service, router
from draftcheck.api.auth import get_current_session
from draftcheck.domain.address import (
    AddressPoint,
    AddressResolutionService,
    GDA2020_TARGET_CRS,
    InMemorySpatialDatasetStore,
    LicenceStatus,
    ManualFact,
    Parcel,
    SourceApprovalStatus,
    SpatialDatasetMetadata,
)
from draftcheck.domain.identity import ActiveSession, InMemoryIdentityStore

ORIGIN_HEADERS = {"origin": "http://localhost:5173"}


def test_unlicensed_datasets_cannot_be_authoritative() -> None:
    store = InMemorySpatialDatasetStore()
    result = store.import_dataset(
        SpatialDatasetMetadata(
            dataset_id="unlicensed-gnaf",
            name="Unlicensed G-NAF fixture",
            provider="fixture",
            version="2026-Q2",
            licence="not approved for authoritative use",
            licence_status=LicenceStatus.UNLICENSED,
            approval_status=SourceApprovalStatus.APPROVED,
            source_version_id="source-version:unlicensed-gnaf:2026-q2",
            source_crs=GDA2020_TARGET_CRS,
        )
    )
    store.add_parcel(
        Parcel(
            parcel_id="parcel-unlicensed-1",
            lot_plan="Lot 99 on P99999",
            local_government="Unverified Council",
            area_m2=900,
            dataset_id="unlicensed-gnaf",
        )
    )
    store.add_address_point(
        AddressPoint(
            address_id="address-unlicensed-1",
            formatted_address="99 Licence Street, Perth WA 6000",
            lon=115.86,
            lat=-31.95,
            parcel_id="parcel-unlicensed-1",
            dataset_id="unlicensed-gnaf",
        )
    )

    client = _client(AddressResolutionService(store))
    response = client.post(
        "/api/v1/projects/project-unlicensed/resolve-address",
        json={"address": "99 Licence Street, Perth WA 6000"},
    )

    assert result.accepted is False
    assert result.authoritative is False
    assert result.target_crs == GDA2020_TARGET_CRS
    assert response.status_code == 200
    body = response.json()
    assert body["resolution_status"] == "unsupported"
    assert "licensed_authoritative_dataset_not_available" in body["issues"]
    assert body["facts"] == []


def test_rejected_dataset_metadata_does_not_overwrite_approved_dataset() -> None:
    store = InMemorySpatialDatasetStore()
    approved = SpatialDatasetMetadata(
        dataset_id="fixture-addresses",
        name="Approved address fixture",
        provider="fixture",
        version="2026-Q2",
        licence="approved fixture licence",
        licence_status=LicenceStatus.LICENSED,
        approval_status=SourceApprovalStatus.APPROVED,
        source_version_id="source-version:approved-addresses",
        source_crs=GDA2020_TARGET_CRS,
    )
    store.import_dataset(approved)
    rejected = store.import_dataset(
        SpatialDatasetMetadata(
            dataset_id=approved.dataset_id,
            name="Rejected replacement fixture",
            provider="fixture",
            version="2026-Q3",
            licence="not approved",
            licence_status=LicenceStatus.UNLICENSED,
            approval_status=SourceApprovalStatus.REJECTED,
            source_version_id="source-version:rejected-addresses",
            source_crs=GDA2020_TARGET_CRS,
        )
    )
    store.add_parcel(
        Parcel(
            parcel_id="parcel-approved-1",
            lot_plan="Lot 1 on P12345",
            local_government="Approved Council",
            area_m2=500,
            dataset_id=approved.dataset_id,
        )
    )
    store.add_address_point(
        AddressPoint(
            address_id="address-approved-1",
            formatted_address="1 Approved Street, Perth WA 6000",
            lon=115.86,
            lat=-31.95,
            parcel_id="parcel-approved-1",
            dataset_id=approved.dataset_id,
        )
    )

    profile = AddressResolutionService(store).resolve_address(
        org_id="org-fixture",
        project_id="project-fixture",
        address="1 Approved Street, Perth WA 6000",
    )

    assert rejected.accepted is False
    assert store.dataset_for(approved.dataset_id) == approved
    assert profile.resolution_status == "resolved"


def test_gda2020_target_datum_is_recorded_for_resolved_fixture() -> None:
    client = _client(AddressResolutionService())

    response = client.post(
        "/api/v1/projects/project-gda/resolve-address",
        json={"address": "1 Example Street, Spearwood WA"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["resolution_status"] == "resolved"
    assert body["target_crs"] == GDA2020_TARGET_CRS
    assert body["provenance"]
    assert {item["target_crs"] for item in body["provenance"]} == {GDA2020_TARGET_CRS}


def test_manual_override_provenance_appears_without_authoritative_claim() -> None:
    client = _client(AddressResolutionService())

    response = client.post(
        "/api/v1/projects/project-manual/resolve-address",
        json={
            "address": "Manual Review Address",
            "manual_override": {
                "override_id": "manual-override-1",
                "entered_by": "reviewer@example.test",
                "reason": "Council GIS extract supplied outside approved import flow.",
                "facts": [
                    {
                        "fact_type": "zone",
                        "value": {"label": "Residential", "code": "R20"},
                        "source_note": "Unapproved manual note.",
                    }
                ],
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["resolution_status"] == "needs_human_review"
    assert "manual_override_requires_human_review" in body["issues"]
    assert body["facts"][0]["review_status"] == "pending_review"
    provenance = body["facts"][0]["provenance"]
    assert provenance["kind"] == "manual_override"
    assert provenance["manual_override_id"] == "manual-override-1"
    assert provenance["source_version_id"] is None


def test_manual_override_rejects_proposal_only_fact_types() -> None:
    client = _client(AddressResolutionService())

    response = client.post(
        "/api/v1/projects/project-manual-invalid/resolve-address",
        json={
            "address": "Manual Review Address",
            "manual_override": {
                "override_id": "manual-override-invalid",
                "entered_by": "reviewer@example.test",
                "reason": "Attempted proposal fact injection.",
                "facts": [
                    {
                        "fact_type": "dwelling_type",
                        "value": {"label": "single_house"},
                    }
                ],
            },
        },
    )

    assert response.status_code == 422


def test_manual_override_rejects_proposal_only_keys_inside_allowed_fact_value() -> None:
    client = _client(AddressResolutionService())

    response = client.post(
        "/api/v1/projects/project-manual-invalid-value/resolve-address",
        json={
            "address": "Manual Review Address",
            "manual_override": {
                "override_id": "manual-override-invalid-value",
                "entered_by": "reviewer@example.test",
                "reason": "Attempted proposal value injection.",
                "facts": [
                    {
                        "fact_type": "zone",
                        "value": {"label": "Residential", "dwelling_type": "single_house"},
                    }
                ],
            },
        },
    )

    assert response.status_code == 422


def test_manual_fact_domain_rejects_non_property_fact_type() -> None:
    with pytest.raises(ValueError, match="property fact"):
        ManualFact(fact_type="dwelling_type", value={"label": "single_house"})


def test_manual_fact_domain_rejects_proposal_only_value_keys() -> None:
    with pytest.raises(ValueError, match="proposal-only keys"):
        ManualFact(fact_type="zone", value={"label": "Residential", "dwelling_type": "single_house"})


def test_address_resolution_requires_authenticated_session() -> None:
    client = _client(AddressResolutionService(), authenticated=False)

    response = client.post(
        "/api/v1/projects/project-auth/resolve-address",
        json={"address": "1 Example Street, Spearwood WA"},
    )

    assert response.status_code == 401


def test_address_resolution_rejects_disallowed_origin() -> None:
    client = _client(AddressResolutionService())

    response = client.post(
        "/api/v1/projects/project-origin/resolve-address",
        headers={"origin": "https://evil.example"},
        json={"address": "1 Example Street, Spearwood WA"},
    )

    assert response.status_code == 403


def test_address_resolution_requires_origin_header() -> None:
    client = _client(AddressResolutionService(), default_origin=False)

    response = client.post(
        "/api/v1/projects/project-origin-missing/resolve-address",
        json={"address": "1 Example Street, Spearwood WA"},
    )

    assert response.status_code == 403


def test_property_response_requires_authenticated_session() -> None:
    service = AddressResolutionService()
    authed_client = _client(service)
    anonymous_client = _client(service, authenticated=False)

    resolved = authed_client.post(
        "/api/v1/projects/project-private/resolve-address",
        json={"address": "1 Example Street, Spearwood WA 6163"},
    )
    leaked = anonymous_client.get("/api/v1/projects/project-private/property")

    assert resolved.status_code == 200
    assert leaked.status_code == 401


def test_property_response_is_scoped_to_authenticated_org() -> None:
    service = AddressResolutionService()
    org_a_client = _client(service, org_slug="org-a")
    org_b_client = _client(service, org_slug="org-b")

    resolved = org_a_client.post(
        "/api/v1/projects/project-cross-org/resolve-address",
        json={"address": "1 Example Street, Spearwood WA 6163"},
    )
    same_org = org_a_client.get("/api/v1/projects/project-cross-org/property")
    other_org = org_b_client.get("/api/v1/projects/project-cross-org/property")

    assert resolved.status_code == 200
    assert resolved.json()["resolution_status"] == "resolved"
    assert same_org.json()["resolution_status"] == "resolved"
    assert other_org.status_code == 200
    assert other_org.json()["resolution_status"] == "missing_info"
    assert other_org.json()["facts"] == []


def test_unresolved_addresses_do_not_invent_facts() -> None:
    client = _client(AddressResolutionService())

    response = client.post(
        "/api/v1/projects/project-missing/resolve-address",
        json={"address": "404 Unknown Road, Nowhere WA"},
    )
    property_response = client.get("/api/v1/projects/project-missing/property")

    assert response.status_code == 200
    body = response.json()
    assert body["resolution_status"] == "missing_info"
    assert "address_point_not_found" in body["issues"]
    assert body["facts"] == []
    assert body["parcel_id"] is None
    assert property_response.status_code == 200
    assert property_response.json()["facts"] == []


def test_property_response_contains_row_per_fact_provenance() -> None:
    client = _client(AddressResolutionService())
    resolved = client.post(
        "/api/v1/projects/project-property/resolve-address",
        json={"address": "1 Example Street, Spearwood WA 6163"},
    )
    assert resolved.status_code == 200

    response = client.get("/api/v1/projects/project-property/property")

    assert response.status_code == 200
    body = response.json()
    assert body["resolution_status"] == "resolved"
    assert body["facts"] == body["property_facts"]
    assert {fact["fact_type"] for fact in body["facts"]} >= {
        "address",
        "parcel",
        "local_government",
        "lot_area_m2",
        "zone",
    }
    for fact in body["facts"]:
        provenance = fact["provenance"]
        assert provenance["kind"] == "spatial_dataset"
        assert provenance["dataset_id"]
        assert provenance["source_version_id"]
        assert provenance["target_crs"] == GDA2020_TARGET_CRS


def _client(
    service: AddressResolutionService,
    *,
    authenticated: bool = True,
    org_slug: str = "fixture",
    default_origin: bool = True,
) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_address_service] = lambda: service
    if authenticated:
        store = InMemoryIdentityStore()
        org = store.get_or_create_org(slug=org_slug)
        user = store.get_or_create_user(org=org, email="owner@example.test")
        session_issue = store.create_session(user=user, org=org)
        app.dependency_overrides[get_current_session] = lambda: ActiveSession(
            session=session_issue.session,
            user=session_issue.user,
            org=session_issue.org,
        )
    return TestClient(app, headers=ORIGIN_HEADERS if default_origin else None)
