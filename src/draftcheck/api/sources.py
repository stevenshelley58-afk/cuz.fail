"""Standalone V3 sources and search router.

The coordinator mounts this router under `/api/v1`; this file deliberately does
not edit `draftcheck.api.v1`.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field, field_validator

from draftcheck.ai import InMemoryJobTraceStore, LocalDeterministicModelAdapter, ModelAdapter, ModelRequest
from draftcheck.api.auth import get_current_session, require_allowed_origin, require_reviewer_session
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
    library: InMemorySourceLibrary | None = None,
    model_adapter: ModelAdapter | None = None,
) -> APIRouter:
    source_library = library or InMemorySourceLibrary()
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
        _active_session: Annotated[ActiveSession, Depends(require_reviewer_session)],
    ) -> dict[str, Any]:
        try:
            result = source_library.refresh_source(source_id)
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
