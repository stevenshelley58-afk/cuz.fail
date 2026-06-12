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
from draftcheck.api.documents import get_persisted_document_facts  # noqa: E402
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
    content = (
        b"Lot area: 450 m2\n"
        b"Site coverage: 48.44%\n"
        b"Front setback: 4.5 m\n"
        b"Drawing No: A101\n"
        b"Revision: B\n"
        b"Drawing Title: Proposed additions\n"
        b"Scale: 1:100\n"
    )
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
        "drawing_number",
        "drawing_revision",
        "drawing_title",
        "drawing_scale",
    } <= {fact.check_key for fact in facts}
    assert all(fact.promoted_to_measurement is False for fact in facts)
    assert all(fact.review_status == "pending_review" for fact in facts)
    title_block_facts = [fact for fact in facts if fact.fact_kind == "drawing_title_block"]
    assert {fact.check_key for fact in title_block_facts} == {
        "drawing_number",
        "drawing_revision",
        "drawing_title",
        "drawing_scale",
    }
    assert all(
        fact.metadata_json["measurement_readiness_reason"]
        == "title-block text is project metadata, not a compliance measurement"
        for fact in title_block_facts
    )
    payload = get_persisted_document_facts(str(document.id), db, None)  # type: ignore[arg-type]
    assert payload["parse_status"] == "parsed"
    assert payload["count"] == len(facts)
    assert {
        "site_area_m2",
        "drawing_number",
    } <= {item["fact_key"] for item in payload["items"]}


def test_document_parse_job_persists_pdf_page_layout_metadata(tmp_path, monkeypatch) -> None:
    import fitz

    monkeypatch.setenv("DRAFTCHECK_EMBEDDING_PROVIDER", "stub")
    db = _session()
    org = Org(id=uuid4(), slug="pdf-layout", name="PDF Layout")
    user = User(
        id=uuid4(),
        org_id=org.id,
        email="owner@pdf-layout.test",
        role=IdentityRole.OWNER,
        status=UserStatus.ACTIVE,
    )
    project = Project(id=uuid4(), org_id=org.id, created_by_user_id=user.id, name="PDF project")
    pdf = fitz.open()
    page = pdf.new_page(width=320, height=240)
    page.insert_text((40, 80), "Front setback: 4.5 m")
    content = pdf.tobytes()
    pdf.close()
    stored = tmp_path / "stored.pdf"
    stored.write_bytes(content)
    document = Document(
        id=uuid4(),
        org_id=org.id,
        project_id=project.id,
        uploaded_by_user_id=user.id,
        title="site-plan.pdf",
        document_type="pdf",
        status="parse_pending",
        storage_path=str(stored),
        sha256="1" * 64,
        media_type="application/pdf",
        size_bytes=len(content),
        metadata_json={"parse_status": "parse_pending"},
    )
    db.add_all([org, user, project, document])
    db.flush()

    result = parse_document_for_session(db, document_id=document.id)

    assert result["parse_status"] == "parsed"
    persisted_page = db.query(DocumentPage).filter_by(document_id=document.id).one()
    assert persisted_page.width == 320
    assert persisted_page.height == 240
    assert persisted_page.metadata_json["extraction_method"] == "pymupdf_text_blocks"
    text_blocks = persisted_page.metadata_json["text_blocks"]
    assert text_blocks
    assert "Front setback" in text_blocks[0]["text"]
    assert text_blocks[0]["measurement_compliance_ready"] is False
    assert text_blocks[0]["measurement_readiness_reason"] == "pdf text block bbox is not a calibrated measurement"


def test_document_parse_job_persists_dxf_dimension_metadata(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DRAFTCHECK_EMBEDDING_PROVIDER", "stub")
    db = _session()
    org = Org(id=uuid4(), slug="dxf-async", name="DXF Async")
    user = User(
        id=uuid4(),
        org_id=org.id,
        email="owner@dxf-async.test",
        role=IdentityRole.OWNER,
        status=UserStatus.ACTIVE,
    )
    project = Project(id=uuid4(), org_id=org.id, created_by_user_id=user.id, name="DXF project")
    content = "\n".join(
        [
            "0",
            "SECTION",
            "2",
            "ENTITIES",
            "0",
            "DIMENSION",
            "5",
            "D42",
            "8",
            "A-DIMENSIONS",
            "1",
            "5.0",
            "42",
            "4.5",
            "0",
            "ENDSEC",
            "0",
            "EOF",
        ]
    ).encode()
    stored = tmp_path / "stored.dxf"
    stored.write_bytes(content)
    document = Document(
        id=uuid4(),
        org_id=org.id,
        project_id=project.id,
        uploaded_by_user_id=user.id,
        title="site-plan.dxf",
        document_type="dxf",
        status="parse_pending",
        storage_path=str(stored),
        sha256="2" * 64,
        media_type="application/dxf",
        size_bytes=len(content),
        metadata_json={"parse_status": "parse_pending"},
    )
    db.add_all([org, user, project, document])
    db.flush()

    parse_document_for_session(db, document_id=document.id)

    fact = db.query(DocumentFact).filter_by(document_id=document.id, fact_kind="drawing_dimension").one()
    assert fact.value_json["numeric_value"] == 4.5
    assert fact.metadata_json["entity_handle"] == "D42"
    assert fact.metadata_json["text_override_differs"] is True
    assert fact.metadata_json["parser_native_fact"] is True
    assert fact.promoted_to_measurement is False


def test_document_parse_job_persists_ifc_quantity_metadata(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DRAFTCHECK_EMBEDDING_PROVIDER", "stub")
    db = _session()
    org = Org(id=uuid4(), slug="ifc-async", name="IFC Async")
    user = User(
        id=uuid4(),
        org_id=org.id,
        email="owner@ifc-async.test",
        role=IdentityRole.OWNER,
        status=UserStatus.ACTIVE,
    )
    project = Project(id=uuid4(), org_id=org.id, created_by_user_id=user.id, name="IFC project")
    content = b"ISO-10303-21;\nDATA;\n#10=IFCQUANTITYAREA('GrossFloorArea',$,$,182.5,$);\nENDSEC;"
    stored = tmp_path / "stored.ifc"
    stored.write_bytes(content)
    document = Document(
        id=uuid4(),
        org_id=org.id,
        project_id=project.id,
        uploaded_by_user_id=user.id,
        title="model.ifc",
        document_type="ifc",
        status="parse_pending",
        storage_path=str(stored),
        sha256="3" * 64,
        media_type="model/ifc",
        size_bytes=len(content),
        metadata_json={"parse_status": "parse_pending"},
    )
    db.add_all([org, user, project, document])
    db.flush()

    parse_document_for_session(db, document_id=document.id)

    fact = db.query(DocumentFact).filter_by(document_id=document.id, fact_kind="model_quantity").one()
    assert fact.value_json["numeric_value"] == 182.5
    assert fact.value_json["unit"] == "m2"
    assert fact.metadata_json["ifc_entity_id"] == "#10"
    assert fact.metadata_json["ifc_quantity_name"] == "GrossFloorArea"
    assert fact.metadata_json["parser_native_fact"] is True
    assert fact.promoted_to_measurement is False


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
