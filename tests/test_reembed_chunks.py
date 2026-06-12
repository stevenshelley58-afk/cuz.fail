from __future__ import annotations

from draftcheck.domain.sources.library import _batch_embed, _embed, default_embedding_config
from scripts.reembed_chunks import BAD_PROVIDERS, ensure_apply_can_write_real_embeddings, pinned_config


def test_embedding_guard_honors_draftcheck_env_production(monkeypatch) -> None:
    monkeypatch.setenv("DRAFTCHECK_ENV", "production")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    config = default_embedding_config()

    try:
        _embed("fixture", config)
    except RuntimeError as exc:
        assert "Real embeddings required in production" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("production hash embedding fallback was not blocked")


def test_batch_embedding_guard_blocks_mock_in_production(monkeypatch) -> None:
    monkeypatch.setenv("DRAFTCHECK_ENV", "production")
    monkeypatch.setenv("DRAFTCHECK_EMBEDDING_PROVIDER", "stub")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    config = default_embedding_config()

    try:
        _batch_embed(["fixture"], config)
    except RuntimeError as exc:
        assert "Real embeddings required in production" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("production batch hash embedding fallback was not blocked")


def test_pinned_config_reads_embedding_env(monkeypatch) -> None:
    monkeypatch.setenv("DRAFTCHECK_EMBEDDING_PROVIDER", "api")
    monkeypatch.setenv("DRAFTCHECK_EMBEDDING_MODEL", "text-embedding-3-small")
    monkeypatch.setenv("DRAFTCHECK_EMBEDDING_DIMENSION", "1536")

    assert pinned_config() == {
        "provider": "api",
        "model": "text-embedding-3-small",
        "dimension": 1536,
    }
    assert {"stub", "hash", "mock"} == set(BAD_PROVIDERS)


def test_reembed_apply_refuses_to_stamp_api_without_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    try:
        ensure_apply_can_write_real_embeddings(
            {"provider": "api", "model": "text-embedding-3-small", "dimension": 1536}
        )
    except SystemExit as exc:
        assert "refusing to label hash fallback vectors" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("api repair without OPENAI_API_KEY was not blocked")


def test_reembed_apply_refuses_mock_provider(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    try:
        ensure_apply_can_write_real_embeddings(
            {"provider": "stub", "model": "text-embedding-3-small", "dimension": 1536}
        )
    except SystemExit as exc:
        assert "mock embedding provider" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("mock repair provider was not blocked")
