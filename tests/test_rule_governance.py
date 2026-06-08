from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from draftcheck_compliance.rule_audits import RuleAuditService
from draftcheck_compliance.rules import RuleGovernanceService
from draftcheck_core.database import Base
from draftcheck_core.json_utils import hash_text, normalize_text, to_json
from draftcheck_core.models import (
    Clause,
    ClauseDisposition,
    RuleExtractionCandidate,
    RuleRow,
    SourceDocument,
    SourceLicenceReview,
    SourceVersion,
    utcnow,
)
from draftcheck_shared.schemas import (
    ClauseDispositionReviewRequest,
    RuleCandidatePromotionRequest,
    RuleCandidateReviewRequest,
    RuleReviewRequest,
)


def test_rule_governance_approves_quote_anchored_rule_row():
    db = _session()
    try:
        version, clause = _source_clause(db)
        rule = RuleRow(
            rule_key="site_cover",
            operator="<=",
            value_json=to_json({"max_percent": 55}),
            unit="percent",
            condition_text="single house",
            quote="Site cover maximum percentage requirement.",
            clause_id=clause.id,
            source_version_id=version.id,
            lifecycle_status="pending_review",
        )
        db.add(rule)
        db.flush()

        service = RuleGovernanceService(db)
        reviewed = service.review_rule_row(
            rule.id,
            RuleReviewRequest(lifecycle_status="approved", reviewed_by="reviewer@example.test"),
        )

        assert reviewed.lifecycle_status == "approved"
        assert reviewed.approved_by == "reviewer@example.test"
        assert reviewed.approved_at is not None
        assert service.list_rule_rows(source_version_id=version.id)[0].id == rule.id
    finally:
        db.close()


def test_rule_governance_rejects_approval_without_quote_anchor():
    db = _session()
    try:
        version, clause = _source_clause(db)
        rule = RuleRow(
            rule_key="site_cover",
            operator="<=",
            value_json=to_json({"max_percent": 55}),
            unit="percent",
            condition_text="single house",
            quote="",
            clause_id=clause.id,
            source_version_id=version.id,
            lifecycle_status="pending_review",
        )
        db.add(rule)
        db.flush()

        with pytest.raises(ValueError, match="quote anchor"):
            RuleGovernanceService(db).review_rule_row(rule.id, RuleReviewRequest(lifecycle_status="approved"))
    finally:
        db.close()


def test_rule_governance_rejects_approval_without_approved_source_licence():
    db = _session()
    try:
        version, clause = _source_clause(db, with_licence=False)
        rule = RuleRow(
            rule_key="site_cover",
            operator="<=",
            value_json=to_json({"max_percent": 55}),
            unit="percent",
            condition_text="single house",
            quote="Site cover maximum percentage requirement.",
            clause_id=clause.id,
            source_version_id=version.id,
            lifecycle_status="pending_review",
        )
        db.add(rule)
        db.flush()

        with pytest.raises(ValueError, match="approved licence"):
            RuleGovernanceService(db).review_rule_row(rule.id, RuleReviewRequest(lifecycle_status="approved"))
    finally:
        db.close()


def test_rule_governance_rejects_approval_when_quote_is_not_verbatim_in_clause():
    db = _session()
    try:
        version, clause = _source_clause(db)
        rule = RuleRow(
            rule_key="site_cover",
            operator="<=",
            value_json=to_json({"max_percent": 55}),
            unit="percent",
            condition_text="single house",
            quote="This quote is not in the clause.",
            clause_id=clause.id,
            source_version_id=version.id,
            lifecycle_status="pending_review",
        )
        db.add(rule)
        db.flush()

        with pytest.raises(ValueError, match="verbatim"):
            RuleGovernanceService(db).review_rule_row(rule.id, RuleReviewRequest(lifecycle_status="approved"))
    finally:
        db.close()


