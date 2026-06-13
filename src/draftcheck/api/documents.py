"""V3 document upload and parser router.

Endpoints
---------
  GET  /documents/parsers                          → parser capability list
  GET  /documents/parsers/accuracy                 → accuracy report

  POST /documents/upload                           → upload + fact extraction
  GET  /documents/projects/{project_id}             → list documents for a project
  GET  /documents/{doc_id}/facts                   → list extracted facts
  PATCH /documents/{doc_id}/facts/{fact_id}        → update value or status
  POST  /documents/{doc_id}/facts/{fact_id}/promote → promote to PropertyFact

The upload endpoint stores files content-addressed at
  /srv/draftcheck/storage/{sha256[:2]}/{sha256}
and creates Document + DocumentPage + DocumentFact rows in the database.

When DATABASE_URL is absent the in-memory library is used for the parser
capability and accuracy report endpoints.  The upload / facts endpoints
return 503 when the database is not configured.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePath
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from draftcheck.api.auth import get_current_session, require_allowed_origin
from draftcheck.api.deps import get_db_session
from draftcheck.db.models import (
    Document,
    DocumentChunk as OrmDocumentChunk,
    DocumentFact as OrmDocumentFact,
    DocumentPage as OrmDocumentPage,
    PropertyFact,
)
from draftcheck.domain.documents import (
    DocumentFact,
    DocumentNotFoundError,
    DocumentParser,
    DocumentReviewStatus,
    InMemoryDocumentLibrary,
    configured_max_document_bytes,
    document_size_limit_label,
    parser_real_sample_evidence_metadata,
    sample_parser_accuracy_report,
    search_persisted_document_chunks,
)
from draftcheck.domain.identity import ActiveSession

router = APIRouter(tags=["documents"])

_document_library: InMemoryDocumentLibrary | None = None

def _configured_storage_root() -> Path:
    return Path(os.getenv("DRAFTCHECK_STORAGE_ROOT") or os.getenv("OBJECT_STORAGE_ROOT") or "/srv/draftcheck/storage")


STORAGE_ROOT = _configured_storage_root()


# ---------------------------------------------------------------------------
# In-memory library (parser capability / accuracy report only)
# ---------------------------------------------------------------------------


def get_document_library() -> InMemoryDocumentLibrary:
    global _document_library
    if _document_library is None:
        _document_library = InMemoryDocumentLibrary()
    return _document_library


DbSession = Annotated[Session, Depends(get_db_session)]


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class FactUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    numeric_value: float | None = Field(default=None)
    status: str | None = Field(default=None, pattern=r"^(pending_review|confirmed|rejected)$")
    calibration_ref: str | None = Field(default=None, min_length=3, max_length=500)
    calibration_note: str | None = Field(default=None, max_length=1000)


class ReviewDocumentFactPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_status: DocumentReviewStatus
    note: str | None = Field(default=None, max_length=1000)


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _orm_fact_payload(fact: OrmDocumentFact) -> dict[str, Any]:
    v = fact.value_json or {}
    return {
        "fact_id": str(fact.id),
        "fact_key": fact.check_key,
        "fact_kind": fact.fact_kind,
        "numeric_value": v.get("numeric_value"),
        "unit": v.get("unit"),
        "source_text": v.get("source_text"),
        "page_number": v.get("page_number"),
        "confidence": fact.confidence,
        "review_status": fact.review_status,
        "promoted_to_measurement": fact.promoted_to_measurement,
        "metadata": fact.metadata_json or {},
    }


def _inmem_fact_payload(fact: DocumentFact) -> dict[str, Any]:
    payload = jsonable_encoder(fact)
    payload["review_status"] = fact.review_status.value
    return payload


def _not_found(exc: DocumentNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document item not found: {exc}")


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------


def _store_content(content: bytes, sha256: str) -> Path:
    """Write bytes to content-addressed storage; return the file path."""
    dest = STORAGE_ROOT / sha256[:2] / sha256
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        dest.write_bytes(content)
    return dest


def _safe_filename(filename: str) -> str:
    import re

    name = PurePath(filename or "upload.bin").name.replace("\x00", "")
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .")
    return name or "upload.bin"


def _infer_media_type(upload: UploadFile) -> str:
    if upload.content_type:
        return upload.content_type.split(";")[0].strip().lower()
    suffix = PurePath(upload.filename or "").suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
        ".dxf": "application/dxf",
        ".csv": "text/csv",
    }.get(suffix, "application/octet-stream")


# ---------------------------------------------------------------------------
# Parser capability / accuracy endpoints (in-memory, no DB needed)
# ---------------------------------------------------------------------------


@router.get("/documents/parsers", tags=["documents"])
def list_document_parsers() -> dict[str, Any]:
    capabilities = DocumentParser().capabilities()
    return {
        "items": jsonable_encoder(capabilities),
        "count": len(capabilities),
        "accuracy_gate": {
            "status": "not_beta_ready",
            "reason": "generated parser fixtures pass, but beta still needs persistence-connected validation and operator-reviewed real samples",
            **parser_real_sample_evidence_metadata(),
            "required_before_beta": [
                "automated review gate connected to persistence",
                "operator-reviewed real project samples",
                "no raster measurement without calibration",
            ],
        },
    }


@router.get("/documents/parsers/accuracy", tags=["documents"])
def get_document_parser_accuracy() -> dict[str, Any]:
    return sample_parser_accuracy_report()


# ---------------------------------------------------------------------------
# POST /documents/upload
# ---------------------------------------------------------------------------


@router.post("/documents/upload", tags=["documents"])
async def upload_document(
    file: Annotated[UploadFile, File()],
    project_id: str,
    db: DbSession,
    _allowed_origin: Annotated[None, Depends(require_allowed_origin)],
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
) -> dict[str, Any]:
    """Accept a multipart file upload, store it, parse text, extract facts.

    Returns document_id and extracted_facts[].
    """
    if active_session.org is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticated org required.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="File is empty.")
    max_upload_bytes = configured_max_document_bytes()
    if len(content) > max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"File exceeds the {document_size_limit_label(max_upload_bytes)} upload limit.",
        )

    filename = _safe_filename(file.filename or "upload.bin")
    media_type = _infer_media_type(file)
    sha256 = hashlib.sha256(content).hexdigest()
    storage_path = str(_store_content(content, sha256))

    # --- Create Document row ---
    doc_id = uuid.uuid4()
    org_id = active_session.org.id

    try:
        proj_uuid = uuid.UUID(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid project_id UUID.") from exc

    document = Document(
        id=doc_id,
        org_id=org_id,
        project_id=proj_uuid,
        uploaded_by_user_id=active_session.user.id if active_session.user else None,
        title=filename,
        document_type=_doc_type_from_media(media_type, filename),
        status="parse_pending",
        storage_path=storage_path,
        sha256=sha256,
        media_type=media_type,
        size_bytes=len(content),
        metadata_json={"original_filename": filename, "parse_status": "parse_pending"},
    )
    db.add(document)
    db.flush()
    # The parse worker uses a separate DB session. Commit the upload record
    # before enqueueing so a fast worker cannot race an uncommitted document.
    db.commit()

    from draftcheck.jobs.documents import enqueue_document_parse, parse_document_for_session

    parse_job = enqueue_document_parse(doc_id)
    if not parse_job["enqueued"]:
        try:
            parse_document_for_session(db, document_id=doc_id, raise_parse_errors=True)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    orm_pages = (
        db.query(OrmDocumentPage)
        .filter(OrmDocumentPage.document_id == doc_id)
        .order_by(OrmDocumentPage.page_number)
        .all()
    )
    orm_chunks = (
        db.query(OrmDocumentChunk)
        .filter(OrmDocumentChunk.document_id == doc_id)
        .order_by(OrmDocumentChunk.chunk_index)
        .all()
    )
    all_orm_facts = (
        db.query(OrmDocumentFact)
        .filter(OrmDocumentFact.document_id == doc_id)
        .order_by(OrmDocumentFact.created_at, OrmDocumentFact.id)
        .all()
    )

    return {
        "document_id": str(doc_id),
        "filename": filename,
        "media_type": media_type,
        "size_bytes": len(content),
        "sha256": sha256,
        "parse_status": document.status,
        "parse_job": parse_job,
        "page_count": len(orm_pages),
        "chunk_count": len(orm_chunks),
        "extracted_facts": [_orm_fact_payload(f) for f in all_orm_facts],
        "fact_count": len(all_orm_facts),
        "review_required": True,
        "advisory_notice": "All extracted measurements are advisory. Promote facts to confirm before running compliance.",
    }


def _doc_type_from_media(media_type: str, filename: str) -> str:
    suffix = PurePath(filename).suffix.lower()
    mapping = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/dxf": "dxf",
        "text/plain": "txt",
        "text/csv": "csv",
    }
    result = mapping.get(media_type)
    if result:
        return result
    return suffix.lstrip(".") or "unknown"


# ---------------------------------------------------------------------------
# PATCH /documents/{doc_id}/facts/{fact_id}
# ---------------------------------------------------------------------------


@router.patch("/documents/{doc_id}/facts/{fact_id}", tags=["documents"])
def update_document_fact(
    doc_id: str,
    fact_id: str,
    payload: FactUpdateRequest,
    db: DbSession,
    _allowed_origin: Annotated[None, Depends(require_allowed_origin)],
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
) -> dict[str, Any]:
    """Update a fact's numeric value, review status, or calibration evidence."""
    fact = _get_fact_or_404(db, doc_id, fact_id)

    if payload.numeric_value is not None:
        updated_value = dict(fact.value_json or {})
        updated_value["numeric_value"] = payload.numeric_value
        fact.value_json = updated_value

    if payload.status is not None:
        fact.review_status = payload.status

    if payload.calibration_ref is not None:
        if fact.fact_kind != "drawing_dimension":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="calibration_ref applies only to drawing_dimension facts.",
            )
        metadata = dict(fact.metadata_json or {})
        metadata.update(
            {
                "calibration_ref": payload.calibration_ref.strip(),
                "calibration_status": "human_confirmed",
                "calibration_recorded_at": datetime.now(UTC).isoformat(),
                "calibration_recorded_by": str(active_session.user.id) if active_session.user else "system",
            }
        )
        if payload.calibration_note:
            metadata["calibration_note"] = payload.calibration_note.strip()
        fact.metadata_json = metadata

    db.flush()
    return _orm_fact_payload(fact)


