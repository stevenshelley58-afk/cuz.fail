"""Embedding job functions for Stage 4+.

Generates and stores vector embeddings for SourceChunk rows.
Embeddings are pinned to a single provider/model/dimension via env config
(default: 'api' / 'text-embedding-3-small' / 1536-dim, cosine, HNSW).

Phase 5 wires procrastinate enqueueing.  For now these are plain async
functions called from tests and the ingestion pipeline.
"""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck.db.models import SourceChunk


# ---------------------------------------------------------------------------
# Default pinned embedding configuration (override via env in config.py)
# ---------------------------------------------------------------------------

DEFAULT_EMBEDDING_PROVIDER = "api"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_DIMENSION = 1536


# ---------------------------------------------------------------------------
# Provider abstraction
# ---------------------------------------------------------------------------


class EmbeddingProvider:
    """Minimal interface for an embedding backend.

    Concrete implementations live alongside the provider they wrap
    (openai, mock, etc.).  This base class raises NotImplementedError so
    static analysis tools can see the expected signature.
    """

    provider: str = "base"
    model: str = "base"
    dimension: int = DEFAULT_EMBEDDING_DIMENSION

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        raise NotImplementedError


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic stub used in tests and Stage 3/4 development.

    Returns a unit vector seeded from the SHA-256 of each text string so
    that identical texts always produce identical embeddings.
    """

    provider = "mock"
    model = "mock-embedding-v0"

    def __init__(self, dimension: int = DEFAULT_EMBEDDING_DIMENSION) -> None:
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            # Extend digest bytes cyclically to fill dimension floats.
            raw: list[float] = []
            i = 0
            while len(raw) < self.dimension:
                raw.append(digest[i % len(digest)] / 255.0)
                i += 1
            # Normalise to unit length (cosine similarity assumes unit vectors).
            magnitude = sum(x * x for x in raw) ** 0.5 or 1.0
            results.append([x / magnitude for x in raw])
        return results


# ---------------------------------------------------------------------------
# Public job functions
# ---------------------------------------------------------------------------


async def embed_chunk(
    chunk_id: UUID,
    provider: EmbeddingProvider,
    session: Session,
) -> list[float]:
    """Compute and persist the embedding for a single SourceChunk.

    Writes `embedding`, `embedding_provider`, `embedding_model`, and
    `embedding_dimension` onto the chunk row, then flushes.

    Returns the embedding vector.
    """
    chunk = session.get(SourceChunk, chunk_id)
    if chunk is None:
        raise ValueError(f"SourceChunk {chunk_id} not found")

    vectors = provider.embed([chunk.text])
    vector = vectors[0]

    chunk.embedding = vector
    chunk.embedding_provider = provider.provider
    chunk.embedding_model = provider.model
    chunk.embedding_dimension = len(vector)
    session.flush()

    return vector


async def embed_source_version(
    source_version_id: UUID,
    provider: EmbeddingProvider,
    session: Session,
    batch_size: int = 64,
) -> dict[str, Any]:
    """Embed all un-embedded chunks for a source version.

    Processes chunks in batches of `batch_size`.  Skips chunks that
    already have a non-null embedding from the same provider + model.

    Returns a summary dict: {"embedded": int, "skipped": int}.
    """
    stmt = (
        select(SourceChunk)
        .where(
            SourceChunk.source_version_id == source_version_id,
        )
        .order_by(SourceChunk.chunk_index)
    )
    chunks: list[SourceChunk] = list(session.scalars(stmt))

    embedded = 0
    skipped = 0

    to_embed = [
        c
        for c in chunks
        if c.embedding is None
        or c.embedding_provider != provider.provider
        or c.embedding_model != provider.model
    ]
    skipped = len(chunks) - len(to_embed)

    for i in range(0, len(to_embed), batch_size):
        batch = to_embed[i : i + batch_size]
        texts = [c.text for c in batch]
        vectors = provider.embed(texts)
        for chunk, vector in zip(batch, vectors):
            chunk.embedding = vector
            chunk.embedding_provider = provider.provider
            chunk.embedding_model = provider.model
            chunk.embedding_dimension = len(vector)
        session.flush()
        embedded += len(batch)

    return {"embedded": embedded, "skipped": skipped}


async def generate_source_chunk_embeddings(
    source_version_id: UUID,
    session: Session,
    provider: EmbeddingProvider | None = None,
    batch_size: int = 64,
) -> dict[str, Any]:
    """Generate embeddings for all un-embedded chunks of a source version.

    Convenience wrapper around ``embed_source_version`` that supplies a
    ``MockEmbeddingProvider`` when no provider is given (useful in tests and
    CI where no real embedding API is available).

    Returns a summary dict: ``{"embedded": int, "skipped": int}``.
    """
    if provider is None:
        provider = MockEmbeddingProvider()
    return await embed_source_version(source_version_id, provider, session, batch_size)
