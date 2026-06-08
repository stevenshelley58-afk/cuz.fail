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


def accept_seeded_source_for_retrieval(client, source):
    candidates = client.get(
        "/v1/rules/candidates",
        params={"source_version_id": source["source_version_id"]},
    )
    assert candidates.status_code == 200, candidates.text
    assert candidates.json()
    for candidate in candidates.json():
        promoted = client.post(
            f"/v1/rules/candidates/{candidate['id']}/promote",
            json={"reviewed_by": "rules@example.test"},
        )
        assert promoted.status_code == 200, promoted.text
        reviewed = client.post(
            f"/v1/rules/{promoted.json()['id']}/review",
            json={"lifecycle_status": "approved", "reviewed_by": "rules@example.test"},
        )
        assert reviewed.status_code == 200, reviewed.text

    review = client.post(
        f"/v1/sources/{source['source_document_id']}/review",
        json={
            "review_status": "accepted",
            "source_version_id": source["source_version_id"],
            "reviewed_by": "reviewer@example.test",
        },
    )
    assert review.status_code == 200, review.text
    body = review.json()
    assert body["status"] == "pass", body
    assert body["can_support_retrieval"] is True
    return body


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


def test_retrieval_refuses_without_accepted_source_review(client):
    unsupported = client.post("/v1/ask-source-library", json={"question": "What is the obscure pool pump colour rule?"})
    assert unsupported.status_code == 200
    assert unsupported.json()["status"] == "unsupported"
    assert unsupported.json()["citations"] == []

    seed_source(client)
    still_unaccepted = client.post("/v1/ask-source-library", json={"question": "front setback garage dominance"})
    assert still_unaccepted.status_code == 200
    body = still_unaccepted.json()
    assert body["status"] == "unsupported"
    assert body["citations"] == []


