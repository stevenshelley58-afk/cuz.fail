from __future__ import annotations

from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):

    def _visit_jsonb(self, type_, **kw):  # type: ignore[misc]
        return "JSON"

    SQLiteTypeCompiler.visit_JSONB = _visit_jsonb  # type: ignore[attr-defined]

import draftcheck.db.models as _models_mod  # noqa: E402

for _tbl in _models_mod.Base.metadata.tables.values():
    for _idx in list(_tbl.indexes):
        if _idx.name in {"ix_documents_sha256", "ix_document_facts_check_key"} and len(_idx.columns) == 1:
            _idx.table.indexes.discard(_idx)

from draftcheck.db.models import Base, Document, DocumentChunk, DocumentFact, DocumentPage, Org, Project, User, UserStatus  # noqa: E402
from draftcheck.domain.identity import IdentityRole  # noqa: E402
from draftcheck.jobs.documents import enqueue_document_parse, parse_document_for_session  # noqa: E402


def test_document_parse_job_persists_status_pages_chunks_and_facts(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DRAFTCHECK_EMBEDDING_PROVIDER", "stub")
    db = _session()
    org = Org(id=uuid4(), slug="parse-job", name="Parse Job")
    user = User(
        id=uuid4(),
        org_id=org.id,
        email="owner@parse-job.test",
        role=IdentityRole.OWNER,
        status=UserStatus.ACTIVE,
    )
    project = Project(id=uuid4(), org_id=org.id, created_by_user_id=user.id, name="Parse job project")
    content = b"Lot area: 450 m2\nSite coverage: 48.44%\nFront setback: 4.5 m"
    stored = tmp_path / "stored.txt"
    stored.write_bytes(content)
    document = Document(
        id=uuid4(),
        org_id=org.id,
        project_id=project.id,
        uploaded_by_user_id=user.id,
        title="site-plan.txt",
        document_type="txt",
        status="parse_pending",
        storage_path=str(stored),
        sha256="0" * 64,
        media_type="text/plain",
        size_bytes=len(content),
        metadata_json={"parse_status": "parse_pending"},
    )
    db.add_all([org, user, project, document])
    db.flush()

    result = parse_document_for_session(db, document_id=document.id)

    assert result["parse_status"] == "parsed"
    assert result["page_count"] == 1
    assert result["chunk_count"] == 1
    assert result["fact_count"] >= 3
    assert document.status == "parsed"
    assert document.metadata_json["parse_status"] == "parsed"
    assert db.query(DocumentPage).filter_by(document_id=document.id).count() == 1
    assert db.query(DocumentChunk).filter_by(document_id=document.id).count() == 1
    facts = db.query(DocumentFact).filter_by(document_id=document.id).all()
    assert {
        "site_area_m2",
        "proposed_site_cover_pct",
        "proposed_setback_front_m",
    } <= {fact.check_key for fact in facts}
    assert all(fact.promoted_to_measurement is False for fact in facts)
    assert all(fact.review_status == "pending_review" for fact in facts)


def test_document_parse_enqueue_reports_sync_fallback_when_queue_is_unavailable(monkeypatch) -> None:
    monkeypatch.delenv("PROCRASTINATE_DB_URI", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    result = enqueue_document_parse(uuid4())

    assert result == {"enqueued": False, "reason": "procrastinate_unavailable"}


def _session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    needed_tables = [
        "orgs",
        "users",
        "projects",
        "documents",
        "document_pages",
        "document_chunks",
        "document_facts",
    ]
    Base.metadata.create_all(
        engine,
        tables=[Base.metadata.tables[name] for name in needed_tables],
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
