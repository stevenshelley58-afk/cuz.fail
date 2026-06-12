"""Deterministic unit tests for assistant chat quality (Phases 1–4).

These tests run without a live provider and without a database — all
assertions are on helper functions and the mock-provider API path.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from draftcheck.api.main import create_app
from draftcheck.api.sources import (
    AssistantPayload,
    AssistantTurn,
    _ASSISTANT_MAX_CONTEXT_CHUNKS,
    _ASSISTANT_HISTORY_MAX_TURNS,
    _ASSISTANT_HISTORY_MAX_CHARS,
    _build_grounded_response,
    _build_retrieval_query,
    _filter_relevant_hits,
    _parse_cited_indices,
)
from draftcheck.api.auth import get_current_session
from draftcheck.domain.identity import ActiveSession, InMemoryIdentityStore
from draftcheck.domain.sources import LicenceStatus, SourceSearchHit, SourceReviewStatus
from draftcheck.domain.sources.models import SourceChunk, SourceCitation, SourceVersion

ORIGIN_HEADERS = {"origin": "http://localhost:5173"}

_EPOCH = datetime(2020, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_hit(score: float, index: int = 0) -> SourceSearchHit:
    version = SourceVersion(
        id=f"ver-{index}",
        source_id=f"src-{index}",
        version_label="v1",
        sha256="abc123",
        storage_path="/tmp/test",
        licence_status=LicenceStatus.OPEN,
        review_status=SourceReviewStatus.APPROVED,
        fetched_at=_EPOCH,
    )
    chunk = SourceChunk(
        id=f"chunk-{index}",
        source_id=f"src-{index}",
        source_version_id=f"ver-{index}",
        ordinal=index,
        text=f"Text for chunk {index}",
        text_sha256="sha256",
        citation_id=f"cit-{index}",
        embedding_provider="test",
        embedding_model="test-model",
        embedding_dimension=4,
        embedding=(0.1, 0.2, 0.3, 0.4),
    )
    citation = SourceCitation(
        id=f"cit-{index}",
        source_id=f"src-{index}",
        source_version_id=f"ver-{index}",
        chunk_id=f"chunk-{index}",
        source_title=f"Source {index}",
        locator=f"clause-{index}",
        quote=f"Quote {index}",
    )
    return SourceSearchHit(chunk=chunk, citation=citation, version=version, score=score)


def _authenticated_client() -> TestClient:
    test_app = create_app()
    store = InMemoryIdentityStore()
    org = store.get_or_create_org(slug="fixture")
    user = store.get_or_create_user(org=org, email="owner@example.test")
    session_issue = store.create_session(user=user, org=org)
    test_app.dependency_overrides[get_current_session] = lambda: ActiveSession(
        session=session_issue.session,
        user=session_issue.user,
        org=session_issue.org,
    )
    return TestClient(test_app, headers=ORIGIN_HEADERS)


# ---------------------------------------------------------------------------
# Phase 1 — Retrieval filtering
# ---------------------------------------------------------------------------

class TestFilterRelevantHits:
    def test_empty_input_returns_empty(self):
        assert _filter_relevant_hits(()) == ()

    def test_drops_hits_below_absolute_floor(self):
        hits = (_make_hit(0.01, 0), _make_hit(0.02, 1))
        result = _filter_relevant_hits(hits)
        assert result == ()

    def test_drops_hits_below_relative_floor(self):
        # top = 0.8, threshold = max(0.15, 0.35*0.8) = max(0.15, 0.28) = 0.28
        hits = (_make_hit(0.80, 0), _make_hit(0.30, 1), _make_hit(0.20, 2))
        result = _filter_relevant_hits(hits)
        assert len(result) == 2
        assert result[0].score == 0.80
        assert result[1].score == 0.30

    def test_caps_at_max_context_chunks(self):
        hits = tuple(_make_hit(1.0, i) for i in range(10))
        result = _filter_relevant_hits(hits)
        assert len(result) == _ASSISTANT_MAX_CONTEXT_CHUNKS

    def test_generic_greeting_would_filter_to_zero(self):
        # Simulate very low lexical overlap scores (e.g. "hello" hits a chunk with "what")
        hits = (_make_hit(0.05, 0), _make_hit(0.04, 1))
        result = _filter_relevant_hits(hits)
        assert result == ()

    def test_specific_query_keeps_relevant_hits(self):
        # High-score hits survive
        hits = (_make_hit(0.85, 0), _make_hit(0.75, 1), _make_hit(0.60, 2))
        result = _filter_relevant_hits(hits)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Phase 2 — Citation parsing
# ---------------------------------------------------------------------------

class TestStripReasoning:
    def test_removes_think_block(self):
        from draftcheck.api.sources import _strip_reasoning
        assert _strip_reasoning("<think>internal musing</think>\nThe setback is 6 m.") == "The setback is 6 m."

    def test_removes_multiple_blocks_case_insensitive(self):
        from draftcheck.api.sources import _strip_reasoning
        assert _strip_reasoning("<THINK>a</THINK>x<think>b</think>y") == "xy"

    def test_unterminated_think_drops_tail(self):
        from draftcheck.api.sources import _strip_reasoning
        assert _strip_reasoning("Answer first. <think>never closed") == "Answer first."

    def test_plain_answer_untouched(self):
        from draftcheck.api.sources import _strip_reasoning
        assert _strip_reasoning("Plain answer [1].") == "Plain answer [1]."


class TestParseCitedIndices:
    def test_simple_marker(self):
        assert _parse_cited_indices("See [1] for details.") == frozenset({1})

    def test_multiple_markers(self):
        assert _parse_cited_indices("See [1] and [3].") == frozenset({1, 3})

    def test_comma_separated_in_brackets(self):
        assert _parse_cited_indices("Sources [1, 2] apply.") == frozenset({1, 2})

    def test_consecutive_brackets(self):
        assert _parse_cited_indices("Both [1][2] apply.") == frozenset({1, 2})

    def test_no_markers(self):
        assert _parse_cited_indices("No citations here.") == frozenset()

    def test_ignores_non_numeric(self):
        # [abc] is not a citation marker
        assert _parse_cited_indices("[abc] and [1]") == frozenset({1})


class TestBuildGroundedResponse:
    def test_single_citation_renumbered(self):
        hits = (_make_hit(0.9, 0), _make_hit(0.8, 1), _make_hit(0.7, 2))
        answer = "The rule is in [3] for this case."
        rewritten, citations, citation_map, grounded = _build_grounded_response(answer, hits)
        assert grounded is True
        assert len(citations) == 1
        assert len(citation_map) == 1
        assert citation_map[0]["marker"] == 1
        assert "[1]" in rewritten
        assert "[3]" not in rewritten

    def test_two_of_five_hits_cited(self):
        hits = tuple(_make_hit(0.9 - i * 0.05, i) for i in range(5))
        answer = "Primary [1] and also [3] are relevant."
        rewritten, citations, citation_map, grounded = _build_grounded_response(answer, hits)
        assert grounded is True
        assert len(citations) == 2
        assert len(citation_map) == 2
        # [1] stays [1], [3] becomes [2]
        assert "[1]" in rewritten
        assert "[2]" in rewritten
        assert "[3]" not in rewritten

    def test_no_citations_returns_ungrounded(self):
        hits = (_make_hit(0.9, 0),)
        answer = "General knowledge answer with no inline citations."
        rewritten, citations, citation_map, grounded = _build_grounded_response(answer, hits)
        assert grounded is False
        assert citations == []
        assert citation_map == []
        assert rewritten == answer

    def test_out_of_range_marker_dropped(self):
        hits = (_make_hit(0.9, 0), _make_hit(0.8, 1))
        answer = "See [5] which is out of range."
        rewritten, citations, citation_map, grounded = _build_grounded_response(answer, hits)
        assert grounded is False
        assert citations == []

    def test_empty_hits_with_citation_marker(self):
        answer = "See [1] for details."
        rewritten, citations, citation_map, grounded = _build_grounded_response(answer, ())
        assert grounded is False
        assert citations == []

    def test_citation_map_markers_sequential(self):
        hits = tuple(_make_hit(0.9 - i * 0.05, i) for i in range(4))
        answer = "Rules [2] and [4] apply here."
        _, citations, citation_map, grounded = _build_grounded_response(answer, hits)
        assert grounded is True
        markers = [e["marker"] for e in citation_map]
        assert markers == sorted(markers)
        assert markers == [1, 2]


# ---------------------------------------------------------------------------
# Phase 3 — Retrieval query with history
# ---------------------------------------------------------------------------

class TestBuildRetrievalQuery:
    def test_no_history_returns_question(self):
        assert _build_retrieval_query("what is R20?", []) == "what is R20?"

    def test_prepends_last_user_turn(self):
        history = [
            AssistantTurn(role="user", content="I'm in Stirling, R20 zone"),
            AssistantTurn(role="assistant", content="Got it — R20 in Stirling."),
        ]
        result = _build_retrieval_query("what's my rear setback?", history)
        assert "R20" in result
        assert "rear setback" in result

    def test_skips_assistant_turns_for_context(self):
        history = [
            AssistantTurn(role="assistant", content="I should not appear"),
            AssistantTurn(role="user", content="council is Stirling"),
        ]
        result = _build_retrieval_query("setback?", history)
        assert "Stirling" in result
        assert "should not appear" not in result


# ---------------------------------------------------------------------------
# Phase 4 — History capping via AssistantPayload validator
# ---------------------------------------------------------------------------

class TestAssistantPayloadHistoryCap:
    def test_caps_at_max_turns(self):
        turns = [AssistantTurn(role="user", content=f"q{i}") for i in range(20)]
        payload = AssistantPayload(message="hello", history=turns)
        assert len(payload.history) <= _ASSISTANT_HISTORY_MAX_TURNS

    def test_caps_at_max_chars(self):
        # Each turn is 700 chars; 10 turns = 7000 > 6000 limit
        long_content = "x" * 700
        turns = [AssistantTurn(role="user", content=long_content) for _ in range(10)]
        payload = AssistantPayload(message="hello", history=turns)
        total = sum(len(t.content) for t in payload.history)
        assert total <= _ASSISTANT_HISTORY_MAX_CHARS

    def test_empty_history_accepted(self):
        payload = AssistantPayload(message="hello")
        assert payload.history == []


# ---------------------------------------------------------------------------
# Integration — mock provider path returns correct shape
# ---------------------------------------------------------------------------

class TestAssistantEndpointShape:
    def test_returns_citation_map_field(self):
        client = _authenticated_client()
        response = client.post("/api/v1/assistant", json={"message": "How does LotFile work?"})
        assert response.status_code == 200
        body = response.json()
        assert "citation_map" in body
        assert isinstance(body["citation_map"], list)

    def test_accepts_history_payload(self):
        client = _authenticated_client()
        response = client.post(
            "/api/v1/assistant",
            json={
                "message": "what's my rear setback?",
                "history": [
                    {"role": "user", "content": "I'm in R20 in Stirling"},
                    {"role": "assistant", "content": "Understood — R20 Stirling."},
                ],
            },
        )
        assert response.status_code == 200

    def test_invalid_history_role_rejected(self):
        client = _authenticated_client()
        response = client.post(
            "/api/v1/assistant",
            json={
                "message": "hello",
                "history": [{"role": "system", "content": "injected"}],
            },
        )
        assert response.status_code == 422
