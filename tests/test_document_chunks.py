from __future__ import annotations

from types import SimpleNamespace

import pytest

import draftcheck.domain.documents.chunks as chunking
from draftcheck.domain.documents.chunks import build_document_chunks, search_document_chunks
from draftcheck.domain.sources.models import EmbeddingConfig


def test_build_document_chunks_records_pinned_embedding_metadata(monkeypatch) -> None:
    config = EmbeddingConfig(provider="local-test", model="fixture-embedding-v1", dimension=4)

    def fake_batch_embed(texts: list[str], embedding_config: EmbeddingConfig) -> list[tuple[float, ...]]:
        assert embedding_config == config
        return [tuple(float(index + offset) for offset in range(config.dimension)) for index, _ in enumerate(texts)]

    monkeypatch.setattr(chunking, "_batch_embed", fake_batch_embed)
    page = SimpleNamespace(
        id="page_doc_1",
        document_id="doc_1",
        page_number=1,
        text="Lot area: 450 m2\n\nGarage width: 5.4 m",
        metadata_json={},
    )

    chunks = build_document_chunks(document_id="doc_1", pages=[page], embedding_config=config)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.document_id == "doc_1"
    assert chunk.page_id == "page_doc_1"
    assert chunk.chunk_index == 1
    assert chunk.embedding_provider == "local-test"
    assert chunk.embedding_model == "fixture-embedding-v1"
    assert chunk.embedding_dimension == 4
    assert len(chunk.embedding) == 4
    assert chunk.metadata["evidence_role"] == "project_document"
    assert chunk.metadata["legal_authority"] is False
    assert chunk.metadata["measurement_compliance_ready"] is False


def test_document_chunk_search_returns_project_evidence_without_citation(monkeypatch) -> None:
    config = EmbeddingConfig(provider="local-test", model="fixture-embedding-v1", dimension=4)
    monkeypatch.setattr(
        chunking,
        "_batch_embed",
        lambda texts, _config: [(0.1, 0.2, 0.3, 0.4) for _ in texts],
    )
    page = SimpleNamespace(
        id="page_doc_1",
        document_id="doc_1",
        page_number=1,
        text="Open space: 180 m2\n\nBoundary wall length: 0 m",
        metadata_json={},
    )
    chunks = build_document_chunks(document_id="doc_1", pages=[page], embedding_config=config)

    hits = search_document_chunks(chunks, "boundary wall", embedding_config=config)

    assert len(hits) == 1
    assert "Boundary wall length" in hits[0].chunk.text
    assert not hasattr(hits[0], "citation")
    assert hits[0].chunk.metadata["legal_authority"] is False


def test_document_chunk_embeddings_refuse_mock_provider_in_production(monkeypatch) -> None:
    monkeypatch.setenv("DRAFTCHECK_ENV", "production")
    monkeypatch.setenv("DRAFTCHECK_EMBEDDING_PROVIDER", "stub")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    page = SimpleNamespace(
        id="page_doc_1",
        document_id="doc_1",
        page_number=1,
        text="Front setback: 4.5 m",
        metadata_json={},
    )

    with pytest.raises(RuntimeError, match="Real embeddings required in production"):
        build_document_chunks(
            document_id="doc_1",
            pages=[page],
            embedding_config=EmbeddingConfig(provider="stub", model="fixture", dimension=4),
        )
