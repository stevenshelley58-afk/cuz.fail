from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_core.audit import record_audit
from draftcheck_core.database import SessionLocal, init_database
from draftcheck_core.json_utils import from_json, hash_text, to_json
from draftcheck_core.models import (
    BackgroundJob,
    JobTrace,
    ResponseDraft,
    RfiItem,
    SourceDocument,
    SourceFetchLog,
    SourceUpdateEvent,
    SourceVersion,
)
from draftcheck_document_ai.rfi import RfiService
from draftcheck_document_ai.extraction import extract_text_from_bytes
from draftcheck_ingestion.service import SourceIngestionService
from draftcheck_scraper.lawful_fetcher import fetch_public_content
from draftcheck_shared.schemas import SourceDocumentCreate

JobHandler = Callable[[Session, BackgroundJob, dict[str, Any]], dict[str, Any] | None]
HANDLERS: dict[str, JobHandler] = {}
REQUIRED_JOB_TYPES = frozenset(
    {"source_ingestion", "council_pack", "rfi_analysis", "source_freshness_audit"}
)
RESTRICTED_SOURCE_TERMS = (
    "paywall",
    "login required",
    "captcha",
    "subscription",
    "paid access",
    "proprietary",
    "no reuse",
    "no redistribution",
    "licence required",
    "license required",
)


class NoWorkerHandlerError(RuntimeError):
    pass


def register_handler(job_type: str, handler: JobHandler) -> None:
    HANDLERS[job_type] = handler


def registered_job_types() -> set[str]:
    return set(HANDLERS)


def missing_required_job_types() -> set[str]:
    return set(REQUIRED_JOB_TYPES.difference(HANDLERS))


def run_background_job(job_id: str) -> dict[str, Any]:
    init_database()
    with SessionLocal() as db:
        job = db.get(BackgroundJob, job_id)
        if not job:
            raise KeyError(f"Background job not found: {job_id}")
        if job.status == "cancelled":
            return {"job_id": job.id, "status": job.status}

        payload: dict[str, Any] = from_json(job.payload_json, {})
        job.status = "running"
        job.error = None
        _store_trace(db, job, "running")
        record_audit(
            db,
            action="job.started",
            target_type="background_job",
            target_id=job.id,
            project_id=job.project_id,
            metadata={"job_type": job.job_type, "provider": job.provider},
        )
        db.commit()

        try:
            handler = HANDLERS.get(job.job_type)
            if not handler:
                raise NoWorkerHandlerError(f"No worker handler registered for {job.job_type}")
            result = handler(db, job, payload) or {}
            job.status = "completed"
            job.error = None
            _store_trace(db, job, "completed", artifacts=[result])
            record_audit(
                db,
                action="job.completed",
                target_type="background_job",
                target_id=job.id,
                project_id=job.project_id,
                metadata={"job_type": job.job_type, "provider": job.provider},
            )
            db.commit()
            return {"job_id": job.id, "status": job.status, "result": result}
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            _store_trace(db, job, "failed", error=str(exc))
            record_audit(
                db,
                action="job.failed",
                target_type="background_job",
                target_id=job.id,
                project_id=job.project_id,
                metadata={"job_type": job.job_type, "provider": job.provider, "error": str(exc)},
            )
            db.commit()
            if isinstance(exc, NoWorkerHandlerError):
                return {"job_id": job.id, "status": job.status, "error": str(exc)}
            raise


def _store_trace(
    db: Session,
    job: BackgroundJob,
    status: str,
    *,
    error: str | None = None,
    artifacts: list[Any] | None = None,
) -> JobTrace:
    now = datetime.now(UTC).replace(tzinfo=None)
    trace = JobTrace(
        job_id=job.id,
        correlation_id=job.correlation_id,
        project_id=job.project_id,
        source_version_id=job.source_version_id,
        prompt=job.payload_json,
        model=job.model,
        provider=job.provider,
        status=status,
        started_at=now,
        finished_at=now if status in {"completed", "failed", "cancelled"} else None,
        error=error,
        artifacts_json=to_json(artifacts or []),
    )
    db.add(trace)
    db.flush()
    return trace


