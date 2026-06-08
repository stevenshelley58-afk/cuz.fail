from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from draftcheck_compliance.rules import RuleGovernanceService
from draftcheck_core.database import Base
from draftcheck_core.json_utils import hash_text, normalize_text
from draftcheck_core.models import (
    Clause,
    RuleExtractionCandidate,
    RuleRow,
    SourceDocument,
    SourceLicenceReview,
    SourceVersion,
    utcnow,
)
from draftcheck_core.source_governance import SourceGovernanceService
from scripts.promote_rule_candidate import promote_candidates


def test_promote_rule_candidate_creates_pending_rule_row_and_reconciles_stale_queue_items():
    db = _session()
    try:
        source, version = _source_with_clause(db)
        extracted = RuleGovernanceService(db).extract_source_version_rules(version.id)
        candidate_id = extracted.candidates[0].id
        SourceGovernanceService(db).acceptance_gate(source.id, version.id, enqueue_review_items=True)
        db.flush()

        summaries, reconciliations = promote_candidates(
            db,
            candidate_ids=[candidate_id],
            reviewed_by="rules@example.test",
            notes="Script fixture promotion.",
            reconcile_source=True,
        )

        assert len(summaries) == 1
        summary = summaries[0]
        assert summary.candidate_id == candidate_id
        assert summary.source_document_id == source.id
        assert summary.source_version_id == version.id
        assert summary.rule_key == "wall_setback"
        assert summary.candidate_status == "pending_review"
        assert summary.rule_lifecycle_status == "pending_review"

        candidate = db.get(RuleExtractionCandidate, candidate_id)
        assert candidate is not None
        assert candidate.status == "pending_review"
        assert "Script fixture promotion." in candidate.review_notes

        rule_row = db.get(RuleRow, summary.rule_row_id)
        assert rule_row is not None
        assert rule_row.lifecycle_status == "pending_review"
        assert rule_row.approved_by is None
        assert rule_row.approved_at is None

        assert len(reconciliations) == 1
        assert len(reconciliations[0].resolved_item_ids) >= 1
        current_targets = {
            (item["target_type"], item["reason"]) for item in reconciliations[0].current_blocker_keys
        }
        assert ("rule_row", "Rule coverage gap: rule_not_approved in clause 5.1") in current_targets
        assert ("rule_extraction_candidate", "Rule coverage gap: candidate_not_promoted in clause 5.1") not in (
            current_targets
        )

        promoted_again, _reconciled_again = promote_candidates(db, candidate_ids=[candidate_id])
        assert promoted_again[0].rule_row_id == summary.rule_row_id
        assert db.scalar(select(RuleRow).where(RuleRow.source_version_id == version.id)).id == summary.rule_row_id
    finally:
        db.close()


def _source_with_clause(db):
    text = "5.1 Street setbacks\nA wall must be set back at least 1.5 m unless exempt."
    source = SourceDocument(
        title="Promotion Fixture Policy",
        authority="Example council",
        source_type="local_planning_policy",
        canonical_url="https://example.test/promotion",
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
