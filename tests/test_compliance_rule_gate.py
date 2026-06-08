from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from draftcheck_compliance.service import ComplianceService
from draftcheck_core.database import Base
from draftcheck_core.json_utils import from_json, hash_text, normalize_text, to_json
from draftcheck_core.models import (
    Clause,
    ClauseDisposition,
    ExtractedMeasurement,
    Project,
    ResolvedRule,
    RuleRow,
    SourceChunk,
    SourceCitation,
    SourceDocument,
    SourceLicenceReview,
    SourceVersion,
    utcnow,
)
from draftcheck_shared.schemas import Citation


def test_approved_rule_row_allows_likely_status_and_is_traced():
    result = _run_site_cover_with_approved_rule(max_percent=55)

    assert result["status"] == "likely_pass"
    assert result["as_of_date"] == "2026-06-06"
    assert result["assessment_basis"] == "current_rules"
    assert "approved rule row for site_cover" not in result["missing_information"]
    assert result["rule_id"] in result["trace_rule_ids"]
    assert result["resolved_rule_id"] in result["trace_resolved_rule_ids"]
    assert result["comparison"] == "50.0 <= 55.0"
    assert result["requirement"]["max_percent"] == 55.0
    assert result["evidence_refs"] == [
        "document:doc_site_plan:page:1:fact:building_footprint",
        "document:doc_site_plan:page:1:fact:site_area",
    ]
    assert result["trace_input_sources"][:2] == [
        {
            "type": "measurement",
            "id": result["measurement_ids"][0],
            "key": "building_footprint_m2",
            "source": "drawing_fact",
            "evidence_ref": "document:doc_site_plan:page:1:fact:building_footprint",
        },
        {
            "type": "measurement",
            "id": result["measurement_ids"][1],
            "key": "site_area_m2",
            "source": "drawing_fact",
            "evidence_ref": "document:doc_site_plan:page:1:fact:site_area",
        },
    ]
    assert result["trace_inputs"]["as_of_date"] == "2026-06-06"
    assert result["trace_inputs"]["assessment_basis"] == "current_rules"


def test_approved_rule_row_threshold_replaces_seed_default():
    result = _run_site_cover_with_approved_rule(max_percent=45)

    assert result["status"] == "likely_fail"
    assert result["comparison"] == "50.0 <= 45.0"
    assert result["requirement"]["max_percent"] == 45.0


def test_approved_rule_row_without_resolved_rule_is_review_gated():
    result = _run_site_cover_with_approved_rule(max_percent=55, with_resolved_rule=False)

    assert result["status"] == "needs_human_review"
    assert "approved resolved rule for site_cover" in result["missing_information"]
    assert result["trace_resolved_rule_ids"] == []


def test_resolved_rule_with_different_assessment_context_is_review_gated():
    result = _run_site_cover_with_approved_rule(max_percent=55, resolved_rule_as_of_date="2026-01-01")

    assert result["status"] == "needs_human_review"
    assert "approved resolved rule for site_cover" in result["missing_information"]
    assert result["trace_resolved_rule_ids"] == []


def test_stale_resolved_rule_is_review_gated():
    result = _run_site_cover_with_approved_rule(max_percent=55, resolved_rule_status="stale")

    assert result["status"] == "needs_human_review"
    assert "approved resolved rule for site_cover" in result["missing_information"]
    assert result["trace_resolved_rule_ids"] == []


def test_likely_status_uses_resolved_rule_citation_not_unrelated_retrieval_hit():
    result = _run_site_cover_with_approved_rule(
        max_percent=55,
        with_rule_source_citation=False,
        with_unrelated_retrieval_citation=True,
    )

    assert result["status"] == "likely_pass"
    assert result["citation_source_titles"] == ["Approved Site Cover Policy"]
    assert result["trace_citation_source_version_ids"] == [result["rule_source_version_id"]]