def test_rule_coverage_audit_tracks_normative_clause_gaps_to_approved_rule():
    db = _session()
    try:
        version, clause = _source_clause(db, text="A wall must be set back at least 1.5 m unless exempt.")
        service = RuleGovernanceService(db)

        no_disposition = service.coverage_audit(source_version_id=version.id)

        assert no_disposition.total_clauses == 1
        assert no_disposition.gap_count == 1
        assert no_disposition.items[0].status == "needs_clause_disposition"
        assert no_disposition.items[0].review_required is True

        db.add(
            ClauseDisposition(
                clause_id=clause.id,
                disposition="rule_bearing",
                rationale="Setback obligation has deterministic threshold language.",
            )
        )
        db.flush()

        missing_rule = service.coverage_audit(source_version_id=version.id)

        assert missing_rule.items[0].status == "missing_rule_row"

        candidate = RuleExtractionCandidate(
            source_version_id=version.id,
            clause_id=clause.id,
            rule_key="wall_setback",
            operator=">=",
            value_json=to_json({"min_m": 1.5}),
            unit="m",
            condition_text="unless exempt",
            quote="A wall must be set back at least 1.5 m unless exempt.",
            status="candidate",
        )
        db.add(candidate)
        db.flush()

        candidate_gap = service.coverage_audit(source_version_id=version.id)

        assert candidate_gap.items[0].status == "candidate_not_promoted"
        assert candidate_gap.items[0].rule_candidate_ids == [candidate.id]

        rule = RuleRow(
            rule_key="wall_setback",
            operator=">=",
            value_json=to_json({"min_m": 1.5}),
            unit="m",
            condition_text="unless exempt",
            quote="A wall must be set back at least 1.5 m unless exempt.",
            clause_id=clause.id,
            source_version_id=version.id,
            lifecycle_status="pending_review",
        )
        db.add(rule)
        db.flush()

        rule_review_gap = service.coverage_audit(source_version_id=version.id)

        assert rule_review_gap.items[0].status == "rule_not_approved"
        assert rule_review_gap.items[0].rule_lifecycle_statuses == {"pending_review": 1}

        service.review_rule_row(rule.id, RuleReviewRequest(lifecycle_status="approved", reviewed_by="rules@example.test"))
        covered_gaps = service.coverage_audit(source_version_id=version.id)
        full_audit = service.coverage_audit(source_version_id=version.id, only_gaps=False)

        assert covered_gaps.items == []
        assert covered_gaps.gap_count == 0
        assert full_audit.items[0].status == "covered"
        assert full_audit.items[0].active_rule_row_ids == [rule.id]
    finally:
        db.close()


def test_rule_coverage_audit_accepts_procedural_normative_disposition():
    db = _session()
    try:
        version, clause = _source_clause(
            db,
            text="The application must include a site plan showing the proposed works.",
        )
        db.add(
            ClauseDisposition(
                clause_id=clause.id,
                disposition="procedural",
                rationale="Document submission requirement; not a deterministic threshold.",
            )
        )
        db.flush()

        audit = RuleGovernanceService(db).coverage_audit(source_version_id=version.id, only_gaps=False)

        assert audit.gap_count == 0
        assert audit.items[0].status == "not_rule_bearing"
        assert audit.items[0].normative_language_detected is True
    finally:
        db.close()


def test_rule_extraction_keeps_substantive_threshold_text_in_manual_review():
    db = _session()
    try:
        version, clause = _source_clause(
            db,
            text=(
                "Single aspect apartments included within the 60 per cent minimum must have "
                "ventilation openings oriented between 45 degrees and 90 degrees of the prevailing cooling wind."
            ),
            heading="Natural ventilation",
        )
        service = RuleGovernanceService(db)

        extracted = service.extract_source_version_rules(version.id)
        reviewed = service.get_clause(clause.id)

        assert extracted.candidates == []
        assert reviewed.latest_disposition is not None
        assert reviewed.latest_disposition.disposition == "manual_review"
        audit = service.coverage_audit(source_version_id=version.id)
        assert audit.items[0].status == "needs_manual_review"
    finally:
        db.close()


def test_no_orphan_audit_allows_numeric_examples_in_procedural_clauses():
    db = _session()
    try:
        version, clause = _source_clause(
            db,
            text=(
                "The diagram provides an example calculation. "
                "A = 3m x 4m = 12 and total length = 20m."
            ),
        )
        db.add(
            ClauseDisposition(
                clause_id=clause.id,
                disposition="procedural",
                rationale="Worked example; not a deterministic planning threshold.",
            )
        )
        db.flush()

        audit = RuleAuditService(db).no_orphan_audit(source_version_id=version.id)

        assert audit.blocking_count == 0
        assert audit.summary == {"ok": 1}
    finally:
        db.close()


