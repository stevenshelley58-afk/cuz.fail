from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from draftcheck_core.database import Base
from draftcheck_core.evals import GoldenEvalService
from draftcheck_core.json_utils import from_json, hash_text, normalize_text, to_json
from draftcheck_core.models import (
    AddressFact,
    AddressProfile,
    CheckResult,
    CheckRun,
    Clause,
    ClauseDisposition,
    DecisionTrace,
    Export,
    GoldenEvalCase,
    LocalGovernmentFact,
    Project,
    ResolvedRule,
    ResponseDraft,
    RfiItem,
    RuleExtractionCandidate,
    RuleRow,
    SourceChunk,
    SourceCitation,
    SourceDocument,
    SourceLicenceReview,
    SourceVersion,
    utcnow,
)
from draftcheck_core.source_governance import SourceGovernanceService
from draftcheck_core.source_support import source_version_can_support_regulatory_output
from draftcheck_retrieval.service import RetrievalService
from draftcheck_shared.schemas import Citation, GoldenEvalRunRequest, SourceReviewRequest


def test_source_review_api_blocks_citable_retrieval_with_rule_gate_gaps(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Acceptance Gate Blocking Policy",
            "jurisdiction": "WA",
            "authority": "Example council",
            "source_type": "local_planning_policy",
            "canonical_url": "https://example.test/acceptance-gate-blocking",
            "licence_notes": "Public council policy fixture.",
            "access_type": "public",
            "content": "5.1 Street setbacks\nA wall must be set back at least 1.5 m unless exempt.",
            "version_label": "current",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()

    review = client.post(
        f"/v1/sources/{body['source_document_id']}/review",
        json={
            "review_status": "accepted",
            "source_version_id": body["source_version_id"],
            "reviewed_by": "reviewer@example.test",
        },
    )

    assert review.status_code == 200, review.text
    gate = review.json()
    assert gate["status"] == "blocked"
    assert gate["can_support_retrieval"] is False
    assert gate["review_status"] == "pending_review"
    assert any(check["name"] == "rule_coverage" and check["blocking"] for check in gate["checks"])
    assert any(check["name"] == "no_orphan" and check["blocking"] for check in gate["checks"])
    assert gate["enqueued_review_item_ids"]

    repeat_review = client.post(
        f"/v1/sources/{body['source_document_id']}/review",
        json={
            "review_status": "accepted",
            "source_version_id": body["source_version_id"],
            "reviewed_by": "reviewer@example.test",
        },
    )
    assert repeat_review.status_code == 200, repeat_review.text
    queue = client.get("/v1/review-queues")
    assert queue.status_code == 200, queue.text
    assert not any(item["evidence"].get("check") == "blocking_review_queue" for item in queue.json())

    answer = client.post("/v1/ask-source-library", json={"question": "wall setback 1.5 m"})
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "unsupported"
    assert body["human_review_required"] is True
    assert body["citations"] == []


def test_acceptance_gate_endpoint_enqueues_detailed_rule_review_items(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Acceptance Gate Detailed Queue Policy",
            "jurisdiction": "WA",
            "authority": "Example council",
            "source_type": "local_planning_policy",
            "canonical_url": "https://example.test/acceptance-gate-detailed-queue",
            "licence_notes": "Public council policy fixture.",
            "access_type": "public",
            "content": "5.1 Street setbacks\nA wall must be set back at least 1.5 m unless exempt.",
            "version_label": "current",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()

    gate = client.get(
        f"/v1/sources/{body['source_document_id']}/versions/{body['source_version_id']}/acceptance-gate",
        params={"enqueue_review_items": True},
    )

    assert gate.status_code == 200, gate.text
    gate_body = gate.json()
    assert gate_body["status"] == "blocked"
    assert gate_body["enqueued_review_item_ids"]

    queue = client.get(
        "/v1/review-queues",
        params={"queue": "rule_review", "status": "open"},
    )
    assert queue.status_code == 200, queue.text
    items = queue.json()
    detailed_items = [item for item in items if item["source_version_id"] == body["source_version_id"]]
    assert {"clause", "rule_extraction_candidate"}.issubset(
        {item["target_type"] for item in detailed_items}
    )
    assert any(item["evidence"].get("audit") == "rule_coverage" for item in detailed_items)
    assert any(item["evidence"].get("audit") == "no_orphan" for item in detailed_items)
    assert any(item["evidence"].get("status") == "candidate_not_promoted" for item in detailed_items)
    assert any(item["target_type"] == "rule_extraction_candidate" for item in detailed_items)
    assert any(item["evidence"].get("status") == "unclaimed_numeric_token" for item in detailed_items)
    assert not any(item["target_type"] == "source_version" for item in detailed_items)

    repeat_gate = client.get(
        f"/v1/sources/{body['source_document_id']}/versions/{body['source_version_id']}/acceptance-gate",
        params={"enqueue_review_items": True},
    )
    assert repeat_gate.status_code == 200, repeat_gate.text
    repeat_queue = client.get(
        "/v1/review-queues",
        params={"queue": "rule_review", "status": "open"},
    )
    assert len(repeat_queue.json()) == len(items)

    scoped_queue = client.get(
        "/v1/review-queues",
        params={
            "queue": "rule_review",
            "status": "open",
            "source_version_id": body["source_version_id"],
        },
    )
    assert scoped_queue.status_code == 200, scoped_queue.text
    scoped_items = scoped_queue.json()
    assert scoped_items
    assert {item["source_version_id"] for item in scoped_items} == {body["source_version_id"]}


def test_source_review_queue_reconcile_resolves_stale_items_but_keeps_current_blockers(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Acceptance Gate Reconcile Policy",
            "jurisdiction": "WA",
            "authority": "Example council",
            "source_type": "local_planning_policy",
            "canonical_url": "https://example.test/acceptance-gate-reconcile",
            "licence_notes": "Public council policy fixture.",
            "access_type": "public",
            "content": "5.1 Street setbacks\nA wall must be set back at least 1.5 m unless exempt.",
            "version_label": "current",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()

    gate = client.get(
        f"/v1/sources/{body['source_document_id']}/versions/{body['source_version_id']}/acceptance-gate",
        params={"enqueue_review_items": True},
    )
    assert gate.status_code == 200, gate.text
    current_item_ids = set(gate.json()["enqueued_review_item_ids"])
    assert current_item_ids

    stale = client.post(
        "/v1/review-queues",
        json={
            "queue": "rule_review",
            "source_version_id": body["source_version_id"],
            "target_type": "source_version",
            "target_id": body["source_version_id"],
            "reason": "Source acceptance blocked: Rule coverage audit has blocking gaps.",
            "suggested_action": "Legacy generic blocker fixture.",
            "priority": "high",
        },
    )
    assert stale.status_code == 200, stale.text

    reconcile = client.post(
        f"/v1/sources/{body['source_document_id']}/versions/"
        f"{body['source_version_id']}/review-queue/reconcile",
        params={"reviewed_by": "reviewer@example.test"},
    )

    assert reconcile.status_code == 200, reconcile.text
    reconciled = reconcile.json()
    assert stale.json()["id"] in reconciled["resolved_item_ids"]
    assert current_item_ids.issubset(set(reconciled["still_open_item_ids"]))
    assert reconciled["gate"]["status"] == "blocked"
    assert reconciled["gate"]["can_support_retrieval"] is False

    open_items = client.get(
        "/v1/review-queues",
        params={"source_version_id": body["source_version_id"], "status": "open"},
    )
    assert open_items.status_code == 200, open_items.text
    assert stale.json()["id"] not in {item["id"] for item in open_items.json()}

    resolved_items = client.get(
        "/v1/review-queues",
        params={"source_version_id": body["source_version_id"], "status": "resolved"},
    )
    assert resolved_items.status_code == 200, resolved_items.text
    resolved_by_id = {item["id"]: item for item in resolved_items.json()}
    assert resolved_by_id[stale.json()["id"]]["evidence"]["reconciled_by"] == "reviewer@example.test"


def test_blocked_source_with_rule_gaps_does_not_support_regulatory_output_or_retrieval():
    db = _session()
    try:
        source, version = _citable_source_with_rule_gaps(db)

        gate = SourceGovernanceService(db).review_source(
            source.id,
            SourceReviewRequest(
                review_status="accepted",
                source_version_id=version.id,
                reviewed_by="reviewer@example.test",
            ),
        )

        assert gate.status == "blocked"
        assert gate.can_support_retrieval is False
        assert gate.review_status == "pending_review"
        assert version.review_status == "pending_review"
        assert source_version_can_support_regulatory_output(db, version.id) is False

        answer = RetrievalService(db).ask("wall setback 1.5 m")
        assert answer.status == "unsupported"
        assert answer.human_review_required is True
        assert answer.citations == []
    finally:
        db.close()


def test_legacy_accepted_source_with_rule_gaps_is_not_citable_without_open_review_queue():
    db = _session()
    try:
        _source, version = _citable_source_with_rule_gaps(db)
        version.review_status = "accepted"
        version.reviewed_by = "legacy-import"
        version.reviewed_at = utcnow()
        db.flush()

        answer = RetrievalService(db).ask("wall setback 1.5 m")

        assert answer.status == "unsupported"
        assert answer.citations == []
        assert "Accepted source versions exist but none currently pass the citable retrieval gate." in (
            answer.missing_information
        )
    finally:
        db.close()


def test_source_acceptance_allows_cited_retrieval_after_gate_passes():
    db = _session()
    try:
        source, version = _accepted_ready_source(db)

        assert RetrievalService(db).citation_for_check("wall setback 1.5 m") == []

        gate = SourceGovernanceService(db).review_source(
            source.id,
            SourceReviewRequest(
                review_status="accepted",
                source_version_id=version.id,
                reviewed_by="reviewer@example.test",
            ),
        )

        assert gate.status == "pass"
        assert gate.can_support_retrieval is True
        assert gate.review_status == "accepted"
        assert version.review_status == "accepted"

        answer = RetrievalService(db).ask("wall setback 1.5 m")

        assert answer.status == "needs_human_review"
        assert answer.citations
        assert answer.citations[0].source_version_id == version.id
        citations = RetrievalService(db).citation_for_check("wall setback 1.5 m")
        assert len(citations) == 1
        assert citations[0].source_version_id == version.id
    finally:
        db.close()


def test_source_acceptance_blocks_active_eval_case_without_passing_run():
    db = _session()
    try:
        source, version = _accepted_ready_source(db)
        db.add(
            GoldenEvalCase(
                track="rule_extraction",
                name="Rule extraction acceptance fixture",
                input_json=to_json({"source_version_id": version.id}),
                expected_json=to_json({"rule_key": "wall_setback"}),
                is_active=True,
            )
        )
        db.flush()

        gate = SourceGovernanceService(db).review_source(
            source.id,
            SourceReviewRequest(
                review_status="accepted",
                source_version_id=version.id,
                reviewed_by="reviewer@example.test",
            ),
        )

        assert gate.status == "blocked"
        assert gate.can_support_retrieval is False
        assert any(check.name == "golden_evals" and check.blocking for check in gate.checks)
    finally:
        db.close()


def test_source_acceptance_passes_after_source_scoped_eval_run_passes():
    db = _session()
    try:
        source, version = _accepted_ready_source(db)
        db.add(
            GoldenEvalCase(
                track="rule_extraction",
                name="Rule extraction source acceptance fixture",
                input_json=to_json({"source_version_id": version.id}),
                expected_json=to_json(
                    {
                        "coverage_gap_count": 0,
                        "no_orphan_blocking_count": 0,
                        "rules": [
                            {
                                "rule_key": "wall_setback",
                                "lifecycle_status": "approved",
                                "quote_anchor_valid": True,
                            }
                        ],
                    }
                ),
                source_version_ids_json=to_json([version.id]),
                is_active=True,
            )
        )
        db.flush()

        eval_run = GoldenEvalService(db).run(GoldenEvalRunRequest(track="rule_extraction", run_by="ci"))
        assert eval_run.passed is True

        gate = SourceGovernanceService(db).review_source(
            source.id,
            SourceReviewRequest(
                review_status="accepted",
                source_version_id=version.id,
                reviewed_by="reviewer@example.test",
            ),
        )

        assert gate.status == "pass"
        assert gate.can_support_retrieval is True
    finally:
        db.close()


def test_source_acceptance_ignores_eval_cases_for_other_source_versions():
    db = _session()
    try:
        source, version = _accepted_ready_source(db)
        _other_source, other_version = _accepted_ready_source(db)
        db.add(
            GoldenEvalCase(
                track="rule_extraction",
                name="Other source rule extraction fixture",
                input_json=to_json({"source_version_id": other_version.id}),
                expected_json=to_json({"rule_key": "other_rule"}),
                source_version_ids_json=to_json([other_version.id]),
                is_active=True,
            )
        )
        db.flush()

        gate = SourceGovernanceService(db).review_source(
            source.id,
            SourceReviewRequest(
                review_status="accepted",
                source_version_id=version.id,
                reviewed_by="reviewer@example.test",
            ),
        )

        assert gate.status == "pass"
        assert gate.can_support_retrieval is True
    finally:
        db.close()


def test_source_unacceptance_stales_dependent_rules_outputs_and_facts():
    db = _session()
    try:
        source, version = _accepted_ready_source(db)
        service = SourceGovernanceService(db)
        accepted_gate = service.review_source(
            source.id,
            SourceReviewRequest(
                review_status="accepted",
                source_version_id=version.id,
                reviewed_by="reviewer@example.test",
            ),
        )
        assert accepted_gate.status == "pass"

        rule = db.scalar(select(RuleRow).where(RuleRow.source_version_id == version.id))
        assert rule is not None
        candidate = RuleExtractionCandidate(
            source_version_id=version.id,
            clause_id=rule.clause_id,
            rule_key="wall_setback",
            operator=">=",
            value_json=to_json({"min_value": 1.5}),
            unit="m",
            quote="A wall must be set back at least 1.5 m unless exempt.",
        )
        project = Project(
            project_name="Stale output project",
            address="1 Example Street, Spearwood WA",
            local_government="Cockburn",
            project_type="single_house",
            stage="concept",
        )
        db.add_all([candidate, project])
        db.flush()
        citation = Citation(
            source_document_id=source.id,
            source_title=source.title,
            source_version_id=version.id,
            version_label=version.version_label,
            effective_date=version.effective_date,
            retrieved_at=version.retrieved_at,
            clause_id="5.1",
            heading="Street setbacks",
            canonical_url=source.canonical_url,
            quote="A wall must be set back at least 1.5 m unless exempt.",
        )
        citation_payload = citation.model_dump(mode="json")
        resolved_rule = ResolvedRule(
            project_id=project.id,
            rule_row_id=rule.id,
            as_of_date="2026-06-06",
            assessment_basis="current_rules",
            applies_reason="Fixture applies.",
            status="likely_pass",
            citations_json=to_json([citation_payload]),
        )
        check_run = CheckRun(
            project_id=project.id,
            status="completed",
            as_of_date="2026-06-06",
            assessment_basis="current_rules",
            source_version_ids_json=to_json([version.id]),
        )
        db.add(check_run)
        db.flush()
        check_result = CheckResult(
            check_run_id=check_run.id,
            project_id=project.id,
            check_key="wall_setback",
            label="Wall setback",
            category="planning",
            status="likely_pass",
            as_of_date="2026-06-06",
            assessment_basis="current_rules",
            citations_json=to_json([citation_payload]),
            confidence=0.8,
        )
        db.add(check_result)
        db.flush()
        trace = DecisionTrace(
            project_id=project.id,
            check_result_id=check_result.id,
            formula="front_setback_m >= min_value",
            comparison="1.5 >= 1.5",
            result="likely_pass",
            citation_ids_json=to_json([{"source_version_id": version.id, "clause_id": "5.1"}]),
            input_sources_json=to_json([{"type": "approved_source_citation", "source_version_id": version.id}]),
            applicability_trace_json=to_json({"missing_information": []}),
        )
        rfi_item = RfiItem(
            project_id=project.id,
            item_number=1,
            issue_summary="Confirm wall setback.",
            requested_action="Confirm wall setback.",
            source_requirement_candidates_json=to_json([citation_payload]),
        )
        response_draft = ResponseDraft(
            project_id=project.id,
            title="Draft response",
            draft_text="RFI item 1 has 1 approved source citation and can be answered from the accepted source.",
            content_json=to_json(
                {
                    "item_table": [
                        {
                            "rfi_item_id": rfi_item.id,
                            "item_number": 1,
                            "source_support_status": "cited",
                            "source_citation_count": 1,
                            "missing_evidence": [],
                        }
                    ],
                }
            ),
            confidence=0.8,
            citations_json=to_json([citation_payload]),
            requires_human_review=False,
        )
        export = Export(
            project_id=project.id,
            export_type="response_pack",
            format="json",
            status="signed_off",
            manifest_json=to_json(
                {
                    "source_version_ids": [version.id],
                    "requires_human_signoff": False,
                    "submission_ready": True,
                    "human_signoff_status": "approved_for_export",
                }
            ),
        )
        address_profile = AddressProfile(
            project_id=project.id,
            input_address=project.address,
            formatted_address=project.address,
            resolution_status="resolved",
            confidence="high",
        )
        db.add_all([resolved_rule, trace, rfi_item, response_draft, export, address_profile])
        db.flush()
        address_fact = AddressFact(
            address_profile_id=address_profile.id,
            fact_type="zoning",
            value_json=to_json({"zone": "R30"}),
            confidence="high",
            method="source_fixture",
            source_version_id=version.id,
            review_status="accepted",
        )
        local_government_fact = LocalGovernmentFact(
            address_profile_id=address_profile.id,
            local_government="Cockburn",
            method="source_fixture",
            confidence="high",
            source_version_id=version.id,
            review_status="accepted",
        )
        db.add_all([address_fact, local_government_fact])
        db.flush()

        gate = service.review_source(
            source.id,
            SourceReviewRequest(
                review_status="pending_review",
                source_version_id=version.id,
                reviewed_by="reviewer@example.test",
            ),
        )

        stale_note = f"Source version {version.id} is no longer accepted."
        assert gate.review_status == "pending_review"
        assert rule.lifecycle_status == "stale"
        assert candidate.status == "stale"
        assert resolved_rule.status == "stale"
        assert check_run.status == "stale"
        assert check_result.status == "unsupported"
        assert check_result.confidence == 0.0
        assert stale_note in from_json(check_result.missing_information_json, [])
        assert trace.result == "unsupported"
        assert from_json(trace.applicability_trace_json, {})["source_support_status"] == "stale_source"
        assert from_json(rfi_item.source_requirement_candidates_json, []) == []
        assert stale_note in from_json(rfi_item.missing_evidence_json, [])
        assert from_json(response_draft.citations_json, []) == []
        assert response_draft.confidence == 0.0
        assert response_draft.requires_human_review is True
        assert response_draft.draft_text.startswith("STALE SOURCE NOTICE:")
        draft_content = from_json(response_draft.content_json, {})
        assert draft_content["source_support_status"] == "stale_source"
        assert version.id in draft_content["stale_source_version_ids"]
        assert draft_content["item_table"][0]["source_support_status"] == "stale_source"
        assert draft_content["item_table"][0]["source_citation_count"] == 0
        assert stale_note in draft_content["item_table"][0]["missing_evidence"]
        assert export.status == "stale"
        export_manifest = from_json(export.manifest_json, {})
        assert version.id in export_manifest["stale_source_version_ids"]
        assert export_manifest["requires_human_signoff"] is True
        assert export_manifest["submission_ready"] is False
        assert export_manifest["human_signoff_status"] == "required_after_source_stale"
        assert "no longer accepted" in export_manifest["source_signoff_notice"]
        assert address_fact.review_status == "stale"
        assert address_fact.stale_at is not None
        assert local_government_fact.review_status == "stale"
    finally:
        db.close()


def _accepted_ready_source(db):
    source = SourceDocument(
        title="Acceptance Ready Policy",
        authority="Example council",
        source_type="local_planning_policy",
        canonical_url="https://example.test/acceptance-ready",
        access_type="public",
    )
    text = "5.1 Street setbacks\nA wall must be set back at least 1.5 m unless exempt."
    version = SourceVersion(
        source_document=source,
        version_label="current",
        effective_date="2026-06-06",
        content_sha256=hash_text(text),
        raw_text=text,
        parse_status="ok",
        review_status="pending_review",
    )
    db.add_all([source, version])
    db.flush()
    db.add(
        SourceLicenceReview(
            source_document_id=source.id,
            source_version_id=version.id,
            allowed_use=True,
            allowed_storage=True,
            allowed_ai_processing=True,
            reviewed_at=utcnow(),
            review_status="approved",
        )
    )
    clause = Clause(
        source_version_id=version.id,
        clause_id="5.1",
        heading="Street setbacks",
        text=text,
        normalized_text=normalize_text(text),
        start_anchor="5.1",
        text_sha256=hash_text(text),
    )
    db.add(clause)
    db.flush()
    db.add(
        ClauseDisposition(
            clause_id=clause.id,
            disposition="rule_bearing",
            rationale="Contains a deterministic setback threshold with an exception.",
            reviewer="reviewer@example.test",
        )
    )
    rule = RuleRow(
        rule_key="wall_setback",
        operator=">=",
        value_json=to_json({"min_value": 1.5}),
        unit="m",
        condition_text="unless exempt",
        quote="A wall must be set back at least 1.5 m unless exempt.",
        clause_id=clause.id,
        source_version_id=version.id,
        lifecycle_status="approved",
        approved_by="reviewer@example.test",
        approved_at=utcnow(),
    )
    chunk = SourceChunk(
        source_version_id=version.id,
        clause_id=clause.id,
        heading=clause.heading,
        text=text,
        token_count=len(text.split()),
    )
    db.add_all([rule, chunk])
    db.flush()
    citation = Citation(
        source_document_id=source.id,
        source_title=source.title,
        source_version_id=version.id,
        version_label=version.version_label,
        effective_date=version.effective_date,
        retrieved_at=version.retrieved_at,
        clause_id=clause.clause_id,
        heading=clause.heading,
        canonical_url=source.canonical_url,
        quote=text,
    )
    db.add(
        SourceCitation(
            source_chunk_id=chunk.id,
            source_version_id=version.id,
            clause_id=clause.id,
            citation_json=to_json(citation.model_dump(mode="json")),
        )
    )
    db.flush()
    return source, version


def _citable_source_with_rule_gaps(db):
    source = SourceDocument(
        title="Citable Policy With Rule Gaps",
        authority="Example council",
        source_type="local_planning_policy",
        canonical_url="https://example.test/citable-rule-gaps",
        access_type="public",
    )
    text = "5.1 Street setbacks\nA wall must be set back at least 1.5 m unless exempt."
    version = SourceVersion(
        source_document=source,
        version_label="current",
        effective_date="2026-06-06",
        content_sha256=hash_text(text),
        raw_text=text,
        parse_status="ok",
        review_status="pending_review",
    )
    db.add_all([source, version])
    db.flush()
    db.add(
        SourceLicenceReview(
            source_document_id=source.id,
            source_version_id=version.id,
            allowed_use=True,
            allowed_storage=True,
            allowed_ai_processing=True,
            reviewed_at=utcnow(),
            review_status="approved",
        )
    )
    clause = Clause(
        source_version_id=version.id,
        clause_id="5.1",
        heading="Street setbacks",
        text=text,
        normalized_text=normalize_text(text),
        start_anchor="5.1",
        text_sha256=hash_text(text),
    )
    db.add(clause)
    db.flush()
    chunk = SourceChunk(
        source_version_id=version.id,
        clause_id=clause.id,
        heading=clause.heading,
        text=text,
        token_count=len(text.split()),
    )
    db.add(chunk)
    db.flush()
    citation = Citation(
        source_document_id=source.id,
        source_title=source.title,
        source_version_id=version.id,
        version_label=version.version_label,
        effective_date=version.effective_date,
        retrieved_at=version.retrieved_at,
        clause_id=clause.clause_id,
        heading=clause.heading,
        canonical_url=source.canonical_url,
        quote=text,
    )
    db.add(
        SourceCitation(
            source_chunk_id=chunk.id,
            source_version_id=version.id,
            clause_id=clause.id,
            citation_json=to_json(citation.model_dump(mode="json")),
        )
    )
    db.flush()
    return source, version


def _session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return session_factory()
