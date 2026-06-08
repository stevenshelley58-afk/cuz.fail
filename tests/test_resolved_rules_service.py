from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from draftcheck_compliance.resolved_rules import ResolvedRuleService
from draftcheck_compliance.service import ComplianceService
from draftcheck_core.database import Base
from draftcheck_core.json_utils import from_json, hash_text, normalize_text, to_json
from draftcheck_core.models import (
    AddressProfile,
    Clause,
    ClauseDisposition,
    ExtractedMeasurement,
    Project,
    RuleOverride,
    RuleRow,
    SourceChunk,
    SourceCitation,
    SourceDocument,
    SourceLicenceReview,
    SourceVersion,
    utcnow,
)
from draftcheck_shared.schemas import Citation, ResolvedRulesRequest


def test_resolved_rules_from_approved_rule_rows_drive_compliance_gate():
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
            project_name="Resolved rule project",
            address="1 Example Street, Spearwood WA",
            local_government="Cockburn",
            project_type="single_house",
            stage="concept",
            as_of_date="2026-06-06",
        )
        db.add(project)
        db.flush()
        profile = AddressProfile(
            project_id=project.id,
            input_address=project.address,
            formatted_address=project.address,
            resolution_status="resolved",
            confidence="high",
            local_government="Cockburn",
            resolver_sources_json="[]",
            dataset_version_ids_json="[]",
            issues_json="[]",
            as_of_date="2026-06-06",
        )
        source = SourceDocument(
            title="Cockburn Site Cover Policy",
            authority="City of Cockburn",
            local_government="Cockburn",
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
        db.add_all([profile, source, version])
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
                disposition="rule_bearing",
                rationale="Approved site-cover rule row exists.",
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
        rule = RuleRow(
            rule_key="site_cover",
            operator="<=",
            value_json=to_json({"max_percent": 55}),
            unit="percent",
            condition_text="single house site cover",
            quote=text,
            clause_id=clause.id,
            source_version_id=version.id,
            lifecycle_status="approved",
            approved_by="tester",
            approved_at=utcnow(),
        )
        db.add_all([chunk, review, rule])
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
        db.add(
            SourceCitation(
                source_chunk_id=chunk.id,
                source_version_id=version.id,
                clause_id=clause.id,
                citation_json=to_json(citation.model_dump(mode="json")),
            )
        )
        db.add_all(
            [
                ExtractedMeasurement(project_id=project.id, key="site_area_m2", value=500, unit="m2"),
                ExtractedMeasurement(
                    project_id=project.id,
                    key="building_footprint_m2",
                    value=250,
                    unit="m2",
                ),
            ]
        )
        db.flush()

        resolved = ResolvedRuleService(db).resolve_for_project(
            project.id,
            ResolvedRulesRequest(address_profile_id=profile.id, as_of_date="2026-06-06"),
        )
        assert resolved.status == "needs_human_review"
        assert resolved.issues == []
        assert len(resolved.resolved_rules) == 1
        assert resolved.resolved_rules[0].rule_row_id == rule.id
        assert resolved.resolved_rules[0].citations

        matrix = ComplianceService(db).run_checks(project.id)
        site_cover = next(row for row in matrix.results if row.check_key == "site_cover")
        assert site_cover.status == "likely_pass"
        assert site_cover.decision_trace_id
        assert site_cover.rule_ids == [rule.id]
        assert site_cover.resolved_rule_ids == [resolved.resolved_rules[0].id]
        assert site_cover.measurement_ids
    finally:
        db.close()


def test_resolved_rules_exclude_legacy_accepted_source_with_unresolved_rule_gaps():
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
            project_name="Legacy gap project",
            address="1 Example Street, Spearwood WA",
            local_government="Cockburn",
            project_type="single_house",
            stage="concept",
            as_of_date="2026-06-06",
        )
        profile = AddressProfile(
            project_id=project.id,
            input_address=project.address,
            formatted_address=project.address,
            resolution_status="resolved",
            confidence="high",
            local_government="Cockburn",
            resolver_sources_json="[]",
            dataset_version_ids_json="[]",
            issues_json="[]",
            as_of_date="2026-06-06",
        )
        source = SourceDocument(
            title="Legacy Accepted Mixed Policy",
            authority="City of Cockburn",
            local_government="Cockburn",
            source_type="local_planning_policy",
            canonical_url="https://example.test/legacy-accepted-mixed-policy",
        )
        version = SourceVersion(
            source_document=source,
            version_label="legacy-accepted",
            effective_date="2026-06-01",
            content_sha256=hash_text("legacy-accepted-mixed-policy"),
            review_status="accepted",
            reviewed_by="legacy-import",
            reviewed_at=utcnow(),
            raw_text="Site cover and unresolved setback controls.",
        )
        db.add_all([project, profile, source, version])
        db.flush()

        site_cover_text = "Site cover maximum percentage requirement."
        site_cover_clause = Clause(
            source_version_id=version.id,
            clause_id="5.3.1",
            heading="Site cover",
            text=site_cover_text,
            normalized_text=normalize_text(site_cover_text),
            start_anchor="5.3.1",
            text_sha256=hash_text(site_cover_text),
        )
        gap_text = "A wall must be set back at least 1.5 m unless exempt."
        gap_clause = Clause(
            source_version_id=version.id,
            clause_id="5.4.1",
            heading="Wall setbacks",
            text=gap_text,
            normalized_text=normalize_text(gap_text),
            start_anchor="5.4.1",
            text_sha256=hash_text(gap_text),
        )
        db.add_all([site_cover_clause, gap_clause])
        db.flush()

        db.add(
            ClauseDisposition(
                clause_id=site_cover_clause.id,
                disposition="rule_bearing",
                rationale="Approved site-cover rule row exists.",
                reviewer="fixture",
            )
        )
        chunk = SourceChunk(
            source_version_id=version.id,
            clause_id=site_cover_clause.id,
            heading=site_cover_clause.heading,
            text=site_cover_text,
            token_count=len(site_cover_text.split()),
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
        rule = RuleRow(
            rule_key="site_cover",
            operator="<=",
            value_json=to_json({"max_percent": 55}),
            unit="percent",
            condition_text="single house site cover",
            quote=site_cover_text,
            clause_id=site_cover_clause.id,
            source_version_id=version.id,
            lifecycle_status="approved",
            approved_by="tester",
            approved_at=utcnow(),
        )
        db.add_all([chunk, review, rule])
        db.flush()

        citation = Citation(
            source_document_id=source.id,
            source_title=source.title,
            source_version_id=version.id,
            version_label=version.version_label,
            effective_date=version.effective_date,
            retrieved_at=version.retrieved_at,
            clause_id=site_cover_clause.clause_id,
            heading=site_cover_clause.heading,
            canonical_url=source.canonical_url,
            quote=site_cover_text,
        )
        db.add(
            SourceCitation(
                source_chunk_id=chunk.id,
                source_version_id=version.id,
                clause_id=site_cover_clause.id,
                citation_json=to_json(citation.model_dump(mode="json")),
            )
        )
        db.flush()

        resolved = ResolvedRuleService(db).resolve_for_project(
            project.id,
            ResolvedRulesRequest(address_profile_id=profile.id, as_of_date="2026-06-06"),
        )

        assert resolved.status == "unsupported"
        assert resolved.resolved_rules == []
        assert "approved_rule_rows_not_available" in resolved.issues
    finally:
        db.close()


def test_resolved_rules_apply_override_precedence_before_compliance_thresholds():
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
            project_name="Override rule project",
            address="1 Example Street, Spearwood WA",
            local_government="Cockburn",
            project_type="single_house",
            stage="concept",
            as_of_date="2026-06-06",
            assessment_basis="current_rules",
        )
        profile = AddressProfile(
            project_id=project.id,
            input_address=project.address,
            formatted_address=project.address,
            resolution_status="resolved",
            confidence="high",
            local_government="Cockburn",
            resolver_sources_json="[]",
            dataset_version_ids_json="[]",
            issues_json="[]",
            as_of_date="2026-06-06",
            assessment_basis="current_rules",
        )
        source = SourceDocument(
            title="Cockburn Override Site Cover Policy",
            authority="City of Cockburn",
            local_government="Cockburn",
            source_type="local_planning_policy",
            canonical_url="https://example.test/site-cover-override-policy",
        )
        version = SourceVersion(
            source_document=source,
            version_label="approved-current",
            effective_date="2026-06-01",
            content_sha256=hash_text("override-site-cover-policy"),
            review_status="accepted",
            reviewed_by="fixture",
            reviewed_at=utcnow(),
            raw_text="Site cover R-Codes open space maximum percentage requirement.",
        )
        db.add_all([project, profile, source, version])
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
                disposition="rule_bearing",
                rationale="Approved site-cover override rule rows exist.",
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
        base_rule = RuleRow(
            rule_key="site_cover",
            operator="<=",
            value_json=to_json({"max_percent": 55}),
            unit="percent",
            condition_text="base site cover",
            quote=text,
            clause_id=clause.id,
            source_version_id=version.id,
            lifecycle_status="approved",
            approved_by="tester",
            approved_at=utcnow(),
        )
        overriding_rule = RuleRow(
            rule_key="site_cover",
            operator="<=",
            value_json=to_json({"max_percent": 45}),
            unit="percent",
            condition_text="local override site cover",
            quote=text,
            clause_id=clause.id,
            source_version_id=version.id,
            lifecycle_status="approved",
            approved_by="tester",
            approved_at=utcnow(),
        )
        db.add_all([chunk, review, base_rule, overriding_rule])
        db.flush()
        db.add(
            RuleOverride(
                overriding_rule_id=overriding_rule.id,
                overridden_rule_id=base_rule.id,
                scope_json=to_json({"local_government": "Cockburn"}),
                reason="Local site-cover policy overrides the base threshold for Cockburn projects.",
            )
        )

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
        db.add(
            SourceCitation(
                source_chunk_id=chunk.id,
                source_version_id=version.id,
                clause_id=clause.id,
                citation_json=to_json(citation.model_dump(mode="json")),
            )
        )
        db.add_all(
            [
                ExtractedMeasurement(project_id=project.id, key="site_area_m2", value=500, unit="m2"),
                ExtractedMeasurement(
                    project_id=project.id,
                    key="building_footprint_m2",
                    value=250,
                    unit="m2",
                ),
            ]
        )
        db.flush()

        resolved = ResolvedRuleService(db).resolve_for_project(
            project.id,
            ResolvedRulesRequest(address_profile_id=profile.id, as_of_date="2026-06-06"),
        )

        assert resolved.issues == []
        assert len(resolved.resolved_rules) == 1
        assert resolved.resolved_rules[0].rule_row_id == overriding_rule.id
        assert resolved.resolved_rules[0].overridden_rule_ids == [base_rule.id]

        service = ComplianceService(db)
        matrix = service.run_checks(project.id)
        site_cover = next(row for row in matrix.results if row.check_key == "site_cover")
        trace = service.get_decision_trace(project.id, site_cover.id)
        assert trace is not None

        assert site_cover.status == "likely_fail"
        assert from_json(trace.rule_ids_json, []) == [overriding_rule.id]
        assert from_json(trace.inputs_json, {})["requirement"]["max_percent"] == 45.0
        assert from_json(trace.precedence_trace_json, {})["overridden_rule_ids"] == [base_rule.id]
    finally:
        db.close()
