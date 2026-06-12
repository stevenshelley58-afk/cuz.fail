"""Document parsing jobs.

The upload API stores the raw file and enqueues this task.  The same
``parse_document_for_session`` helper is used by tests and local fallbacks so
the persisted pages/facts stay deterministic without a running worker.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path
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
    DocumentFact,
    DocumentParseError,
    DocumentParser,
    write_document_chunks,
)
from draftcheck.domain.documents.parsers import ParsedDocument
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
        parsed_document = _parse_content(
            document_id=doc_uuid,
            media_type=document.media_type or "",
            filename=document.title,
            content=content,
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
    for parsed_page in parsed_document.pages:
        page_metadata = dict(parsed_page.metadata or {})
        page = OrmDocumentPage(
            id=uuid4(),
            document_id=doc_uuid,
            page_number=parsed_page.page_number,
            width=page_metadata.pop("width", None),
            height=page_metadata.pop("height", None),
            rotation_degrees=page_metadata.pop("rotation_degrees", None),
            text=parsed_page.text,
            metadata_json={
                "parser_name": parsed_document.parser_name,
                "parser_version": parsed_document.parser_version,
                **page_metadata,
            },
        )
        session.add(page)
        pages.append(page)
    session.flush()

    chunks = write_document_chunks(session, document_id=doc_uuid, pages=pages)

    facts: list[OrmDocumentFact] = []
    for fact in _extract_parser_native_facts(
        document_id=doc_uuid,
        parsed_document=parsed_document,
        org_id=document.org_id,
        project_id=document.project_id,
        page_id=pages[0].id if pages else None,
    ):
        session.add(fact)
        facts.append(fact)

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
            metadata = dict(fact.metadata_json or {})
            metadata.update(
                {
                    "parser_boundary_source": True,
                    "parser_page_parser_name": parsed_document.parser_name,
                    "parser_page_number": page.page_number,
                }
            )
            fact.metadata_json = metadata
            _attach_pdf_text_block_evidence(fact, page)
            session.add(fact)
            facts.append(fact)
    session.flush()

    parse_status = "parsed" if pages or facts else "needs_more_info"
    document.status = parse_status
    metadata = dict(document.metadata_json or {})
    metadata.update(
        {
            "parse_status": parse_status,
            "parser_name": parsed_document.parser_name,
            "parser_version": parsed_document.parser_version,
            "page_count": len(pages),
            "chunk_count": len(chunks),
            "fact_count": len(facts),
            "parser_artifacts": [artifact.to_dict() for artifact in parsed_document.artifacts],
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
        parser_name=parsed_document.parser_name,
    )


def _parse_content(
    *,
    document_id: UUID,
    media_type: str,
    filename: str,
    content: bytes,
) -> ParsedDocument:
    parser = DocumentParser()
    return parser.parse_document(
        document_id=str(document_id),
        filename=filename,
        media_type=media_type,
        content=content,
    )


def _extract_parser_native_facts(
    *,
    document_id: UUID,
    parsed_document: ParsedDocument,
    org_id: UUID | None,
    project_id: UUID | None,
    page_id: UUID | None,
) -> list[OrmDocumentFact]:
    if parsed_document.parser_name not in {"draftcheck.dxf_text_parser", "draftcheck.ifc_text_parser"}:
        return []
    facts: list[OrmDocumentFact] = []
    for index, fact in enumerate(parsed_document.facts, start=1):
        if fact.numeric_value is None or fact.unit is None:
            continue
        check_key = _parser_fact_key(fact.label, index)
        value_json = {
            "numeric_value": fact.numeric_value,
            "unit": fact.unit,
            "fact_key": check_key,
            "source_text": fact.label,
            "page_number": 1,
        }
        evidence_ref = _parser_fact_evidence(fact)
        facts.append(
            OrmDocumentFact(
                id=uuid4(),
                org_id=org_id,
                project_id=project_id,
                document_id=document_id,
                page_id=page_id,
                fact_kind=fact.fact_type,
                check_key=check_key,
                value_json=value_json,
                confidence=fact.confidence,
                evidence_ref_json=evidence_ref,
                promoted_to_measurement=False,
                review_status="pending_review",
                parser_name=parsed_document.parser_name,
                parser_version=parsed_document.parser_version,
                metadata_json={
                    **fact.metadata,
                    "parser_native_fact": True,
                    "measurement_compliance_ready": False,
                    "measurement_readiness_reason": fact.metadata.get(
                        "measurement_readiness_reason",
                        "human promotion required before compliance use",
                    ),
                },
            )
        )
    return facts


def _attach_pdf_text_block_evidence(fact: OrmDocumentFact, page: OrmDocumentPage) -> None:
    text_blocks = (page.metadata_json or {}).get("text_blocks")
    if not isinstance(text_blocks, list):
        return

    source_text = str((fact.evidence_ref_json or {}).get("source_text") or "")
    source_key = _normalise_evidence_text(source_text)
    if not source_key:
        return

    for block in text_blocks:
        if not isinstance(block, dict):
            continue
        block_text = str(block.get("text") or "")
        if source_key not in _normalise_evidence_text(block_text):
            continue
        bbox = block.get("bbox")
        if not bbox:
            return
        evidence = dict(fact.evidence_ref_json or {})
        evidence.update(
            {
                "bbox": bbox,
                "text_block_number": block.get("block_number"),
                "evidence_method": "pdf_text_block_match",
                "measurement_compliance_ready": False,
                "measurement_readiness_reason": "pdf text block bbox is not a calibrated measurement",
            }
        )
        metadata = dict(fact.metadata_json or {})
        metadata.update(
            {
                "pdf_text_block_bbox": bbox,
                "pdf_text_block_number": block.get("block_number"),
                "pdf_text_block_evidence_method": "pdf_text_block_match",
                "measurement_compliance_ready": False,
                "measurement_readiness_reason": metadata.get(
                    "measurement_readiness_reason",
                    "human promotion required before compliance use",
                ),
            }
        )
        fact.evidence_ref_json = evidence
        fact.metadata_json = metadata
        return


def _normalise_evidence_text(text: str) -> str:
    return " ".join(text.casefold().split())


def _parser_fact_evidence(fact: DocumentFact) -> dict[str, object]:
    evidence: dict[str, object] = {"page_number": 1, "source_text": fact.label}
    for key in (
        "entity_handle",
        "entity_layer",
        "entity_type",
        "cad_space",
        "layout_name",
        "block_name",
        "insert_handle",
        "insert_layer",
        "insert_scale",
        "ifc_entity_id",
        "ifc_quantity_set_id",
        "ifc_related_object_id",
    ):
        value = fact.metadata.get(key)
        if value is not None:
            evidence[key] = value
    return evidence


def _parser_fact_key(label: str, index: int) -> str:
    sanitized = "".join(char.lower() if char.isalnum() else "_" for char in label).strip("_")
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")
    return sanitized or f"parser_fact_{index}"


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