def test_clause_disposition_review_sets_latest_disposition_and_validates_normative_text():
    db = _session()
    try:
        version, clause = _source_clause(
            db,
            text="The application must include a site plan showing the proposed works.",
        )
        service = RuleGovernanceService(db)

        with pytest.raises(ValueError, match="Normative clauses cannot"):
            service.review_clause_disposition(
                clause.id,
                ClauseDispositionReviewRequest(
                    disposition="informational",
                    rationale="Incorrect fixture classification.",
                    reviewed_by="rules@example.test",
                ),
            )

        reviewed = service.review_clause_disposition(
            clause.id,
            ClauseDispositionReviewRequest(
                disposition="procedural",
                rationale="Document submission requirement.",
                reviewed_by="rules@example.test",
            ),
        )

        assert reviewed.id == clause.id
        assert reviewed.source_version_id == version.id
        assert reviewed.latest_disposition is not None
        assert reviewed.latest_disposition.disposition == "procedural"
        assert reviewed.latest_disposition.rationale == "Document submission requirement."
        assert reviewed.latest_disposition.reviewer == "rules@example.test"
        assert service.get_clause(clause.id).latest_disposition.id == reviewed.latest_disposition.id

        audit = service.coverage_audit(source_version_id=version.id, only_gaps=False)
        assert audit.gap_count == 0
        assert audit.items[0].status == "not_rule_bearing"
    finally:
        db.close()


def test_rule_candidate_promotion_creates_pending_rule_row_and_unblocks_candidate_orphan():
    db = _session()
    try:
        version, _clause = _source_clause(
            db,
            text="A wall must be set back at least 1.5 m unless exempt.",
        )
        service = RuleGovernanceService(db)
        extracted = service.extract_source_version_rules(version.id)
        candidate = extracted.candidates[0]

        promoted = service.promote_rule_candidate(
            candidate.id,
            RuleCandidatePromotionRequest(reviewed_by="rules@example.test", notes="Fixture promotion."),
        )

        assert promoted.rule_key == "wall_setback"
        assert promoted.lifecycle_status == "pending_review"
        assert promoted.value == {"min_value": 1.5}
        assert promoted.condition_text == "unless exempt"

        promoted_again = service.promote_rule_candidate(candidate.id, RuleCandidatePromotionRequest())
        assert promoted_again.id == promoted.id

        candidate_after = db.get(RuleExtractionCandidate, candidate.id)
        assert candidate_after is not None
        assert candidate_after.status == "pending_review"
        assert promoted.id in candidate_after.review_notes

        coverage = service.coverage_audit(source_version_id=version.id)
        assert coverage.items[0].status == "rule_not_approved"

        no_orphan = RuleAuditService(db).no_orphan_audit(source_version_id=version.id)
        assert no_orphan.blocking_count == 2
        items_by_status = {item.status: item for item in no_orphan.items}
        assert set(items_by_status) == {"pending_rule_review", "unclaimed_numeric_token"}
        assert items_by_status["pending_rule_review"].evidence == {
            "rule_candidate_ids": [],
            "rule_row_ids": [promoted.id],
        }

        reviewed = service.review_rule_row(
            promoted.id,
            RuleReviewRequest(lifecycle_status="approved", reviewed_by="approver@example.test"),
        )
        assert reviewed.lifecycle_status == "approved"
        assert service.coverage_audit(source_version_id=version.id).gap_count == 0
        assert RuleAuditService(db).no_orphan_audit(source_version_id=version.id).blocking_count == 0
    finally:
        db.close()


def test_rule_extraction_does_not_treat_building_length_as_setback_threshold():
    db = _session()
    try:
        version, _clause = _source_clause(
            db,
            text=(
                "The intent of introducing an average setback requirement for buildings longer than 16m "
                "is to reduce wall bulk. A wall must have a setback of 3.5m."
            ),
            heading="Side and rear setbacks",
        )
        service = RuleGovernanceService(db)

        extracted = service.extract_source_version_rules(version.id)

        assert len(extracted.candidates) == 1
        assert extracted.candidates[0].rule_key == "side_setback"
        assert extracted.candidates[0].value == {"min_value": 3.5}
        assert extracted.candidates[0].quote == "A wall must have a setback of 3.5m."
    finally:
        db.close()


