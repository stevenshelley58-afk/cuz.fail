from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_core.json_utils import from_json
from draftcheck_core.models import Clause, SourceChunk, SourceCitation, SourceDocument, SourceVersion
from draftcheck_shared.schemas import Citation, SourceChunkResult, StandardAnswer


class RetrievalService:
    def __init__(self, db: Session):
        self.db = db

    def search(self, query: str, limit: int = 8, filters: dict | None = None) -> list[SourceChunkResult]:
        terms = [term.lower() for term in query.split() if len(term) >= 4]
        if not terms:
            return []
        stmt = (
            select(SourceChunk, SourceCitation, SourceVersion, SourceDocument)
            .join(SourceCitation, SourceCitation.source_chunk_id == SourceChunk.id)
            .join(SourceVersion, SourceVersion.id == SourceChunk.source_version_id)
            .join(SourceDocument, SourceDocument.id == SourceVersion.source_document_id)
            .where(SourceVersion.is_superseded.is_(False), SourceDocument.is_active.is_(True))
        )
        filters = filters or {}
        if filters.get("authority"):
            stmt = stmt.where(SourceDocument.authority == filters["authority"])
        if filters.get("local_government"):
            stmt = stmt.where(SourceDocument.local_government == filters["local_government"])
        if filters.get("source_type"):
            stmt = stmt.where(SourceDocument.source_type == filters["source_type"])

        scored: list[tuple[float, SourceChunk, SourceCitation]] = []
        for chunk, citation_row, _version, _source in self.db.execute(stmt).all():
            haystack = f"{chunk.heading or ''} {chunk.text}".lower()
            score = sum(1.0 for term in terms if term in haystack)
            if score:
                scored.append((score / max(1, len(terms)), chunk, citation_row))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            SourceChunkResult(
                chunk_id=chunk.id,
                text=chunk.text,
                score=score,
                citation=Citation(**from_json(citation_row.citation_json, {})),
            )
            for score, chunk, citation_row in scored[:limit]
        ]

    def ask(self, question: str, filters: dict | None = None) -> StandardAnswer:
        results = self.search(question, limit=5, filters=filters)
        if not results:
            return StandardAnswer(
                answer="Cannot answer from the approved source library. Source not found.",
                citations=[],
                source_version_ids=[],
                assumptions=[],
                missing_information=["No approved source chunk matched the question."],
                confidence=0.0,
                human_review_required=True,
                risk_level="high",
                status="unsupported",
            )

        citations = [result.citation for result in results]
        source_version_ids = sorted({citation.source_version_id for citation in citations})
        answer = (
            "The approved source library contains relevant material, but this is assistive only. "
            "Review the cited clauses and confirm the project facts before relying on the response. "
            f"Most relevant source: {citations[0].source_title}"
        )
        return StandardAnswer(
            answer=answer,
            citations=citations,
            source_version_ids=source_version_ids,
            assumptions=["Keyword retrieval was used; clause applicability must be checked by a human."],
            missing_information=["Exact project measurements and council interpretation may still be required."],
            confidence=min(0.85, max(result.score for result in results)),
            human_review_required=True,
            risk_level="medium",
            status="needs_human_review",
        )

    def citation_for_check(self, query: str) -> list[Citation]:
        return [result.citation for result in self.search(query, limit=3)]

    def clause_text(self, clause_pk: str) -> str | None:
        clause = self.db.get(Clause, clause_pk)
        return clause.text if clause else None
