"""Standalone V3 sources and search router.

The coordinator mounts this router under `/api/v1`; this file deliberately does
not edit `draftcheck.api.v1`.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
import os
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field, field_validator

from draftcheck.ai import InMemoryJobTraceStore, LocalDeterministicModelAdapter, ModelAdapter, ModelRequest
from draftcheck.api.auth import get_current_session, require_allowed_origin, require_reviewer_session
from draftcheck.db.engine import database_url_from_env
from draftcheck.domain.identity import ActiveSession
from draftcheck.domain.sources import (
    AnswerStatus,
    InMemorySourceLibrary,
    InMemorySourceSearchService,
    LicenceStatus,
    SourceAnswer,
    SourceChunk,
    SourceImportResult,
    SourceNotFoundError,
    SourceReviewStatus,
    SourceSearchHit,
)
from draftcheck.domain.sources.sqlalchemy_store import SqlAlchemySourceLibrary


class SourceImportPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=300)
    content: str = ""
    source_id: str | None = Field(default=None, max_length=120)
    uri: str | None = Field(default=None, max_length=1000)
    publisher: str | None = Field(default=None, max_length=200)
    licence_status: LicenceStatus = LicenceStatus.OPEN
    media_type: str = Field(default="text/plain", max_length=120)
    metadata_only: bool = False

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("source title is required")
        return normalized


class SourceReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_version_id: str | None = Field(default=None, max_length=160)
    review_status: SourceReviewStatus = SourceReviewStatus.APPROVED
    licence_status: LicenceStatus | None = None
    notes: str | None = Field(default=None, max_length=1000)


class SearchChunksPayload(BaseModel):
    query: str | None = Field(default=None, max_length=1000)
    q: str | None = Field(default=None, max_length=1000)
    limit: int = Field(default=8, ge=1, le=50)


class SearchAskPayload(BaseModel):
    question: str | None = Field(default=None, max_length=1000)
    query: str | None = Field(default=None, max_length=1000)
    q: str | None = Field(default=None, max_length=1000)
    limit: int = Field(default=4, ge=1, le=12)


def _required_query(*values: str | None) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="query is required",
    )


def _source_not_found(exc: SourceNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _chunk_payload(chunk: SourceChunk) -> dict[str, Any]:
    return {
        "id": chunk.id,
        "source_id": chunk.source_id,
        "source_version_id": chunk.source_version_id,
        "ordinal": chunk.ordinal,
        "text": chunk.text,
        "text_sha256": chunk.text_sha256,
        "citation_id": chunk.citation_id,
        "embedding": {
            "provider": chunk.embedding_provider,
            "model": chunk.embedding_model,
            "dimension": chunk.embedding_dimension,
        },
    }


def _import_payload(result: SourceImportResult) -> dict[str, Any]:
    return {
        "source": jsonable_encoder(result.source),
        "version": jsonable_encoder(result.version),
        "artifacts": jsonable_encoder(result.artifacts),
        "chunks": [_chunk_payload(chunk) for chunk in result.chunks],
        "citations": jsonable_encoder(result.citations),
        "duplicate": result.duplicate,
        "metadata_only": result.metadata_only,
        "imported": 0 if result.duplicate else 1,
        "skipped": 0,
        "error_count": 0,
        "errors": [],
    }


def _hit_payload(hit: SourceSearchHit) -> dict[str, Any]:
    return {
        "chunk": _chunk_payload(hit.chunk),
        "citation": jsonable_encoder(hit.citation),
        "source_version": jsonable_encoder(hit.version),
        "score": hit.score,
    }


def _answer_payload(answer: SourceAnswer) -> dict[str, Any]:
    payload = jsonable_encoder(answer)
    if answer.status is not AnswerStatus.UNSUPPORTED and not answer.citations:
        raise RuntimeError("source answer invariant violated: cited answer has no citations")
    return payload


def _default_source_library() -> Any:
    database_url = database_url_from_env()
    if database_url and os.getenv("DRAFTCHECK_SOURCE_STORE", "auto") != "memory":
        return SqlAlchemySourceLibrary.from_database_url(database_url)
    return InMemorySourceLibrary()


def _fallback_ingestion_status(
    source_library: InMemorySourceLibrary,
    *,
    local_government: str | None,
) -> dict[str, Any]:
    del local_government
    sources = source_library.list_sources()
    versions = [
        version
        for source in sources
        for version in source_library.list_versions(source.id)
    ]
    counts = {
        "sources": len(sources),
        "versions": len(versions),
        "pending_review_versions": sum(
            1 for version in versions if version.review_status is SourceReviewStatus.PENDING_REVIEW
        ),
        "approved_citable_versions": sum(
            1 for version in versions if version.can_support_citable_retrieval
        ),
        "metadata_only_versions": sum(1 for version in versions if version.metadata_only),
        "chunks": sum(
            len(source_library.get_chunks_for_version(version.id)) for version in versions
        ),
        "citations": len(source_library.citations),
        "pending_fetches": 0,
        "review_ready_versions": 0,
        "low_signal_versions": 0,
        "parse_repair_ready_versions": 0,
        "parse_repair_missing_raw_artifact_versions": 0,
        "raw_source_artifact_versions": 0,
        "repaired_text_artifact_versions": 0,
    }
    readiness_counts = {
        "pending_lawful_fetch": 0,
        "parse_or_citation_repair_required": 0,
        "parse_quality_review_required": 0,
        "source_review_ready": 0,
        "licence_review_required": 0,
        "source_refresh_required": 0,
        "source_rejected": 0,
        "citable_search_ready": 0,
        "review_follow_up": 0,
    }
    source_type_counts: Counter[str] = Counter()
    pending_action_counts: Counter[str] = Counter()
    for version in versions:
        chunk_count = len(source_library.get_chunks_for_version(version.id))
        citation_count = len(
            [
                citation
                for citation in source_library.citations.values()
                if citation.source_version_id == version.id
            ]
        )
        low_signal = (
            not version.metadata_only and (chunk_count <= 1 or citation_count <= 1)
        )
        readiness = _source_version_readiness(
            version=version,
            chunk_count=chunk_count,
            citation_count=citation_count,
            low_signal=low_signal,
        )
        readiness_counts[readiness] += 1
        source_type_counts["source_document"] += 1
        if low_signal:
            counts["low_signal_versions"] += 1
        if (
            not version.metadata_only
            and not low_signal
            and chunk_count > 0
            and citation_count > 0
        ):
            counts["review_ready_versions"] += 1
        pending_action_counts[_fallback_pending_action(version, chunk_count, citation_count)] += 1
    return {
        "status": "ingestion_in_progress" if versions else "not_started",
        "answer_policy": "cite_or_refuse",
        "local_government": None,
        "beta_status": "not_beta_accurate_yet",
        "counts": counts,
        "items": [],
        "blocked_outputs": [
            "final_compliance_claims",
            "uncited_regulatory_answers",
            "unpromoted_measurement_verdicts",
        ],
        "pending": [
            "lawful source fetch",
            "human source approval",
            "rule extraction review",
            "deterministic check promotion",
        ],
        "quality_gates": _quality_gates(counts),
        "readiness_counts": readiness_counts,
        "source_type_counts": dict(source_type_counts),
        "pending_action_counts": dict(pending_action_counts),
        "latest_fetch_summary": {
            "requested_at": None,
            "successful_at": None,
        },
    }


def _fallback_review_worklist(
    source_library: InMemorySourceLibrary,
    *,
    local_government: str | None,
    source_type: str | None,
    include_metadata_only: bool,
    limit: int,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    counts = {
        "review_items": 0,
        "fetched_review_items": 0,
        "pending_fetch_items": 0,
        "approved_citable_versions": 0,
        "rejected_versions": 0,
        "chunks": 0,
        "citations": 0,
    }
    for source in source_library.list_sources():
        for version in source_library.list_versions(source.id):
            if version.can_support_citable_retrieval:
                counts["approved_citable_versions"] += 1
                continue
            if version.review_status is SourceReviewStatus.REJECTED:
                counts["rejected_versions"] += 1
            if version.metadata_only and not include_metadata_only:
                continue
            chunks = source_library.get_chunks_for_version(version.id)
            citation_count = len(
                [citation for citation in source_library.citations.values() if citation.source_version_id == version.id]
            )
            items.append(
                {
                    "source_id": source.id,
                    "source_version_id": version.id,
                    "title": source.title,
                    "authority": source.publisher,
                    "local_government": None,
                    "source_type": "source_document",
                    "canonical_url": source.uri,
                    "licence_status": version.licence_status.value,
                    "review_status": version.review_status.value,
                    "metadata_only": version.metadata_only,
                    "chunk_count": len(chunks),
                    "citation_count": citation_count,
                    "latest_fetch": None,
                    "priority": "normal" if chunks else "medium",
                    "issue_codes": _fallback_review_issue_codes(
                        version,
                        chunk_count=len(chunks),
                        citation_count=citation_count,
                    ),
                    "recommended_action": (
                        "lawful_fetch"
                        if version.metadata_only
                        else "human_source_review"
                        if chunks and citation_count
                        else "repair_parse_or_citations"
                    ),
                    "can_support_search": False,
                }
            )
            counts["review_items"] += 1
            counts["chunks"] += len(chunks)
            counts["citations"] += citation_count
            if version.metadata_only:
                counts["pending_fetch_items"] += 1
            else:
                counts["fetched_review_items"] += 1
    return {
        "status": "review_required" if counts["review_items"] else "clear",
        "answer_policy": "cite_or_refuse",
        "local_government": local_government,
        "source_type": source_type,
        "counts": counts,
        "items": items[: max(limit, 0)],
        "count": min(len(items), max(limit, 0)),
        "total": len(items),
        "blocked_until": [
            "human source review",
            "licence verification",
            "rule extraction review",
            "deterministic rule promotion",
        ],
    }


def _fallback_review_issue_codes(
    version: Any,
    *,
    chunk_count: int,
    citation_count: int,
) -> list[str]:
    issues: list[str] = []
    if version.metadata_only:
        issues.append("metadata_only_pending_fetch")
    if version.review_status is SourceReviewStatus.PENDING_REVIEW:
        issues.append("source_version_pending_review")
    if version.licence_status is LicenceStatus.PENDING_REVIEW:
        issues.append("licence_pending_review")
    if not version.metadata_only and chunk_count == 0:
        issues.append("no_chunks")
    if not version.metadata_only and citation_count == 0:
        issues.append("no_citations")
    return issues


def _fallback_pending_action(
    version: Any,
    chunk_count: int,
    citation_count: int,
) -> str:
    if version.metadata_only:
        return "lawful_fetch"
    if chunk_count == 0 or citation_count == 0:
        return "repair_parse_or_citations"
    return "human_source_review"


def _fallback_quality_report(
    source_library: InMemorySourceLibrary,
    *,
    local_government: str | None,
    source_type: str | None,
    readiness: str | None,
    limit: int,
) -> dict[str, Any]:
    worklist = _fallback_review_worklist(
        source_library,
        local_government=local_government,
        source_type=source_type,
        include_metadata_only=True,
        limit=limit,
    )
    counts = dict(worklist["counts"])
    counts["source_types"] = {"source_document": counts["review_items"]}
    counts["low_signal_versions"] = sum(
        1
        for item in worklist["items"]
        if not item["metadata_only"] and (item["chunk_count"] <= 1 or item["citation_count"] <= 1)
    )
    counts["review_ready_versions"] = sum(
        1
        for item in worklist["items"]
        if not item["metadata_only"]
        and item["chunk_count"] > 1
        and item["citation_count"] > 1
    )
    counts["blocked_versions"] = counts["review_items"]
    gates = _quality_gates(counts)
    items = [
        {
            **item,
            "readiness": _fallback_quality_readiness(item),
        }
        for item in worklist["items"]
    ]
    if readiness:
        items = [item for item in items if item["readiness"] == readiness]
    limited_items = items[: max(limit, 0)]
    return {
        "status": "blocked" if any(gate["status"] == "blocked" for gate in gates) else "review_ready",
        "answer_policy": "cite_or_refuse",
        "beta_status": "not_beta_accurate_yet",
        "local_government": local_government,
        "source_type": source_type,
        "readiness": readiness,
        "counts": counts,
        "quality_gates": gates,
        "items": limited_items,
        "count": len(limited_items),
        "total": len(items),
    }


def _fallback_quality_readiness(item: dict[str, Any]) -> str:
    if item["can_support_search"]:
        return "citable_search_ready"
    if item["metadata_only"]:
        return "pending_lawful_fetch"
    if item["chunk_count"] == 0 or item["citation_count"] == 0:
        return "parse_or_citation_repair_required"
    if item["chunk_count"] <= 1 or item["citation_count"] <= 1:
        return "parse_quality_review_required"
    if item["review_status"] == SourceReviewStatus.PENDING_REVIEW.value:
        return "source_review_ready"
    if item["review_status"] == SourceReviewStatus.REJECTED.value:
        return "source_rejected"
    if item["review_status"] == SourceReviewStatus.STALE.value:
        return "source_refresh_required"
    if item["licence_status"] == LicenceStatus.PENDING_REVIEW.value:
        return "licence_review_required"
    return "review_follow_up"


def _fallback_source_review_packet(
    source_library: InMemorySourceLibrary,
    *,
    source_id: str,
    source_version_id: str,
    sample_limit: int,
    sample_chars: int,
) -> dict[str, Any]:
    source = source_library.get_source(source_id)
    version = source_library.get_version(source_version_id)
    if version.source_id != source.id:
        raise SourceNotFoundError(f"source version does not belong to source: {source_version_id}")
    chunks = source_library.get_chunks_for_version(version.id)
    citations = [
        citation
        for citation in source_library.citations.values()
        if citation.source_version_id == version.id
    ]
    citation_by_chunk = {citation.chunk_id: citation for citation in citations}
    low_signal = (
        not version.metadata_only
        and (len(chunks) <= 1 or len(citations) <= 1)
    )
    issue_codes = _fallback_review_issue_codes(
        version,
        chunk_count=len(chunks),
        citation_count=len(citations),
    )
    if low_signal:
        issue_codes.append("low_signal_parse_review")
    readiness = _source_version_readiness(
        version=version,
        chunk_count=len(chunks),
        citation_count=len(citations),
        low_signal=low_signal,
    )
    chunk_samples = [
        {
            "id": chunk.id,
            "ordinal": chunk.ordinal,
            "text": _truncate_review_text(chunk.text, sample_chars),
            "text_truncated": len(chunk.text) > sample_chars,
            "text_sha256": chunk.text_sha256,
            "citation": jsonable_encoder(citation_by_chunk.get(chunk.id)),
        }
        for chunk in _sample_ordered(chunks, limit=sample_limit)
    ]
    artifacts = [
        artifact
        for artifact in source_library.artifacts.values()
        if artifact.subject_id == version.id
    ]
    return {
        "status": "review_required" if readiness != "citable_search_ready" else "citable_search_ready",
        "answer_policy": "cite_or_refuse",
        "source": jsonable_encoder(source),
        "version": jsonable_encoder(version),
        "counts": {
            "chunks": len(chunks),
            "citations": len(citations),
            "artifacts": len(artifacts),
        },
        "readiness": readiness,
        "issue_codes": issue_codes,
        "recommended_action": (
            "repair_parse_or_citations"
            if readiness in {"parse_or_citation_repair_required", "parse_quality_review_required"}
            else "lawful_fetch"
            if readiness == "pending_lawful_fetch"
            else "human_source_review"
        ),
        "can_support_search": version.can_support_citable_retrieval and bool(chunks) and bool(citations),
        "artifacts": jsonable_encoder(artifacts),
        "chunk_samples": chunk_samples,
        "blocked_outputs": [
            "final_compliance_claims",
            "uncited_regulatory_answers",
            "unpromoted_measurement_verdicts",
        ],
        "required_before_beta": [
            "human source review",
            "licence verification",
            "parse quality review when flagged",
            "rule extraction review",
            "deterministic rule promotion",
        ],
    }


def _source_version_readiness(
    *,
    version: Any,
    chunk_count: int,
    citation_count: int,
    low_signal: bool,
) -> str:
    if version.can_support_citable_retrieval and chunk_count > 0 and citation_count > 0:
        return "citable_search_ready"
    if version.metadata_only:
        return "pending_lawful_fetch"
    if chunk_count == 0 or citation_count == 0:
        return "parse_or_citation_repair_required"
    if low_signal:
        return "parse_quality_review_required"
    if version.review_status is SourceReviewStatus.PENDING_REVIEW:
        return "source_review_ready"
    if version.review_status is SourceReviewStatus.REJECTED:
        return "source_rejected"
    if version.review_status is SourceReviewStatus.STALE:
        return "source_refresh_required"
    if not version.licence_status.can_support_citation:
        return "licence_review_required"
    return "review_follow_up"


def _sample_ordered(items: tuple[Any, ...], *, limit: int) -> tuple[Any, ...]:
    if limit <= 0 or len(items) <= limit:
        return items
    if limit == 1:
        return (items[0],)
    indexes = {0, len(items) - 1}
    if limit > 2:
        step = (len(items) - 1) / (limit - 1)
        indexes.update(round(step * index) for index in range(limit))
    return tuple(items[index] for index in sorted(indexes)[:limit])


def _truncate_review_text(text: str, max_chars: int) -> str:
    normalized_limit = max(max_chars, 0)
    if len(text) <= normalized_limit:
        return text
    return text[:normalized_limit].rstrip()


def _quality_gates(counts: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "gate": "lawful_fetch_complete",
            "status": "blocked" if counts.get("pending_fetch_items", 0) else "passed",
            "blocking_count": counts.get("pending_fetch_items", 0),
        },
        {
            "gate": "source_review_complete",
            "status": "blocked" if counts.get("review_items", 0) else "passed",
            "blocking_count": counts.get("review_items", 0),
        },
        {
            "gate": "parse_quality_review",
            "status": "needs_review" if counts.get("low_signal_versions", 0) else "passed",
            "blocking_count": counts.get("low_signal_versions", 0),
        },
        {
            "gate": "citable_search_ready",
            "status": "blocked" if counts.get("approved_citable_versions", 0) == 0 else "passed",
            "blocking_count": 0 if counts.get("approved_citable_versions", 0) else 1,
        },
        {
            "gate": "deterministic_rules_promoted",
            "status": "blocked",
            "blocking_count": 1,
        },
    ]


def _trace_supported_answer(
    answer: SourceAnswer,
    *,
    question: str,
    source_library: InMemorySourceLibrary,
    model_adapter: ModelAdapter,
) -> SourceAnswer:
    if answer.status is AnswerStatus.UNSUPPORTED:
        return answer
    input_artifact_ids = tuple(
        dict.fromkeys(
            artifact_id
            for source_version_id in answer.source_version_ids
            for artifact_id in source_library.get_version(source_version_id).artifact_ids
        )
    )
    model_response = model_adapter.complete(
        ModelRequest(
            job_id=f"search_ask_{uuid4().hex}",
            job_type="search.ask",
            skill_version_id="sources-ask-substrate-v0",
            prompt=(
                "Draft an answer only from the supplied approved source citations.\n"
                f"Question: {question}\n"
                f"Source versions: {', '.join(answer.source_version_ids)}\n"
                f"Citations: {', '.join(citation.id for citation in answer.citations)}"
            ),
            max_output_tokens=256,
            input_artifact_ids=input_artifact_ids,
        )
    )
    if model_response.status == "refused" or not model_response.trace_id.strip():
        return SourceAnswer(
            status=AnswerStatus.UNSUPPORTED,
            answer="Unsupported: governed model adapter refused the traced answer draft.",
            citations=(),
            source_version_ids=(),
            missing_information=("governed model trace",),
            human_review_required=True,
            trace_id=model_response.trace_id,
        )
    trace_store = getattr(model_adapter, "trace_store", None)
    if not isinstance(trace_store, InMemoryJobTraceStore) or not any(
        trace.id == model_response.trace_id for trace in trace_store.list_traces()
    ):
        return SourceAnswer(
            status=AnswerStatus.UNSUPPORTED,
            answer="Unsupported: governed model adapter did not record the traced answer draft.",
            citations=(),
            source_version_ids=(),
            missing_information=("governed model trace",),
            human_review_required=True,
            trace_id=model_response.trace_id,
        )
    return replace(answer, trace_id=model_response.trace_id)


def create_sources_router(
    library: Any | None = None,
    model_adapter: ModelAdapter | None = None,
) -> APIRouter:
    source_library = library or _default_source_library()
    search_service = InMemorySourceSearchService(source_library)
    governed_model_adapter = model_adapter or LocalDeterministicModelAdapter(mode="local")
    api_router = APIRouter()

    @api_router.post("/sources/import", tags=["sources"])
    def import_source(
        payload: SourceImportPayload,
        _allowed_origin: Annotated[None, Depends(require_allowed_origin)],
        _active_session: Annotated[ActiveSession, Depends(require_reviewer_session)],
    ) -> dict[str, Any]:
        try:
            result = source_library.import_source(
                title=payload.title,
                content=payload.content,
                source_id=payload.source_id,
                uri=payload.uri,
                publisher=payload.publisher,
                licence_status=payload.licence_status,
                review_status=SourceReviewStatus.PENDING_REVIEW,
                media_type=payload.media_type,
                metadata_only=payload.metadata_only,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
        return _import_payload(result)

    @api_router.get("/sources", tags=["sources"])
    def list_sources() -> dict[str, Any]:
        items = source_library.list_sources()
        return {"items": jsonable_encoder(items), "count": len(items)}

    @api_router.get("/sources/freshness", tags=["sources"])
    def source_freshness() -> dict[str, Any]:
        items = source_library.freshness()
        return {"items": jsonable_encoder(items), "count": len(items)}

    @api_router.get("/sources/ingestion-status", tags=["sources"])
    def source_ingestion_status(local_government: str | None = None) -> dict[str, Any]:
        status_provider = getattr(source_library, "ingestion_status", None)
        if callable(status_provider):
            return status_provider(local_government=local_government)
        return _fallback_ingestion_status(source_library, local_government=local_government)

    @api_router.get("/sources/review-worklist", tags=["sources"])
    def source_review_worklist(
        _allowed_origin: Annotated[None, Depends(require_allowed_origin)],
        _active_session: Annotated[ActiveSession, Depends(require_reviewer_session)],
        local_government: str | None = None,
        source_type: str | None = None,
        include_metadata_only: bool = True,
        limit: int = Query(default=100, ge=1, le=500),
    ) -> dict[str, Any]:
        worklist_provider = getattr(source_library, "review_worklist", None)
        if callable(worklist_provider):
            return worklist_provider(
                local_government=local_government,
                source_type=source_type,
                include_metadata_only=include_metadata_only,
                limit=limit,
            )
        return _fallback_review_worklist(
            source_library,
            local_government=local_government,
            source_type=source_type,
            include_metadata_only=include_metadata_only,
            limit=limit,
        )

    @api_router.get("/sources/quality-report", tags=["sources"])
    def source_quality_report(
        _allowed_origin: Annotated[None, Depends(require_allowed_origin)],
        _active_session: Annotated[ActiveSession, Depends(require_reviewer_session)],
        local_government: str | None = None,
        source_type: str | None = None,
        readiness: str | None = Query(default=None, max_length=80),
        limit: int = Query(default=100, ge=1, le=500),
    ) -> dict[str, Any]:
        report_provider = getattr(source_library, "quality_report", None)
        if callable(report_provider):
            return report_provider(
                local_government=local_government,
                source_type=source_type,
                readiness=readiness,
                limit=limit,
            )
        return _fallback_quality_report(
            source_library,
            local_government=local_government,
            source_type=source_type,
            readiness=readiness,
            limit=limit,
        )

    @api_router.get("/sources/{source_id}/versions/{source_version_id}/review-packet", tags=["sources"])
    def source_review_packet(
        source_id: str,
        source_version_id: str,
        _allowed_origin: Annotated[None, Depends(require_allowed_origin)],
        _active_session: Annotated[ActiveSession, Depends(require_reviewer_session)],
        sample_limit: int = Query(default=12, ge=1, le=30),
        sample_chars: int = Query(default=4000, ge=500, le=12000),
    ) -> dict[str, Any]:
        packet_provider = getattr(source_library, "review_packet", None)
        try:
            if callable(packet_provider):
                return packet_provider(
                    source_id=source_id,
                    source_version_id=source_version_id,
                    sample_limit=sample_limit,
                    sample_chars=sample_chars,
                )
            return _fallback_source_review_packet(
                source_library,
                source_id=source_id,
                source_version_id=source_version_id,
                sample_limit=sample_limit,
                sample_chars=sample_chars,
            )
        except SourceNotFoundError as exc:
            raise _source_not_found(exc) from exc

    @api_router.get("/sources/{source_id}", tags=["sources"])
    def get_source(source_id: str) -> dict[str, Any]:
        try:
            return jsonable_encoder(source_library.get_source(source_id))
        except SourceNotFoundError as exc:
            raise _source_not_found(exc) from exc

    @api_router.get("/sources/{source_id}/versions", tags=["sources"])
    def get_source_versions(source_id: str) -> dict[str, Any]:
        try:
            items = source_library.list_versions(source_id)
        except SourceNotFoundError as exc:
            raise _source_not_found(exc) from exc
        return {"items": jsonable_encoder(items), "count": len(items)}

    @api_router.post("/sources/{source_id}/review", tags=["sources"])
    def review_source(
        source_id: str,
        payload: SourceReviewPayload,
        _allowed_origin: Annotated[None, Depends(require_allowed_origin)],
        active_session: Annotated[ActiveSession, Depends(require_reviewer_session)],
    ) -> dict[str, Any]:
        try:
            version = source_library.review_source(
                source_id=source_id,
                source_version_id=payload.source_version_id,
                review_status=payload.review_status,
                licence_status=payload.licence_status,
                org_id=str(active_session.org.id),
                reviewer_id=str(active_session.user.id),
                notes=payload.notes,
            )
        except SourceNotFoundError as exc:
            raise _source_not_found(exc) from exc
        return jsonable_encoder(version)

    @api_router.post("/sources/{source_id}/refresh", tags=["sources"])
    def refresh_source(
        source_id: str,
        _allowed_origin: Annotated[None, Depends(require_allowed_origin)],
        active_session: Annotated[ActiveSession, Depends(require_reviewer_session)],
    ) -> dict[str, Any]:
        try:
            result = source_library.refresh_source(
                source_id,
                org_id=str(active_session.org.id),
                reviewer_id=str(active_session.user.id),
            )
        except SourceNotFoundError as exc:
            raise _source_not_found(exc) from exc
        return jsonable_encoder(result)

    @api_router.post("/search/chunks", tags=["search"])
    def search_chunks(
        payload: SearchChunksPayload,
        _allowed_origin: Annotated[None, Depends(require_allowed_origin)],
        _active_session: Annotated[ActiveSession, Depends(get_current_session)],
    ) -> dict[str, Any]:
        query = _required_query(payload.query, payload.q)
        hits = search_service.search_chunks(query, limit=payload.limit)
        return {"items": [_hit_payload(hit) for hit in hits], "count": len(hits)}

    @api_router.post("/search/ask", tags=["search"])
    def search_ask(
        payload: SearchAskPayload,
        _allowed_origin: Annotated[None, Depends(require_allowed_origin)],
        _active_session: Annotated[ActiveSession, Depends(get_current_session)],
    ) -> dict[str, Any]:
        question = _required_query(payload.question, payload.query, payload.q)
        answer = search_service.ask(question, limit=payload.limit)
        traced_answer = _trace_supported_answer(
            answer,
            question=question,
            source_library=source_library,
            model_adapter=governed_model_adapter,
        )
        return _answer_payload(traced_answer)

    return api_router


router = create_sources_router()
