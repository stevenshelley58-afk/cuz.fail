from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from draftcheck_core.bootstrap_sources import ensure_demo_source_library
from draftcheck_core.database import Base
from draftcheck_core.json_utils import to_json
from draftcheck_core.models import (
    Clause,
    RuleRow,
    SourceChunk,
    SourceCitation,
    SourceDocument,
    SourceLicenceReview,
    SourceVersion,
)
from draftcheck_shared.schemas import Citation
from scripts.audit_source_library import _build_report, _fts_count


def test_source_library_audit_reports_runtime_citable_gate_for_bootstrap_source():
    db = _session()
    try:
        ensure_demo_source_library(db)

        report = "\n".join(_build_report(db))

        assert "- Stored source chunks: 10" in report
        assert "- SQLite FTS citable indexed chunks:" in report
        assert "- Citable retrieval supported source versions: 7" in report
        assert "## Citable Retrieval Gate" in report
        assert "R-Codes Volume 1 bootstrap excerpt" in report
        assert "4.1 Solar and daylight access - Demonstrating solar access" in report
        assert "4.2 Natural ventilation - Optimal orientation for natural ventilation" in report
        assert "Bushfires: BAL Assessment (Basic) Report" in report
    finally:
        db.close()


def test_source_library_audit_warns_when_chunks_exist_but_gate_has_no_supported_versions():
    db = _session()
    try:
        source = SourceDocument(
            id="src_chunks_only",
            title="Accepted chunks without rule audit clearance",
            authority="Example authority",
            source_type="guidance",
            canonical_url="https://example.test/source",
        )
        version = SourceVersion(
            id="sv_chunks_only",
            source_document_id=source.id,
            version_label="current",
            content_sha256="abc123",
            parse_status="ok",
            review_status="accepted",
            raw_text="R30 maximum site cover 60%.",
        )
        licence = SourceLicenceReview(
            source_document_id=source.id,
            source_version_id=version.id,
            review_status="approved",
            allowed_use=True,
            allowed_storage=True,
            allowed_ai_processing=True,
            reviewed_by="test",
            reviewed_at=datetime.now(UTC),
        )
        clause = Clause(
            id="cl_chunks_only",
            source_version_id=version.id,
            clause_id="1.1",
            heading="Site cover",
            page_number=1,
            text="R30 maximum site cover 60%.",
            normalized_text="r30 maximum site cover 60%.",
            start_anchor="p1",
            text_sha256="def456",
        )
        chunk = SourceChunk(
            id="chk_chunks_only",
            source_version_id=version.id,
            clause_id=clause.id,
            heading="Site cover",
            page_number=1,
            text=clause.text,
            token_count=5,
        )
        citation = Citation(
            source_document_id=source.id,
            source_title=source.title,
            source_version_id=version.id,
            version_label=version.version_label,
            retrieved_at=datetime.now(UTC),
            clause_id=clause.clause_id,
            heading=clause.heading,
            page_number=clause.page_number,
            canonical_url=source.canonical_url,
            quote=clause.text,
        )
        db.add_all(
            [
                source,
                version,
                licence,
                clause,
                chunk,
                SourceCitation(
                    id="cit_chunks_only",
                    source_chunk_id=chunk.id,
                    source_version_id=version.id,
                    clause_id=clause.id,
                    citation_json=to_json(citation.model_dump(mode="json")),
                ),
            ]
        )
        db.flush()

        report = "\n".join(_build_report(db))

        assert "- Stored source chunks: 1" in report
        assert "- Citable retrieval supported source versions: 0" in report
        assert "No source version currently passes the runtime citable retrieval gate." in report
        assert "Stored chunks alone are not enough" in report
    finally:
        db.close()


def test_source_library_audit_separates_pending_and_approved_rule_rows():
    db = _session()
    try:
        source = SourceDocument(
            id="src_rules",
            title="Rule count fixture",
            authority="Example authority",
            source_type="guidance",
            canonical_url="https://example.test/rules",
        )
        version = SourceVersion(
            id="sv_rules",
            source_document_id=source.id,
            version_label="current",
            content_sha256="rules-hash",
            parse_status="ok",
            review_status="accepted",
            raw_text="A wall must be set back at least 1.5 m.",
        )
        clause = Clause(
            id="cl_rules",
            source_version_id=version.id,
            clause_id="1.1",
            heading="Setbacks",
            page_number=1,
            text="A wall must be set back at least 1.5 m.",
            normalized_text="a wall must be set back at least 1.5 m.",
            start_anchor="p1",
            text_sha256="rules-clause-hash",
        )
        db.add_all(
            [
                source,
                version,
                clause,
                RuleRow(
                    source_version_id=version.id,
                    clause_id=clause.id,
                    rule_key="wall_setback",
                    operator=">=",
                    value_json=to_json({"min_value": 1.5}),
                    unit="m",
                    quote="A wall must be set back at least 1.5 m.",
                    lifecycle_status="approved",
                    approved_by="reviewer@example.test",
                    approved_at=datetime.now(UTC),
                ),
                RuleRow(
                    source_version_id=version.id,
                    clause_id=clause.id,
                    rule_key="wall_setback",
                    operator=">=",
                    value_json=to_json({"min_value": 2.0}),
                    unit="m",
                    quote="A wall must be set back at least 1.5 m.",
                    lifecycle_status="pending_review",
                ),
            ]
        )
        db.flush()

        report = "\n".join(_build_report(db))

        assert "- Rule rows: 2 total, 1 approved" in report
        assert "- Approved rule rows: 2" not in report
    finally:
        db.close()


def test_source_library_audit_skips_sqlite_fts_count_on_postgres_dialect():
    class FakeBind:
        class dialect:
            name = "postgresql"

    class FakeSession:
        def get_bind(self):
            return FakeBind()

        def execute(self, _statement):
            raise AssertionError("Postgres audit must not query sqlite_master")

    assert _fts_count(FakeSession()) is None


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
