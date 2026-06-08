"""Tests for the grounded conversational assistant (GPT-5.5 wiring)."""

from __future__ import annotations

from datetime import datetime, timezone

from draftcheck_core.providers import (
    MockChatProvider,
    OpenAIChatProvider,
    get_chat_provider,
)
from draftcheck_retrieval.chat import GroundedChatService
from draftcheck_shared.schemas import Citation, SourceChunkResult, StandardAnswer


def _citation() -> Citation:
    return Citation(
        source_document_id="d1",
        source_title="Residential Design Codes Volume 1",
        source_version_id="v1",
        clause_id="5.1.3",
        retrieved_at=datetime.now(timezone.utc),
        quote="Maximum site cover is 50%.",
    )


def _chunk() -> SourceChunkResult:
    return SourceChunkResult(chunk_id="c1", text="Maximum site cover is 50%.", score=0.9, citation=_citation())


class _FakeLiveProvider:
    name = "fake"
    model = "fake-frontier-1"
    is_live = True

    def __init__(self, text: str = "LLM ANSWER", raises: bool = False) -> None:
        self._text = text
        self._raises = raises

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if self._raises:
            raise RuntimeError("simulated model failure")
        return self._text


def _standard_answer() -> StandardAnswer:
    return StandardAnswer(
        answer="Deterministic cited answer.",
        citations=[_citation()],
        source_version_ids=["v1"],
        assumptions=[],
        missing_information=[],
        confidence=0.5,
        human_review_required=True,
        risk_level="medium",
        status="needs_human_review",
    )


# --- provider selection -----------------------------------------------------


def test_get_chat_provider_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert isinstance(get_chat_provider(), MockChatProvider)


def test_get_chat_provider_openai_when_configured(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_MODEL", "gpt-5.5")
    provider = get_chat_provider()
    assert isinstance(provider, OpenAIChatProvider)
    assert provider.model == "gpt-5.5"
    assert provider.is_live is True


def test_get_chat_provider_openai_without_key_falls_back_to_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert isinstance(get_chat_provider(), MockChatProvider)


# --- grounded chat behaviour ------------------------------------------------


def test_grounded_uses_live_model_and_returns_citations(monkeypatch):
    provider = _FakeLiveProvider("Grounded answer from sources.")
    monkeypatch.setattr("draftcheck_retrieval.chat.get_chat_provider", lambda *a, **k: provider)
    service = GroundedChatService(db=None)
    monkeypatch.setattr(service.retrieval, "search", lambda *a, **k: [_chunk()])

    reply = service.reply("what is the maximum site cover")

    assert reply.grounded is True
    assert reply.answer == "Grounded answer from sources."
    assert len(reply.citations) == 1
    assert reply.provider == "fake"
    assert reply.used_fallback is False


def test_ungrounded_uses_general_model_without_citations(monkeypatch):
    provider = _FakeLiveProvider("Hi! Here's how DraftCheck works.")
    monkeypatch.setattr("draftcheck_retrieval.chat.get_chat_provider", lambda *a, **k: provider)
    service = GroundedChatService(db=None)
    monkeypatch.setattr(service.retrieval, "search", lambda *a, **k: [])

    reply = service.reply("hi")

    assert reply.grounded is False
    assert reply.answer == "Hi! Here's how DraftCheck works."
    assert reply.citations == []
    assert reply.used_fallback is False


def test_live_model_failure_falls_back_to_deterministic(monkeypatch):
    provider = _FakeLiveProvider(raises=True)
    monkeypatch.setattr("draftcheck_retrieval.chat.get_chat_provider", lambda *a, **k: provider)
    service = GroundedChatService(db=None)
    monkeypatch.setattr(service.retrieval, "search", lambda *a, **k: [_chunk()])
    monkeypatch.setattr(service.retrieval, "ask", lambda *a, **k: _standard_answer())

    reply = service.reply("maximum site cover")

    assert reply.answer == "Deterministic cited answer."
    assert reply.grounded is True
    assert reply.used_fallback is True


def test_mock_provider_ungrounded_returns_helpful_general_answer(monkeypatch):
    monkeypatch.setattr("draftcheck_retrieval.chat.get_chat_provider", lambda *a, **k: MockChatProvider())
    service = GroundedChatService(db=None)
    monkeypatch.setattr(service.retrieval, "search", lambda *a, **k: [])

    reply = service.reply("hello there")

    assert reply.grounded is False
    assert reply.used_fallback is True
    assert "DraftCheck works" in reply.answer
    # Never leak provider/config internals into the user-facing answer.
    assert "not configured" not in reply.answer.lower()


def test_mock_provider_grounded_uses_deterministic_cited_answer(monkeypatch):
    monkeypatch.setattr("draftcheck_retrieval.chat.get_chat_provider", lambda *a, **k: MockChatProvider())
    service = GroundedChatService(db=None)
    monkeypatch.setattr(service.retrieval, "search", lambda *a, **k: [_chunk()])
    monkeypatch.setattr(service.retrieval, "ask", lambda *a, **k: _standard_answer())

    reply = service.reply("maximum site cover")

    assert reply.answer == "Deterministic cited answer."
    assert reply.grounded is True
    assert reply.used_fallback is True
    assert len(reply.citations) == 1