def test_unknown_access_source_is_ingested_but_cannot_support_answers(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Unknown Access Planning Note",
            "jurisdiction": "WA",
            "authority": "Unknown authority",
            "source_type": "guidance",
            "canonical_url": "https://example.test/unknown-access-note",
            "licence_notes": "Access terms not reviewed.",
            "access_type": "unknown",
            "content": "5.1.3 Front setback unknown access content.",
            "version_label": "unknown-access",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["chunks_created"] >= 1

    answer = client.post("/v1/ask-source-library", json={"question": "front setback unknown access"})
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "unsupported"
    assert body["citations"] == []


def test_seeded_accepted_source_with_rule_coverage_gaps_cannot_support_chat(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted Bypass Normative Setback Fixture",
            "jurisdiction": "WA",
            "authority": "City of Cockburn",
            "local_government": "Cockburn",
            "source_type": "local_planning_policy",
            "canonical_url": "https://example.test/accepted-bypass-normative-setback",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": "5.1.3 Setback\nA wall must be set back at least 1.5m unless a variation is approved.",
            "version_label": "accepted",
        },
    )
    assert response.status_code == 200, response.text
    source = response.json()

    gate = client.get(
        f"/v1/sources/{source['source_document_id']}/versions/{source['source_version_id']}/acceptance-gate"
    )
    assert gate.status_code == 200, gate.text
    gate_body = gate.json()
    assert gate_body["status"] == "blocked"
    assert gate_body["can_support_retrieval"] is False

    answer = client.post(
        "/v1/ask-source-library",
        json={"question": "What setback must a wall meet in Cockburn?"},
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "unsupported"
    assert body["citations"] == []
    assert "1.5m" not in body["answer"]


def test_chat_style_source_question_refuses_pending_source_review(client):
    seed_source(client)

    search = client.get("/v1/source-chunks/search", params={"q": "what's the front-setback rule?"})
    assert search.status_code == 200, search.text
    assert search.json() == []

    answer = client.post(
        "/v1/ask-source-library",
        json={"question": "What's the front-setback rule and garage-dominance issue?"},
    )
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "unsupported"
    assert body["human_review_required"] is True
    assert body["citations"] == []


def test_chat_alias_accepts_message_payload(client):
    response = client.post("/v1/chat", json={"message": "Front setback rules?"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "unsupported"
    assert body["human_review_required"] is True
    assert "No accepted current source versions are available for citable retrieval." in body["missing_information"]


def test_unsupported_chat_reports_pending_source_coverage(client):
    accepted = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted Readiness R-Code Site Cover Table Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://example.test/readiness-r-code-site-cover-table",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "content": "\n".join(
                [
                    "R30 grouped dwelling site area requirements apply before the table.",
                    "C3.1.1 Development on each site does not exceed the maximum site cover percentages of Table 3.1a.",
                    "Table 3.1a Maximum site cover requirements",
                    "R20 maximum site cover 50 per cent.",
                    "R30 maximum site cover 55 per cent.",
                    "R40 maximum site cover 60 per cent.",
                ]
            ),
            "version_label": "accepted",
        },
    )
    assert accepted.status_code == 200, accepted.text
    accept_seeded_source_for_retrieval(client, accepted.json())
    pending = client.post(
        "/v1/sources/seed",
        json={
            "title": "Pending Eaves Coverage Fixture",
            "jurisdiction": "WA",
            "authority": "City of Stirling",
            "source_type": "local_planning_policy",
            "canonical_url": "https://example.test/pending-eaves-coverage-fixture",
            "licence_notes": "Public source fixture; human review required before use.",
            "access_type": "public",
            "content": "Eaves clearance material is pending review and not citable yet.",
            "version_label": "pending",
        },
    )
    assert pending.status_code == 200, pending.text

    response = client.post("/v1/chat", json={"message": "What is the eaves clearance rule?"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "unsupported"
    assert body["citations"] == []
    assert "1 current source version is pending review" in " ".join(body["missing_information"])


def test_chat_refuses_property_specific_question_without_resolved_context(client):
    response = client.post("/v1/chat", json={"message": "What is my setback?"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "missing_info"
    assert body["citations"] == []
    assert "resolved address/profile" in body["answer"]


def test_chat_refuses_design_compliance_question_without_project_evidence(client):
    response = client.post("/v1/chat", json={"message": "Does my design comply?"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "missing_info"
    assert body["citations"] == []
    assert "resolved address/profile" in body["answer"]


def test_chat_refuses_broad_setback_prompt_instead_of_fragment_snippets(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted Broad Setback Fragment Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://example.test/broad-setback-fragments",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": "\n".join(
                [
                    "1m minimum to secondary street",
                    "Front fences within the primary street setback area being a maximum height of 900mm above natural ground level.",
                    "Boundary setbacks",
                    "0.75m into the lot boundary setback.",
                ]
            ),
            "version_label": "accepted",
        },
    )
    assert response.status_code == 200, response.text

    answer = client.post("/v1/chat", json={"message": "What are the setbacks?"})

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "missing_info"
    assert body["citations"] == []
    assert "specific setback type" in " ".join(body["missing_information"])


def test_chat_refuses_proposal_build_question_without_property_context(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted NCC Farm Shed Fixture",
            "jurisdiction": "WA",
            "authority": "Australian Building Codes Board",
            "source_type": "ncc",
            "canonical_url": "https://example.test/ncc-farm-shed",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": "\n".join(
                [
                    "D3D14 applies where it serves a farm building or a farm shed.",
                    "The NCC has definitions of farm building and farm shed.",
                    "Farm sheds are often used for storage of farm vehicles.",
                ]
            ),
            "version_label": "accepted",
        },
    )
    assert response.status_code == 200, response.text

    answer = client.post("/v1/chat", json={"message": "Can I build a shed in Cockburn?"})

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "missing_info"
    assert body["citations"] == []
    assert "resolved address/profile" in body["answer"]


def test_chat_refuses_broad_two_storey_house_prompts_without_property_context(client):
    messages = [
        "Is a two storey house allowed?",
        "Can I have a two storey house?",
        "Can I add a second storey?",
        "Can we add a second storey?",
        "Can I add an upper floor?",
        "What are the two storey house rules?",
    ]

    for message in messages:
        answer = client.post("/v1/chat", json={"message": message})

        assert answer.status_code == 200, answer.text
        body = answer.json()
        assert body["status"] == "missing_info", message
        assert body["citations"] == []
        missing = " ".join(body["missing_information"]).lower()
        assert "property" in missing or "density code" in missing


def test_chat_suppresses_known_dead_fixture_citation_url(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Cockburn Dead Link Fixture",
            "jurisdiction": "WA",
            "authority": "City of Cockburn",
            "local_government": "Cockburn",
            "source_type": "local_planning_policy",
            "canonical_url": "https://www.cockburn.wa.gov.au/example-policy",
            "licence_notes": "Fixture source with a known dead demo URL.",
            "access_type": "public",
            "content": "5.1.3 Front setback\nPrimary street setbacks should be checked against the current R-Codes table.",
            "version_label": "accepted",
            "review_status": "accepted",
        },
    )
    assert response.status_code == 200, response.text

    answer = client.post("/v1/chat", json={"message": "Front setback rules?"})

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["citations"]
    assert {citation["canonical_url"] for citation in body["citations"]} == {None}


def test_chat_alias_accepts_messages_array_and_null_filters(client):
    response = client.post(
        "/v1/chat",
        json={
            "messages": [
                {"role": "system", "content": "Use approved sources only."},
                {"role": "user", "content": "Front setback rules?"},
            ],
            "source_filters": None,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "unsupported"


def test_project_chat_alias_accepts_message_payload(client):
    project = client.post(
        "/v1/projects",
        json={
            "project_name": "Chat Alias Project",
            "address": "1 Example Street",
            "local_government": "Cockburn",
            "project_type": "single_house",
            "stage": "concept",
        },
    )
    assert project.status_code == 200, project.text

    response = client.post(
        f"/v1/projects/{project.json()['id']}/chat",
        json={"message": "Front setback rules?", "filters": {"local_government": "Cockburn"}},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "unsupported"
    assert body["citations"] == []
    assert "No deterministic project evidence matched this question" in body["answer"]
    assert "approved source library also cannot support" in body["answer"]
    assert "No completed compliance run exists for this project." in body["missing_information"]


def test_project_chat_uses_source_lookup_without_project_evidence_for_rule_questions(client):
    source = client.post(
        "/v1/sources/seed",
        json={
            "title": "Cockburn Project Chat Source Fallback Fixture",
            "jurisdiction": "WA",
            "authority": "City of Cockburn",
            "local_government": "Cockburn",
            "source_type": "local_planning_policy",
            "canonical_url": "https://www.cockburn.wa.gov.au/front-setback-chat-fallback",
            "licence_notes": "Public council policy fixture.",
            "access_type": "public",
            "content": "5.1.3 Front setback\nCockburn front setback accepted text.",
            "version_label": "accepted",
            "review_status": "accepted",
        },
    )
    assert source.status_code == 200, source.text
    project = client.post(
        "/v1/projects",
        json={
            "project_name": "Project Chat Source Fallback Project",
            "address": "1 Example Street",
            "local_government": "Cockburn",
            "project_type": "single_house",
            "stage": "concept",
        },
    )
    assert project.status_code == 200, project.text

    response = client.post(
        f"/v1/projects/{project.json()['id']}/chat",
        json={"message": "Front setback"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "needs_human_review"
    assert body["citations"]
    assert "Source-library result for this project scope" in body["answer"]
    assert "Cockburn front setback accepted text" in body["answer"]
    assert "No completed compliance run exists for this project." in body["missing_information"]
    assert (
        "The cited source-library result has not verified this project's facts, measurements, or drawings."
        in body["missing_information"]
    )


def test_project_source_lookup_defaults_to_project_local_government_source_scope(client):
    cockburn = client.post(
        "/v1/sources/seed",
        json={
            "title": "Cockburn Accepted Front Setback Policy",
            "jurisdiction": "WA",
            "authority": "City of Cockburn",
            "local_government": "Cockburn",
            "source_type": "local_planning_policy",
            "canonical_url": "https://www.cockburn.wa.gov.au/front-setback-accepted",
            "licence_notes": "Public council policy fixture.",
            "access_type": "public",
            "content": "5.1.3 Front setback\nCockburn front setback accepted text.",
            "version_label": "accepted",
            "review_status": "accepted",
        },
    )
    assert cockburn.status_code == 200, cockburn.text
    fremantle = client.post(
        "/v1/sources/seed",
        json={
            "title": "Fremantle Accepted Front Setback Policy",
            "jurisdiction": "WA",
            "authority": "City of Fremantle",
            "local_government": "Fremantle",
            "source_type": "local_planning_policy",
            "canonical_url": "https://www.fremantle.wa.gov.au/front-setback-accepted",
            "licence_notes": "Public council policy fixture.",
            "access_type": "public",
            "content": "5.1.3 Front setback\nFremantle front setback accepted text.",
            "version_label": "accepted",
            "review_status": "accepted",
        },
    )
    assert fremantle.status_code == 200, fremantle.text
    project = client.post(
        "/v1/projects",
        json={
            "project_name": "Scoped Chat Project",
            "address": "1 Example Street",
            "local_government": "Cockburn",
            "project_type": "single_house",
            "stage": "concept",
        },
    )
    assert project.status_code == 200, project.text

    response = client.post(f"/v1/projects/{project.json()['id']}/ask-source", json={"message": "Front setback"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["citations"]
    assert {citation["source_title"] for citation in body["citations"]} == {
        "Cockburn Accepted Front Setback Policy"
    }
    assert "Fremantle" not in body["answer"]


def test_chat_prefers_requested_r_code_over_conflicting_r_code_snippets(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted R-Code Density Ranking Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://example.test/r-code-density-ranking",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "content": "\n".join(
                    [
                        "R80 Code standards apply to single houses and grouped dwellings in areas coded R100, R160 and RAC.",
                        "Road widening examples discuss adjusted street boundaries.",
                        "R30, R35 and R40 coded lots",
                    "Figure 3.3c Set back of garage from the primary street.",
                    "Street setback line Xm (Table 3.3a).",
                    "Table 3.3a Minimum setback of buildings from the street",
                    "Street type R30 R35 R40 R50 R60 R80",
                    "Primary street setback 4m 4m 3m 2m 2m 2m",
                    "C3.3.2 In areas coded R30, R35 and R40, primary street setback context appears after the table.",
                ]
            ),
            "version_label": "accepted",
        },
    )
    assert response.status_code == 200, response.text
    accept_seeded_source_for_retrieval(client, response.json())

    answer = client.post(
        "/v1/ask-source-library",
        json={"question": "What is the front setback for an R30 single house?"},
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["citations"]
    assert "R30 primary street setback: 4m" in body["answer"]
    assert "Figure 3.3c" not in body["answer"]
    assert "R80 Code standards" not in body["answer"]
    assert "may be reduced by up to 1m" not in body["answer"]


def test_chat_prefers_numeric_setback_table_over_density_context(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted R-Code Street Setback Table Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://example.test/r-code-street-setback-table",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "content": "\n".join(
                [
                    "R30 context",
                    "R30, as they relate to single houses, includes setbacks and other controls.",
                    "C3.3.3 Street setbacks",
                    "Table 3.3a Minimum setback of buildings from the street",
                    "Street type R30 R35 R40 R50 R60 R80",
                    "Primary street setback 4m 4m 3m 2m 2m 2m",
                    "Secondary street setback 1.5m 1.5m 1m 1m 1m 1m",
                ]
            ),
            "version_label": "accepted",
        },
    )
    assert response.status_code == 200, response.text
    accept_seeded_source_for_retrieval(client, response.json())

    answer = client.post(
        "/v1/ask-source-library",
        json={"question": "What is the front setback for an R30 single house?"},
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["citations"]
    assert "R30 primary street setback: 4m" in body["answer"]
    assert "R30, as they relate to single houses" not in body["answer"]


def test_chat_selects_density_table_row_instead_of_context_heading(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted R-Code Site Cover Table Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://example.test/r-code-site-cover-table",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "content": "\n".join(
                [
                    "R30 grouped dwelling site area requirements apply before the table.",
                    "C3.1.1 Development on each site does not exceed the maximum site cover percentages of Table 3.1a.",
                    "Table 3.1a Maximum site cover requirements",
                    "R20 maximum site cover 50 per cent.",
                    "R30 maximum site cover 55 per cent.",
                    "R40 maximum site cover 60 per cent.",
                ]
            ),
            "version_label": "accepted",
        },
    )
    assert response.status_code == 200, response.text
    accept_seeded_source_for_retrieval(client, response.json())

    answer = client.post(
        "/v1/ask-source-library",
        json={"question": "What is the site cover requirement for R30?"},
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["citations"]
    assert "R30 site cover: 55 per cent" in body["answer"]
    assert "site area requirements" not in body["answer"]
    assert "R20 maximum site cover 50 per cent" not in body["answer"]


def test_chat_stitches_fragmented_site_cover_table_from_same_source(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted Fragmented R-Code Site Cover Table Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://example.test/fragmented-r-code-site-cover",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": "\n".join(
                [
                    "C3.1.1 Development on each site does not exceed the maximum site cover percentages of Table 3.1a.",
                    "Table 3.1a Maximum site cover requirements",
                    "R30 R35 R40 R50 R60 R80",
                    "60% 60% 65% 65% 70% 70%",
                ]
            ),
            "version_label": "accepted",
        },
    )
    assert response.status_code == 200, response.text

    answer = client.post(
        "/v1/ask-source-library",
        json={"question": "What is the site cover requirement for R30?"},
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "needs_human_review"
    assert body["citations"]
    assert "R30 site cover: 60%" in body["answer"]
    assert {citation["clause_id"] for citation in body["citations"]} == {"C3.1.1"}


def test_chat_refuses_weak_density_requirement_match(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Cockburn Accepted Site Plan Note",
            "jurisdiction": "WA",
            "authority": "City of Cockburn",
            "local_government": "Cockburn",
            "source_type": "local_planning_policy",
            "canonical_url": "https://www.cockburn.wa.gov.au/site-plan-note",
            "licence_notes": "Public council policy fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": "5.3.1 Open space\nOpen space and site cover calculations should be shown on the site plan.",
            "version_label": "accepted",
        },
    )
    assert response.status_code == 200, response.text

    answer = client.post(
        "/v1/ask-source-library",
        json={"question": "What is the site cover requirement for R30?"},
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "unsupported"
    assert body["citations"] == []


def test_chat_refuses_requirement_answer_from_average_setback_calculation_example(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted Average Side Setback Calculation Example",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://www.wa.gov.au/average-side-setback-example",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": "\n".join(
                [
                    "3 Average side setback",
                    (
                        "The diagram below provides a method of calculating the average side setback, "
                        "however the example numbers are not deemed-to-comply."
                    ),
                    "3.25m Average side setback",
                    "Side boundary A = 3m x 3m = 9",
                    "Total length = 20m",
                    "Average side setback of 3.5m =",
                ]
            ),
            "version_label": "accepted",
        },
    )
    assert response.status_code == 200, response.text

    calculation_answer = client.post(
        "/v1/ask-source-library",
        json={"question": "How do I calculate average side setbacks?"},
    )

    assert calculation_answer.status_code == 200, calculation_answer.text
    calculation_body = calculation_answer.json()
    assert calculation_body["status"] == "needs_human_review"
    assert calculation_body["citations"]

    requirement_answer = client.post(
        "/v1/ask-source-library",
        json={"question": "What is the side setback requirement from the average side setback example?"},
    )

    assert requirement_answer.status_code == 200, requirement_answer.text
    requirement_body = requirement_answer.json()
    assert requirement_body["status"] == "unsupported"
    assert requirement_body["citations"] == []


def test_chat_refuses_ncc_condensation_question_from_unrelated_building_source(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted R-Code Building Bulk Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://www.wa.gov.au/r-code-building-bulk",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": "Building bulk can be affected by average side setback calculations.",
            "version_label": "accepted",
        },
    )
    assert response.status_code == 200, response.text

    answer = client.post(
        "/v1/ask-source-library",
        json={"question": "NCC condensation buildings"},
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "unsupported"
    assert body["citations"] == []


def test_chat_refuses_bushfire_bal_question_from_unrelated_area_source(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted Deep Soil Area Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://www.wa.gov.au/deep-soil-area-fixture",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": "Deep soil areas may include landscape design notes and area calculations.",
            "version_label": "accepted",
        },
    )
    assert response.status_code == 200, response.text

    answer = client.post(
        "/v1/ask-source-library",
        json={"question": "bushfire prone areas BAL report"},
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "unsupported"
    assert body["citations"] == []


def test_chat_refuses_livable_housing_question_from_generic_design_source(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted Landscape Design Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://www.wa.gov.au/landscape-design-fixture",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": "Landscape design guidance for apartments includes tree canopy and deep soil areas.",
            "version_label": "accepted",
        },
    )
    assert response.status_code == 200, response.text

    answer = client.post(
        "/v1/ask-source-library",
        json={"question": "livable housing design handbook"},
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "unsupported"
    assert body["citations"] == []


def test_chat_refuses_requirement_question_from_solar_background_without_normative_evidence(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted Solar Access Background Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://www.wa.gov.au/solar-access-background-fixture",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": (
                "Solar access is the capacity of a building to receive direct sunlight. "
                "Daylight changes with the time of day, season and weather conditions."
            ),
            "version_label": "accepted",
        },
    )
    assert response.status_code == 200, response.text
    unrelated_threshold = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted Unrelated Site Cover Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://www.wa.gov.au/unrelated-site-cover-fixture",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": "R30 maximum site cover 60%.",
            "version_label": "accepted",
        },
    )
    assert unrelated_threshold.status_code == 200, unrelated_threshold.text

    method_answer = client.post(
        "/v1/ask-source-library",
        json={"question": "How do I demonstrate solar access?"},
    )
    assert method_answer.status_code == 200, method_answer.text
    assert method_answer.json()["status"] == "needs_human_review"

    requirement_answer = client.post(
        "/v1/ask-source-library",
        json={"question": "What are the solar access requirements?"},
    )

    assert requirement_answer.status_code == 200, requirement_answer.text
    body = requirement_answer.json()
    assert body["status"] == "unsupported"
    assert body["citations"] == []


