from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_compliance.service import ComplianceService
from draftcheck_core.audit import list_audit_events, record_audit
from draftcheck_core.database import get_db
from draftcheck_core.hermes import HermesAdapter
from draftcheck_core.json_utils import from_json
from draftcheck_core.models import (
    BackgroundJob,
    CheckResult,
    HumanSignoff,
    Project,
    ProjectDocument,
    SourceDocument,
    SourceVersion,
)
from draftcheck_core.object_storage import LocalObjectStorage
from draftcheck_core.project_service import ProjectService, property_to_dict
from draftcheck_document_ai.rfi import RfiService
from draftcheck_document_ai.extraction import extract_pages_from_bytes, extract_text_from_bytes
from draftcheck_document_ai.service import DocumentAnalysisService
from draftcheck_export.service import ExportService
from draftcheck_ingestion.service import SourceIngestionService
from draftcheck_retrieval.service import RetrievalService
from draftcheck_scraper.lawful_fetcher import fetch_public_content
from draftcheck_shared.schemas import (
    AskRequest,
    CheckResultRead,
    DocumentCreate,
    DocumentRead,
    ExportManifest,
    ExportRequest,
    HermesCorpusImportRequest,
    JobStatus,
    ManifestImportRequest,
    MeasurementCreate,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    PropertyRead,
    PropertyUpsert,
    ResponseDraftRead,
    RfiItemRead,
    RfiParseRequest,
    SignoffCreate,
    SourceChunkResult,
    SourceDocumentCreate,
    SourceDocumentRead,
    SourceVersionRead,
    StandardAnswer,
)

router = APIRouter()


@router.post("/auth/dev-login")
def dev_login() -> dict[str, Any]:
    return {"access_token": "dev-token", "token_type": "bearer", "user": {"id": "dev-user", "role": "designer"}}


@router.get("/me")
def me() -> dict[str, str]:
    return {"id": "dev-user", "email": "dev@example.local", "role": "designer"}


@router.post("/projects", response_model=ProjectRead)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectRead:
    project = ProjectService(db).create_project(payload)
    db.commit()
    return _project_read(project)


@router.get("/projects", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)) -> list[ProjectRead]:
    return [_project_read(project) for project in ProjectService(db).list_projects()]


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: Session = Depends(get_db)) -> ProjectRead:
    return _project_read(ProjectService(db).get_project(project_id))


@router.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)) -> ProjectRead:
    project = ProjectService(db).update_project(project_id, payload)
    db.commit()
    return _project_read(project)


