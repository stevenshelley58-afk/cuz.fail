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
from draftcheck.api.documents import (  # noqa: E402
    _configured_storage_root,
    get_persisted_document_facts,
    search_project_document_evidence,
)
from draftcheck.jobs.documents import enqueue_document_parse, parse_document, parse_document_for_session  # noqa: E402
from draftcheck.domain.documents.chunks import write_document_chunks  # noqa: E402
from draftcheck.domain.documents.facts import DocumentFactService  # noqa: E402


def test_document_fact_service_extracts_cockburn_measurements_and_derived_percentages() -> None:
    service = DocumentFactService()
    document_id = uuid4()
    text = "\n".join(
        [
            "Lot area: 580 m2",
            "Building footprint: 232 m2",
            "Open space: 348 m2",
            "Garage width: 5.8 m",
            "Facade width: 14.5 m",
            "Boundary wall length: 9.0 m",
            "Boundary wall height: 3.2 m",
            "Lot frontage: 16.0 m",
            "Lot depth: 32.0 m",
            "Driveway width: 4.0 m",
            "Retaining wall height: 0.5 m",
            "Front fence height: 1.2 m",
            "Side fence height: 1.8 m",
            "Parking bays per dwelling: 2",
            "Visitor parking per dwelling: 0.25",
            "Plot ratio: 0.5",
            "Building storeys: 2",
            "Ceiling height: 2.7 m",
            "Ground floor height: 3.2 m",
            "Drawing No: A101",
            "Revision: B",
            "Scale: 1:100",
            "North arrow",
            "Dimensions shown",
        ]
    )

    facts = service.extract_facts_from_text(text, document_id, 1, org_id=uuid4(), project_id=uuid4())
    by_key = {fact.check_key: fact for fact in facts}

    assert {
        "site_area_m2",
        "proposed_covered_area_m2",
        "proposed_open_space_m2",
        "proposed_garage_width_m",
        "dwelling_facade_width_m",
        "proposed_boundary_wall_length_m",
        "proposed_boundary_wall_height_m",
        "frontage_width_m",
        "lot_depth_m",
        "driveway_width_m",
        "retaining_wall_height_m",
        "front_fence_height_m",
        "side_fence_height_m",
        "parking_bays_per_dwelling",
        "visitor_parking_per_dwelling",
        "plot_ratio",
        "building_storeys",
        "ceiling_height_m",
        "ground_floor_height_m",
        "proposed_site_cover_pct",
        "proposed_open_space_pct",
        "proposed_garage_width_dominance_pct",
        "title_block_present",
        "revision_present",
        "scale_present",
        "north_point_present",
        "dimensions_present",
    } <= set(by_key)
    assert by_key["site_area_m2"].value_json["unit"] == "m2"
    assert by_key["proposed_site_cover_pct"].value_json["unit"] == "%"
    assert by_key["proposed_site_cover_pct"].value_json["numeric_value"] == 40.0
    assert by_key["proposed_open_space_pct"].value_json["numeric_value"] == 60.0
    assert by_key["proposed_garage_width_dominance_pct"].value_json["numeric_value"] == 40.0
    assert by_key["proposed_site_cover_pct"].metadata_json["derived_from_fact_keys"] == [
        "proposed_covered_area_m2",
        "site_area_m2",
    ]
    assert all(fact.review_status == "pending_review" for fact in facts)
    assert all(fact.metadata_json["measurement_compliance_ready"] is False for fact in facts)