def test_rule_extraction_skips_worked_average_side_setback_calculations():
    db = _session()
    try:
        version, clause = _source_clause(
            db,
            text=(
                "Average side setback\n"
                "Side boundary\n"
                "A = 3m x 3m = 9\n"
                "Total length = 20m\n"
                "Average side\n"
                "setback of 3.5m"
            ),
            heading="m",
        )
        service = RuleGovernanceService(db)

        extracted = service.extract_source_version_rules(version.id)

        assert extracted.candidates == []
        disposition = db.get(ClauseDisposition, service.get_clause(clause.id).latest_disposition.id)
        assert disposition is not None
        assert disposition.disposition == "informational"
    finally:
        db.close()


def test_rule_extraction_uses_clause_context_for_fragmented_side_setback_requirements():
    db = _session()
    try:
        version, _clause = _source_clause(
            db,
            text=(
                "Minimum side setback\n"
                "Side boundary\n"
                "setback of 3.5m"
            ),
            heading="Side and rear setbacks",
        )
        service = RuleGovernanceService(db)

        extracted = service.extract_source_version_rules(version.id)

        assert len(extracted.candidates) == 1
        assert extracted.candidates[0].rule_key == "side_setback"
        assert extracted.candidates[0].value == {"min_value": 3.5}
        assert extracted.candidates[0].quote == "setback of 3.5m"
    finally:
        db.close()


def test_coverage_audit_targets_active_candidate_when_rejected_candidates_exist():
    db = _session()
    try:
        version, clause = _source_clause(
            db,
            text="A wall must be set back at least 1.5 m unless exempt.",
        )
        rejected = RuleExtractionCandidate(
            source_version_id=version.id,
            clause_id=clause.id,
            rule_key="wall_setback",
            operator=">=",
            value_json=to_json({"min_value": 1.0}),
            unit="m",
            condition_text="unless exempt",
            quote="A wall must be set back at least 1.5 m unless exempt.",
            status="rejected",
        )
        active = RuleExtractionCandidate(
            source_version_id=version.id,
            clause_id=clause.id,
            rule_key="wall_setback",
            operator=">=",
            value_json=to_json({"min_value": 1.5}),
            unit="m",
            condition_text="unless exempt",
            quote="A wall must be set back at least 1.5 m unless exempt.",
            status="candidate",
        )
        db.add_all(
            [
                ClauseDisposition(
                    clause_id=clause.id,
                    disposition="rule_bearing",
                    rationale="Fixture candidate review.",
                    reviewer="test",
                ),
                rejected,
                active,
            ]
        )
        db.flush()

        audit = RuleGovernanceService(db).coverage_audit(source_version_id=version.id)

        assert audit.items[0].status == "candidate_not_promoted"
        assert audit.items[0].rule_candidate_ids == [active.id]
        assert audit.items[0].rule_candidate_statuses == {"candidate": 1, "rejected": 1}
    finally:
        db.close()


def test_rule_candidate_rejection_removes_active_candidate_gap_but_keeps_rule_gap():
    db = _session()
    try:
        version, _clause = _source_clause(
            db,
            text="A wall must be set back at least 1.5 m unless exempt.",
        )
        service = RuleGovernanceService(db)
        extracted = service.extract_source_version_rules(version.id)
        candidate = extracted.candidates[0]

        before_review = service.coverage_audit(source_version_id=version.id)
        assert before_review.items[0].status == "candidate_not_promoted"

        reviewed = service.review_rule_candidate(
            candidate.id,
            RuleCandidateReviewRequest(
                status="rejected",
                reviewed_by="rules@example.test",
                notes="False positive fixture.",
            ),
        )

        assert reviewed.status == "rejected"
        assert "False positive fixture" in reviewed.review_notes
        rejected = service.list_rule_candidates(source_version_id=version.id, status="rejected")
        assert [row.id for row in rejected] == [candidate.id]
        open_candidates = service.list_rule_candidates(source_version_id=version.id, status="candidate")
        assert open_candidates == []

        after_review = service.coverage_audit(source_version_id=version.id)
        assert after_review.items[0].status == "missing_rule_row"
        assert after_review.items[0].rule_candidate_statuses == {"rejected": 1}
        no_orphan = RuleAuditService(db).no_orphan_audit(source_version_id=version.id)
        assert no_orphan.blocking_count == 2
        assert {item.status for item in no_orphan.items} == {
            "exception_language_orphan",
            "unclaimed_numeric_token",
        }

        with pytest.raises(ValueError, match="Rejected rule extraction candidates cannot be promoted"):
            service.promote_rule_candidate(candidate.id, RuleCandidatePromotionRequest())
    finally:
        db.close()