@router.delete("/projects/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    ProjectService(db).delete_project(project_id)
    db.commit()
    return {"status": "deleted"}


@router.put("/projects/{project_id}/property", response_model=PropertyRead)
def upsert_property(project_id: str, payload: PropertyUpsert, db: Session = Depends(get_db)) -> dict:
    prop = ProjectService(db).upsert_property(project_id, payload)
    db.commit()
    return property_to_dict(prop)


@router.get("/projects/{project_id}/property", response_model=PropertyRead | None)
def get_property(project_id: str, db: Session = Depends(get_db)) -> dict | None:
    prop = ProjectService(db).get_property(project_id)
    return property_to_dict(prop) if prop else None


@router.post("/projects/{project_id}/documents", response_model=DocumentRead)
def add_document(project_id: str, payload: DocumentCreate, db: Session = Depends(get_db)) -> DocumentRead:
    doc = ProjectService(db).add_document(project_id, payload)
    if payload.text_content:
        DocumentAnalysisService(db).extract_facts_for_document(project_id, doc.id)
    db.commit()
    return _document_read(doc)


@router.post("/projects/{project_id}/documents/upload", response_model=DocumentRead)
async def upload_document(
    project_id: str,
    document_type: str = Form(...),
    title: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentRead:
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"
    filename = (file.filename or "upload.bin").replace("\\", "/").split("/")[-1] or "upload.bin"
    stored = LocalObjectStorage().put_bytes(f"projects/{project_id}/documents/{filename}", content)
    extraction_content_type = f"{content_type}; filename={filename}"
    pages = extract_pages_from_bytes(content, extraction_content_type)
    doc = ProjectService(db).add_extracted_document(
        project_id,
        document_type=document_type,
        title=title or filename,
        filename=filename,
        content_type=content_type,
        raw_object_key=stored.object_key,
        content_sha256=stored.content_sha256,
        pages=pages,
        metadata={"byte_size": stored.byte_size, "upload_filename": filename},
    )
    DocumentAnalysisService(db).extract_facts_for_document(project_id, doc.id)
    db.commit()
    return _document_read(doc)


@router.get("/projects/{project_id}/documents", response_model=list[DocumentRead])
def list_documents(project_id: str, db: Session = Depends(get_db)) -> list[DocumentRead]:
    return [_document_read(doc) for doc in ProjectService(db).list_documents(project_id)]


@router.get("/projects/{project_id}/documents/{document_id}", response_model=DocumentRead)
def get_document(project_id: str, document_id: str, db: Session = Depends(get_db)) -> DocumentRead:
    return _document_read(ProjectService(db).get_document(project_id, document_id))


@router.post("/projects/{project_id}/documents/{document_id}/analyze", response_model=list[CheckResultRead])
def analyze_document(project_id: str, document_id: str, db: Session = Depends(get_db)) -> list[CheckResultRead]:
    rows = DocumentAnalysisService(db).analyze_document(project_id, document_id)
    db.commit()
    return [_check_result_read(row) for row in rows]


@router.get("/projects/{project_id}/documents/{document_id}/pages")
def document_pages(project_id: str, document_id: str, db: Session = Depends(get_db)) -> list[dict]:
    return DocumentAnalysisService(db).pages_for_document(project_id, document_id)


@router.get("/projects/{project_id}/documents/{document_id}/facts")
def document_facts(project_id: str, document_id: str, db: Session = Depends(get_db)) -> list[dict]:
    ProjectService(db).get_document(project_id, document_id)
    return DocumentAnalysisService(db).list_facts(project_id, document_id)


@router.get("/projects/{project_id}/document-search")
def search_project_documents(
    project_id: str,
    q: str = Query(...),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[dict]:
    ProjectService(db).get_project(project_id)
    return DocumentAnalysisService(db).search_project_documents(project_id, q, limit)


@router.post("/sources/manifest/import")
def import_manifest(payload: ManifestImportRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    service = SourceIngestionService(db)
    if payload.manifest_yaml:
        results = service.import_manifest_yaml(payload.manifest_yaml)
    else:
        results = service.import_entries(payload.entries or [])
    db.commit()
    return {"results": [result.__dict__ for result in results]}


@router.post("/sources/hermes-corpus/import")
def import_hermes_corpus(payload: HermesCorpusImportRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    inventory_jsonl = payload.inventory_jsonl
    corpus_root = Path(payload.corpus_root).expanduser().resolve() if payload.corpus_root else None
    if payload.inventory_path:
        inventory_path = Path(payload.inventory_path).expanduser().resolve()
        try:
            inventory_jsonl = inventory_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise HTTPException(status_code=400, detail=f"Unable to read inventory_path: {exc}") from exc
        corpus_root = corpus_root or inventory_path.parent

    result = SourceIngestionService(db).import_hermes_corpus(
        inventory_jsonl=inventory_jsonl or "",
        corpus_root=corpus_root,
    )
    db.commit()
    return result.to_dict()


@router.post("/sources/seed")
def seed_source(payload: SourceDocumentCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    result = SourceIngestionService(db).ingest_source(payload)
    db.commit()
    return result.__dict__


@router.post("/sources/ingest")
async def ingest_source(payload: SourceDocumentCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    if payload.canonical_url and not payload.content:
        fetched = await fetch_public_content(
            payload.canonical_url,
            licence_notes=payload.licence_notes,
            access_type=payload.access_type,
        )
        extracted_text = extract_text_from_bytes(fetched.content, fetched.content_type)
        payload = payload.model_copy(update={"content": extracted_text})
    result = SourceIngestionService(db).ingest_source(payload)
    db.commit()
    return result.__dict__


@router.get("/sources", response_model=list[SourceDocumentRead])
def list_sources(db: Session = Depends(get_db)) -> list[SourceDocumentRead]:
    sources = db.scalars(select(SourceDocument).order_by(SourceDocument.title)).all()
    return [_source_read(source) for source in sources]


@router.get("/sources/fetch-logs")
def fetch_logs(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(BackgroundJob).order_by(BackgroundJob.created_at.desc())).all()
    return [{"id": row[0].id, "job_type": row[0].job_type, "status": row[0].status} for row in rows]


@router.get("/sources/{source_id}", response_model=SourceDocumentRead)
def get_source(source_id: str, db: Session = Depends(get_db)) -> SourceDocumentRead:
    source = db.get(SourceDocument, source_id)
    if not source:
        raise KeyError("Source not found")
    return _source_read(source)


@router.get("/sources/{source_id}/versions", response_model=list[SourceVersionRead])
def source_versions(source_id: str, db: Session = Depends(get_db)) -> list[SourceVersionRead]:
    versions = db.scalars(
        select(SourceVersion)
        .where(SourceVersion.source_document_id == source_id)
        .order_by(SourceVersion.retrieved_at.desc())
    ).all()
    return [_version_read(version) for version in versions]


@router.post("/sources/{source_id}/refresh", response_model=JobStatus)
def refresh_source(source_id: str, db: Session = Depends(get_db)) -> JobStatus:
    source = db.get(SourceDocument, source_id)
    if not source:
        raise KeyError("Source not found")
    job = HermesAdapter(db).enqueue_source_freshness_audit({"source_document_id": source_id, "url": source.canonical_url})
    db.commit()
    return job


@router.get("/source-chunks/search", response_model=list[SourceChunkResult])
def search_chunks(q: str = Query(...), db: Session = Depends(get_db)) -> list[SourceChunkResult]:
    return RetrievalService(db).search(q)


@router.post("/checks/definitions/import")
def import_check_definitions(payload: dict[str, str], db: Session = Depends(get_db)) -> dict[str, Any]:
    yaml_text = payload.get("manifest_yaml") or payload.get("yaml") or ""
    definitions = ComplianceService(db).load_check_definitions_yaml(yaml_text)
    db.commit()
    return {"imported": len(definitions), "keys": [definition.key for definition in definitions]}


@router.post("/ask-source-library", response_model=StandardAnswer)
def ask_source_library(payload: AskRequest, db: Session = Depends(get_db)) -> StandardAnswer:
    return RetrievalService(db).ask(payload.question, payload.source_filters)


@router.post("/projects/{project_id}/ask-source", response_model=StandardAnswer)
def ask_project_source(project_id: str, payload: AskRequest, db: Session = Depends(get_db)) -> StandardAnswer:
    ProjectService(db).get_project(project_id)
    return RetrievalService(db).ask(payload.question, payload.source_filters)


@router.post("/projects/{project_id}/checks/run")
@router.post("/projects/{project_id}/compliance/run")
def run_checks(project_id: str, db: Session = Depends(get_db)):
    ProjectService(db).get_project(project_id)
    matrix = ComplianceService(db).run_checks(project_id)
    db.commit()
    return matrix


@router.get("/projects/{project_id}/checks", response_model=list[CheckResultRead])
@router.get("/projects/{project_id}/compliance", response_model=list[CheckResultRead])
def list_checks(project_id: str, db: Session = Depends(get_db)) -> list[CheckResultRead]:
    ProjectService(db).get_project(project_id)
    return ComplianceService(db).list_results(project_id)


@router.patch("/projects/{project_id}/checks/{check_result_id}", response_model=CheckResultRead)
def patch_check_result(
    project_id: str,
    check_result_id: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> CheckResultRead:
    result = db.get(CheckResult, check_result_id)
    if not result or result.project_id != project_id:
        raise KeyError("Check result not found")
    if "status" in payload:
        result.status = payload["status"]
    if "proposed" in payload:
        result.proposed = payload["proposed"]
    record_audit(
        db,
        action="check_result.updated",
        target_type="check_result",
        target_id=result.id,
        project_id=project_id,
        metadata=payload,
    )
    db.commit()
    return _check_result_read(result)


@router.get("/projects/{project_id}/compliance-matrix")
def compliance_matrix(project_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "results": [result.model_dump(mode="json") for result in ComplianceService(db).list_results(project_id)],
    }


@router.post("/projects/{project_id}/measurements")
def add_measurement(project_id: str, payload: MeasurementCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    measurement = ProjectService(db).add_measurement(project_id, payload)
    db.commit()
    return {
        "id": measurement.id,
        "project_id": measurement.project_id,
        "key": measurement.key,
        "value": measurement.value,
        "unit": measurement.unit,
        "source": measurement.source,
        "confidence": measurement.confidence,
        "evidence_ref": measurement.evidence_ref,
    }


@router.get("/projects/{project_id}/measurements")
def list_measurements(project_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return [
        {
            "id": measurement.id,
            "key": measurement.key,
            "value": measurement.value,
            "unit": measurement.unit,
            "source": measurement.source,
            "confidence": measurement.confidence,
            "evidence_ref": measurement.evidence_ref,
        }
        for measurement in ProjectService(db).list_measurements(project_id)
    ]


@router.post("/projects/{project_id}/rfi/parse", response_model=list[RfiItemRead])
@router.post("/projects/{project_id}/rfi/analyse", response_model=list[RfiItemRead])
def parse_rfi(project_id: str, payload: RfiParseRequest, db: Session = Depends(get_db)) -> list[RfiItemRead]:
    ProjectService(db).get_project(project_id)
    items = RfiService(db).parse_rfi(project_id, text=payload.text, document_id=payload.document_id)
    HermesAdapter(db).enqueue_rfi_analysis_job(project_id, {"rfi_item_count": len(items)})
    db.commit()
    return items


@router.get("/projects/{project_id}/rfi/items", response_model=list[RfiItemRead])
@router.get("/projects/{project_id}/rfi", response_model=list[RfiItemRead])
def list_rfi(project_id: str, db: Session = Depends(get_db)) -> list[RfiItemRead]:
    ProjectService(db).get_project(project_id)
    return RfiService(db).list_items(project_id)


@router.patch("/projects/{project_id}/rfi/items/{rfi_item_id}", response_model=RfiItemRead)
def patch_rfi(project_id: str, rfi_item_id: str, payload: dict[str, Any], db: Session = Depends(get_db)) -> RfiItemRead:
    item = next((row for row in RfiService(db).list_items(project_id) if row.id == rfi_item_id), None)
    if not item:
        raise KeyError("RFI item not found")
    record_audit(db, action="rfi.updated", target_type="rfi_item", target_id=rfi_item_id, project_id=project_id, metadata=payload)
    db.commit()
    return item


@router.post("/projects/{project_id}/rfi/draft-response", response_model=ResponseDraftRead)
@router.post("/projects/{project_id}/responses/generate", response_model=ResponseDraftRead)
def draft_response(project_id: str, db: Session = Depends(get_db)) -> ResponseDraftRead:
    ProjectService(db).get_project(project_id)
    draft = RfiService(db).generate_response(project_id)
    HermesAdapter(db).enqueue_council_pack_job(project_id, {"response_draft_id": draft.id})
    db.commit()
    return draft


@router.get("/projects/{project_id}/responses", response_model=list[ResponseDraftRead])
def list_responses(project_id: str, db: Session = Depends(get_db)) -> list[ResponseDraftRead]:
    ProjectService(db).get_project(project_id)
    return RfiService(db).list_responses(project_id)


@router.post("/projects/{project_id}/exports", response_model=ExportManifest)
@router.post("/projects/{project_id}/exports/response-pack", response_model=ExportManifest)
def create_export(project_id: str, payload: ExportRequest | None = None, db: Session = Depends(get_db)) -> ExportManifest:
    payload = payload or ExportRequest()
    export = ExportService(db).create_export(
        project_id,
        format=payload.format,
        sections=payload.sections,
        created_by=payload.created_by,
    )
    db.commit()
    return export


@router.get("/projects/{project_id}/exports", response_model=list[ExportManifest])
def list_exports(project_id: str, db: Session = Depends(get_db)) -> list[ExportManifest]:
    ProjectService(db).get_project(project_id)
    return ExportService(db).list_exports(project_id)


@router.get("/projects/{project_id}/exports/{export_id}", response_model=ExportManifest)
def get_export(project_id: str, export_id: str, db: Session = Depends(get_db)) -> ExportManifest:
    return ExportService(db).get_export(project_id, export_id)


@router.get("/projects/{project_id}/exports/{export_id}/download")
def download_export(project_id: str, export_id: str, db: Session = Depends(get_db)) -> FileResponse:
    service = ExportService(db)
    manifest = service.get_export(project_id, export_id)
    path = service.export_file_path(project_id, export_id)
    media_type = _export_media_type(manifest.format)
    return FileResponse(
        path=path,
        filename=path.name,
        media_type=media_type,
        headers={"x-draftcheck-export-id": export_id},
    )


@router.post("/projects/{project_id}/signoffs")
def create_signoff(project_id: str, payload: SignoffCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    signoff = ProjectService(db).create_signoff(project_id, payload)
    db.commit()
    return _signoff_read(signoff)


@router.get("/projects/{project_id}/signoffs")
def list_signoffs(project_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.scalars(select(HumanSignoff).where(HumanSignoff.project_id == project_id)).all()
    return [_signoff_read(row) for row in rows]


@router.get("/jobs/{job_id}", response_model=JobStatus)
def job_status(job_id: str, db: Session = Depends(get_db)) -> JobStatus:
    job = HermesAdapter(db).poll_job_status(job_id)
    db.commit()
    return job


@router.post("/jobs/{job_id}/retry", response_model=JobStatus)
def retry_job(job_id: str, db: Session = Depends(get_db)) -> JobStatus:
    job = HermesAdapter(db).retry_failed_job(job_id)
    db.commit()
    return job


@router.post("/jobs/{job_id}/cancel", response_model=JobStatus)
def cancel_job(job_id: str, db: Session = Depends(get_db)) -> JobStatus:
    job = HermesAdapter(db).cancel_job(job_id)
    db.commit()
    return job


@router.get("/jobs/{job_id}/traces")
def job_traces(job_id: str, db: Session = Depends(get_db)) -> list[dict]:
    return HermesAdapter(db).list_traces(job_id)


@router.get("/audit")
def audit(project_id: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    return list_audit_events(db, project_id)


def _project_read(project: Project) -> ProjectRead:
    return ProjectRead(
        id=project.id,
        project_name=project.project_name,
        client_name=project.client_name,
        address=project.address,
        local_government=project.local_government,
        lot_plan=project.lot_plan,
        project_type=project.project_type,
        stage=project.stage,
        r_code_density=project.r_code_density,
        ncc_edition=project.ncc_edition,
        created_by=project.created_by,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _document_read(doc: ProjectDocument) -> DocumentRead:
    return DocumentRead(
        id=doc.id,
        project_id=doc.project_id,
        document_type=doc.document_type,
        title=doc.title,
        filename=doc.filename,
        content_type=doc.content_type,
        raw_object_key=doc.raw_object_key,
        parse_status=doc.parse_status,
        analysis_status=doc.analysis_status,
        content_sha256=doc.content_sha256,
        created_at=doc.created_at,
    )


def _source_read(source: SourceDocument) -> SourceDocumentRead:
    return SourceDocumentRead(
        id=source.id,
        title=source.title,
        jurisdiction=source.jurisdiction,
        authority=source.authority,
        local_government=source.local_government,
        source_type=source.source_type,
        canonical_url=source.canonical_url,
        licence_notes=source.licence_notes,
        access_type=source.access_type,
        scrape_allowed=source.scrape_allowed,
        is_active=source.is_active,
        created_at=source.created_at,
    )


def _version_read(version: SourceVersion) -> SourceVersionRead:
    return SourceVersionRead(
        id=version.id,
        source_document_id=version.source_document_id,
        version_label=version.version_label,
        effective_date=version.effective_date,
        published_date=version.published_date,
        retrieved_at=version.retrieved_at,
        content_sha256=version.content_sha256,
        is_superseded=version.is_superseded,
        parse_status=version.parse_status,
    )


def _check_result_read(row: CheckResult) -> CheckResultRead:
    return CheckResultRead(
        id=row.id,
        check_key=row.check_key,
        label=row.label,
        category=row.category,
        status=row.status,  # type: ignore[arg-type]
        requirement=row.requirement,
        proposed=row.proposed,
        evidence_refs=from_json(row.evidence_refs_json, []),
        citations=from_json(row.citations_json, []),
        assumptions=from_json(row.assumptions_json, []),
        missing_information=from_json(row.missing_information_json, []),
        confidence=row.confidence,
        requires_human_review=row.requires_human_review,
        created_at=row.created_at,
    )


def _signoff_read(row: HumanSignoff) -> dict[str, Any]:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "target_type": row.target_type,
        "target_id": row.target_id,
        "status": row.status,
        "signed_by": row.signed_by,
        "notes": row.notes,
        "created_at": row.created_at,
    }


def _export_media_type(format_value: str) -> str:
    return {
        "json": "application/json",
        "csv": "text/csv",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "html": "text/html",
    }.get(format_value, "application/octet-stream")