# ---------------------------------------------------------------------------
# POST /documents/{doc_id}/facts/{fact_id}/promote
# ---------------------------------------------------------------------------


@router.post("/documents/{doc_id}/facts/{fact_id}/promote", tags=["documents"])
def promote_document_fact(
    doc_id: str,
    fact_id: str,
    db: DbSession,
    _allowed_origin: Annotated[None, Depends(require_allowed_origin)],
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
) -> dict[str, Any]:
    """Set status='confirmed', promote fact to PropertyFact on the project.

    Creates a new PropertyFact row linked to the document fact's project.
    """
    fact = _get_fact_or_404(db, doc_id, fact_id)

    v = fact.value_json or {}
    numeric_value = v.get("numeric_value")
    unit = v.get("unit", "")
    fact_key = fact.check_key or fact.fact_kind

    _confidence_threshold = float(os.getenv("FACT_CONFIDENCE_THRESHOLD", "0.7"))
    promotion_errors: list[str] = []
    if numeric_value is None:
        promotion_errors.append("numeric_value required for promotion")
    if not unit:
        promotion_errors.append("unit required for promotion")
    if not fact_key:
        promotion_errors.append("check_key or fact_kind required for promotion")
    if (fact.confidence or 0.0) < _confidence_threshold:
        promotion_errors.append(
            f"confidence {fact.confidence} below threshold {_confidence_threshold}"
        )
    if fact.fact_kind == "drawing_dimension" and not fact.metadata_json.get("calibration_ref"):
        promotion_errors.append(
            "drawing_dimension facts require calibration_ref in metadata before promotion"
        )
    if promotion_errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": promotion_errors},
        )

    fact.review_status = "confirmed"
    fact.promoted_to_measurement = True
    calibration_ref = (fact.metadata_json or {}).get("calibration_ref")
    value_json = {"value": numeric_value, "unit": unit, "document_fact_id": str(fact.id)}
    provenance_json = {
        "entered_by": str(active_session.user.id) if active_session.user else "system",
        "reason": "promoted from document fact",
        "method": "document_extraction_promoted",
        "source_document_id": str(fact.document_id),
        "source_fact_id": str(fact.id),
    }
    if calibration_ref is not None:
        value_json["calibration_ref"] = str(calibration_ref)
        provenance_json["calibration_ref"] = str(calibration_ref)

    property_fact = PropertyFact(
        id=uuid.uuid4(),
        org_id=fact.org_id,
        project_id=fact.project_id,
        fact_type=fact_key,
        value_json=value_json,
        confidence=fact.confidence,
        method="document_extraction_promoted",
        provenance_json=provenance_json,
        review_status="confirmed",
    )
    db.add(property_fact)
    db.flush()

    return {
        "fact_id": str(fact.id),
        "review_status": fact.review_status,
        "promoted_to_measurement": fact.promoted_to_measurement,
        "property_fact_id": str(property_fact.id),
        "advisory_notice": "Promoted fact is advisory. Not a legal or compliance certification.",
    }


