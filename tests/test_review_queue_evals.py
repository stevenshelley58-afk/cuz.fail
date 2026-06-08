from __future__ import annotations

from tests.test_sources_retrieval import accept_seeded_source_for_retrieval


def test_compliance_run_creates_idempotent_blocking_review_queue_items(client):
    project_response = client.post(
        "/v1/projects",
        json={
            "project_name": "Review queue project",
            "address": "1 Example Street, Spearwood WA",
            "local_government": "Cockburn",
            "project_type": "single_house",
            "stage": "concept",
            "as_of_date": "2026-06-06",
            "assessment_basis": "current_rules",
        },
    )
    assert project_response.status_code == 200, project_response.text
    project_id = project_response.json()["id"]

    first_run = client.post(f"/v1/projects/{project_id}/compliance/run")
    assert first_run.status_code == 200, first_run.text
    first_items = client.get("/v1/review-queues", params={"project_id": project_id})
    assert first_items.status_code == 200, first_items.text
    first_body = first_items.json()
    assert first_body
    assert {item["queue"] for item in first_body} == {"conflict_review"}
    assert {item["blocking_level"] for item in first_body} == {"blocking"}
    assert all(item["status"] == "open" for item in first_body)
    assert all(item["evidence"]["check_result_id"] for item in first_body)
    assert any("approved source citation" in item["evidence"]["missing_information"] for item in first_body)

    second_run = client.post(f"/v1/projects/{project_id}/compliance/run")
    assert second_run.status_code == 200, second_run.text
    second_items = client.get("/v1/review-queues", params={"project_id": project_id})
    assert second_items.status_code == 200, second_items.text
    assert len(second_items.json()) == len(first_body)

    patch = client.patch(
        f"/v1/review-queues/{first_body[0]['id']}",
        json={"status": "resolved", "reviewed_by": "reviewer@example.test"},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["status"] == "resolved"

    audit = client.get("/v1/audit", params={"project_id": project_id})
    assert audit.status_code == 200, audit.text
    assert any(event["action"] == "review_queue.reviewed" for event in audit.json())


def test_rfi_draft_with_unsupported_source_support_enqueues_blocking_review_item(client):
    project_response = client.post(
        "/v1/projects",
        json={
            "project_name": "RFI source review project",
            "address": "1 Example Street, Spearwood WA",
            "local_government": "Cockburn",
            "project_type": "single_house",
            "stage": "RFI",
            "as_of_date": "2026-06-06",
            "assessment_basis": "current_rules",
        },
    )
    assert project_response.status_code == 200, project_response.text
    project_id = project_response.json()["id"]
    rfi = client.post(
        f"/v1/projects/{project_id}/rfi/parse",
        json={"text": "1. Please confirm the front setback dimension and update the site plan."},
    )
    assert rfi.status_code == 200, rfi.text
    assert len(rfi.json()) == 1
    assert rfi.json()[0]["requested_action"].startswith("Please confirm")
    assert rfi.json()[0]["source_requirement_candidates"] == []

    first_draft = client.post(f"/v1/projects/{project_id}/rfi/draft-response")
    assert first_draft.status_code == 200, first_draft.text
    second_draft = client.post(f"/v1/projects/{project_id}/rfi/draft-response")
    assert second_draft.status_code == 200, second_draft.text

    queue = client.get("/v1/review-queues", params={"project_id": project_id, "queue": "source_review"})
    assert queue.status_code == 200, queue.text
    items = queue.json()
    assert len(items) == 1
    item = items[0]
    assert item["blocking_level"] == "blocking"
    assert item["status"] == "open"
    assert item["target_type"] == "rfi_item"
    assert item["target_id"] == rfi.json()[0]["id"]
    assert item["reason"] == "RFI item 1 lacks approved source support"
    assert item["priority"] == "high"
    assert item["evidence"]["rfi_item_id"] == rfi.json()[0]["id"]
    assert item["evidence"]["response_draft_id"] == second_draft.json()["id"]
    assert item["evidence"]["source_support_status"] == "unsupported"
    assert "approved source citation for RFI item 1" in item["evidence"]["missing_information"]


def test_repeated_rfi_parse_reuses_existing_item_instead_of_duplicate_work(client):
    project_response = client.post(
        "/v1/projects",
        json={
            "project_name": "Repeated RFI parse project",
            "address": "1 Example Street, Spearwood WA",
            "local_government": "Cockburn",
            "project_type": "single_house",
            "stage": "RFI",
            "as_of_date": "2026-06-06",
            "assessment_basis": "current_rules",
        },
    )
    assert project_response.status_code == 200, project_response.text
    project_id = project_response.json()["id"]
    payload = {"text": "1. Please confirm the front setback dimension and update the site plan."}

    first_parse = client.post(f"/v1/projects/{project_id}/rfi/parse", json=payload)
    assert first_parse.status_code == 200, first_parse.text
    second_parse = client.post(f"/v1/projects/{project_id}/rfi/parse", json=payload)
    assert second_parse.status_code == 200, second_parse.text

    assert [item["id"] for item in second_parse.json()] == [item["id"] for item in first_parse.json()]
    items = client.get(f"/v1/projects/{project_id}/rfi/items")
    assert items.status_code == 200, items.text
    assert len(items.json()) == 1
    assert items.json()[0]["item_number"] == 1

    draft = client.post(f"/v1/projects/{project_id}/rfi/draft-response")
    assert draft.status_code == 200, draft.text
    draft_body = draft.json()
    assert draft_body["draft_text"].count("Item 1:") == 1

    queue = client.get("/v1/review-queues", params={"project_id": project_id, "queue": "source_review"})
    assert queue.status_code == 200, queue.text
    assert len(queue.json()) == 1


def test_golden_eval_run_executes_retrieval_case_and_passes_without_review_queue(client):
    case = client.post(
        "/v1/evals/cases",
        json={
            "track": "retrieval",
            "name": "Australian Standards full text refusal",
            "input": {"question": "What are the AS 3959 full text requirements for bushfire construction?"},
            "expected": {"status": "unsupported", "citation_count": 0, "source_version_ids": []},
        },
    )
    assert case.status_code == 200, case.text

    run = client.post("/v1/evals/run", json={"track": "retrieval", "commit_sha": "test-sha", "run_by": "ci"})

    assert run.status_code == 200, run.text
    body = run.json()
    assert body["status"] == "passed"
    assert body["passed"] is True
    assert body["case_count"] == 1
    assert body["passed_count"] == 1
    assert body["failed_count"] == 0
    assert body["metrics"]["release_gate_satisfied"] is True
    assert body["metrics"]["false_likely_pass_count"] == 0
    assert body["case_results"][0]["status"] == "passed"

    queue = client.get("/v1/review-queues", params={"queue": "eval_failure_review"})
    assert queue.status_code == 200, queue.text
    assert queue.json() == []


def test_retrieval_eval_checks_answer_and_citation_quality(client):
    source = client.post(
        "/v1/sources/seed",
        json={
            "title": "Eval R-Code Density Ranking Fixture",
            "jurisdiction": "WA",
            "authority": "Department of Planning, Lands and Heritage",
            "source_type": "r_code",
            "canonical_url": "https://example.test/eval-r-code-density-ranking",
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
                ]
            ),
            "version_label": "accepted",
        },
    )
    assert source.status_code == 200, source.text
    accept_seeded_source_for_retrieval(client, source.json())
    case = client.post(
        "/v1/evals/cases",
        json={
            "track": "retrieval",
            "name": "R30 retrieval avoids conflicting R80 snippet",
            "input": {"question": "What is the front setback for an R30 single house?"},
            "expected": {
                "status": "needs_human_review",
                "min_citation_count": 1,
                "answer_contains": ["R30 primary street setback: 4m"],
                "answer_not_contains": ["R80 Code standards"],
                "citation_titles_include": ["Eval R-Code Density Ranking Fixture"],
            },
        },
    )
    assert case.status_code == 200, case.text

    run = client.post("/v1/evals/run", json={"track": "retrieval", "commit_sha": "test-sha", "run_by": "ci"})

    assert run.status_code == 200, run.text
    body = run.json()
    assert body["status"] == "passed"
    assert body["passed"] is True
    assert body["case_results"][0]["status"] == "passed"