def test_seed_threshold_ignores_raw_retrieval_citation_without_approved_rule_row():
    result = _run_site_cover_with_approved_rule(
        max_percent=55,
        with_approved_rule_row=False,
        with_resolved_rule=False,
        with_rule_source_citation=True,
    )

    assert result["status"] == "unsupported"
    assert result["citation_source_titles"] == []
    assert "approved rule row for site_cover" in result["missing_information"]
    assert "approved source citation" in result["missing_information"]
    assert result["trace_citation_source_version_ids"] == []


def _run_site_cover_with_approved_rule(
    max_percent: float,
    with_approved_rule_row: bool = True,
    with_resolved_rule: bool = True,
    resolved_rule_as_of_date: str = "2026-06-06",
    resolved_rule_status: str = "needs_human_review",
    with_rule_source_citation: bool = True,
    with_unrelated_retrieval_citation: bool = False,
) -> dict[str, Any]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    db = session_factory()
    try:
        project = Project(
            project_name="Approved rule project",
            address="1 Example Street, Spearwood WA",
            local_government="Cockburn",
            project_type="single_house",
            stage="concept",
            as_of_date="2026-06-06",
            assessment_basis="current_rules",
        )
        source = SourceDocument(
            title="Approved Site Cover Policy",
            authority="City of Cockburn",
            source_type="local_planning_policy",
            canonical_url="https://example.test/site-cover-policy",
        )
        version = SourceVersion(
            source_document=source,
            version_label="approved-current",
            effective_date="2026-06-01",
            content_sha256=hash_text("approved-site-cover-policy"),
            review_status="accepted",
            reviewed_by="fixture",
            reviewed_at=utcnow(),
            raw_text="Site cover R-Codes open space maximum percentage requirement.",
        )
        db.add_all([project, source, version])
        db.flush()

        text = "Site cover R-Codes open space maximum percentage requirement."
        clause = Clause(
            source_version_id=version.id,
            clause_id="5.3.1",
            heading="Site cover",
            page_number=1,
            text=text,
            normalized_text=normalize_text(text),
            start_anchor="5.3.1",
            text_sha256=hash_text(text),
        )
        db.add(clause)
        db.flush()
        db.add(
            ClauseDisposition(
                clause_id=clause.id,
                disposition="rule_bearing" if with_approved_rule_row else "informational",
                rationale="Fixture source review disposition.",
                reviewer="fixture",
            )
        )

        chunk = SourceChunk(
            source_version_id=version.id,
            clause_id=clause.id,
            heading=clause.heading,
            page_number=1,
            text=text,
            token_count=len(text.split()),
        )
        review = SourceLicenceReview(
            source_document_id=source.id,
            source_version_id=version.id,
            allowed_use=True,
            allowed_storage=True,
            allowed_ai_processing=True,
            reviewed_at=utcnow(),
            review_status="approved",
        )
        rule = None
        if with_approved_rule_row:
            rule = RuleRow(
                rule_key="site_cover",
                operator="<=",
                value_json=to_json({"max_percent": max_percent}),
                unit="percent",
                condition_text="single house site cover",
                quote=text,
                clause_id=clause.id,
                source_version_id=version.id,
                lifecycle_status="approved",
                approved_by="tester",
                approved_at=utcnow(),
            )
            db.add(rule)
        db.add_all([chunk, review])
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
            page_number=1,
            canonical_url=source.canonical_url,
            quote=text,
        )
        resolved_rule = None
        if with_resolved_rule and rule:
            resolved_rule = ResolvedRule(
                project_id=project.id,
                rule_row_id=rule.id,
                as_of_date=resolved_rule_as_of_date,
                assessment_basis="current_rules",
                applies_reason="Fixture project resolves to the approved site cover rule.",
                status=resolved_rule_status,
                citations_json=to_json([citation.model_dump(mode="json")]),
            )
        if with_rule_source_citation:
            db.add(
                SourceCitation(
                    source_chunk_id=chunk.id,
                    source_version_id=version.id,
                    clause_id=clause.id,
                    citation_json=to_json(citation.model_dump(mode="json")),
                )
            )
        if with_unrelated_retrieval_citation:
            other_source = SourceDocument(
                title="Unrelated Retrieval Hit",
                authority="City of Cockburn",
                source_type="local_planning_policy",
                canonical_url="https://example.test/unrelated-site-cover",
            )
            other_version = SourceVersion(
                source_document=other_source,
                version_label="approved-current",
                effective_date="2026-06-01",
                content_sha256=hash_text("unrelated-site-cover"),
                review_status="accepted",
                reviewed_by="fixture",
                reviewed_at=utcnow(),
                raw_text=text,
            )
            db.add_all([other_source, other_version])
            db.flush()
            other_clause = Clause(
                source_version_id=other_version.id,
                clause_id="9.9",
                heading="Unrelated site cover note",
                page_number=9,
                text=text,
                normalized_text=normalize_text(text),
                start_anchor="9.9",
                text_sha256=hash_text(f"unrelated:{text}"),
            )
            db.add(other_clause)
            db.flush()
            other_chunk = SourceChunk(
                source_version_id=other_version.id,
                clause_id=other_clause.id,
                heading=other_clause.heading,
                page_number=9,
                text=text,
                token_count=len(text.split()),
            )
            other_review = SourceLicenceReview(
                source_document_id=other_source.id,
                source_version_id=other_version.id,
                allowed_use=True,
                allowed_storage=True,
                allowed_ai_processing=True,
                reviewed_at=utcnow(),
                review_status="approved",
            )
            db.add_all([other_chunk, other_review])
            db.flush()
            other_citation = Citation(
                source_document_id=other_source.id,
                source_title=other_source.title,
                source_version_id=other_version.id,
                version_label=other_version.version_label,
                effective_date=other_version.effective_date,
                retrieved_at=other_version.retrieved_at,
                clause_id=other_clause.clause_id,
                heading=other_clause.heading,
                page_number=9,
                canonical_url=other_source.canonical_url,
                quote=text,
            )
            db.add(
                SourceCitation(
                    source_chunk_id=other_chunk.id,
                    source_version_id=other_version.id,
                    clause_id=other_clause.id,
                    citation_json=to_json(other_citation.model_dump(mode="json")),
                )
            )
        if resolved_rule:
            db.add(resolved_rule)
        db.add_all(
            [
                ExtractedMeasurement(
                    project_id=project.id,
                    key="site_area_m2",
                    value=500,
                    unit="m2",
                    source="drawing_fact",
                    evidence_ref="document:doc_site_plan:page:1:fact:site_area",
                ),
                ExtractedMeasurement(
                    project_id=project.id,
                    key="building_footprint_m2",
                    value=250,
                    unit="m2",
                    source="drawing_fact",
                    evidence_ref="document:doc_site_plan:page:1:fact:building_footprint",
                ),
            ]
        )
        db.flush()

        service = ComplianceService(db)
        matrix = service.run_checks(project.id)
        site_cover = next(row for row in matrix.results if row.check_key == "site_cover")
        trace = service.get_decision_trace(project.id, site_cover.id)
        assert trace is not None
        trace_citations = from_json(trace.citation_ids_json, [])

        return {
            "status": site_cover.status,
            "as_of_date": site_cover.as_of_date,
            "assessment_basis": site_cover.assessment_basis,
            "missing_information": site_cover.missing_information,
            "citation_source_titles": [citation.source_title for citation in site_cover.citations],
            "trace_citation_source_version_ids": [
                item.get("source_version_id") for item in trace_citations if isinstance(item, dict)
            ],
            "rule_id": rule.id if rule else None,
            "rule_source_version_id": version.id,
            "trace_rule_ids": from_json(trace.rule_ids_json, []),
            "trace_resolved_rule_ids": from_json(trace.resolved_rule_ids_json, []),
            "measurement_ids": from_json(trace.measurement_ids_json, []),
            "evidence_refs": site_cover.evidence_refs,
            "trace_input_sources": from_json(trace.input_sources_json, []),
            "resolved_rule_id": resolved_rule.id if resolved_rule else None,
            "comparison": trace.comparison,
            "trace_inputs": from_json(trace.inputs_json, {}),
            "requirement": from_json(trace.inputs_json, {})["requirement"],
        }
    finally:
        db.close()
