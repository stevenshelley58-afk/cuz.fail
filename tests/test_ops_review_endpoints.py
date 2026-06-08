from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from draftcheck_core.audit import record_audit
from draftcheck_core.database import Base
from draftcheck_core.json_utils import hash_text, normalize_text, to_json
from draftcheck_core.models import (
    Clause,
    SourceChunk,
    SourceCitation,
    SourceDocument,
    SourceLicenceReview,
    SourceVersion,
    utcnow,
)
from draftcheck_core.ops import OpsDashboardService
from draftcheck_shared.schemas import Citation


def test_review_queues_empty_by_default(client):
    response = client.get("/v1/review-queues")

    assert response.status_code == 200, response.text
    assert response.json() == []


def test_ops_dashboard_empty_database_counts_are_deterministic(client):
    response = client.get("/v1/ops/dashboard")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["sources"]["documents"] == {"total": 0, "active": 0, "inactive": 0}
    assert body["sources"]["versions"] == {"total": 0, "current": 0, "superseded": 0, "parse_error": 0}
    assert body["rules"]["total"] == 0
    assert body["jobs"]["total"] == 0
    assert body["compliance"]["total_results"] == 0
    assert body["review_queues"]["total"] == 0
    assert body["review_queues"]["blocking_open"] == 0
    assert body["review_queues"]["by_queue"]["source_review"] == {"total": 0, "open": 0, "blocking_open": 0}
    assert body["release_gate"]["satisfied"] is False
    assert "last_successful_backup_not_recorded" in body["issues"]


def test_ops_dashboard_reports_accepted_sources_blocked_from_citable_retrieval():
    db = _session()
    try:
        source = SourceDocument(
            title="Legacy Accepted Policy With Rule Gaps",
            authority="Example council",
            source_type="local_planning_policy",
            canonical_url="https://example.test/legacy-rule-gaps",
            access_type="public",
        )
        text = "5.1 Street setbacks\nA wall must be set back at least 1.5 m unless exempt."
        version = SourceVersion(
            source_document=source,
            version_label="legacy-accepted",
            effective_date="2026-06-06",
            content_sha256=hash_text(text),
            raw_text=text,
            parse_status="ok",
            review_status="accepted",
            reviewed_by="legacy-import",
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

        dashboard = OpsDashboardService(db).dashboard()

        readiness = dashboard.sources["citable_retrieval"]
        assert readiness["readiness_status"] == "blocked"
        assert readiness["accepted_current_versions"] == 1
        assert readiness["accepted_with_citable_artifacts"] == 1
        assert readiness["supported_versions"] == 0
        assert readiness["blocked_accepted_versions"] == 1
        assert readiness["blocked_by_check"]["rule_coverage"] == 1
        assert readiness["blocked_by_check"]["no_orphan"] == 1
        assert readiness["sample_blocked_versions"][0]["source_version_id"] == version.id
        assert "no_citable_source_versions_available" in dashboard.issues
    finally:
        db.close()


def test_ops_dashboard_requires_production_grade_backup_restore_evidence():
    db = _session()
    try:
        record_audit(
            db,
            action="infra.backup.completed",
            target_type="infrastructure",
            target_id="local-backup",
            metadata={
                "environment": "local",
                "offsite": False,
                "encrypted": False,
                "schedule": "manual",
                "db_backup": "postgres.dump",
                "minio_backup": "minio",
                "manifest_sha256": "abc123",
                "duration_seconds": 1.2,
            },
        )
        record_audit(
            db,
            action="infra.restore.completed",
            target_type="infrastructure",
            target_id="local-restore",
            metadata={
                "environment": "local",
                "clean_machine_restore": False,
                "checksum_validated": True,
                "manifest_sha256": "abc123",
                "duration_seconds": 1.8,
            },
        )

        dashboard = OpsDashboardService(db).dashboard()

        assert dashboard.backups["backup_recorded"] is True
        assert dashboard.backups["restore_recorded"] is True
        assert dashboard.backups["backup_verified"] is False
        assert dashboard.backups["restore_verified"] is False
        assert "production_environment_required" in dashboard.backups["backup_verification_issues"]
        assert "offsite_backup_required" in dashboard.backups["backup_verification_issues"]
        assert "clean_machine_restore_required" in dashboard.backups["restore_verification_issues"]
        assert "last_successful_backup_not_recorded" not in dashboard.issues
        assert "last_successful_restore_test_not_recorded" not in dashboard.issues
        assert "production_backup_not_verified" in dashboard.issues
        assert "production_restore_test_not_verified" in dashboard.issues
    finally:
        db.close()


def test_ops_dashboard_accepts_production_grade_backup_restore_evidence():
    db = _session()
    try:
        record_audit(
            db,
            action="infra.backup.completed",
            target_type="infrastructure",
            target_id="prod-backup",
            metadata={
                "environment": "production",
                "offsite": True,
                "encrypted": True,
                "schedule": "daily",
                "db_backup": "postgres.dump",
                "object_storage_backup": "r2://draftcheck-backups/storage",
                "manifest_sha256": "abc123",
                "duration_seconds": 12.2,
            },
        )
        record_audit(
            db,
            action="infra.restore.completed",
            target_type="infrastructure",
            target_id="prod-restore",
            metadata={
                "environment": "production",
                "clean_machine_restore": True,
                "checksum_validated": True,
                "manifest_sha256": "abc123",
                "duration_seconds": 25.5,
            },
        )

        dashboard = OpsDashboardService(db).dashboard()

        assert dashboard.backups["backup_verified"] is True
        assert dashboard.backups["restore_verified"] is True
        assert dashboard.backups["backup_verification_issues"] == []
        assert dashboard.backups["restore_verification_issues"] == []
        assert "last_successful_backup_not_recorded" not in dashboard.issues
        assert "last_successful_restore_test_not_recorded" not in dashboard.issues
        assert "production_backup_not_verified" not in dashboard.issues
        assert "production_restore_test_not_verified" not in dashboard.issues
    finally:
        db.close()


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
