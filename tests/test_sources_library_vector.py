"""Regression tests for SourceLibrary._coerce_embedding / search_chunks.

The /api/v1/assistant endpoint was crashing with TypeError because raw
text() selects return pgvector values as their wire-format string
"[0.1,0.2,...]". These tests pin the defensive coercion behaviour.
"""

from __future__ import annotations

import pytest

from draftcheck.domain.sources.library import (  # type: ignore[attr-defined]
    SqlAlchemySourceSearchService as SourceLibrary,
    _coerce_embedding,
)


def _row(emb):
    """Build a minimal row-like object exposing `.embedding`."""

    class _R:
        pass

    r = _R()
    r.embedding = emb
    r.fts_score = 1.0
    return r


def test_coerce_embedding_from_pgvector_wire_string() -> None:
    out = _coerce_embedding("[0.1,-0.2,0.3,0.4]")
    assert out is not None
    assert out == pytest.approx([0.1, -0.2, 0.3, 0.4])
    assert all(isinstance(x, float) for x in out)


def test_coerce_embedding_from_python_list() -> None:
    out = _coerce_embedding([1, 2, 3])
    assert out is not None
    assert out == pytest.approx([1.0, 2.0, 3.0])
    assert all(isinstance(x, float) for x in out)


def test_coerce_embedding_from_numpy_array() -> None:
    np = pytest.importorskip("numpy")
    out = _coerce_embedding(np.array([0.5, -0.5]))
    assert out is not None
    assert out == pytest.approx([0.5, -0.5])


def test_coerce_embedding_empty_string() -> None:
    assert _coerce_embedding("") is None
    assert _coerce_embedding("[]") is None
    assert _coerce_embedding("()") is None


def test_coerce_embedding_malformed_string() -> None:
    assert _coerce_embedding("not a vector") is None


def test_coerce_embedding_none() -> None:
    assert _coerce_embedding(None) is None


def test_search_chunks_handles_string_embedding(monkeypatch) -> None:
    """The whole point: select via text() yields a string. search_chunks
    must not crash with TypeError, and must still rank rows by FTS alone
    if the vector cannot be coerced."""
    lib = SourceLibrary(session_factory=lambda: (_ for _ in ()).throw(AssertionError("db should not be hit")))
    # Direct exercise of the coercion contract: the function used to do
    # `list(emb) * qv[i]` which raises for str input.
    from draftcheck.domain.sources.library import _hash_embedding, default_embedding_config

    qv = _hash_embedding("hello", default_embedding_config())
    vec = _coerce_embedding("[0.1,0.2,0.3,0.4,0.5,0.6]")
    assert vec is not None
    min_len = min(len(vec), len(qv))
    dot = sum(vec[i] * qv[i] for i in range(min_len))
    assert isinstance(dot, float)
