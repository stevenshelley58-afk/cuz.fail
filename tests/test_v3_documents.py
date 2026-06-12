from __future__ import annotations

from fastapi.testclient import TestClient

from draftcheck.api.auth import get_current_session
from draftcheck.api.main import create_app
from draftcheck.domain.documents import DocumentReviewStatus, InMemoryDocumentLibrary
from draftcheck.domain.identity import ActiveSession, IdentityRole, InMemoryIdentityStore


ORIGIN_HEADERS = {"origin": "http://localhost:5173"}


def test_v3_document_parser_capabilities_are_live() -> None:
    client = _client()

    response = client.get("/api/v1/documents/parsers")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 6
    assert body["accuracy_gate"]["status"] == "not_beta_ready"
    assert {item["media_type"] for item in body["items"]} >= {
        "text/plain",
        "application/pdf",
        "application/dxf",
        "model/ifc",
        "image/*",
    }


def test_v3_document_parser_accuracy_reports_canary_sample_pass() -> None:
    client = _client()

    response = client.get("/api/v1/documents/parsers/accuracy")

    assert response.status_code == 200
    body = response.json()
    assert body["demo_fixture_status"] == "passed"
    assert body["beta_status"] == "not_beta_ready"
    assert body["expected_fact_count"] == 6
    assert body["extracted_fact_count"] == 6
    assert body["matched_fact_count"] == 6
    assert body["recall"] == 1.0
    assert body["precision"] == 1.0
    assert body["missing"] == []
    assert body["mismatched"] == []