# ---------------------------------------------------------------------------
# Legacy in-memory endpoints (kept for backward compatibility with existing tests)
# ---------------------------------------------------------------------------


@router.get("/documents/{document_id}/persisted-facts", tags=["documents"])
def get_persisted_document_facts(
    document_id: str,
    db: DbSession,
    _active_session: Annotated[ActiveSession, Depends(get_current_session)],
) -> dict[str, Any]:
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid document UUID.") from exc

    document = db.get(Document, doc_uuid)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document {document_id} not found.")

    facts = (
        db.query(OrmDocumentFact)
        .filter(OrmDocumentFact.document_id == doc_uuid)
        .order_by(OrmDocumentFact.created_at, OrmDocumentFact.id)
        .all()
    )
    return {
        "document_id": str(document.id),
        "parse_status": (document.metadata_json or {}).get("parse_status", document.status),
        "items": [_orm_fact_payload(fact) for fact in facts],
        "count": len(facts),
    }


@router.get("/documents/projects/{project_id}/evidence-search", tags=["documents"])
def search_project_document_evidence(
    project_id: str,
    db: DbSession,
    _active_session: Annotated[ActiveSession, Depends(get_current_session)],
    q: Annotated[str, Query(min_length=2, max_length=300)],
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> dict[str, Any]:
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid project UUID.") from exc

    hits = search_persisted_document_chunks(
        db,
        project_id=project_uuid,
        query=q,
        limit=limit,
    )
    doc_ids = [uuid.UUID(hit.chunk.document_id) for hit in hits]
    docs = (
        db.query(Document)
        .filter(Document.id.in_(doc_ids))
        .all()
        if doc_ids
        else []
    )
    titles = {str(doc.id): doc.title for doc in docs}
    items = [
        {
            "document_id": hit.chunk.document_id,
            "document_title": titles.get(hit.chunk.document_id),
            "page_number": hit.chunk.page_number,
            "chunk_index": hit.chunk.chunk_index,
            "text": hit.chunk.text,
            "score": round(hit.score, 6),
            "metadata": {
                **hit.chunk.metadata,
                "evidence_role": "project_document",
                "legal_authority": False,
            },
        }
        for hit in hits
    ]
    return {
        "project_id": str(project_uuid),
        "query": q,
        "items": items,
        "count": len(items),
        "legal_authority": False,
        "advisory_notice": (
            "Uploaded document evidence is project context only. It is not an approved legal source "
            "and cannot support compliance verdicts without approved rules and promoted measurements."
        ),
    }


@router.post("/documents/projects/{project_id}/upload", tags=["documents"])
async def upload_project_document(
    project_id: str,
    file: Annotated[UploadFile, File()],
    library: Annotated[InMemoryDocumentLibrary, Depends(get_document_library)],
    _allowed_origin: Annotated[None, Depends(require_allowed_origin)],
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
) -> dict[str, Any]:
    content = await file.read()
    try:
        result = library.upload(
            org_id=str(active_session.org.id),
            project_id=project_id,
            user_id=str(active_session.user.id),
            filename=file.filename or "upload.bin",
            media_type=file.content_type or "",
            content=content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return {
        "document": jsonable_encoder(result.document),
        "pages": len(result.pages),
        "chunks": len(result.chunks),
        "facts": [_inmem_fact_payload(fact) for fact in result.facts],
        "fact_count": len(result.facts),
        "review_required": True,
    }


@router.get("/documents/{document_id}", tags=["documents"])
def get_document(
    document_id: str,
    library: Annotated[InMemoryDocumentLibrary, Depends(get_document_library)],
    _active_session: Annotated[ActiveSession, Depends(get_current_session)],
) -> dict[str, Any]:
    try:
        return jsonable_encoder(library.get_document(document_id))
    except DocumentNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/documents/{document_id}/pages", tags=["documents"])
def get_document_pages(
    document_id: str,
    library: Annotated[InMemoryDocumentLibrary, Depends(get_document_library)],
    _active_session: Annotated[ActiveSession, Depends(get_current_session)],
) -> dict[str, Any]:
    try:
        pages = library.get_pages(document_id)
    except DocumentNotFoundError as exc:
        raise _not_found(exc) from exc
    return {"items": jsonable_encoder(pages), "count": len(pages)}


@router.get("/documents/{document_id}/facts", tags=["documents"])
def get_document_facts_inmem(
    document_id: str,
    library: Annotated[InMemoryDocumentLibrary, Depends(get_document_library)],
    _active_session: Annotated[ActiveSession, Depends(get_current_session)],
) -> dict[str, Any]:
    try:
        facts = library.get_facts(document_id)
    except DocumentNotFoundError as exc:
        raise _not_found(exc) from exc
    return {"items": [_inmem_fact_payload(f) for f in facts], "count": len(facts)}


@router.post("/documents/{document_id}/facts/{fact_id}/review", tags=["documents"])
def review_document_fact(
    document_id: str,
    fact_id: str,
    payload: ReviewDocumentFactPayload,
    library: Annotated[InMemoryDocumentLibrary, Depends(get_document_library)],
    _allowed_origin: Annotated[None, Depends(require_allowed_origin)],
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
) -> dict[str, Any]:
    try:
        fact = library.review_fact(
            document_id=document_id,
            fact_id=fact_id,
            review_status=payload.review_status,
            reviewed_by=str(active_session.user.id),
            note=payload.note,
        )
    except DocumentNotFoundError as exc:
        raise _not_found(exc) from exc
    return _inmem_fact_payload(fact)


# ---------------------------------------------------------------------------
# GET /documents/projects/{project_id} — list documents for a project (DB-backed)
# ---------------------------------------------------------------------------


@router.get("/documents/projects/{project_id}", tags=["documents"])
def list_project_documents(
    project_id: str,
    db: DbSession,
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
) -> dict[str, Any]:
    """Return all documents uploaded for a project, with their fact counts."""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid project UUID.") from exc

    docs = (
        db.query(Document)
        .filter(Document.project_id == project_uuid)
        .order_by(Document.created_at.desc())
        .all()
    )
    result = []
    for doc in docs:
        fact_count = (
            db.query(OrmDocumentFact)
            .filter(OrmDocumentFact.document_id == doc.id)
            .count()
        )
        result.append({
            "id": str(doc.id),
            "title": doc.title,
            "document_type": doc.document_type,
            "status": doc.status,
            "parse_status": (doc.metadata_json or {}).get("parse_status", doc.status),
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "fact_count": fact_count,
        })
    return {"items": result, "count": len(result)}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_fact_or_404(db: Session, doc_id: str, fact_id: str) -> OrmDocumentFact:
    try:
        doc_uuid = uuid.UUID(doc_id)
        fact_uuid = uuid.UUID(fact_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid UUID.") from exc

    fact: OrmDocumentFact | None = (
        db.query(OrmDocumentFact)
        .filter(
            OrmDocumentFact.id == fact_uuid,
            OrmDocumentFact.document_id == doc_uuid,
        )
        .first()
    )
    if fact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fact {fact_id} not found on document {doc_id}.",
        )
    return fact