def test_document_fact_service_accepts_site_cover_and_open_space_percent_variants() -> None:
    service = DocumentFactService()
    facts = service.extract_facts_from_text(
        "Site cover: 45%\nOpen space minimum: 55%\nGarage dominance: 40%",
        uuid4(),
        1,
        org_id=uuid4(),
        project_id=uuid4(),
    )

    by_key = {fact.check_key: fact for fact in facts}
    assert by_key["proposed_site_cover_pct"].value_json["numeric_value"] == 45.0
    assert by_key["proposed_open_space_pct"].value_json["numeric_value"] == 55.0
    assert by_key["proposed_garage_width_dominance_pct"].value_json["numeric_value"] == 40.0


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
    assert document.metadata_json["parser_artifacts"][0]["kind"] == "parser_output"
    assert document.metadata_json["parser_artifacts"][0]["metadata"]["parser_name"] == "draftcheck.plain_text_parser"
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
    measurement_facts = [fact for fact in facts if fact.fact_kind == "drawing_measurement"]
    assert measurement_facts
    assert all(fact.metadata_json["parser_boundary_source"] is True for fact in measurement_facts)
    assert all(fact.metadata_json["parser_page_parser_name"] == "draftcheck.plain_text_parser" for fact in measurement_facts)
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


def test_document_parse_task_uses_fresh_session_factory(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DRAFTCHECK_EMBEDDING_PROVIDER", "stub")
    db = _session()
    org = Org(id=uuid4(), slug="parse-task", name="Parse Task")
    user = User(
        id=uuid4(),
        org_id=org.id,
        email="owner@parse-task.test",
        role=IdentityRole.OWNER,
        status=UserStatus.ACTIVE,
    )
    project = Project(id=uuid4(), org_id=org.id, created_by_user_id=user.id, name="Parse task project")
    content = b"Lot area: 450 m2\nFront setback: 4.5 m\n"
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
        sha256="6" * 64,
        media_type="text/plain",
        size_bytes=len(content),
        metadata_json={"parse_status": "parse_pending"},
    )
    db.add_all([org, user, project, document])
    db.flush()

    monkeypatch.setattr("draftcheck.jobs.documents.create_session_factory", lambda: lambda: db)

    result = parse_document(str(document.id))

    assert result["parse_status"] == "parsed"
    assert result["page_count"] == 1
    assert result["fact_count"] >= 2
    assert document.status == "parsed"
    assert db.query(DocumentPage).filter_by(document_id=document.id).count() == 1


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
    page.draw_line((40, 120), (280, 120), color=(0, 0, 0), width=1)
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
    assert document.metadata_json["parser_artifacts"][0]["metadata"]["parser_name"] == "draftcheck.pdf_text_parser"
    assert persisted_page.width == 320
    assert persisted_page.height == 240
    assert persisted_page.metadata_json["extraction_method"] == "pymupdf_text_blocks"
    text_blocks = persisted_page.metadata_json["text_blocks"]
    assert text_blocks
    assert "Front setback" in text_blocks[0]["text"]
    assert text_blocks[0]["measurement_compliance_ready"] is False
    assert text_blocks[0]["measurement_readiness_reason"] == "pdf text block bbox is not a calibrated measurement"
    vector_paths = persisted_page.metadata_json["vector_paths"]
    assert vector_paths
    assert vector_paths[0]["bbox"]
    assert vector_paths[0]["item_count"] >= 1
    assert vector_paths[0]["measurement_compliance_ready"] is False
    assert vector_paths[0]["measurement_readiness_reason"] == "pdf vector path is not a calibrated measurement"
    assert vector_paths[0]["calibration_required"] is True
    fact = db.query(DocumentFact).filter_by(
        document_id=document.id,
        check_key="proposed_setback_front_m",
    ).one()
    assert fact.evidence_ref_json["page_number"] == 1
    assert fact.evidence_ref_json["source_text"] == "Front setback: 4.5 m"
    assert fact.evidence_ref_json["bbox"]
    assert fact.evidence_ref_json["evidence_method"] == "pdf_text_block_match"
    assert fact.evidence_ref_json["measurement_compliance_ready"] is False
    assert fact.evidence_ref_json["measurement_readiness_reason"] == (
        "pdf text block bbox is not a calibrated measurement"
    )
    assert fact.metadata_json["pdf_text_block_bbox"] == fact.evidence_ref_json["bbox"]
    assert fact.promoted_to_measurement is False
    assert fact.review_status == "pending_review"


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
            "67",
            "1",
            "410",
            "Layout1",
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
    assert fact.metadata_json["entity_layer"] == "A-DIMENSIONS"
    assert fact.metadata_json["cad_space"] == "paper_space"
    assert fact.metadata_json["layout_name"] == "Layout1"
    assert fact.metadata_json["text_override_differs"] is True
    assert fact.metadata_json["parser_native_fact"] is True
    assert fact.evidence_ref_json["entity_handle"] == "D42"
    assert fact.evidence_ref_json["entity_layer"] == "A-DIMENSIONS"
    assert fact.evidence_ref_json["cad_space"] == "paper_space"
    assert fact.evidence_ref_json["layout_name"] == "Layout1"
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


