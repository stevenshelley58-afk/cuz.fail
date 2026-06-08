from __future__ import annotations

import math
from typing import Iterable

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from draftcheck_core.json_utils import from_json, to_json
from draftcheck_core.models import SourceChunk, SourceChunkEmbedding
from draftcheck_core.providers import (
    MOCK_EMBEDDING_DIMENSIONS,
    embedding_model_name,
    embedding_provider_name,
    get_embedding_provider,
)

EMBEDDING_PROVIDER = "mock"
EMBEDDING_MODEL = "mock-hash-v1"
EMBEDDING_DIMENSIONS = MOCK_EMBEDDING_DIMENSIONS


def embed_query(text_value: str) -> list[float]:
    return get_embedding_provider().embed([text_value])[0]


def store_chunk_embedding(db: Session, chunk: SourceChunk) -> SourceChunkEmbedding:
    provider = embedding_provider_name()
    model = embedding_model_name()
    vector = get_embedding_provider().embed([_chunk_embedding_text(chunk)])[0]
    existing = db.scalar(
        select(SourceChunkEmbedding).where(
            SourceChunkEmbedding.source_chunk_id == chunk.id,
            SourceChunkEmbedding.provider == provider,
            SourceChunkEmbedding.model == model,
        )
    )
    if existing:
        existing.source_version_id = chunk.source_version_id
        existing.dimensions = len(vector)
        existing.embedding_json = to_json(vector)
        db.flush()
        chunk.embedding_ref = f"source_chunk_embeddings:{existing.id}"
        _store_pgvector_embedding(db, existing.id, vector)
        return existing

    embedding = SourceChunkEmbedding(
        source_chunk_id=chunk.id,
        source_version_id=chunk.source_version_id,
        provider=provider,
        model=model,
        dimensions=len(vector),
        embedding_json=to_json(vector),
    )
    db.add(embedding)
    db.flush()
    chunk.embedding_ref = f"source_chunk_embeddings:{embedding.id}"
    _store_pgvector_embedding(db, embedding.id, vector)
    return embedding


def rebuild_source_chunk_embeddings(db: Session, source_version_id: str | None = None) -> dict[str, int]:
    stmt = select(SourceChunk).order_by(SourceChunk.source_version_id, SourceChunk.id)
    if source_version_id:
        stmt = stmt.where(SourceChunk.source_version_id == source_version_id)

    scanned = 0
    created = 0
    refreshed = 0
    provider = embedding_provider_name()
    model = embedding_model_name()
    for chunk in db.scalars(stmt):
        scanned += 1
        before = db.scalar(
            select(SourceChunkEmbedding.id).where(
                SourceChunkEmbedding.source_chunk_id == chunk.id,
                SourceChunkEmbedding.provider == provider,
                SourceChunkEmbedding.model == model,
            )
        )
        store_chunk_embedding(db, chunk)
        if before:
            refreshed += 1
        else:
            created += 1

    db.flush()
    return {"scanned": scanned, "created": created, "refreshed": refreshed}


def cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    left_values = list(left)
    right_values = list(right)
    if len(left_values) != len(right_values) or not left_values:
        return 0.0

    dot = sum(left * right for left, right in zip(left_values, right_values, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left_values))
    right_norm = math.sqrt(sum(value * value for value in right_values))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def embedding_from_json(value: str | None) -> list[float]:
    parsed = from_json(value, [])
    if not isinstance(parsed, list):
        return []
    vector: list[float] = []
    for item in parsed:
        try:
            vector.append(float(item))
        except (TypeError, ValueError):
            return []
    return vector


def pgvector_literal(vector: Iterable[float]) -> str:
    return "[" + ",".join(f"{float(value):.8f}" for value in vector) + "]"


def _chunk_embedding_text(chunk: SourceChunk) -> str:
    return " ".join(value for value in [chunk.heading or "", chunk.text] if value)


def _store_pgvector_embedding(db: Session, embedding_id: str, vector: list[float]) -> None:
    if db.get_bind().dialect.name == "sqlite" or len(vector) != MOCK_EMBEDDING_DIMENSIONS:
        return
    try:
        db.execute(
            text(
                """
                update source_chunk_embeddings
                set embedding_vector = CAST(:embedding AS vector)
                where id = :embedding_id
                """
            ),
            {"embedding_id": embedding_id, "embedding": pgvector_literal(vector)},
        )
    except Exception:
        # JSON fallback remains available; migrations/readiness should surface extension issues.
        return
