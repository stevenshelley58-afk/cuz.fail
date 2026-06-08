from __future__ import annotations


def _create_project(client):
    response = client.post(
        "/v1/projects",
        json={
            "project_name": "Address contract job",
            "address": "12 Example Street, Perth WA 6000",
            "local_government": "Perth",
            "project_type": "single_house",
            "stage": "concept",
            "as_of_date": "2026-06-06",
            "lodgement_date": "2026-06-01",
            "assessment_basis": "current_rules",
            "created_by": "tester",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_address_resolver_uses_resolution_status_and_refuses_missing_geometry(client):
    response = client.post(
        "/v1/address/resolve",
        json={"address": "12 Example Street, Perth WA 6000", "as_of_date": "2026-06-06"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["resolution_status"] == "missing_info"
    assert body["confidence"] == "low"
    assert "status" not in body
    assert "address_point_not_found" in body["issues"]
    assert "parcel_not_verified" in body["issues"]
    assert body["planning"] is None
    assert body["facts"] == []


def test_address_autocomplete_returns_project_history_when_spatial_points_are_absent(client):
    _create_project(client)

    response = client.get("/v1/address/autocomplete", params={"q": "12 Example", "limit": 5})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body == [
        {
            "address": "12 Example Street, Perth WA 6000",
            "formatted_address": "12 Example Street, Perth WA 6000",
            "local_government": "Perth",
            "lot_plan": None,
            "parcel_id": None,
            "confidence": "low",
            "source": "project_history",
        }
    ]


def test_project_proposal_is_separate_from_address_facts(client):
    project = _create_project(client)

    proposal = client.put(
        f"/v1/projects/{project['id']}/proposal",
        json={
            "proposal_type": "addition",
            "dwelling_type": "single_house",
            "building_class": "Class 1a",
            "work_type": "alteration",
            "lot_type": "corner_lot",
            "primary_street_confirmed": True,
        },
    )
    assert proposal.status_code == 200, proposal.text
    assert proposal.json()["dwelling_type"] == "single_house"

    profile = client.post(f"/v1/projects/{project['id']}/property/resolve", json={})
    assert profile.status_code == 200, profile.text
    body = profile.json()
    assert body["proposal"]["dwelling_type"] == "single_house"
    assert body["address_profile"]["facts"] == []
    assert body["address_profile"]["resolution_status"] == "missing_info"


def test_property_resolve_persists_row_per_fact_profile_without_opaque_status(client):
    project = _create_project(client)
    response = client.post(
        f"/v1/projects/{project['id']}/property/resolve",
        json={
            "facts": [
                {
                    "fact_type": "zone",
                    "value_json": {"label": "Residential", "code": "R40"},
                    "confidence": "medium",
                    "method": "manual_review",
                    "review_status": "pending_review",
                },
                {
                    "fact_type": "heritage_overlay",
                    "value_json": {"value": True, "register": "State Heritage"},
                    "confidence": "low",
                    "method": "manual_review",
                    "review_status": "pending_review",
                },
            ]
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    prop = body["property"]
    assert prop["address_profile_id"]
    assert prop["zoning"] == "Residential R40"
    facts = body["address_profile"]["facts"]
    assert [fact["fact_type"] for fact in facts] == ["zone", "heritage_overlay"]
    assert body["address_profile"]["planning"]["zone"] == "Residential R40"
    assert body["address_profile"]["resolution_status"] == "missing_info"

    profile = client.get(f"/v1/projects/{project['id']}/property/profile")
    assert profile.status_code == 200, profile.text
    assert profile.json()["property"]["address_profile_id"] == prop["address_profile_id"]


def test_resolved_rules_endpoint_refuses_without_resolved_profile_and_approved_rules(client):
    project = _create_project(client)
    client.post(f"/v1/projects/{project['id']}/property/resolve", json={})

    response = client.post(
        f"/v1/projects/{project['id']}/resolved-rules",
        json={"as_of_date": "2026-06-06", "assessment_basis": "current_rules"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "unsupported"
    assert body["resolved_rules"] == []
    assert "address_profile_not_resolved" in body["issues"]
    assert "approved_rule_rows_not_available" in body["issues"]