def _source_freshness_audit_handler(
    db: Session,
    job: BackgroundJob,
    payload: dict[str, Any],
) -> dict[str, Any]:
    source_document_id = str(payload.get("source_document_id") or "").strip()
    if not source_document_id:
        raise ValueError("source_freshness_audit requires source_document_id")

    source = db.get(SourceDocument, source_document_id)
    if not source:
        raise KeyError(f"Source document not found: {source_document_id}")
    if not source.is_active:
        return _blocked_freshness_result(db, source, "Source document is inactive")
    if not source.canonical_url:
        return _blocked_freshness_result(
            db,
            source,
            "Source document has no canonical_url for freshness audit",
            log_fetch=False,
        )
    if not source.scrape_allowed:
        return _blocked_freshness_result(db, source, "Source document is marked scrape_allowed=false")
    if _is_standards_australia_source(source):
        return _blocked_freshness_result(
            db,
            source,
            "Standards Australia sources are metadata-only; full text is not fetched or stored",
        )

    fetch_access_type = "public" if source.access_type == "open" else source.access_type
    if fetch_access_type != "public":
        return _blocked_freshness_result(
            db,
            source,
            f"Source access_type={source.access_type} requires human review before automated fetch",
        )
    if _has_restricted_source_terms(source):
        return _blocked_freshness_result(
            db,
            source,
            "Source licence or access notes indicate restricted reuse",
        )

    try:
        fetched = asyncio.run(
            fetch_public_content(
                source.canonical_url,
                licence_notes=source.licence_notes,
                access_type=fetch_access_type,
            )
        )
    except Exception as exc:
        _record_source_fetch(db, source, status="failed", error_message=str(exc))
        _record_source_event(db, source, "freshness_audit_failed", str(exc))
        raise

    extracted_text = extract_text_from_bytes(fetched.content, fetched.content_type)
    if not extracted_text.strip():
        _record_source_fetch(
            db,
            source,
            status="manual_review_required",
            http_status=fetched.status_code,
            metadata={"robots_allowed": fetched.robots_allowed, "fetched_url": fetched.url},
            error_message="Fetched content did not contain extractable public text",
        )
        _record_source_event(
            db,
            source,
            "freshness_manual_review_required",
            "Fetched content did not contain extractable public text; no source version was ingested.",
        )
        return {
            "status": "manual_review_required",
            "source_document_id": source.id,
            "reason": "Fetched content did not contain extractable public text",
        }

    content_sha256 = hash_text(extracted_text)
    _record_source_fetch(
        db,
        source,
        status="success",
        http_status=fetched.status_code,
        content_sha256=content_sha256,
        metadata={"robots_allowed": fetched.robots_allowed, "fetched_url": fetched.url},
    )

    current = _current_source_version(db, source.id)
    if current and current.content_sha256 == content_sha256:
        job.source_version_id = current.id
        _record_source_event(
            db,
            source,
            "freshness_unchanged",
            f"Fetched content hash matches current source version {current.id}.",
        )
        return {
            "status": "unchanged",
            "source_document_id": source.id,
            "source_version_id": current.id,
            "content_sha256": content_sha256,
        }

    result = SourceIngestionService(db).ingest_source(
        SourceDocumentCreate(
            title=source.title,
            jurisdiction=source.jurisdiction,
            authority=source.authority,
            local_government=source.local_government,
            source_type=source.source_type,
            canonical_url=source.canonical_url,
            licence_notes=source.licence_notes,
            access_type=fetch_access_type,
            scrape_allowed=source.scrape_allowed,
            content=extracted_text,
            review_status="pending_review",
            retrieved_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
    job.source_version_id = result.source_version_id
    _record_source_event(
        db,
        source,
        "freshness_changed",
        f"Fetched content created source version {result.source_version_id}; human review required.",
    )
    return {
        "status": "changed",
        "source_document_id": result.source_document_id,
        "source_version_id": result.source_version_id,
        "clauses_created": result.clauses_created,
        "chunks_created": result.chunks_created,
        "source_artifacts_created": result.source_artifacts_created,
        "duplicate": result.duplicate,
        "content_sha256": content_sha256,
        "requires_human_review": True,
    }


def _source_ingestion_handler(
    db: Session,
    job: BackgroundJob,
    payload: dict[str, Any],
) -> dict[str, Any]:
    service = SourceIngestionService(db)
    if manifest_yaml := str(payload.get("manifest_yaml") or payload.get("yaml") or "").strip():
        results = service.import_manifest_yaml(manifest_yaml)
        return _source_ingestion_batch_result(job, results)

    entries = payload.get("entries")
    if isinstance(entries, list):
        results = [service.ingest_source(SourceDocumentCreate(**entry)) for entry in entries]
        return _source_ingestion_batch_result(job, results)

    source_payload = payload.get("source") if isinstance(payload.get("source"), dict) else payload
    result = service.ingest_source(SourceDocumentCreate(**source_payload))
    job.source_version_id = result.source_version_id
    return {
        "status": "duplicate" if result.duplicate else "ingested",
        "source_document_id": result.source_document_id,
        "source_version_id": result.source_version_id,
        "clauses_created": result.clauses_created,
        "chunks_created": result.chunks_created,
        "source_artifacts_created": result.source_artifacts_created,
        "rule_dispositions_created": result.rule_dispositions_created,
        "rule_candidates_created": result.rule_candidates_created,
        "rule_candidates_existing": result.rule_candidates_existing,
        "duplicate": result.duplicate,
        "requires_human_review": True,
    }


def _source_ingestion_batch_result(
    job: BackgroundJob,
    results,
) -> dict[str, Any]:
    if results:
        job.source_version_id = results[-1].source_version_id
    return {
        "status": "imported",
        "imported": len(results),
        "duplicates": sum(1 for result in results if result.duplicate),
        "source_version_ids": [result.source_version_id for result in results],
        "source_artifacts_created": sum(result.source_artifacts_created for result in results),
        "rule_dispositions_created": sum(result.rule_dispositions_created for result in results),
        "rule_candidates_created": sum(result.rule_candidates_created for result in results),
        "rule_candidates_existing": sum(result.rule_candidates_existing for result in results),
        "requires_human_review": True,
    }


def _rfi_analysis_handler(
    db: Session,
    job: BackgroundJob,
    payload: dict[str, Any],
) -> dict[str, Any]:
    project_id = _job_project_id(job, payload, "rfi_analysis")
    items = db.scalars(
        select(RfiItem)
        .where(RfiItem.project_id == project_id)
        .order_by(RfiItem.item_number, RfiItem.created_at)
    ).all()
    missing_evidence = sorted(
        {
            missing
            for item in items
            for missing in from_json(item.missing_evidence_json, [])
        }
    )
    candidate_count = sum(
        len(from_json(item.source_requirement_candidates_json, []))
        for item in items
    )
    record_audit(
        db,
        action="rfi.analysis.completed",
        target_type="project",
        target_id=project_id,
        project_id=project_id,
        metadata={
            "rfi_item_count": len(items),
            "source_requirement_candidate_count": candidate_count,
        },
    )
    return {
        "status": "completed",
        "project_id": project_id,
        "rfi_item_count": len(items),
        "open_item_count": sum(1 for item in items if item.status == "open"),
        "source_requirement_candidate_count": candidate_count,
        "missing_evidence": missing_evidence,
        "requires_human_review": True,
    }


def _council_pack_handler(
    db: Session,
    job: BackgroundJob,
    payload: dict[str, Any],
) -> dict[str, Any]:
    project_id = _job_project_id(job, payload, "council_pack")
    draft_id = str(payload.get("response_draft_id") or "").strip()
    draft: ResponseDraft | None = None
    generated = False
    if draft_id:
        draft = db.get(ResponseDraft, draft_id)
        if not draft or draft.project_id != project_id:
            raise KeyError("Response draft not found")
    else:
        draft = db.scalar(
            select(ResponseDraft)
            .where(ResponseDraft.project_id == project_id)
            .order_by(ResponseDraft.created_at.desc(), ResponseDraft.id.desc())
        )
        if not draft:
            generated_schema = RfiService(db).generate_response(project_id)
            draft = db.get(ResponseDraft, generated_schema.id)
            generated = True

    if not draft:
        raise KeyError("Response draft not found")

    citations = from_json(draft.citations_json, [])
    missing_information = from_json(draft.missing_information_json, [])
    draft.requires_human_review = True
    record_audit(
        db,
        action="council_pack.prepared",
        target_type="response_draft",
        target_id=draft.id,
        project_id=project_id,
        metadata={
            "citation_count": len(citations),
            "missing_information_count": len(missing_information),
            "generated": generated,
        },
    )
    return {
        "status": "draft_generated" if generated else "draft_ready",
        "project_id": project_id,
        "response_draft_id": draft.id,
        "citation_count": len(citations),
        "missing_information_count": len(missing_information),
        "requires_human_review": True,
    }


def _job_project_id(job: BackgroundJob, payload: dict[str, Any], job_type: str) -> str:
    project_id = str(job.project_id or payload.get("project_id") or "").strip()
    if not project_id:
        raise ValueError(f"{job_type} requires project_id")
    return project_id


def _blocked_freshness_result(
    db: Session,
    source: SourceDocument,
    reason: str,
    *,
    log_fetch: bool = True,
) -> dict[str, Any]:
    if log_fetch:
        _record_source_fetch(
            db,
            source,
            status="blocked",
            error_message=reason,
            metadata={"note": "No automated fetch attempted."},
        )
    _record_source_event(db, source, "freshness_blocked", reason)
    return {"status": "blocked", "source_document_id": source.id, "reason": reason}


def _current_source_version(db: Session, source_document_id: str) -> SourceVersion | None:
    return db.scalar(
        select(SourceVersion)
        .where(
            SourceVersion.source_document_id == source_document_id,
            SourceVersion.is_superseded.is_(False),
        )
        .order_by(SourceVersion.retrieved_at.desc(), SourceVersion.created_at.desc())
    )


def _record_source_fetch(
    db: Session,
    source: SourceDocument,
    *,
    status: str,
    http_status: int | None = None,
    content_sha256: str | None = None,
    error_message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.add(
        SourceFetchLog(
            source_document_id=source.id,
            url=source.canonical_url or "",
            status=status,
            http_status=http_status,
            error_message=error_message,
            retrieved_at=datetime.now(UTC).replace(tzinfo=None) if status == "success" else None,
            content_sha256=content_sha256,
            metadata_json=to_json(metadata or {}),
        )
    )


def _record_source_event(
    db: Session,
    source: SourceDocument,
    event_type: str,
    notes: str,
) -> None:
    db.add(SourceUpdateEvent(source_document_id=source.id, event_type=event_type, notes=notes))


def _has_restricted_source_terms(source: SourceDocument) -> bool:
    haystack = f"{source.licence_notes} {source.access_type}".lower()
    return any(term in haystack for term in RESTRICTED_SOURCE_TERMS)


def _is_standards_australia_source(source: SourceDocument) -> bool:
    haystack = " ".join(
        value
        for value in [
            source.title,
            source.authority,
            source.source_type,
            source.canonical_url or "",
        ]
        if value
    ).lower()
    return "standards australia" in haystack or "standards.org.au" in haystack


register_handler("source_freshness_audit", _source_freshness_audit_handler)
register_handler("source_ingestion", _source_ingestion_handler)
register_handler("rfi_analysis", _rfi_analysis_handler)
register_handler("council_pack", _council_pack_handler)
