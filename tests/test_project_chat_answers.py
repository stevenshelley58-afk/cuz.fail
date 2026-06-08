from __future__ import annotations

from datetime import datetime, timezone

from draftcheck_api.router import _project_compliance_summary_answer, _targeted_project_check_answer
from draftcheck_shared.schemas import CheckResultRead, Citation


def test_project_chat_summary_prioritizes_likely_fail_status_and_blocking_order():
    citation = Citation(
        source_document_id="src_site_cover",
        source_title="Approved Site Cover Policy",
        source_version_id="sv_site_cover",
        version_label="approved-current",
        effective_date="2026-06-01",
        retrieved_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
        clause_id="5.3.1",
        heading="Site cover",
        page_number=1,
        canonical_url="https://example.test/site-cover-policy",
        quote="Site cover must not exceed 45 per cent.",
    )
    answer = _project_compliance_summary_answer(
        [
            _check_result(
                check_key="garage_dominance",
                label="Garage dominance",
                status="missing_info",
                missing_information=["garage_width_m"],
                confidence=0.2,
            ),
            _check_result(
                check_key="front_setback",
                label="Front setback",
                status="likely_pass",
                proposed="4.8m",
                citations=[citation],
                confidence=0.8,
            ),
            _check_result(
                check_key="site_cover",
                label="Site cover",
                status="likely_fail",
                proposed="50.0% from 250m2 / 500m2",
                citations=[citation],
                confidence=0.8,
            ),
        ]
    )

    assert answer.status == "likely_fail"
    assert answer.risk_level == "high"
    assert answer.citations == [citation]
    assert answer.source_version_ids == ["sv_site_cover"]
    blocking_lines = [line for line in answer.answer.splitlines() if line.startswith("- ")]
    assert blocking_lines[0].startswith("- Site cover: likely_fail")


def test_project_chat_summary_does_not_cite_unmentioned_passing_checks():
    citation = Citation(
        source_document_id="src_front_setback",
        source_title="Approved Front Setback Policy",
        source_version_id="sv_front_setback",
        version_label="approved-current",
        effective_date="2026-06-01",
        retrieved_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
        clause_id="4.1",
        heading="Front setback",
        page_number=1,
        canonical_url="https://example.test/front-setback-policy",
        quote="Front setback must be at least 4 metres.",
    )

    answer = _project_compliance_summary_answer(
        [
            _check_result(
                check_key="garage_dominance",
                label="Garage dominance",
                status="missing_info",
                missing_information=["garage_width_m"],
                confidence=0.2,
            ),
            _check_result(
                check_key="front_setback",
                label="Front setback",
                status="likely_pass",
                proposed="4.8m",
                citations=[citation],
                confidence=0.8,
            ),
        ]
    )

    assert answer.status == "missing_info"
    assert answer.citations == []
    assert answer.source_version_ids == []
    assert "Garage dominance: missing_info" in answer.answer
    assert "Front setback" not in answer.answer


def test_project_chat_summary_all_pass_still_requires_human_review_status():
    citation = Citation(
        source_document_id="src_front_setback",
        source_title="Approved Front Setback Policy",
        source_version_id="sv_front_setback",
        version_label="approved-current",
        effective_date="2026-06-01",
        retrieved_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
        clause_id="4.1",
        heading="Front setback",
        page_number=1,
        canonical_url="https://example.test/front-setback-policy",
        quote="Front setback must be at least 4 metres.",
    )

    answer = _project_compliance_summary_answer(
        [
            _check_result(
                check_key="front_setback",
                label="Front setback",
                status="likely_pass",
                proposed="4.8m",
                citations=[citation],
                confidence=0.8,
            ),
            _check_result(
                check_key="heritage_overlay_trigger",
                label="Heritage overlay trigger",
                status="not_applicable",
                proposed="heritage_overlay_flag=0",
                confidence=0.7,
            ),
        ]
    )

    assert answer.status == "needs_human_review"
    assert answer.citations == [citation]
    assert answer.source_version_ids == ["sv_front_setback"]
    assert "Human signoff is required before any export is treated as submission-ready." in answer.missing_information


def test_targeted_project_chat_answer_includes_trace_and_evidence_refs():
    result = _check_result(
        check_key="site_cover",
        label="Site cover",
        status="likely_fail",
        proposed="50.0% from 250m2 / 500m2",
        confidence=0.8,
        evidence_refs=[
            "document:doc_site_plan:page:1:fact:building_footprint",
            "document:doc_site_plan:page:1:fact:site_area",
        ],
    )

    answer = _targeted_project_check_answer([result])

    assert answer.status == "likely_fail"
    assert "Decision trace: dt_site_cover" in answer.answer
    assert "Evidence refs:" in answer.answer
    assert "document:doc_site_plan:page:1:fact:building_footprint" in answer.answer


def test_targeted_project_chat_likely_pass_keeps_signoff_requirement_in_metadata():
    citation = Citation(
        source_document_id="src_front_setback",
        source_title="Approved Front Setback Policy",
        source_version_id="sv_front_setback",
        version_label="approved-current",
        effective_date="2026-06-01",
        retrieved_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
        clause_id="4.1",
        heading="Front setback",
        page_number=1,
        canonical_url="https://example.test/front-setback-policy",
        quote="Front setback must be at least 4 metres.",
    )
    result = _check_result(
        check_key="front_setback",
        label="Front setback",
        status="likely_pass",
        proposed="4.8m",
        citations=[citation],
        confidence=0.8,
    )

    answer = _targeted_project_check_answer([result])

    assert answer.status == "likely_pass"
    assert answer.human_review_required is True
    assert "Human signoff is required before any export is treated as submission-ready." in answer.missing_information
    assert "This does not assert final compliance" in answer.answer


def _check_result(
    *,
    check_key: str,
    label: str,
    status: str,
    proposed: str = "not evaluated",
    missing_information: list[str] | None = None,
    citations: list[Citation] | None = None,
    evidence_refs: list[str] | None = None,
    confidence: float = 0.0,
) -> CheckResultRead:
    return CheckResultRead(
        id=f"res_{check_key}",
        decision_trace_id=f"dt_{check_key}",
        check_key=check_key,
        label=label,
        category="planning",
        status=status,  # type: ignore[arg-type]
        as_of_date="2026-06-06",
        assessment_basis="current_rules",
        requirement='{"source": "fixture"}',
        proposed=proposed,
        evidence_refs=evidence_refs or [],
        citations=citations or [],
        assumptions=[],
        missing_information=missing_information or [],
        confidence=confidence,
        requires_human_review=True,
        created_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
    )
