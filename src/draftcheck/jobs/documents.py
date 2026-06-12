"""Document parsing jobs.

The upload API stores the raw file and enqueues this task.  The same
``parse_document_for_session`` helper is used by tests and local fallbacks so
the persisted pages/facts stay deterministic without a running worker.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path, PurePath
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from draftcheck.db.engine import create_session_factory
from draftcheck.db.models import (
    Document,
    DocumentChunk as OrmDocumentChunk,
    DocumentFact as OrmDocumentFact,
    DocumentPage as OrmDocumentPage,
)
from draftcheck.domain.documents import (
    DocumentParseError,
    decode_text_bytes,
    extract_docx_text,
    extract_pdf_pages,
    write_document_chunks,
)
from draftcheck.domain.documents.facts import DocumentFactService
from draftcheck.jobs import procrastinate_app

DOCUMENT_PARSE_TASK_NAME = "draftcheck.documents.parse"
DOCUMENT_PARSE_QUEUE = "default"

_logger = logging.getLogger(__name__)
_fact_service = DocumentFactService()


@procrastinate_app.task(name=DOCUMENT_PARSE_TASK_NAME, queue=DOCUMENT_PARSE_QUEUE)
def parse_document(document_id: str) -> dict[str, Any]:
    """Parse one uploaded document and persist pages/facts."""

    session_factory = create_session_factory()
    session = session_factory()
    try:
        result = parse_document_for_session(session, document_id=document_id)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def enqueue_document_parse(document_id: UUID) -> dict[str, Any]:
    """Best-effort enqueue for the parse task.

    Returns ``{"enqueued": False}`` when the queue is not configured, allowing
    the API to run the deterministic local fallback used by tests.
    """

    if _sync_fallback_requested():
        return {"enqueued": False, "reason": "sync_fallback_requested"}

    defer = getattr(parse_document, "defer", None)
    if defer is None:
        return {"enqueued": False, "reason": "procrastinate_unavailable"}

    try:
        job_id = defer(document_id=str(document_id))
    except Exception as exc:  # pragma: no cover - depends on external queue state.
        _logger.warning("Failed to enqueue document parse for %s; using sync fallback: %s", document_id, exc)
        return {"enqueued": False, "reason": "enqueue_failed", "error": str(exc)}
    return {"enqueued": True, "job_id": job_id, "queue": DOCUMENT_PARSE_QUEUE}


def parse_document_for_session(
    session: Session,
    *,
    document_id: str | UUID,
    raise_parse_errors: bool = False,
) -> dict[str, Any]:
    """Parse an uploaded document using an existing SQLAlchemy session."""

    doc_uuid = document_id if isinstance(document_id, UUID) else UUID(str(document_id))
    document = session.get(Document, doc_uuid)
    if document is None:
        raise ValueError(f"document {document_id} not found")

    metadata = dict(document.metadata_json or {})
    metadata["parse_status"] = "parsing"
    metadata["parse_started_at"] = _utc_now()
    document.status = "parsing"
    document.metadata_json = metadata
    session.flush()

    try:
        content = Path(document.storage_path).read_bytes()
        page_texts, parser_name = _extract_text_from_content(
            document.media_type or "",
            document.title,
            content,
        )
    except DocumentParseError as exc:
        _mark_parse_failed(session, document, str(exc))
        if raise_parse_errors:
            raise
        return _summary(document, page_count=0, chunk_count=0, fact_count=0, parser_name=None)
    except OSError as exc:
        message = f"Failed to read stored document: {exc}"
        _mark_parse_failed(session, document, message)
        if raise_parse_errors:
            raise DocumentParseError(message) from exc
        return _summary(document, page_count=0, chunk_count=0, fact_count=0, parser_name=None)

    (
        session.query(OrmDocumentChunk)
        .filter(OrmDocumentChunk.document_id == doc_uuid)
        .delete(synchronize_session=False)
    )
    (
        session.query(OrmDocumentFact)
        .filter(OrmDocumentFact.document_id == doc_uuid)
        .delete(synchronize_session=False)
    )
    (
        session.query(OrmDocumentPage)
        .filter(OrmDocumentPage.document_id == doc_uuid)
        .delete(synchronize_session=False)
    )
    session.flush()

    pages: list[OrmDocumentPage] = []
    for page_number, page_text in enumerate(page_texts, start=1):
        page = OrmDocumentPage(
            id=uuid4(),
            document_id=doc_uuid,
            page_number=page_number,
            text=page_text,
            metadata_json={
                "parser_name": parser_name,
                "parser_version": DocumentFactService.PARSER_VERSION,
            },
        )
        session.add(page)
        pages.append(page)
    session.flush()

    chunks = write_document_chunks(session, document_id=doc_uuid, pages=pages)

    facts: list[OrmDocumentFact] = []
    for page in pages:
        extracted = _fact_service.extract_facts_from_text(
            text=page.text or "",
            document_id=doc_uuid,
            page_number=page.page_number,
            org_id=document.org_id,
            project_id=document.project_id,
            page_id=page.id,
        )
        for fact in extracted:
            session.add(fact)
            facts.append(fact)
    session.flush()

    parse_status = "parsed" if pages or facts else "needs_more_info"
    document.status = parse_status
    metadata = dict(document.metadata_json or {})
    metadata.update(
        {
            "parse_status": parse_status,
            "parser_name": parser_name,
            "parser_version": DocumentFactService.PARSER_VERSION,
            "page_count": len(pages),
            "chunk_count": len(chunks),
            "fact_count": len(facts),
            "parsed_at": _utc_now(),
            "measurement_policy": "Measurements are advisory pending automated validation.",
            "raster_measurement_policy": "Raster/PDF/image measurements are not compliance-ready without calibration.",
        }
    )
    document.metadata_json = metadata
    session.flush()
    return _summary(
        document,
        page_count=len(pages),
        chunk_count=len(chunks),
        fact_count=len(facts),
        parser_name=parser_name,
    )


def _extract_text_from_content(media_type: str, filename: str, content: bytes) -> tuple[list[str], str]:
    """Return per-page text and parser name without promoting measurements."""

    suffix = PurePath(filename).suffix.lower()
    parser_name = "draftcheck.plain_text_parser"

    if media_type == "application/pdf" or suffix == ".pdf":
        parser_name = "draftcheck.pdf_text_parser"
        return extract_pdf_pages(content), parser_name

    if media_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or suffix == ".docx":
        parser_name = "draftcheck.docx_text_parser"
        text = extract_docx_text(content)
        return [text] if text.strip() else [], parser_name

    if suffix == ".dxf" or "dxf" in media_type:
        parser_name = "draftcheck.dxf_text_parser"
        text = decode_text_bytes(content)
        return [text] if text.strip() else [], parser_name

    text = decode_text_bytes(content)
    return [text] if text.strip() else [], parser_name


def _mark_parse_failed(session: Session, document: Document, error: str) -> None:
    document.status = "parse_failed"
    metadata = dict(document.metadata_json or {})
    metadata.update({"parse_status": "parse_failed", "parse_error": error, "parse_failed_at": _utc_now()})
    document.metadata_json = metadata
    session.flush()


def _summary(
    document: Document,
    *,
    page_count: int,
    chunk_count: int,
    fact_count: int,
    parser_name: str | None,
) -> dict[str, Any]:
    return {
        "document_id": str(document.id),
        "parse_status": document.status,
        "page_count": page_count,
        "chunk_count": chunk_count,
        "fact_count": fact_count,
        "parser_name": parser_name,
    }


def _sync_fallback_requested() -> bool:
    value = os.getenv("DRAFTCHECK_DOCUMENT_PARSE_SYNC", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