def test_project_document_evidence_search_is_project_scoped_and_not_legal_authority(monkeypatch) -> None:
    monkeypatch.setenv("DRAFTCHECK_EMBEDDING_PROVIDER", "stub")
    db = _session()
    org = Org(id=uuid4(), slug="evidence-search", name="Evidence Search")
    user = User(
        id=uuid4(),
        org_id=org.id,
        email="owner@evidence-search.test",
        role=IdentityRole.OWNER,
        status=UserStatus.ACTIVE,
    )
    project = Project(id=uuid4(), org_id=org.id, created_by_user_id=user.id, name="Target project")
    other_project = Project(id=uuid4(), org_id=org.id, created_by_user_id=user.id, name="Other project")
    document = Document(
        id=uuid4(),
        org_id=org.id,
        project_id=project.id,
        uploaded_by_user_id=user.id,
        title="front-setback.txt",
        document_type="txt",
        status="parsed",
        storage_path="front-setback.txt",
        sha256="4" * 64,
        media_type="text/plain",
        size_bytes=42,
        metadata_json={"parse_status": "parsed"},
    )
    other_document = Document(
        id=uuid4(),
        org_id=org.id,
        project_id=other_project.id,
        uploaded_by_user_id=user.id,
        title="rear-patio.txt",
        document_type="txt",
        status="parsed",
        storage_path="rear-patio.txt",
        sha256="5" * 64,
        media_type="text/plain",
        size_bytes=42,
        metadata_json={"parse_status": "parsed"},
    )
    page = DocumentPage(
        document_id=document.id,
        page_number=1,
        text="Front setback to alfresco wall is 4.5 m.",
        metadata_json={},
    )
    other_page = DocumentPage(
        document_id=other_document.id,
        page_number=1,
        text="Front setback to garage wall is 2.0 m.",
        metadata_json={},
    )
    db.add_all([org, user, project, other_project, document, other_document, page, other_page])
    db.flush()
    write_document_chunks(db, document_id=document.id, pages=[page])
    write_document_chunks(db, document_id=other_document.id, pages=[other_page])
    db.flush()

    payload = search_project_document_evidence(
        str(project.id),
        db,
        None,  # type: ignore[arg-type]
        q="front setback garage",
        limit=5,
    )

    assert payload["count"] == 1
    assert payload["legal_authority"] is False
    assert "approved legal source" in payload["advisory_notice"]
    [hit] = payload["items"]
    assert hit["document_id"] == str(document.id)
    assert hit["document_title"] == "front-setback.txt"
    assert hit["metadata"]["legal_authority"] is False
    assert "garage" not in hit["text"]


def test_document_parse_enqueue_reports_sync_fallback_when_queue_is_unavailable(monkeypatch) -> None:
    monkeypatch.delenv("PROCRASTINATE_DB_URI", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    result = enqueue_document_parse(uuid4())

    assert result == {"enqueued": False, "reason": "procrastinate_unavailable"}


def test_document_storage_root_accepts_object_storage_root_fallback(monkeypatch) -> None:
    monkeypatch.delenv("DRAFTCHECK_STORAGE_ROOT", raising=False)
    monkeypatch.setenv("OBJECT_STORAGE_ROOT", "/app/.storage")

    assert _configured_storage_root().as_posix() == "/app/.storage"

    monkeypatch.setenv("DRAFTCHECK_STORAGE_ROOT", "/srv/draftcheck/storage")

    assert _configured_storage_root().as_posix() == "/srv/draftcheck/storage"


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
