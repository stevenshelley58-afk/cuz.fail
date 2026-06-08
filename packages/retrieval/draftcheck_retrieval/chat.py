"""Grounded conversational assistant.

Always uses the best configured chat model, grounded in the approved source
library when relevant chunks exist. When no live model is configured the service
falls back to the deterministic, cite-or-refuse retrieval engine so answers stay
honest. When no source supports a regulatory question, the assistant says so
rather than inventing a requirement (see CLAUDE.md governance rules).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from draftcheck_core.providers import ChatProvider, get_chat_provider
from draftcheck_retrieval.service import RetrievalService
from draftcheck_shared.schemas import ChatReply, Citation, SourceChunkResult

_ASSISTIVE_DISCLAIMER = (
    "Assistive only — this is not a compliance determination. Confirm the current "
    "source version and project facts, and have a human review before relying on it."
)

GROUNDED_SYSTEM_PROMPT = (
    "You are DraftCheck's assistant for Western Australian residential planning and design. "
    "Answer the user's question using ONLY the numbered SOURCES provided below. "
    "Quote or paraphrase them faithfully and do not introduce requirements, figures, "
    "clause numbers, or facts that are not present in the SOURCES. "
    "If the SOURCES do not actually answer the question, say so plainly instead of guessing. "
    "Never state that a specific property, drawing, or design is compliant or approved — "
    "that requires human review. Be clear, concise and helpful."
)

GENERAL_SYSTEM_PROMPT = (
    "You are DraftCheck's assistant. DraftCheck checks Western Australian residential "
    "drawings against the Residential Design Codes (R-Codes) and council planning rules, "
    "and answers with citations to approved sources. "
    "Be warm, concise and genuinely helpful. You may explain how DraftCheck works and give "
    "general, non-binding guidance. "
    "You do NOT have a cited source for this particular question, so you must NOT invent "
    "specific regulatory requirements, clause numbers, setbacks, site-cover, height or "
    "R-Code figures, and must NOT say whether anything is compliant. "
    "For property-specific or rule-specific questions, explain that the precise answer must "
    "come from the cited source library: invite the user to look up the property's address, "
    "or to ask for a specific source-backed rule, and mention what information would help."
)

_GENERAL_FALLBACK_ANSWER = (
    "Here's how DraftCheck works: you look up a property by address, and each address becomes "
    "its own workspace. I then check the drawings against the R-Codes and the relevant council "
    "rules — setbacks, site cover, open space, building height, boundary walls and more — and "
    "answer with a citation for each point. For anything about a specific block, look up its "
    "address first so I can answer from that property's sources rather than guessing."
)


class GroundedChatService:
    def __init__(self, db: Session):
        self.db = db
        self.retrieval = RetrievalService(db)

    def reply(self, question: str, filters: dict[str, Any] | None = None) -> ChatReply:
        question = (question or "").strip()
        provider = get_chat_provider()
        results = self.retrieval.search(question, limit=6, filters=filters)

        if not getattr(provider, "is_live", False):
            return self._deterministic_reply(question, filters, results, provider, used_fallback=True)

        try:
            if results:
                context = _format_sources(results)
                text = provider.complete(
                    GROUNDED_SYSTEM_PROMPT,
                    f"Question: {question}\n\nSOURCES:\n{context}",
                )
                return ChatReply(
                    answer=text,
                    citations=_dedupe_citations([result.citation for result in results]),
                    grounded=True,
                    model=provider.model,
                    provider=provider.name,
                    used_fallback=False,
                    disclaimer=_ASSISTIVE_DISCLAIMER,
                )
            text = provider.complete(GENERAL_SYSTEM_PROMPT, question)
            return ChatReply(
                answer=text,
                citations=[],
                grounded=False,
                model=provider.model,
                provider=provider.name,
                used_fallback=False,
                disclaimer=None,
            )
        except Exception:
            # A live model call failed (network/HTTP/parse): never hard-fail the
            # chat. Fall back to the deterministic, cite-or-refuse engine.
            return self._deterministic_reply(question, filters, results, provider, used_fallback=True)

    def _deterministic_reply(
        self,
        question: str,
        filters: dict[str, Any] | None,
        results: list[SourceChunkResult],
        provider: ChatProvider,
        *,
        used_fallback: bool,
    ) -> ChatReply:
        if results:
            answer = self.retrieval.ask(question, filters)
            return ChatReply(
                answer=answer.answer,
                citations=answer.citations,
                grounded=bool(answer.citations),
                model=provider.model,
                provider=provider.name,
                used_fallback=used_fallback,
                disclaimer=_ASSISTIVE_DISCLAIMER,
            )
        return ChatReply(
            answer=_GENERAL_FALLBACK_ANSWER,
            citations=[],
            grounded=False,
            model=provider.model,
            provider=provider.name,
            used_fallback=used_fallback,
            disclaimer=None,
        )


def _format_sources(results: list[SourceChunkResult]) -> str:
    blocks: list[str] = []
    for index, result in enumerate(results, start=1):
        citation = result.citation
        label_parts = [part for part in [citation.source_title, citation.clause_id] if part]
        if citation.page_number:
            label_parts.append(f"p.{citation.page_number}")
        label = " · ".join(label_parts) if label_parts else "source"
        snippet = " ".join((result.text or "").split())[:700]
        blocks.append(f"[{index}] {label}\n{snippet}")
    return "\n\n".join(blocks)


def _dedupe_citations(citations: list[Citation]) -> list[Citation]:
    seen: set[tuple[str, str | None, int | None]] = set()
    deduped: list[Citation] = []
    for citation in citations:
        key = (citation.source_version_id, citation.clause_id or citation.heading, citation.page_number)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(citation)
    return deduped