def test_v3_document_upload_extracts_review_gated_text_measurements() -> None:
    client = _client()

    response = client.post(
        "/api/v1/documents/projects/project-docs/upload",
        files={
            "file": (
                "site-plan.txt",
                b"Lot area: 450 m2\nFootprint: 218 m2\nFront setback: 4.5 m",
                "text/plain",
            )
        },
        headers=ORIGIN_HEADERS,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["document"]["parse_status"] == "parsed"
    assert body["chunks"] == 1
    assert body["fact_count"] == 3
    assert body["review_required"] is True
    assert {fact["label"] for fact in body["facts"]} == {
        "lot area",
        "building footprint",
        "front setback",
    }
    assert all(fact["review_status"] == "pending_review" for fact in body["facts"])
    assert all(fact["metadata"]["measurement_compliance_ready"] is False for fact in body["facts"])

    document_id = body["document"]["id"]
    pages = client.get(f"/api/v1/documents/{document_id}/pages")
    facts = client.get(f"/api/v1/documents/{document_id}/facts")

    assert pages.status_code == 200
    assert pages.json()["count"] == 1
    assert facts.status_code == 200
    assert facts.json()["count"] == 3

    from draftcheck.api.documents import get_document_library

    chunks = get_document_library().get_chunks(document_id)
    assert len(chunks) == 1
    assert chunks[0].embedding_model == "text-embedding-3-small"
    assert chunks[0].embedding_dimension == 1536
    assert chunks[0].metadata["legal_authority"] is False


def test_v3_dxf_upload_extracts_dimension_preview_without_promoting_measurement() -> None:
    client = _client()
    dxf_text = "\n".join(
        [
            "0",
            "SECTION",
            "2",
            "ENTITIES",
            "8",
            "A-DIMENSIONS",
            "DIMENSION 4.5",
            "0",
            "ENDSEC",
        ]
    )

    response = client.post(
        "/api/v1/documents/projects/project-docs/upload",
        files={"file": ("site-plan.dxf", dxf_text.encode(), "application/dxf")},
        headers=ORIGIN_HEADERS,
    )

    assert response.status_code == 200, response.text
    facts = response.json()["facts"]
    assert any(
        fact["label"] == "dxf dimension 1"
        and fact["numeric_value"] == 4.5
        and fact["metadata"]["measurement_compliance_ready"] is False
        for fact in facts
    )


def test_v3_dxf_dimension_uses_group_42_and_records_text_override_difference() -> None:
    library = InMemoryDocumentLibrary()
    dxf_text = "\n".join(
        [
            "0",
            "SECTION",
            "2",
            "ENTITIES",
            "0",
            "DIMENSION",
            "5",
            "2A",
            "8",
            "A-DIMENSIONS",
            "1",
            "5.0",
            "42",
            "4.5",
            "0",
            "ENDSEC",
            "0",
            "EOF",
        ]
    )

    result = library.upload(
        org_id="org-docs",
        project_id="project-docs",
        user_id="user-docs",
        filename="override.dxf",
        media_type="application/dxf",
        content=dxf_text.encode(),
    )

    fact = result.facts[0]
    assert fact.numeric_value == 4.5
    assert fact.review_status == DocumentReviewStatus.PENDING_REVIEW
    assert fact.metadata["entity_handle"] == "2A"
    assert fact.metadata["entity_layer"] == "A-DIMENSIONS"
    assert fact.metadata["entity_type"] == "DIMENSION"
    assert fact.metadata["text_override"] == "5.0"
    assert fact.metadata["text_override_numeric_value"] == 5.0
    assert fact.metadata["text_override_differs"] is True
    assert fact.metadata["measurement_compliance_ready"] is False


def test_v3_dxf_block_insert_uniform_scale_is_recorded_on_dimension_fact() -> None:
    library = InMemoryDocumentLibrary()
    dxf_text = "\n".join(
        [
            "0",
            "SECTION",
            "2",
            "BLOCKS",
            "0",
            "BLOCK",
            "2",
            "SETBACK_BLOCK",
            "0",
            "DIMENSION",
            "5",
            "D1",
            "8",
            "A-DIMENSIONS",
            "1",
            "<>",
            "42",
            "2.5",
            "0",
            "ENDBLK",
            "0",
            "ENDSEC",
            "0",
            "SECTION",
            "2",
            "ENTITIES",
            "0",
            "INSERT",
            "5",
            "I1",
            "8",
            "A-SITE",
            "2",
            "SETBACK_BLOCK",
            "41",
            "2.0",
            "42",
            "2.0",
            "43",
            "1.0",
            "0",
            "ENDSEC",
            "0",
            "EOF",
        ]
    )

    result = library.upload(
        org_id="org-docs",
        project_id="project-docs",
        user_id="user-docs",
        filename="block-scale.dxf",
        media_type="application/dxf",
        content=dxf_text.encode(),
    )

    fact = result.facts[0]
    assert fact.numeric_value == 5.0
    assert fact.review_status == DocumentReviewStatus.PENDING_REVIEW
    assert fact.metadata["block_name"] == "SETBACK_BLOCK"
    assert fact.metadata["entity_handle"] == "D1"
    assert fact.metadata["insert_handle"] == "I1"
    assert fact.metadata["insert_layer"] == "A-SITE"
    assert fact.metadata["insert_scale"] == {"x": 2.0, "y": 2.0, "z": 1.0}
    assert fact.metadata["insert_scale_applied"] is True
    assert fact.metadata["insert_scale_uncertain"] is False
    assert fact.metadata["scale_status"] == "insert_scale_known"
    assert fact.metadata["measurement_compliance_ready"] is False


def test_v3_image_upload_is_review_only_until_calibrated() -> None:
    client = _client()

    response = client.post(
        "/api/v1/documents/projects/project-docs/upload",
        files={"file": ("photo.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        headers=ORIGIN_HEADERS,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["document"]["parse_status"] == "needs_more_info"
    assert body["fact_count"] == 0
    assert "image_ocr_requires_calibration" in body["document"]["metadata"]["extraction_notes"]


def test_v3_document_fact_review_requires_reviewer_and_records_status() -> None:
    client = _client()
    upload = client.post(
        "/api/v1/documents/projects/project-docs/upload",
        files={"file": ("site-plan.txt", b"Open space: 180 m2", "text/plain")},
        headers=ORIGIN_HEADERS,
    )
    assert upload.status_code == 200, upload.text
    document_id = upload.json()["document"]["id"]
    fact_id = upload.json()["facts"][0]["id"]

    reviewed = client.post(
        f"/api/v1/documents/{document_id}/facts/{fact_id}/review",
        json={"review_status": "human_confirmed", "note": "Fixture confirmation only."},
        headers=ORIGIN_HEADERS,
    )

    assert reviewed.status_code == 200, reviewed.text
    body = reviewed.json()
    assert body["review_status"] == "human_confirmed"
    assert body["metadata"]["review_note"] == "Fixture confirmation only."


def _client() -> TestClient:
    app = create_app()
    store = InMemoryIdentityStore()
    org = store.get_or_create_org(slug="fixture")
    user = store.get_or_create_user(
        org=org,
        email="owner@example.test",
        role=IdentityRole.OWNER,
    )
    session_issue = store.create_session(user=user, org=org)
    active_session = ActiveSession(
        session=session_issue.session,
        user=session_issue.user,
        org=session_issue.org,
    )
    app.dependency_overrides[get_current_session] = lambda: active_session
    return TestClient(app, headers=ORIGIN_HEADERS)
