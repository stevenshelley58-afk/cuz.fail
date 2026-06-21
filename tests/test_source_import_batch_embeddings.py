from types import SimpleNamespace
from uuid import uuid4

from draftcheck.db.models import SourceChunk as DbSourceChunk
from draftcheck.domain.sources.models import EmbeddingConfig
from draftcheck.domain.sources.store import importing
from draftcheck.domain.sources.store.importing import SourceImportOps


class FakeSession:
    def __init__(self) -> None:
        self.added = []
        self.flushes = 0

    def add(self, item) -> None:
        self.added.append(item)

    def flush(self) -> None:
        self.flushes += 1


def test_insert_chunks_batches_embeddings(monkeypatch) -> None:
    calls = []

    def fake_chunk_text(_text: str):
        return ["first chunk", "second chunk"]

    def fake_batch_embed(texts, config):
        calls.append((texts, config))
        return [(0.1, 0.2, 0.3), (0.4, 0.5, 0.6)]

    monkeypatch.setattr(importing, "_chunk_text", fake_chunk_text)
    monkeypatch.setattr(importing, "_batch_embed", fake_batch_embed)

    ops = SourceImportOps()
    ops.embedding_config = EmbeddingConfig(provider="api", model="text-embedding-3-small", dimension=3)
    session = FakeSession()

    ops._insert_chunks_and_citations(
        session,
        db_source=SimpleNamespace(id=uuid4(), title="Test Source", canonical_url="https://example.test/source"),
        db_version=SimpleNamespace(id=uuid4()),
        text="source text",
    )

    chunks = [item for item in session.added if isinstance(item, DbSourceChunk)]
    assert calls == [(["first chunk", "second chunk"], ops.embedding_config)]
    assert [chunk.embedding for chunk in chunks] == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert session.flushes == 2