def test_retrieval_eval_quality_mismatch_enqueues_failure(client):
    case = client.post(
        "/v1/evals/cases",
        json={
            "track": "retrieval",
            "name": "Retrieval answer quality mismatch fixture",
            "input": {"question": "What is the obscure pool pump colour rule?"},
            "expected": {
                "status": "unsupported",
                "citation_count": 0,
                "answer_contains": ["nonexistent expected wording"],
            },
        },
    )
    assert case.status_code == 200, case.text

    run = client.post("/v1/evals/run", json={"track": "retrieval", "commit_sha": "test-sha", "run_by": "ci"})

    assert run.status_code == 200, run.text
    body = run.json()
    assert body["status"] == "failed"
    assert body["passed"] is False
    assert body["case_results"][0]["status"] == "failed"
    assert any(mismatch["path"] == "$.answer_contains[0]" for mismatch in body["case_results"][0]["mismatches"])

    queue = client.get("/v1/review-queues", params={"queue": "eval_failure_review"})
    assert queue.status_code == 200, queue.text
    assert len(queue.json()) == 1


def test_golden_eval_run_enqueues_failure_when_expected_output_mismatches(client):
    case = client.post(
        "/v1/evals/cases",
        json={
            "track": "rule_extraction",
            "name": "Front setback minimum fixture",
            "input": {"q": "front_setback_min_m", "local_government": "Fixture"},
            "expected": {"value": 6.0, "unit": "m"},
            "source_version_ids": [],
            "notes": "Fixture only; expected value must be source-verified before release use.",
        },
    )
    assert case.status_code == 200, case.text
    assert case.json()["track"] == "rule_extraction"

    run = client.post(
        "/v1/evals/run",
        json={"track": "rule_extraction", "commit_sha": "test-sha", "run_by": "ci"},
    )
    assert run.status_code == 200, run.text
    body = run.json()
    assert body["status"] == "failed"
    assert body["passed"] is False
    assert body["case_count"] == 1
    assert body["passed_count"] == 0
    assert body["failed_count"] == 1
    assert body["metrics"]["release_gate_satisfied"] is False
    assert body["metrics"]["false_likely_pass_count"] == 0
    assert body["case_results"][0]["reason"] == "Expected output did not match actual output."
    assert body["case_results"][0]["mismatches"]

    fetched = client.get(f"/v1/evals/runs/{body['id']}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["id"] == body["id"]

    queue = client.get("/v1/review-queues", params={"queue": "eval_failure_review"})
    assert queue.status_code == 200, queue.text
    items = queue.json()
    assert len(items) == 1
    assert items[0]["target_type"] == "golden_eval_run"
    assert items[0]["target_id"] == body["id"]
    assert items[0]["priority"] == "critical"


def test_ops_dashboard_reports_safety_rates_and_release_gate(client):
    project_response = client.post(
        "/v1/projects",
        json={
            "project_name": "Ops dashboard project",
            "address": "1 Example Street, Spearwood WA",
            "local_government": "Cockburn",
            "project_type": "single_house",
            "stage": "concept",
            "as_of_date": "2026-06-06",
            "assessment_basis": "current_rules",
        },
    )
    assert project_response.status_code == 200, project_response.text
    project_id = project_response.json()["id"]

    source = client.post(
        "/v1/sources/seed",
        json={
            "title": "Ops Dashboard Unknown Licence Source",
            "jurisdiction": "WA",
            "authority": "Example authority",
            "source_type": "guidance",
            "canonical_url": "https://example.test/ops-dashboard-source",
            "licence_notes": "Access terms not reviewed.",
            "access_type": "unknown",
            "content": "5.1 Front setback\nA wall must be set back at least 1.5 m unless exempt.",
            "version_label": "ops-fixture",
        },
    )
    assert source.status_code == 200, source.text

    run_checks = client.post(f"/v1/projects/{project_id}/compliance/run")
    assert run_checks.status_code == 200, run_checks.text

    case = client.post(
        "/v1/evals/cases",
        json={
            "track": "compliance",
            "name": "Ops dashboard compliance fixture",
            "input": {"project_id": project_id},
            "expected": {"statuses_by_check": {"site_cover": "missing_info"}},
        },
    )
    assert case.status_code == 200, case.text
    eval_run = client.post("/v1/evals/run", json={"track": "compliance", "run_by": "ci"})
    assert eval_run.status_code == 200, eval_run.text
    assert eval_run.json()["metrics"]["false_likely_pass_count"] == 0

    dashboard = client.get("/v1/ops/dashboard")

    assert dashboard.status_code == 200, dashboard.text
    body = dashboard.json()
    assert body["sources"]["documents"]["total"] == 1
    assert body["sources"]["versions"]["current"] == 1
    assert body["sources"]["restricted_licence_reviews"] == 1
    assert body["compliance"]["total_results"] > 0
    assert body["compliance"]["unsupported_count"] > 0
    assert body["compliance"]["unsupported_rate"] > 0
    assert body["evals"]["tracks"]["compliance"]["active_case_count"] == 1
    assert body["evals"]["tracks"]["compliance"]["latest_run"]["passed"] is True
    assert body["review_queues"]["by_queue"]["conflict_review"]["blocking_open"] > 0
    assert body["review_queues"]["by_queue"]["eval_failure_review"]["blocking_open"] == 0
    assert body["review_queues"]["by_queue"]["source_review"] == {"total": 0, "open": 0, "blocking_open": 0}
    assert body["backups"]["backup_verified"] is False
    assert body["backups"]["restore_verified"] is False
    assert body["release_gate"]["satisfied"] is False
    assert "unsupported_or_missing_info_compliance_results_present" not in body["issues"]
    assert "unsupported_compliance_results_present" in body["health_signals"]
    assert "golden_eval_release_gate_not_satisfied" not in body["issues"]
    assert "last_successful_backup_not_recorded" in body["issues"]