def test_negated_deemed_to_comply_text_does_not_create_exception_or_normative_blocker():
    db = _session()
    try:
        version, clause = _source_clause(
            db,
            text=(
                "The diagram provides a method of calculating the average side setback. "
                "The example numbers are not deemed-to-comply and are explanatory only."
            ),
            heading="Average side setback example",
        )
        db.add(
            ClauseDisposition(
                clause_id=clause.id,
                disposition="informational",
                rationale="Explanatory example with negated deemed-to-comply wording.",
                reviewer="rules@example.test",
            )
        )
        db.flush()

        coverage = RuleGovernanceService(db).coverage_audit(source_version_id=version.id, only_gaps=False)
        no_orphan = RuleAuditService(db).no_orphan_audit(source_version_id=version.id)

        assert coverage.gap_count == 0
        assert coverage.items[0].normative_language_detected is False
        assert coverage.items[0].status == "not_rule_bearing"
        assert no_orphan.blocking_count == 0
        assert no_orphan.summary == {"ok": 1}
    finally:
        db.close()


def test_rule_coverage_audit_endpoint_reports_ingested_normative_gaps(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Coverage Audit Planning Policy",
            "jurisdiction": "WA",
            "authority": "Example council",
            "source_type": "local_planning_policy",
            "canonical_url": "https://example.test/coverage-policy",
            "licence_notes": "Public council policy fixture.",
            "access_type": "public",
            "content": "\n".join(
                [
                    "5.1 Street setbacks",
                    "A wall must be set back at least 1.5 m unless exempt.",
                ]
            ),
            "version_label": "current",
            "effective_date": "2026-06-06",
        },
    )
    assert response.status_code == 200, response.text
    source_version_id = response.json()["source_version_id"]
    assert response.json()["rule_dispositions_created"] == 1
    assert response.json()["rule_candidates_created"] == 1

    audit = client.get("/v1/rules/coverage-audit", params={"source_version_id": source_version_id})

    assert audit.status_code == 200, audit.text
    body = audit.json()
    assert body["source_version_id"] == source_version_id
    assert body["gap_count"] == 1
    assert body["summary"] == {"candidate_not_promoted": 1}
    assert body["items"][0]["status"] == "candidate_not_promoted"
    assert body["items"][0]["source_title"] == "Coverage Audit Planning Policy"
    assert body["items"][0]["normative_language_detected"] is True
    assert "final compliance" not in body["items"][0]["recommended_action"].lower()


def test_clause_disposition_review_endpoint_updates_coverage_audit(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Clause Disposition Review Policy",
            "jurisdiction": "WA",
            "authority": "Example council",
            "source_type": "local_planning_policy",
            "canonical_url": "https://example.test/clause-disposition-review-policy",
            "licence_notes": "Public council policy fixture.",
            "access_type": "public",
            "content": "5.1 Application documents\nThe application must include a site plan.",
            "version_label": "current",
            "effective_date": "2026-06-06",
        },
    )
    assert response.status_code == 200, response.text
    source_version_id = response.json()["source_version_id"]
    assert response.json()["rule_dispositions_created"] == 1
    assert response.json()["rule_candidates_created"] == 0
    audit = client.get(
        "/v1/rules/coverage-audit",
        params={"source_version_id": source_version_id, "only_gaps": False},
    )
    assert audit.status_code == 200, audit.text
    clause_row_id = audit.json()["items"][0]["clause_row_id"]

    unsupported = client.post(
        f"/v1/clauses/{clause_row_id}/disposition",
        json={
            "disposition": "informational",
            "rationale": "Should be rejected.",
            "reviewed_by": "rules@example.test",
        },
    )
    assert unsupported.status_code == 400
    assert "Normative clauses cannot" in unsupported.json()["detail"]

    clause = client.get(f"/v1/clauses/{clause_row_id}")
    assert clause.status_code == 200, clause.text
    assert clause.json()["latest_disposition"]["disposition"] == "procedural"

    reviewed = client.post(
        f"/v1/clauses/{clause_row_id}/disposition",
        json={
            "disposition": "procedural",
            "rationale": "Documentation requirement, not a deterministic threshold.",
            "reviewed_by": "rules@example.test",
        },
    )
    assert reviewed.status_code == 200, reviewed.text
    body = reviewed.json()
    assert body["latest_disposition"]["disposition"] == "procedural"
    assert body["latest_disposition"]["reviewer"] == "rules@example.test"

    post_review_audit = client.get(
        "/v1/rules/coverage-audit",
        params={"source_version_id": source_version_id, "only_gaps": False},
    )
    assert post_review_audit.status_code == 200, post_review_audit.text
    audit_body = post_review_audit.json()
    assert audit_body["gap_count"] == 0
    assert audit_body["items"][0]["status"] == "not_rule_bearing"


