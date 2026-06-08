from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from draftcheck_core.database import Base
from draftcheck_core.embeddings import embed_query, store_chunk_embedding
from draftcheck_core.json_utils import to_json
from draftcheck_core.models import SourceChunk, SourceChunkEmbedding
from draftcheck_core.providers import get_embedding_provider
from draftcheck_retrieval.service import RetrievalService
from tests.test_rebuild_source_search_index import _add_chunk


class _FakeEmbeddingResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_openai_embedding_provider_posts_expected_payload(monkeypatch):
    captured: dict = {}

    def fake_urlopen(request, timeout):
        captured["timeout"] = timeout
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["auth"] = request.get_header("Authorization")
        return _FakeEmbeddingResponse(
            {
                "data": [
                    {"index": 1, "embedding": [0.2, 0.3]},
                    {"index": 0, "embedding": [0.1, 0.0]},
                ]
            }
        )

    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-small")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "32")
    monkeypatch.setenv("EMBEDDING_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("draftcheck_core.providers.urlopen", fake_urlopen)

    provider = get_embedding_provider()
    vectors = provider.embed(["front setback", ""])

    assert vectors == [[0.1, 0.0], [0.2, 0.3]]
    assert captured["url"] == "https://api.openai.com/v1/embeddings"
    assert captured["timeout"] == 7
    assert captured["auth"] == "Bearer test-key"
    assert captured["body"] == {
        "input": ["front setback", "missing text"],
        "model": "text-embedding-3-small",
        "encoding_format": "float",
        "dimensions": 32,
    }


def test_openai_embedding_provider_requires_api_key(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required"):
        get_embedding_provider().embed(["front setback"])


def test_store_chunk_embedding_uses_configured_provider_and_model(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    monkeypatch.setenv("EMBEDDING_MODEL", "fixture-mock-v2")
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        chunk_id = _add_chunk(db, "Accepted Setback Policy", "Primary street setback is 4m.")
        chunk = db.get(SourceChunk, chunk_id)
        assert chunk is not None

        embedding = store_chunk_embedding(db, chunk)

    assert embedding.provider == "mock"
    assert embedding.model == "fixture-mock-v2"
    assert embedding.dimensions == 16


def test_json_vector_scores_ignore_other_provider_embeddings(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    monkeypatch.delenv("EMBEDDING_MODEL", raising=False)
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)

    query_vector = embed_query("front setback")
    with Session(engine) as db:
        matching_chunk_id = _add_chunk(db, "Matching Provider Policy", "Primary street setback is 4m.")
        other_chunk_id = _add_chunk(db, "Other Provider Policy", "Garage parking requirement.")
        db.add_all(
            [
                SourceChunkEmbedding(
                    source_chunk_id=matching_chunk_id,
                    source_version_id=db.get(SourceChunk, matching_chunk_id).source_version_id,
                    provider="mock",
                    model="mock-hash-v1",
                    dimensions=len(query_vector),
                    embedding_json=to_json(query_vector),
                ),
                SourceChunkEmbedding(
                    source_chunk_id=other_chunk_id,
                    source_version_id=db.get(SourceChunk, other_chunk_id).source_version_id,
                    provider="other",
                    model="other-model",
                    dimensions=len(query_vector),
                    embedding_json=to_json(query_vector),
                ),
            ]
        )
        db.flush()

        scores = RetrievalService(db)._candidate_chunk_scores_from_json_embeddings(
            query_vector,
            "mock",
            "mock-hash-v1",
            limit=10,
        )

    assert matching_chunk_id in scores
    assert other_chunk_id not in scores
