from __future__ import annotations


def seed_source(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Cockburn Residential Design Policy Example",
            "jurisdiction": "WA",
            "authority": "City of Cockburn",
            "local_government": "Cockburn",
            "source_type": "local_planning_policy",
            "canonical_url": "https://www.cockburn.wa.gov.au/example-policy",
            "licence_notes": "Public council policy example fixture.",
            "access_type": "public",
            "content": "\n".join(
                [
                    "5.1.3 Front setback",
                    "Primary street setbacks should be assessed using the applicable R-Codes table and local policy context.",
                    "5.2.2 Garage dominance",
                    "Garage width and street surveillance should be reviewed to avoid dominant vehicle access outcomes.",
                    "5.3.1 Open space",
                    "Open space and site cover calculations should be shown on the site plan.",
                ]
            ),
            "version_label": "example-current",
            "effective_date": "2026-05-27",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_source_ingestion_is_versioned_and_idempotent(client):
    first = seed_source(client)
    assert first["clauses_created"] >= 3
    assert first["chunks_created"] >= 3
    duplicate = seed_source(client)
    assert duplicate["duplicate"] is True

    versions = client.get(f"/v1/sources/{first['source_document_id']}/versions")
    assert versions.status_code == 200
    data = versions.json()
    assert len(data) == 1
    assert data[0]["content_sha256"]
    assert data[0]["is_superseded"] is False


def test_retrieval_refuses_without_support_and_cites_when_supported(client):
    unsupported = client.post("/v1/ask-source-library", json={"question": "What is the obscure pool pump colour rule?"})
    assert unsupported.status_code == 200
    assert unsupported.json()["status"] == "unsupported"
    assert unsupported.json()["citations"] == []

    seed_source(client)
    supported = client.post("/v1/ask-source-library", json={"question": "front setback garage dominance"})
    assert supported.status_code == 200
    body = supported.json()
    assert body["status"] == "needs_human_review"
    assert body["human_review_required"] is True
    assert body["citations"]
    assert body["citations"][0]["source_title"] == "Cockburn Residential Design Policy Example"
    assert body["source_version_ids"]
