from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from draftcheck_core.database import Base
from draftcheck_core.models import (
    Clause,
    ClauseDisposition,
    RuleExtractionCandidate,
    SourceDocument,
    SourceLicenceReview,
    SourceVersion,
)
from scripts.extract_source_rules import extract_targets, select_targets


def test_extract_source_rules_selects_accepted_parseable_sources_by_title():
    db = _session()
    try:
        _add_source(db, "src_ok", "R-Codes Accepted Fixture", review_status="accepted")
        _add_source(db, "src_pending", "R-Codes Pending Fixture", review_status="pending_review")
        _add_source(db, "src_metadata", "R-Codes Metadata Fixture", parse_status="metadata_only")
        db.flush()

        targets = select_targets(db, source_title_contains="R-Codes", all_sources=False)

        assert [target.source_document_id for target in targets] == ["src_ok"]
    finally:
        db.close()


def test_extract_source_rules_creates_reviewable_candidates_without_approving_rules():
    db = _session()
    try:
        _add_source(db, "src_site_cover", "Site Cover Fixture")
        db.add(
            Clause(
                id="cl_site_cover",
                source_version_id="sv_src_site_cover",
                clause_id="1.1",
                heading="Site cover",
                page_number=1,
                text="R30 maximum site cover 60%.",
                normalized_text="r30 maximum site cover 60%.",
                start_anchor="p1",
                text_sha256="hash-clause",
            )
        )
        db.flush()
        targets = select_targets(db, source_title_contains="Site Cover Fixture")

        summaries = extract_targets(db, targets)

        assert len(summaries) == 1
        assert summaries[0].clauses_scanned == 1
        assert summaries[0].dispositions_created == 1
        assert summaries[0].candidates_created == 1
        assert summaries[0].can_support_retrieval is False
        candidate = db.scalar(select(RuleExtractionCandidate))
        assert candidate is not None
        assert candidate.rule_key == "site_cover"
        assert candidate.status == "candidate"
        disposition = db.scalar(select(ClauseDisposition))
        assert disposition is not None
        assert disposition.disposition == "rule_bearing"
    finally:
        db.close()


def test_extract_source_rules_requires_explicit_source_selection():
    db = _session()
    try:
        try:
            select_targets(db)
        except SystemExit as exc:
            assert "Select a source" in str(exc)
        else:
            raise AssertionError("Expected SystemExit")
    finally:
        db.close()


def _add_source(
    db,
    source_id: str,
    title: str,
    *,
    review_status: str = "accepted",
    parse_status: str = "ok",
) -> None:
    version_id = f"sv_{source_id}"
    db.add(
        SourceDocument(
            id=source_id,
            title=title,
            authority="Example authority",
            source_type="r_code",
            canonical_url=f"https://example.test/{source_id}",
        )
    )
    db.add(
        SourceVersion(
            id=version_id,
            source_document_id=source_id,
            version_label="current",
            content_sha256=f"hash-{source_id}",
            parse_status=parse_status,
            review_status=review_status,
            raw_text="R30 maximum site cover 60%.",
        )
    )
    db.add(
        SourceLicenceReview(
            source_document_id=source_id,
            source_version_id=version_id,
            review_status="approved",
            allowed_use=True,
            allowed_storage=True,
            allowed_ai_processing=True,
            reviewed_by="test",
        )
    )


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
