from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from draftcheck_compliance.rules import RuleGovernanceService
from draftcheck_core.database import Base
from draftcheck_core.json_utils import hash_text, normalize_text
from draftcheck_core.models import Clause, SourceDocument, SourceLicenceReview, SourceVersion, utcnow
from draftcheck_core.source_governance import SourceGovernanceService
from draftcheck_shared.schemas import RuleCandidatePromotionRequest
from scripts.rule_review_worklist import _build_report, _select_targets


def test_rule_review_worklist_reports_gate_candidates_and_source_scoped_queue_items():
    db = _session()
    try:
        source, version = _source_with_clause(db)
        RuleGovernanceService(db).extract_source_version_rules(version.id)
        SourceGovernanceService(db).acceptance_gate(source.id, version.id, enqueue_review_items=True)
        db.flush()

        targets = _select_targets(
            db,
            source_version_id=version.id,
            source_title_contains=None,
            limit=None,
        )
        report = "\n".join(_build_report(db, targets))

        assert "# Rule Review Worklist" in report
        assert "Worklist Fixture Policy" in report
        assert f"Source version: `{version.id}`" in report
        assert "Acceptance gate: `blocked`" in report
        assert "`rule_coverage`: fail blocking" in report
        assert "### Rule Rows" in report
        assert "### Rule Candidates" in report
        assert "`wall_setback`" in report
        assert "A wall must be set back at least 1.5 m unless exempt" in report
        assert "`rule_review`" in report
        assert "Suggested action:" in report
        assert "Audit: `rule_coverage` / `candidate_not_promoted`" in report
        assert "Audit: `no_orphan` / `pending_rule_review`" in report
        assert "Evidence quote:" in report
        assert "Candidate IDs:" in report
    finally:
        db.close()


def test_rule_review_worklist_reports_pending_rule_rows():
    db = _session()
    try:
        _source, version = _source_with_clause(db)
        rules = RuleGovernanceService(db)
        extracted = rules.extract_source_version_rules(version.id)
        promoted = rules.promote_rule_candidate(
            extracted.candidates[0].id,
            RuleCandidatePromotionRequest(reviewed_by="rules@example.test"),
        )
        db.flush()

        targets = _select_targets(
            db,
            source_version_id=version.id,
            source_title_contains=None,
            limit=None,
        )
        report = "\n".join(_build_report(db, targets))

        assert "### Rule Rows" in report
        assert f"`{promoted.id}` `pending_review` `wall_setback`" in report
        assert "approve only after source, quote, condition, and rule semantics are verified" in report
    finally:
        db.close()


def test_rule_review_worklist_requires_explicit_source_filter():
    db = _session()
    try:
        try:
            _select_targets(db, source_version_id=None, source_title_contains=None, limit=None)
        except SystemExit as exc:
            assert "Select a source" in str(exc)
        else:
            raise AssertionError("Expected SystemExit")
    finally:
        db.close()


def _source_with_clause(db):
    text = "5.1 Street setbacks\nA wall must be set back at least 1.5 m unless exempt."
    source = SourceDocument(
        title="Worklist Fixture Policy",
        authority="Example council",
        source_type="local_planning_policy",
        canonical_url="https://example.test/worklist",
        access_type="public",
    )
    version = SourceVersion(
        source_document=source,
        version_label="current",
        effective_date="2026-06-06",
        content_sha256=hash_text(text),
        raw_text=text,
        parse_status="ok",
        review_status="accepted",
        reviewed_by="fixture",
        reviewed_at=utcnow(),
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
    db.add(
        Clause(
            source_version_id=version.id,
            clause_id="5.1",
            heading="Street setbacks",
            text=text,
            normalized_text=normalize_text(text),
            start_anchor="5.1",
            text_sha256=hash_text(text),
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