def test_rule_extraction_endpoint_creates_reviewable_candidates_and_dispositions(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Rule Extraction Planning Policy",
            "jurisdiction": "WA",
            "authority": "Example council",
            "source_type": "local_planning_policy",
            "canonical_url": "https://example.test/rule-extraction-policy",
            "licence_notes": "Public council policy fixture.",
            "access_type": "public",
            "content": "\n".join(
                [
                    "5.1 Street setbacks",
                    "A wall must be set back at least 1.5 m unless exempt.",
                    "5.2 Site cover",
                    "Maximum site cover must not exceed 55%.",
                    "5.3 Application documents",
                    "The application must include a site plan.",
                    "5.4 Context",
                    "This policy explains local character.",
                ]
            ),
            "version_label": "current",
            "effective_date": "2026-06-06",
        },
    )
    assert response.status_code == 200, response.text
    seed_body = response.json()
    assert seed_body["rule_dispositions_created"] == 4
    assert seed_body["rule_candidates_created"] == 2
    source_document_id = response.json()["source_document_id"]
    source_version_id = response.json()["source_version_id"]

    extract = client.post(f"/v1/sources/{source_document_id}/versions/{source_version_id}/rules/extract")

    assert extract.status_code == 200, extract.text
    body = extract.json()
    assert body["source_document_id"] == source_document_id
    assert body["source_version_id"] == source_version_id
    assert body["clauses_scanned"] == 4
    assert body["dispositions_created"] == 0
    assert body["candidates_created"] == 0
    assert body["candidates_existing"] == 2
    candidates_by_key = {candidate["rule_key"]: candidate for candidate in body["candidates"]}
    assert candidates_by_key["wall_setback"]["operator"] == ">="
    assert candidates_by_key["wall_setback"]["value"] == {"min_value": 1.5}
    assert candidates_by_key["wall_setback"]["unit"] == "m"
    assert candidates_by_key["wall_setback"]["condition_text"] == "unless exempt"
    assert candidates_by_key["site_cover"]["operator"] == "<="
    assert candidates_by_key["site_cover"]["value"] == {"max_percent": 55.0}
    assert candidates_by_key["site_cover"]["unit"] == "percent"
    assert {candidate["status"] for candidate in body["candidates"]} == {"candidate"}

    second_extract = client.post(f"/v1/sources/{source_document_id}/versions/{source_version_id}/rules/extract")
    assert second_extract.status_code == 200, second_extract.text
    second_body = second_extract.json()
    assert second_body["dispositions_created"] == 0
    assert second_body["candidates_created"] == 0
    assert second_body["candidates_existing"] == 2

    audit = client.get("/v1/rules/coverage-audit", params={"source_version_id": source_version_id})

    assert audit.status_code == 200, audit.text
    audit_body = audit.json()
    assert audit_body["gap_count"] == 2
    assert audit_body["summary"] == {"candidate_not_promoted": 2, "not_rule_bearing": 2}
    assert {item["status"] for item in audit_body["items"]} == {"candidate_not_promoted"}