def test_chat_merges_lexical_candidates_when_vector_candidate_has_weak_evidence(client, monkeypatch):
    weak = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted Solar Contents Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://www.wa.gov.au/solar-contents-fixture",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": "Solar and daylight\naccess\nContents",
            "version_label": "accepted",
        },
    )
    assert weak.status_code == 200, weak.text
    strong = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted Solar Demonstration Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://www.wa.gov.au/solar-demonstration-fixture",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": "The following diagrams are an example of how solar access can be demonstrated.",
            "version_label": "accepted",
        },
    )
    assert strong.status_code == 200, strong.text
    weak_search = client.get("/v1/source-chunks/search", params={"q": "contents"})
    assert weak_search.status_code == 200, weak_search.text
    weak_chunk_id = weak_search.json()[0]["chunk_id"]

    from draftcheck_retrieval.service import RetrievalService

    monkeypatch.setattr(
        RetrievalService,
        "_candidate_chunk_scores_from_vector",
        lambda self, query, limit: {weak_chunk_id: 0.9},
    )

    answer = client.post(
        "/v1/ask-source-library",
        json={"question": "How do I demonstrate solar access?"},
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "needs_human_review"
    assert body["citations"]
    assert body["citations"][0]["source_title"] == "Accepted Solar Demonstration Fixture"
    assert "solar access can be demonstrated" in body["answer"]


def test_chat_refuses_natural_ventilation_question_from_solar_only_source(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted Solar Daylight Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://www.wa.gov.au/solar-daylight-fixture",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": "Solar and daylight access can contribute to amenity for apartments.",
            "version_label": "accepted",
        },
    )
    assert response.status_code == 200, response.text
    checklist = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted Cross Ventilation Checklist Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://www.wa.gov.au/cross-ventilation-checklist-fixture",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": (
                "Development details should include the indicative percentage of apartments receiving "
                "the minimum level of cross ventilation and daylight access."
            ),
            "version_label": "accepted",
        },
    )
    assert checklist.status_code == 200, checklist.text

    answer = client.post(
        "/v1/ask-source-library",
        json={"question": "How should I orient apartments for natural ventilation?"},
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "unsupported"
    assert body["citations"] == []


def test_development_application_question_excludes_unrelated_materials_source(client):
    application = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted Development Application Guidance Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://www.wa.gov.au/development-application-guidance-fixture",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": (
                "Development application guidance assists proponents in formulating the appropriate "
                "materials when submitting a development application."
            ),
            "version_label": "accepted",
        },
    )
    assert application.status_code == 200, application.text
    unrelated = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted Structural Materials Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://www.wa.gov.au/structural-materials-fixture",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": "Structural materials such as rock can support root zones under pavements.",
            "version_label": "accepted",
        },
    )
    assert unrelated.status_code == 200, unrelated.text

    answer = client.post(
        "/v1/ask-source-library",
        json={"question": "What materials are needed for a development application under R-Codes Volume 2?"},
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "needs_human_review"
    assert body["citations"]
    assert {citation["source_title"] for citation in body["citations"]} == {
        "Accepted Development Application Guidance Fixture"
    }


def test_design_review_question_excludes_unrelated_volume_two_guidance(client):
    design_review = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted Design Review Guidance Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://www.wa.gov.au/design-review-guidance-fixture",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": (
                "R-Codes Volume 2 design review guidance lists basic information that should be "
                "provided by the applicant for design review prior to development application."
            ),
            "version_label": "accepted",
        },
    )
    assert design_review.status_code == 200, design_review.text
    unrelated = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted Deep Soil Calculation Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://www.wa.gov.au/deep-soil-calculation-fixture",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": (
                "SPP 7.3 R-Codes Volume 2 Apartments explains tree canopy and deep soil area "
                "calculation examples."
            ),
            "version_label": "accepted",
        },
    )
    assert unrelated.status_code == 200, unrelated.text

    answer = client.post(
        "/v1/ask-source-library",
        json={"question": "What information should be provided for R-Codes Volume 2 design review?"},
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "needs_human_review"
    assert body["citations"]
    assert {citation["source_title"] for citation in body["citations"]} == {
        "Accepted Design Review Guidance Fixture"
    }


def test_chat_refuses_non_operative_background_docs_for_can_i_build_question(client):
    for title, content in [
        (
            "Medium Density Housing Code Submission Summary",
            "\n".join(
                [
                    "3.2 Building height",
                    "Community concern was raised about three storeys in R40 areas.",
                    "Reduction of building height in R40 to two storeys.",
                ]
            ),
        ),
        (
            "Medium Density Housing Code Testing Report",
            "\n".join(
                [
                    "2 R-Codes Volume 1 Medium Density Testing Report",
                    "Designers reviewed apartments on R40-R60 coded lots and two storey dwellings.",
                ]
            ),
        ),
    ]:
        response = client.post(
            "/v1/sources/seed",
            json={
                "title": title,
                "jurisdiction": "WA",
                "authority": "Department of Planning, Lands and Heritage",
                "source_type": "guidance",
                "canonical_url": f"https://example.test/{title.lower().replace(' ', '-')}",
                "licence_notes": "Public background document fixture.",
                "access_type": "public",
                "review_status": "accepted",
                "content": content,
                "version_label": "accepted",
            },
        )
        assert response.status_code == 200, response.text

    answer = client.post(
        "/v1/chat",
        json={"question": "Can I build a two storey house in R40 in Cockburn?"},
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "missing_info"
    assert body["citations"] == []
    assert "resolved address/profile" in body["answer"]


def test_chat_refuses_first_person_build_question_from_operative_r_code_snippet(client):
    background = client.post(
        "/v1/sources/seed",
        json={
            "title": "Medium Density Housing Code Submission Summary",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "guidance",
            "canonical_url": "https://example.test/medium-density-submission-summary",
            "licence_notes": "Public background document fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": "\n".join(
                [
                    "3.2 Building height",
                    "Reduction of building height in R40 to two storeys.",
                ]
            ),
            "version_label": "accepted",
        },
    )
    assert background.status_code == 200, background.text
    operative = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted R-Code Building Height Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://example.test/r-code-building-height",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": "\n".join(
                [
                    "C3.2.1 Building height",
                    "For R40 coded lots, a single house may be two storeys where other standards are satisfied.",
                ]
            ),
            "version_label": "accepted",
        },
    )
    assert operative.status_code == 200, operative.text

    answer = client.post(
        "/v1/chat",
        json={"question": "Can I build a two storey house in R40 in Cockburn?"},
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "missing_info"
    assert body["citations"] == []
    assert "resolved address/profile" in body["answer"]
    assert "single house may be two storeys" not in body["answer"]

    source_question = client.post(
        "/v1/chat",
        json={"question": "What does the R-Code say about two storey single houses in R40?"},
    )

    assert source_question.status_code == 200, source_question.text
    source_body = source_question.json()
    assert source_body["status"] == "needs_human_review"
    assert source_body["citations"]
    assert {citation["source_title"] for citation in source_body["citations"]} == {
        "Accepted R-Code Building Height Fixture"
    }
    assert "single house may be two storeys" in source_body["answer"]
    assert "Submission Summary" not in source_body["answer"]


def test_chat_refuses_r40_house_context_without_storey_or_height_support(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted R-Code Adjacent Context Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://example.test/r-code-adjacent-context",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": "\n".join(
                [
                    "R30, R35 and R40 coded lots",
                    "Figure 3.3c Set back of garage from the primary street.",
                    "R40 Single house 45 20 4 1 *",
                    "Secondary street includes communal street, private street, and right-of-way as street.",
                ]
            ),
            "version_label": "accepted",
        },
    )
    assert response.status_code == 200, response.text

    answer = client.post(
        "/v1/chat",
        json={"question": "Can I build a two storey house in R40 in Cockburn?"},
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "missing_info"
    assert body["citations"] == []
    assert "resolved address/profile" in body["answer"]


def test_chat_refuses_storey_context_without_single_house_support(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Accepted R-Code Volume 2 Context Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://example.test/r-code-volume-2-context",
            "licence_notes": "Public source fixture.",
            "access_type": "public",
            "review_status": "accepted",
            "content": "\n".join(
                [
                    "A2 Streetscape character types",
                    "Single houses are referenced elsewhere in the source framework.",
                    "Suburban contexts include detached housing, group housing and apartments.",
                    "They are predominately 1-2 storeys but may include 3-storey development.",
                    "Note: Refer to R-Codes Volume 1 for R40 and R50 development.",
                ]
            ),
            "version_label": "accepted",
        },
    )
    assert response.status_code == 200, response.text

    answer = client.post(
        "/v1/chat",
        json={"question": "Can I build a two storey house in R40 in Cockburn?"},
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "missing_info"
    assert body["citations"] == []
    assert "resolved address/profile" in body["answer"]


def test_australian_standard_requirement_questions_are_not_answered_from_metadata(client):
    seed_source(client)

    answer = client.post(
        "/v1/ask-source-library",
        json={"question": "What are the AS 3959 full text requirements for bushfire construction?"},
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "unsupported"
    assert body["citations"] == []
    assert "Australian Standards full text is not stored" in body["answer"]
