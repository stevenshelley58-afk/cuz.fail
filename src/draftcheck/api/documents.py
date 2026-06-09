"""V3 document upload and parser router."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field

from draftcheck.api.auth import get_current_session, require_allowed_origin
from draftcheck.domain.documents import (
    DocumentFact,
    DocumentNotFoundError,
    DocumentParser,
    DocumentReviewStatus,
    InMemoryDocumentLibrary,
    sample_parser_accuracy_report,
)
from draftcheck.domain.identity import ActiveSession


router = APIRouter(tags=["documents"])
_document_library: InMemoryDocumentLibrary | None = None


class ReviewDocumentFactPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_status: DocumentReviewStatus
    note: str | None = Field(default=None, max_length=1000)


def get_document_library() -> InMemoryDocumentLibrary:
    global _document_library
    if _document_library is None:
        _document_library = InMemoryDocumentLibrary()
    return _document_library


def _not_found(exc: DocumentNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document item not found: {exc}")


def _fact_payload(fact: DocumentFact) -> dict[str, Any]:
    payload = jsonable_encoder(fact)
    payload["review_status"] = fact.review_status.value
    return payload


@router.get("/documents/parsers", tags=["documents"])
def list_document_parsers() -> dict[str, Any]:
    capabilities = DocumentParser().capabilities()
    return {
        "items": jsonable_encoder(capabilities),
        "count": len(capabilities),
        "accuracy_gate": {
            "status": "not_beta_ready",
            "reason": "parser coverage and golden eval accuracy gates have not passed",
            "required_before_beta": [
                "real PDF/DOCX/DXF/IFC fixture set",
                "per-field precision/recall report",
                "automated review gate",
                "no raster measurement without calibration",
            ],
        },
    }


@router.get("/documents/parsers/accuracy", tags=["documents"])
def get_document_parser_accuracy() -> dict[str, Any]:
    return sample_parser_accuracy_report()


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
        "facts": [_fact_payload(fact) for fact in result.facts],
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
def get_document_facts(
    document_id: str,
    library: Annotated[InMemoryDocumentLibrary, Depends(get_document_library)],
    _active_session: Annotated[ActiveSession, Depends(get_current_session)],
) -> dict[str, Any]:
    try:
        facts = library.get_facts(document_id)
    except DocumentNotFoundError as exc:
        raise _not_found(exc) from exc
    return {"items": [_fact_payload(fact) for fact in facts], "count": len(facts)}


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
    return _fact_payload(fact)