def test_rule_candidate_promote_endpoint_returns_pending_rule_row(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Rule Candidate Promotion Policy",
            "jurisdiction": "WA",
            "authority": "Example council",
            "source_type": "local_planning_policy",
            "canonical_url": "https://example.test/rule-candidate-promotion-policy",
            "licence_notes": "Public council policy fixture.",
            "access_type": "public",
            "content": "5.1 Street setbacks\nA wall must be set back at least 1.5 m unless exempt.",
            "version_label": "current",
            "effective_date": "2026-06-06",
        },
    )
    assert response.status_code == 200, response.text
    source_document_id = response.json()["source_document_id"]
    source_version_id = response.json()["source_version_id"]
    extract = client.post(f"/v1/sources/{source_document_id}/versions/{source_version_id}/rules/extract")
    assert extract.status_code == 200, extract.text
    candidate_id = extract.json()["candidates"][0]["id"]

    candidates = client.get("/v1/rules/candidates", params={"source_version_id": source_version_id})
    assert candidates.status_code == 200, candidates.text
    assert [candidate["id"] for candidate in candidates.json()] == [candidate_id]

    promote = client.post(
        f"/v1/rules/candidates/{candidate_id}/promote",
        json={"reviewed_by": "rules@example.test"},
    )

    assert promote.status_code == 200, promote.text
    body = promote.json()
    assert body["rule_key"] == "wall_setback"
    assert body["lifecycle_status"] == "pending_review"
    assert body["value"] == {"min_value": 1.5}
    assert body["quote"] == "A wall must be set back at least 1.5 m unless exempt."

    promote_again = client.post(f"/v1/rules/candidates/{candidate_id}/promote", json={})
    assert promote_again.status_code == 200, promote_again.text
    assert promote_again.json()["id"] == body["id"]


def test_rule_candidate_review_endpoint_rejects_candidate_and_filters_by_status(client):
    response = client.post(
        "/v1/sources/seed",
        json={
            "title": "Rule Candidate Review Policy",
            "jurisdiction": "WA",
            "authority": "Example council",
            "source_type": "local_planning_policy",
            "canonical_url": "https://example.test/rule-candidate-review-policy",
            "licence_notes": "Public council policy fixture.",
            "access_type": "public",
            "content": "5.1 Street setbacks\nA wall must be set back at least 1.5 m unless exempt.",
            "version_label": "current",
            "effective_date": "2026-06-06",
        },
    )
    assert response.status_code == 200, response.text
    source_document_id = response.json()["source_document_id"]
    source_version_id = response.json()["source_version_id"]
    extract = client.post(f"/v1/sources/{source_document_id}/versions/{source_version_id}/rules/extract")
    assert extract.status_code == 200, extract.text
    candidate_id = extract.json()["candidates"][0]["id"]

    review = client.post(
        f"/v1/rules/candidates/{candidate_id}/review",
        json={
            "status": "rejected",
            "reviewed_by": "rules@example.test",
            "notes": "Not a deterministic project threshold.",
        },
    )

    assert review.status_code == 200, review.text
    body = review.json()
    assert body["id"] == candidate_id
    assert body["status"] == "rejected"
    assert "Not a deterministic project threshold" in body["review_notes"]

    rejected = client.get(
        "/v1/rules/candidates",
        params={"source_version_id": source_version_id, "status": "rejected"},
    )
    assert rejected.status_code == 200, rejected.text
    assert [candidate["id"] for candidate in rejected.json()] == [candidate_id]

    coverage = client.get("/v1/rules/coverage-audit", params={"source_version_id": source_version_id})
    assert coverage.status_code == 200, coverage.text
    assert coverage.json()["items"][0]["status"] == "missing_rule_row"


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


def _source_clause(
    db,
    text: str = "Site cover maximum percentage requirement.",
    with_licence: bool = True,
    heading: str = "Site cover",
):
    source = SourceDocument(
        title="Rule Governance Fixture",
        authority="Fixture authority",
        source_type="local_planning_policy",
        canonical_url="https://example.test/rules",
    )
    version = SourceVersion(
        source_document=source,
        version_label="current",
        effective_date="2026-06-01",
        content_sha256=hash_text(text),
        review_status="accepted",
        reviewed_by="fixture",
        reviewed_at=utcnow(),
        raw_text=text,
    )
    db.add_all([source, version])
    db.flush()
    if with_licence:
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
        db.flush()
    clause = Clause(
        source_version_id=version.id,
        clause_id="5.3.1",
        heading=heading,
        text=text,
        normalized_text=normalize_text(text),
        start_anchor="5.3.1",
        text_sha256=hash_text(text),
    )
    db.add(clause)
    db.flush()
    return version, clause
