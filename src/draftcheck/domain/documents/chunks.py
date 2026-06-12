"""Document chunking and retrieval helpers.

Document chunks are project evidence for drawings/uploads. They are never
regulatory authority and must not be mixed into cite-or-refuse source answers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Protocol
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from draftcheck.db.models import DocumentChunk as OrmDocumentChunk
from draftcheck.db.models import DocumentPage as OrmDocumentPage
from draftcheck.domain.sources.library import (
    _batch_embed,
    _coerce_embedding,
    default_embedding_config,
)
from draftcheck.domain.sources.models import EmbeddingConfig


MAX_DOCUMENT_CHUNK_CHARS = 1200
TOKEN_RE = re.compile(r"[a-z0-9]+")


class PageLike(Protocol):
    id: Any
    document_id: Any
    page_number: int
    text: str | None
    metadata_json: dict[str, Any]


@dataclass(frozen=True)
class DocumentChunk:
    id: str
    document_id: str
    page_id: str | None
    page_number: int | None
    chunk_index: int
    text: str
    text_sha256: str
    token_count: int
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    embedding: tuple[float, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentChunkSearchHit:
    chunk: DocumentChunk
    score: float


def build_document_chunks(
    *,
    document_id: str,
    pages: Iterable[PageLike],
    embedding_config: EmbeddingConfig | None = None,
) -> tuple[DocumentChunk, ...]:
    """Create embedded document chunks from parsed pages.

    Uses the same pinned embedding provider/model/dimension config as source
    chunks. In production, the imported embedding helper refuses mock/hash
    embeddings when real embeddings are not configured.
    """

    config = embedding_config or default_embedding_config()
    chunk_inputs: list[tuple[PageLike, str]] = []
    for page in pages:
        for text in chunk_text(page.text or ""):
            chunk_inputs.append((page, text))

    if not chunk_inputs:
        return ()

    vectors = _batch_embed([text for _, text in chunk_inputs], config)
    chunks: list[DocumentChunk] = []
    for index, ((page, text), vector) in enumerate(zip(chunk_inputs, vectors, strict=True), start=1):
        page_id = str(page.id) if page.id is not None else None
        chunks.append(
            DocumentChunk(
                id=_chunk_id(document_id, index, text),
                document_id=document_id,
                page_id=page_id,
                page_number=page.page_number,
                chunk_index=index,
                text=text,
                text_sha256=sha256(text.encode("utf-8")).hexdigest(),
                token_count=len(TOKEN_RE.findall(text.lower())),
                embedding_provider=config.provider,
                embedding_model=config.model,
                embedding_dimension=config.dimension,
                embedding=tuple(vector),
                metadata={
                    "page_number": page.page_number,
                    "evidence_role": "project_document",
                    "legal_authority": False,
                    "measurement_compliance_ready": False,
                    "measurement_readiness_reason": (
                        "document chunks are project evidence; measurements require promotion"
                    ),
                },
            )
        )
    return tuple(chunks)


def write_document_chunks(
    session: Session,
    *,
    document_id: UUID,
    pages: Iterable[OrmDocumentPage],
    embedding_config: EmbeddingConfig | None = None,
) -> list[OrmDocumentChunk]:
    """Persist embedded chunks for a parsed document.

    Existing chunks for the document are replaced so reparses do not leave stale
    embeddings behind. This helper deliberately writes only document evidence
    chunks; source citation tables are untouched.
    """

    session.execute(delete(OrmDocumentChunk).where(OrmDocumentChunk.document_id == document_id))
    built = build_document_chunks(
        document_id=str(document_id),
        pages=pages,
        embedding_config=embedding_config,
    )
    rows: list[OrmDocumentChunk] = []
    for chunk in built:
        row = OrmDocumentChunk(
            document_id=document_id,
            page_id=UUID(chunk.page_id) if chunk.page_id else None,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            token_count=chunk.token_count,
            embedding_provider=chunk.embedding_provider,
            embedding_model=chunk.embedding_model,
            embedding_dimension=chunk.embedding_dimension,
            embedding=list(chunk.embedding),
            metadata_json={
                **chunk.metadata,
                "text_sha256": chunk.text_sha256,
            },
        )
        session.add(row)
        rows.append(row)
    session.flush()
    return rows


def search_document_chunks(
    chunks: Iterable[DocumentChunk],
    query: str,
    *,
    limit: int = 8,
    embedding_config: EmbeddingConfig | None = None,
) -> tuple[DocumentChunkSearchHit, ...]:
    """Rank document chunks as project evidence.

    This is intentionally separate from source retrieval; hits have no
    regulatory citation and cannot support legal answers by themselves.
    """

    query_tokens = _tokens(query)
    if not query_tokens:
        return ()

    config = embedding_config or default_embedding_config()
    query_vector = _batch_embed([query], config)[0]
    hits: list[DocumentChunkSearchHit] = []
    for chunk in chunks:
        text_tokens = _tokens(chunk.text)
        overlap = query_tokens & text_tokens
        if not overlap and query.lower() not in chunk.text.lower():
            continue
        lexical_score = len(overlap) / max(len(query_tokens), 1)
        if query.lower() in chunk.text.lower():
            lexical_score += 0.25
        vector_score = _cosine(_coerce_embedding(chunk.embedding), list(query_vector))
        score = (0.65 * lexical_score) + (0.35 * max(0.0, vector_score))
        hits.append(DocumentChunkSearchHit(chunk=chunk, score=score))
    hits.sort(key=lambda hit: (-hit.score, hit.chunk.document_id, hit.chunk.chunk_index))
    return tuple(hits[:limit])


def search_persisted_document_chunks(
    session: Session,
    *,
    project_id: UUID,
    query: str,
    limit: int = 8,
    embedding_config: EmbeddingConfig | None = None,
) -> tuple[DocumentChunkSearchHit, ...]:
    """Search persisted document chunks for one project."""

    from draftcheck.db.models import Document

    rows = session.execute(
        select(OrmDocumentChunk, OrmDocumentPage.page_number)
        .join(Document, Document.id == OrmDocumentChunk.document_id)
        .outerjoin(OrmDocumentPage, OrmDocumentPage.id == OrmDocumentChunk.page_id)
        .where(Document.project_id == project_id)
        .order_by(OrmDocumentChunk.document_id, OrmDocumentChunk.chunk_index)
    ).all()
    chunks = (
        _domain_chunk_from_row(row, page_number=page_number)
        for row, page_number in rows
    )
    return search_document_chunks(
        chunks,
        query,
        limit=limit,
        embedding_config=embedding_config,
    )


def chunk_text(text: str, *, max_chars: int = MAX_DOCUMENT_CHUNK_CHARS) -> tuple[str, ...]:
    normalized = text.strip()
    if not normalized:
        return ()

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs or [normalized]:
        parts = _split_oversized(paragraph, max_chars=max_chars)
        for part in parts:
            if not current:
                current = part
                continue
            if len(current) + len(part) + 2 <= max_chars:
                current = f"{current}\n\n{part}"
            else:
                chunks.append(current)
                current = part
    if current:
        chunks.append(current)
    return tuple(chunks)


def _split_oversized(text: str, *, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    parts: list[str] = []
    current = ""
    for word in words:
        if len(word) > max_chars:
            if current:
                parts.append(current)
                current = ""
            parts.extend(word[i : i + max_chars] for i in range(0, len(word), max_chars))
            continue
        if not current:
            current = word
            continue
        if len(current) + len(word) + 1 <= max_chars:
            current = f"{current} {word}"
        else:
            parts.append(current)
            current = word
    if current:
        parts.append(current)
    return parts


def _domain_chunk_from_row(row: OrmDocumentChunk, *, page_number: int | None) -> DocumentChunk:
    metadata = dict(row.metadata_json or {})
    return DocumentChunk(
        id=str(row.id),
        document_id=str(row.document_id),
        page_id=str(row.page_id) if row.page_id else None,
        page_number=page_number,
        chunk_index=row.chunk_index,
        text=row.text,
        text_sha256=str(metadata.get("text_sha256") or sha256(row.text.encode("utf-8")).hexdigest()),
        token_count=row.token_count,
        embedding_provider=row.embedding_provider,
        embedding_model=row.embedding_model,
        embedding_dimension=row.embedding_dimension,
        embedding=tuple(_coerce_embedding(row.embedding) or ()),
        metadata=metadata,
    )


def _tokens(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


def _cosine(left: list[float] | None, right: list[float]) -> float:
    if not left or not right:
        return 0.0
    count = min(len(left), len(right))
    if count <= 0:
        return 0.0
    dot = sum(left[index] * right[index] for index in range(count))
    left_norm = sum(value * value for value in left[:count]) ** 0.5
    right_norm = sum(value * value for value in right[:count]) ** 0.5
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _chunk_id(document_id: str, index: int, text: str) -> str:
    digest = sha256(f"{document_id}:{index}:{text}".encode("utf-8")).hexdigest()
    return f"dchk_{digest[:16]}"
