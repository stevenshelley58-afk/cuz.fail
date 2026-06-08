from __future__ import annotations

import re
from urllib.parse import urlparse

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session, defer

from draftcheck_core.embeddings import (
    cosine_similarity,
    embedding_model_name,
    embedding_provider_name,
    embed_query,
    embedding_from_json,
    pgvector_literal,
)
from draftcheck_core.json_utils import from_json
from draftcheck_core.models import (
    Clause,
    SourceChunk,
    SourceChunkEmbedding,
    SourceCitation,
    SourceDocument,
    SourceLicenceReview,
    SourceVersion,
)
from draftcheck_core.source_support import (
    source_version_can_support_citable_retrieval,
    source_version_citable_retrieval_conditions,
)
from draftcheck_shared.schemas import Citation, SourceChunkResult, StandardAnswer

_ASSISTIVE_RELIANCE_NOTICE = (
    "This is assistive only and does not establish final compliance; confirm the current source version, "
    "project facts, and any council interpretation before relying on it."
)


class RetrievalService:
    def __init__(self, db: Session):
        self.db = db

    def search(self, query: str, limit: int = 8, filters: dict | None = None) -> list[SourceChunkResult]:
        scored = self._rank_chunks(query, limit=limit, filters=filters, require_accepted=True)
        return [
            SourceChunkResult(
                chunk_id=chunk.id,
                text=chunk.text,
                score=score,
                citation=_safe_citation(Citation(**from_json(citation_row.citation_json, {}))),
            )
            for score, chunk, citation_row in scored[:limit]
        ]

    def ask(self, question: str, filters: dict | None = None) -> StandardAnswer:
        if _requires_paid_standard_text(question):
            return StandardAnswer(
                answer=(
                    "The approved source library cannot support an answer to that Australian Standard "
                    "requirement. Paid or proprietary Australian Standards full text is not stored; only "
                    "public metadata and access notes may be held."
                ),
                citations=[],
                source_version_ids=[],
                assumptions=[],
                missing_information=[
                    "Australian Standards full text is not available in the approved source library.",
                    "Use licensed access and human review for the standard requirements.",
                ],
                confidence=0.0,
                human_review_required=True,
                risk_level="high",
                status="unsupported",
            )

        if _requires_bushfire_construction_standard_text(question):
            return StandardAnswer(
                answer=(
                    "The approved source library cannot support bushfire construction requirements from the "
                    "current public-source excerpts. Those requirements depend on the BCA, AS 3959, the assigned "
                    "BAL, and project-specific assessment."
                ),
                citations=[],
                source_version_ids=[],
                assumptions=[],
                missing_information=[
                    "BCA and AS 3959 construction requirement detail is not available as approved citable text.",
                    "Use licensed standard access, a BAL assessor, building surveyor, and human review.",
                ],
                confidence=0.0,
                human_review_required=True,
                risk_level="high",
                status="unsupported",
            )

        if _requires_resolved_property_context(question):
            return _property_context_required_answer()

        missing_context = _missing_rule_context_for(question)
        if missing_context:
            return _missing_rule_context_answer(missing_context)

        results = _answer_supported_results(question, self.search(question, limit=5, filters=filters))
        if not results:
            stitched_answer = self._stitched_threshold_table_answer(question, filters)
            if stitched_answer:
                return stitched_answer
            return _unsupported_answer(
                readiness_missing_information=_source_library_readiness_missing_information(self.db)
            )

        evidence_results = _select_evidence_results(question, results)
        if not evidence_results:
            stitched_answer = self._stitched_threshold_table_answer(question, filters)
            if stitched_answer:
                return stitched_answer
            return _unsupported_answer(
                "No matched source chunk contained a direct evidence sentence for the requested topic.",
                readiness_missing_information=_source_library_readiness_missing_information(self.db),
            )
        display_results = _display_evidence_results(question, evidence_results)
        citations = _dedupe_citations([result.citation for result in display_results])
        source_version_ids = sorted({citation.source_version_id for citation in citations})
        answer = _compose_answer(question, display_results)
        confidence = min(0.85, max(result.score for result in display_results))
        return StandardAnswer(
            answer=answer,
            citations=citations,
            source_version_ids=source_version_ids,
            assumptions=[
                "Only active, non-superseded approved source chunks were searched.",
                "Clause applicability must be checked against the project facts by a human reviewer.",
            ],
            missing_information=_missing_information_for(question),
            confidence=confidence,
            human_review_required=True,
            risk_level="medium" if confidence >= 0.45 else "high",
            status="needs_human_review",
        )

    def citation_for_check(self, query: str) -> list[Citation]:
        scored = self._rank_chunks(query, limit=3, filters=None, require_accepted=True)
        return [
            _safe_citation(Citation(**from_json(citation_row.citation_json, {})))
            for _score, _chunk, citation_row in scored[:3]
        ]

    def citations_for_supported_answer(self, question: str, filters: dict | None = None) -> list[Citation]:
        answer = self.ask(question, filters)
        if answer.status != "needs_human_review":
            return []
        return answer.citations

    def clause_text(self, clause_pk: str) -> str | None:
        clause = self.db.get(Clause, clause_pk)
        return clause.text if clause else None

    def _stitched_threshold_table_answer(self, question: str, filters: dict | None = None) -> StandardAnswer | None:
        query_tokens = set(_tokenize(question))
        requested_codes = sorted(_density_codes_from_tokens(query_tokens))
        if len(requested_codes) != 1:
            return None

        stitched = self._stitched_threshold_table_evidence(requested_codes[0], query_tokens, filters or {})
        if not stitched:
            return None

        label, value, citations = stitched
        confidence = 0.62
        return StandardAnswer(
            answer=_format_supported_answer(
                f"{label}: {value}.",
                citations,
            ),
            citations=citations,
            source_version_ids=sorted({citation.source_version_id for citation in citations}),
            assumptions=[
                "Only active, non-superseded approved source chunks were searched.",
                "Adjacent table fragments were stitched only within the same approved source version.",
                "Clause applicability must be checked against the project facts by a human reviewer.",
            ],
            missing_information=_missing_information_for(question),
            confidence=confidence,
            human_review_required=True,
            risk_level="medium",
            status="needs_human_review",
        )

    def _stitched_threshold_table_evidence(
        self,
        density_code: str,
        query_tokens: set[str],
        filters: dict,
    ) -> tuple[str, str, list[Citation]] | None:
        if not (
            {"site", "cover"}.issubset(query_tokens)
            or {"street", "setback"}.issubset(query_tokens)
        ):
            return None

        stmt = (
            select(SourceChunk, SourceCitation, SourceVersion, SourceDocument, Clause)
            .join(SourceCitation, SourceCitation.source_chunk_id == SourceChunk.id)
            .join(SourceVersion, SourceVersion.id == SourceChunk.source_version_id)
            .join(SourceDocument, SourceDocument.id == SourceVersion.source_document_id)
            .join(SourceLicenceReview, SourceLicenceReview.source_version_id == SourceVersion.id)
            .join(Clause, Clause.id == SourceChunk.clause_id)
            .where(
                SourceDocument.is_active.is_(True),
                SourceDocument.source_type == "r_code",
                *source_version_citable_retrieval_conditions(),
            )
            .options(defer(SourceVersion.raw_text, raiseload=False))
            .order_by(
                SourceVersion.created_at.desc(),
                SourceVersion.id,
                Clause.created_at,
                SourceChunk.created_at,
                SourceChunk.id,
            )
        )
        if filters.get("authority"):
            stmt = stmt.where(SourceDocument.authority == filters["authority"])
        if filters.get("local_government"):
            stmt = stmt.where(
                or_(
                    SourceDocument.local_government == filters["local_government"],
                    SourceDocument.local_government.is_(None),
                )
            )
        if filters.get("source_type"):
            stmt = stmt.where(SourceDocument.source_type == filters["source_type"])

        rows_by_version: dict[
            str,
            list[tuple[SourceChunk, SourceCitation, SourceVersion, SourceDocument, Clause]],
        ] = {}
        for row in self.db.execute(stmt).all():
            _chunk, _citation_row, version, _source, _clause = row
            rows_by_version.setdefault(version.id, []).append(row)

        for rows in rows_by_version.values():
            stitched = _find_threshold_table_value(density_code, query_tokens, rows)
            if stitched:
                return stitched
        return None

    def _rank_chunks(
        self,
        query: str,
        limit: int,
        filters: dict | None = None,
        *,
        require_accepted: bool,
    ) -> list[tuple[float, SourceChunk, SourceCitation]]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        stmt = (
            select(SourceChunk, SourceCitation, SourceVersion, SourceDocument)
            .join(SourceCitation, SourceCitation.source_chunk_id == SourceChunk.id)
            .join(SourceVersion, SourceVersion.id == SourceChunk.source_version_id)
            .join(SourceDocument, SourceDocument.id == SourceVersion.source_document_id)
            .join(SourceLicenceReview, SourceLicenceReview.source_version_id == SourceVersion.id)
            .where(SourceDocument.is_active.is_(True))
            # raw_text can be megabytes per version; never load it during retrieval
            # ranking or a single /chat request can exceed serverless memory limits.
            .options(defer(SourceVersion.raw_text, raiseload=False))
        )
        if require_accepted:
            stmt = stmt.where(*source_version_citable_retrieval_conditions())
        else:
            stmt = stmt.where(
                SourceVersion.is_superseded.is_(False),
                SourceVersion.parse_status.in_(("ok", "partial")),
                SourceLicenceReview.review_status == "approved",
                SourceLicenceReview.allowed_storage.is_(True),
                SourceLicenceReview.allowed_ai_processing.is_(True),
            )
        filters = filters or {}
        if filters.get("authority"):
            stmt = stmt.where(SourceDocument.authority == filters["authority"])
        if filters.get("local_government"):
            # Council-scoped retrieval must still include state-wide sources
            # (local_government is NULL for R-Codes, NCC, SPPs, etc.).
            stmt = stmt.where(
                or_(
                    SourceDocument.local_government == filters["local_government"],
                    SourceDocument.local_government.is_(None),
                )
            )
        if filters.get("source_type"):
            stmt = stmt.where(SourceDocument.source_type == filters["source_type"])

        base_stmt = stmt
        vector_scores = self._candidate_chunk_scores_from_vector(query, limit=max(50, limit * 10))
        fts_candidate_chunk_ids = self._candidate_chunk_ids_from_fts(query_tokens)
        candidate_chunk_ids = _merge_candidate_chunk_ids(fts_candidate_chunk_ids, vector_scores)
        if candidate_chunk_ids is not None:
            if not candidate_chunk_ids:
                return []
            stmt = stmt.where(SourceChunk.id.in_(candidate_chunk_ids))
        else:
            stmt = _with_sql_prefilter(stmt, query_tokens)

        threshold_query = _requires_threshold_evidence(set(query_tokens))
        query_set = set(query_tokens)
        citable_support_cache: dict[str, bool] = {}

        def score_statement(active_stmt) -> list[tuple[float, SourceChunk, SourceCitation]]:
            scored: list[tuple[float, SourceChunk, SourceCitation]] = []
            for chunk, citation_row, version, source in self.db.execute(active_stmt).all():
                if require_accepted and not _source_version_supports_citable_retrieval(
                    self.db,
                    version.id,
                    citable_support_cache,
                ):
                    continue
                if _domain_relevance_mismatch(query_set, f"{chunk.heading or ''} {chunk.text}", source):
                    continue
                score = _score_chunk(query_tokens, chunk, version, source)
                semantic_score = 0.0 if threshold_query else _semantic_score(vector_scores.get(chunk.id))
                if semantic_score:
                    score = score + semantic_score if score else semantic_score
                if score:
                    scored.append((score, chunk, citation_row))
            scored.sort(key=lambda item: item[0], reverse=True)
            return scored

        scored = score_statement(stmt)
        if candidate_chunk_ids is not None:
            lexical_scored = score_statement(_with_sql_prefilter(base_stmt, query_tokens))
            scored = _merge_scored_chunks(scored, lexical_scored)
        if not scored and candidate_chunk_ids is not None:
            scored = score_statement(_with_sql_prefilter(base_stmt, query_tokens))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[:limit]

    def _candidate_chunk_ids_from_fts(self, query_tokens: list[str]) -> list[str] | None:
        bind = self.db.get_bind()
        if bind.dialect.name != "sqlite":
            return None
        fts_exists = self.db.execute(
            text(
                "select 1 from sqlite_master "
                "where type = 'table' and name = 'source_chunk_fts' limit 1"
            )
        ).scalar()
        if not fts_exists:
            return None

        match_queries = [_fts_query(query_tokens, require_all=True), _fts_query(query_tokens, require_all=False)]
        match_queries = [query for query in match_queries if query]
        if not match_queries:
            return []
        try:
            for match_query in match_queries:
                chunk_ids = list(
                    self.db.execute(
                        text(
                            "select chunk_id from source_chunk_fts "
                            "where source_chunk_fts match :query "
                            "order by bm25(source_chunk_fts) limit 1000"
                        ),
                        {"query": match_query},
                    ).scalars()
                )
                if chunk_ids:
                    return chunk_ids
            return None
        except Exception:
            return None

    def _candidate_chunk_scores_from_vector(self, query: str, limit: int) -> dict[str, float]:
        vector = embed_query(query)
        provider = embedding_provider_name()
        model = embedding_model_name()
        bind = self.db.get_bind()
        if bind.dialect.name != "sqlite" and len(vector) == 16:
            try:
                rows = self.db.execute(
                    text(
                        """
                        select source_chunk_id,
                               1 - (embedding_vector <=> CAST(:embedding AS vector)) as similarity
                        from source_chunk_embeddings
                        where embedding_vector is not null
                          and provider = :provider
                          and model = :model
                        order by embedding_vector <=> CAST(:embedding AS vector)
                        limit :limit
                        """
                    ),
                    {"embedding": pgvector_literal(vector), "provider": provider, "model": model, "limit": limit},
                ).all()
                return {
                    str(row.source_chunk_id): float(row.similarity)
                    for row in rows
                    if row.similarity is not None and float(row.similarity) >= 0.35
                }
            except Exception:
                return self._candidate_chunk_scores_from_json_embeddings(vector, provider, model, limit)

        return self._candidate_chunk_scores_from_json_embeddings(vector, provider, model, limit)

    def _candidate_chunk_scores_from_json_embeddings(
        self,
        vector: list[float],
        provider: str,
        model: str,
        limit: int,
    ) -> dict[str, float]:
        rows = self.db.execute(
            select(SourceChunkEmbedding.source_chunk_id, SourceChunkEmbedding.embedding_json)
            .where(
                SourceChunkEmbedding.provider == provider,
                SourceChunkEmbedding.model == model,
                SourceChunkEmbedding.dimensions == len(vector),
            )
            .limit(5000)
        ).all()
        scored = [
            (chunk_id, cosine_similarity(vector, embedding_from_json(embedding_json)))
            for chunk_id, embedding_json in rows
        ]
        scored = [(chunk_id, score) for chunk_id, score in scored if score >= 0.35]
        scored.sort(key=lambda item: item[1], reverse=True)
        return {chunk_id: score for chunk_id, score in scored[:limit]}


def _unsupported_answer(
    missing_information: str = "No approved source chunk matched the question with enough support.",
    *,
    readiness_missing_information: str | None = None,
) -> StandardAnswer:
    missing = [missing_information]
    if readiness_missing_information and readiness_missing_information not in missing:
        missing.append(readiness_missing_information)
    return StandardAnswer(
        answer=(
            "The approved source library cannot support an answer to that question. "
            "No active, citable source chunk matched the request with enough support."
        ),
        citations=[],
        source_version_ids=[],
        assumptions=[],
        missing_information=missing,
        confidence=0.0,
        human_review_required=True,
        risk_level="high",
        status="unsupported",
    )


def _source_version_supports_citable_retrieval(
    db: Session,
    source_version_id: str,
    cache: dict[str, bool],
) -> bool:
    if source_version_id not in cache:
        cache[source_version_id] = source_version_can_support_citable_retrieval(db, source_version_id)
    return cache[source_version_id]


def _source_library_readiness_missing_information(db: Session) -> str | None:
    accepted_version_ids = list(
        db.scalars(
            select(SourceVersion.id)
            .join(SourceDocument, SourceDocument.id == SourceVersion.source_document_id)
            .where(
                SourceDocument.is_active.is_(True),
                SourceVersion.is_superseded.is_(False),
                SourceVersion.review_status == "accepted",
            )
        ).all()
    )
    pending_version_count = (
        db.scalar(
            select(func.count(SourceVersion.id))
            .join(SourceDocument, SourceDocument.id == SourceVersion.source_document_id)
            .where(
                SourceDocument.is_active.is_(True),
                SourceVersion.is_superseded.is_(False),
                SourceVersion.review_status == "pending_review",
            )
        )
        or 0
    )
    if not accepted_version_ids:
        return "No accepted current source versions are available for citable retrieval."

    chunked_version_ids = set(
        db.scalars(
            select(SourceChunk.source_version_id)
            .where(SourceChunk.source_version_id.in_(accepted_version_ids))
            .distinct()
        ).all()
    )
    cited_version_ids = set(
        db.scalars(
            select(SourceCitation.source_version_id)
            .where(SourceCitation.source_version_id.in_(accepted_version_ids))
            .distinct()
        ).all()
    )
    if not (chunked_version_ids & cited_version_ids):
        return "Accepted current source versions exist, but none have both source chunks and citations for retrieval."

    support_cache: dict[str, bool] = {}
    if any(_source_version_supports_citable_retrieval(db, version_id, support_cache) for version_id in accepted_version_ids):
        if pending_version_count:
            noun = "version is" if pending_version_count == 1 else "versions are"
            return (
                f"{pending_version_count} current source {noun} pending review and cannot support "
                "citable retrieval until accepted."
            )
        return None
    return "Accepted source versions exist but none currently pass the citable retrieval gate."


def _property_context_required_answer() -> StandardAnswer:
    return StandardAnswer(
        answer=(
            "That is property-specific. A resolved address/profile and proposal facts are required "
            "before the approved source library can support an answer."
        ),
        citations=[],
        source_version_ids=[],
        assumptions=[],
        missing_information=[
            "Resolve the address/property profile before asking for this property's setback, zoning, lot, or site-specific controls.",
            "A human reviewer must confirm proposal facts before any export is treated as submission-ready.",
        ],
        confidence=0.0,
        human_review_required=True,
        risk_level="high",
        status="missing_info",
    )


def _missing_rule_context_answer(missing_information: str) -> StandardAnswer:
    return StandardAnswer(
        answer=(
            "That question needs a more specific rule context before the approved source library "
            "can support an answer."
        ),
        citations=[],
        source_version_ids=[],
        assumptions=[],
        missing_information=[
            missing_information,
            (
                "Ask for a specific source-backed rule, or resolve the project address/profile and proposal "
                "facts before asking for a project-specific judgement."
            ),
        ],
        confidence=0.0,
        human_review_required=True,
        risk_level="high",
        status="missing_info",
    )


_MIN_GENERAL_ANSWER_SCORE = 0.25
_MIN_NORMATIVE_ANSWER_SCORE = 0.4

_ACCESSORY_PROPOSAL_TERMS = (
    "ancillary dwelling",
    "carport",
    "extension",
    "fence",
    "garage",
    "granny flat",
    "outbuilding",
    "patio",
    "pool",
    "shed",
)

_DWELLING_PROPOSAL_TERMS = (
    "dwelling",
    "grouped dwelling",
    "house",
    "single house",
)

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "applicable",
    "apply",
    "applies",
    "be",
    "by",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "relevant",
    "rule",
    "rules",
    "say",
    "says",
    "should",
    "that",
    "the",
    "this",
    "to",
    "what",
    "whats",
    "when",
    "where",
    "which",
    "with",
}

_SYNONYMS = {
    "allowable": "allow",
    "allowed": "allow",
    "approvals": "approval",
    "approved": "approval",
    "approves": "approval",
    "coverage": "cover",
    "covered": "cover",
    "covers": "cover",
    "calculations": "calculation",
    "calculate": "calculation",
    "calculated": "calculation",
    "calculating": "calculation",
    "constructed": "construct",
    "construction": "construct",
    "demonstrated": "demonstrate",
    "demonstrating": "demonstrate",
    "demonstration": "demonstrate",
    "dominant": "dominance",
    "front": "street",
    "frontage": "street",
    "garages": "garage",
    "measurements": "measurement",
    "measures": "measurement",
    "orientation": "orient",
    "orientations": "orient",
    "oriented": "orient",
    "permitted": "permit",
    "permission": "permit",
    "permissible": "permit",
    "provided": "provide",
    "providing": "provide",
    "requirements": "requirement",
    "setbacks": "setback",
    "spaces": "space",
    "stories": "storey",
    "story": "storey",
}


def _tokenize(value: str) -> list[str]:
    tokens: list[str] = []
    normalized_value = value.lower()
    normalized_value = re.sub(r"\bfront\s+set\s+backs?\b", "primary street setback", normalized_value)
    normalized_value = re.sub(r"\bfront\s+setbacks?\b", "primary street setback", normalized_value)
    normalized_value = re.sub(r"\bset\s+backs?\b", "setback", normalized_value)
    for raw_token in re.findall(r"[a-z0-9]+(?:\.[a-z0-9]+)*", normalized_value):
        token = _normalize_token(raw_token)
        if len(token) >= 3 and token not in _STOPWORDS:
            tokens.append(token)
    return tokens


def _fts_query(query_tokens: list[str], require_all: bool) -> str:
    pieces = []
    for token in list(dict.fromkeys(query_tokens))[:8]:
        cleaned = re.sub(r"[^a-z0-9.]+", "", token.lower())
        if not cleaned:
            continue
        suffix = "*" if len(cleaned) >= 4 else ""
        pieces.append(f"{cleaned}{suffix}")
    return " ".join(pieces) if require_all else " OR ".join(pieces)


def _merge_candidate_chunk_ids(
    fts_chunk_ids: list[str] | None,
    vector_scores: dict[str, float],
) -> list[str] | None:
    if fts_chunk_ids is None and not vector_scores:
        return None
    merged: list[str] = []
    for chunk_id in fts_chunk_ids or []:
        if chunk_id not in merged:
            merged.append(chunk_id)
    for chunk_id in vector_scores:
        if chunk_id not in merged:
            merged.append(chunk_id)
    return merged


def _merge_scored_chunks(
    *groups: list[tuple[float, SourceChunk, SourceCitation]],
) -> list[tuple[float, SourceChunk, SourceCitation]]:
    merged: dict[str, tuple[float, SourceChunk, SourceCitation]] = {}
    for group in groups:
        for score, chunk, citation in group:
            existing = merged.get(chunk.id)
            if existing is None or score > existing[0]:
                merged[chunk.id] = (score, chunk, citation)
    return list(merged.values())


def _with_sql_prefilter(stmt, query_tokens: list[str]):
    prefilter_tokens = list(dict.fromkeys(query_tokens))[:8]
    prefilter_conditions = []
    for token in prefilter_tokens:
        pattern = f"%{token}%"
        prefilter_conditions.extend(
            [
                SourceChunk.text.ilike(pattern),
                SourceChunk.heading.ilike(pattern),
                SourceDocument.title.ilike(pattern),
                SourceDocument.authority.ilike(pattern),
                SourceDocument.local_government.ilike(pattern),
                SourceDocument.source_type.ilike(pattern),
            ]
        )
    if prefilter_conditions:
        return stmt.where(or_(*prefilter_conditions))
    return stmt


def _semantic_score(similarity: float | None) -> float:
    if similarity is None or similarity < 0.45:
        return 0.0
    return min(0.36, 0.23 + ((similarity - 0.45) * 0.36))


def _normalize_token(token: str) -> str:
    if token in _SYNONYMS:
        return _SYNONYMS[token]
    if len(token) > 5 and token.endswith("ies"):
        token = f"{token[:-3]}y"
    elif len(token) > 5 and token.endswith("ing"):
        token = token[:-3]
    elif len(token) > 4 and token.endswith("ed"):
        token = token[:-2]
    elif len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        token = token[:-1]
    return _SYNONYMS.get(token, token)


def _score_chunk(
    query_tokens: list[str],
    chunk: SourceChunk,
    version: SourceVersion,
    source: SourceDocument,
) -> float:
    query_set = set(query_tokens)
    query_weights = _query_token_weights(query_tokens)
    text_value = f"{chunk.heading or ''} {chunk.text}"
    text_haystack = text_value.lower()
    if not text_haystack.strip():
        return 0.0

    query_density_codes = _density_codes_from_tokens(query_set)
    text_density_codes = _density_codes(text_value)
    if query_density_codes and text_density_codes and query_density_codes.isdisjoint(text_density_codes):
        return 0.0
    if query_density_codes and not text_density_codes and source.local_government is None:
        return 0.0
    if (
        _asks_for_normative_requirement(query_set) or _requires_threshold_evidence(query_set)
    ) and _is_non_normative_source(source, query_set):
        return 0.0

    text_tokens = _tokenize(text_value)
    text_token_set = set(text_tokens)
    if _domain_relevance_mismatch(query_set, text_value, source):
        return 0.0
    if not _supports_required_topic_phrases(query_set, text_token_set):
        return 0.0

    matched_text_tokens = query_set & text_token_set
    if not matched_text_tokens:
        return 0.0

    metadata_value = " ".join(
        value
        for value in [
            source.title,
            source.authority,
            source.local_government or "",
            source.source_type,
            version.version_label or "",
        ]
        if value
    )
    heading_tokens = set(_tokenize(chunk.heading or ""))
    metadata_tokens = set(_tokenize(metadata_value))
    occurrence_hits = sum(min(text_tokens.count(token), 3) * query_weights[token] for token in query_set)
    total_weight = sum(query_weights.values())
    coverage = sum(query_weights[token] for token in matched_text_tokens) / total_weight
    occurrence_score = occurrence_hits / (total_weight * 3)
    heading_bonus = 0.08 * sum(query_weights[token] for token in query_set & heading_tokens) / total_weight
    metadata_bonus = 0.05 * sum(query_weights[token] for token in query_set & metadata_tokens) / total_weight
    density_adjustment = _density_code_adjustment(query_density_codes, text_density_codes)
    threshold_adjustment = _threshold_evidence_adjustment(query_set, text_value)
    return max(
        0.0,
        (coverage * 0.78)
        + (occurrence_score * 0.17)
        + heading_bonus
        + metadata_bonus
        + density_adjustment
        + threshold_adjustment
        + _chunk_quality_adjustment(chunk)
        + _source_quality_adjustment(source),
    )


def _query_token_weights(query_tokens: list[str]) -> dict[str, float]:
    weights: dict[str, float] = {}
    for token in set(query_tokens):
        if _is_density_code(token):
            weights[token] = 3.0
        elif re.fullmatch(r"\d+(?:\.\d+)?", token):
            weights[token] = 2.0
        else:
            weights[token] = 1.0
    return weights


def _density_codes_from_tokens(tokens: set[str]) -> set[str]:
    return {token for token in tokens if _is_density_code(token)}


def _density_codes(value: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"\br(?:ac|\d{2,3})\b", value, flags=re.IGNORECASE)
    }


def _ordered_density_codes(value: str) -> list[str]:
    return [
        token.lower()
        for token in re.findall(r"\br(?:ac|\d{2,3})\b", value, flags=re.IGNORECASE)
    ]


def _is_density_code(token: str) -> bool:
    return bool(re.fullmatch(r"r(?:ac|\d{2,3})", token.lower()))


def _density_code_adjustment(
    query_density_codes: set[str],
    text_density_codes: set[str],
) -> float:
    if not query_density_codes:
        return 0.0
    if query_density_codes & text_density_codes:
        return 0.14
    return 0.0


def _answer_supported_results(question: str, results: list[SourceChunkResult]) -> list[SourceChunkResult]:
    query_tokens = set(_tokenize(question))
    minimum_score = (
        _MIN_NORMATIVE_ANSWER_SCORE
        if _asks_for_normative_requirement(query_tokens) or _density_codes_from_tokens(query_tokens)
        else _MIN_GENERAL_ANSWER_SCORE
    )
    supported = [result for result in results if result.score >= minimum_score]
    if _asks_for_normative_requirement(query_tokens):
        supported = [
            result
            for result in supported
            if not _is_nonoperative_requirement_evidence(result.text)
            and _has_normative_requirement_evidence(result.text)
        ]
    if _requires_threshold_evidence(query_tokens):
        supported = [result for result in supported if _has_threshold_evidence(result.text)]
        supported.sort(
            key=lambda result: _threshold_result_priority(query_tokens, result.text),
            reverse=True,
        )
        if any(_looks_like_requirement_table(result.text.lower()) for result in supported):
            supported = [
                result for result in supported if not _is_threshold_figure_noise(result.text)
            ]
    return supported


_REQUIRED_TOPIC_PHRASES = (
    ("bal", "report"),
    ("design", "review"),
    ("solar", "access"),
    ("open", "space"),
    ("outdoor", "liv"),
    ("site", "cover"),
    ("street", "setback"),
)

_INFORMATIVE_EVIDENCE_TOKENS = {
    "assist",
    "example",
    "expect",
    "include",
    "maximum",
    "method",
    "minimum",
    "provide",
    "requirement",
    "show",
}

def _supports_required_topic_phrases(query_tokens: set[str], text_tokens: set[str]) -> bool:
    for phrase_tokens in _REQUIRED_TOPIC_PHRASES:
        phrase_set = set(phrase_tokens)
        if phrase_set.issubset(query_tokens) and not phrase_set.issubset(text_tokens):
            return False
    if "storey" in query_tokens and "storey" not in text_tokens:
        return False
    if "height" in query_tokens and not text_tokens & {"height", "storey"}:
        return False
    if query_tokens & {"height", "storey"} and query_tokens & {"dwelling", "house"}:
        if not text_tokens & {"dwelling", "house"}:
            return False
    return True


def _requires_direct_topic_sentence(query_tokens: set[str]) -> bool:
    return any(set(phrase_tokens).issubset(query_tokens) for phrase_tokens in _REQUIRED_TOPIC_PHRASES) or bool(
        query_tokens & {"height", "storey"}
    )


def _domain_relevance_mismatch(query_tokens: set[str], text: str, source: SourceDocument) -> bool:
    text_token_set = set(_tokenize(text))
    full_haystack = f"{source.title} {text}".lower()
    if source.source_type != "r_code" and {"code", "volume"}.issubset(query_tokens) and not any(
        marker in full_haystack
        for marker in [
            "r-code",
            "r code",
            "r-codes",
            "r codes",
            "residential design code",
        ]
    ):
        return True
    if "ncc" in query_tokens and source.source_type != "ncc" and "ncc" not in text_token_set:
        return True
    if "condensation" in query_tokens and "condensation" not in text_token_set:
        return True
    if "ventilation" in query_tokens and "ventilation" not in text_token_set:
        return True
    if {"natural", "ventilation"}.issubset(query_tokens) and not {"natural", "ventilation"}.issubset(text_token_set):
        return True
    if "orient" in query_tokens and not (text_token_set & {"orient", "orientation", "oriented"}):
        return True
    if {"development", "application"}.issubset(query_tokens) and not {"development", "application"}.issubset(
        text_token_set
    ):
        return True
    if query_tokens & {"bal", "bushfire"} and source.source_type != "bushfire" and not (
        text_token_set & {"bal", "bushfire"}
    ):
        return True
    return "livable" in query_tokens and "livable" not in text_token_set


def _asks_for_normative_requirement(query_tokens: set[str]) -> bool:
    return bool(
        query_tokens
        & {
            "allow",
            "approval",
            "build",
            "compliance",
            "comply",
            "construct",
            "develop",
            "dwelling",
            "height",
            "house",
            "may",
            "maximum",
            "minimum",
            "must",
            "permit",
            "requirement",
            "shall",
            "storey",
            "threshold",
        }
    )


def _requires_threshold_evidence(query_tokens: set[str]) -> bool:
    if "requirement" in query_tokens:
        return True
    if _density_codes_from_tokens(query_tokens) and any(
        set(phrase_tokens).issubset(query_tokens) for phrase_tokens in _REQUIRED_TOPIC_PHRASES
    ):
        return True
    if "setback" in query_tokens and _asks_for_normative_requirement(query_tokens):
        return True
    return bool(
        query_tokens
        & {
            "maximum",
            "minimum",
            "threshold",
        }
    )


def _threshold_values(text: str) -> list[str]:
    return re.findall(
        r"\b\d+(?:\.\d+)?\s*(?:(?:m|m2|sqm|per\s+cent)\b|%)",
        text,
        flags=re.IGNORECASE,
    )


def _percentage_values(text: str) -> list[str]:
    return re.findall(
        r"\b\d+(?:\.\d+)?\s*(?:per\s+cent\b|%)",
        text,
        flags=re.IGNORECASE,
    )


def _has_threshold_evidence(text: str) -> bool:
    return bool(_threshold_values(text))


def _has_normative_requirement_evidence(text: str) -> bool:
    lowered = text.lower()
    return _has_threshold_evidence(text) or bool(
        re.search(
            r"\b(?:must|shall|required|requires|minimum|maximum|not\s+less\s+than|"
            r"not\s+exceed|may\s+be|acceptable\s+outcome|deemed[- ]to[- ]comply)\b",
            lowered,
        )
    )


def _threshold_evidence_adjustment(query_tokens: set[str], text: str) -> float:
    if not _requires_threshold_evidence(query_tokens):
        return 0.0
    if not _has_threshold_evidence(text):
        return -0.2

    lowered = text.lower()
    adjustment = 0.18
    if _looks_like_requirement_table(lowered):
        adjustment += 0.08
    return adjustment


def _threshold_result_priority(query_tokens: set[str], text: str) -> float:
    lowered = text.lower()
    priority = 0.0
    if _looks_like_requirement_table(lowered):
        priority += 4.0
    if _density_codes_from_tokens(query_tokens) & _density_codes(text):
        priority += 2.0
    if _has_threshold_evidence(text):
        priority += 1.0
    if any(set(phrase_tokens).issubset(set(_tokenize(text))) for phrase_tokens in _REQUIRED_TOPIC_PHRASES):
        priority += 1.0
    if any(marker in lowered for marker in ["figure", "reduction", "reduced by"]):
        priority -= 1.0
    if any(marker in lowered for marker in ["boundary wall", "boundary walls"]):
        priority -= 3.0
    return priority


def _looks_like_requirement_table(lowered_text: str) -> bool:
    if "table" not in lowered_text:
        return False
    return any(
        marker in lowered_text
        for marker in [
            "maximum site cover",
            "minimum setback",
            "setback of buildings from the street",
            "site cover requirements",
            "street type",
        ]
    )


def _is_threshold_figure_noise(text: str) -> bool:
    lowered = text.lower()
    if "figure" not in lowered or _looks_like_requirement_table(lowered):
        return False
    return "may be reduced" not in lowered and "permitted" not in lowered


def _is_nonoperative_requirement_evidence(text: str) -> bool:
    lowered = text.lower()
    if "not deemed-to-comply" in lowered or "not deemed to comply" in lowered:
        return True
    if "method of calculating" in lowered and "average side setback" in lowered:
        return True
    return bool(
        "average side setback" in lowered
        and "total length" in lowered
        and re.search(r"\b\d+(?:\.\d+)?\s*m\s*x\s*\d", lowered)
    )


def _is_non_normative_source(source: SourceDocument, query_tokens: set[str]) -> bool:
    if query_tokens & {
        "consultation",
        "explanatory",
        "guideline",
        "practice",
        "report",
        "submission",
        "summary",
        "template",
        "testing",
    }:
        return False

    title = source.title.lower()
    return any(
        marker in title
        for marker in [
            "application form",
            "assessment template",
            "consultation",
            "engagement outcomes",
            "explanatory guideline",
            "outcomes report",
            "practice note",
            "proposal for change",
            "submission",
            "submission summary",
            "stakeholder",
            "summary report",
            "template",
            "testing report",
        ]
    )


def _chunk_quality_adjustment(chunk: SourceChunk) -> float:
    heading = (chunk.heading or "").lower()
    text_start = chunk.text[:500].lower()
    pipe_count = chunk.text[:500].count("|")
    if "contents  |" in text_start or "contents |" in text_start:
        return -0.18
    if pipe_count >= 4 and any(marker in text_start for marker in ["a1 definitions", "part a", "appendices"]):
        return -0.16
    if pipe_count >= 3 and any(marker in heading for marker in ["definitions", "application documentation"]):
        return -0.14
    return 0.0


def _source_quality_adjustment(source: SourceDocument) -> float:
    title = source.title.lower()
    adjustment = 0.0
    if source.source_type in {"r_code", "ncc", "local_planning_policy", "bushfire", "bushfire_guidance"}:
        adjustment += 0.04
    if "residential design codes volume 1 - april 2026" in title:
        adjustment += 0.08
    elif "residential design codes - volume 2" in title:
        adjustment += 0.06
    elif "residential design codes" in title:
        adjustment += 0.03
    if any(
        marker in title
        for marker in [
            "application form",
            "consultation",
            "proposal for change",
            "submission",
            "stakeholder",
            "template",
            "testing report",
        ]
    ):
        adjustment -= 0.14
    elif "report" in title and "residential design codes" not in title:
        adjustment -= 0.08
    if source.source_type == "map_layer":
        adjustment -= 0.06
    return adjustment


def _dedupe_citations(citations: list[Citation]) -> list[Citation]:
    seen: set[tuple[str, str | None, int | None, str | None]] = set()
    deduped: list[Citation] = []
    for raw_citation in citations:
        citation = _safe_citation(raw_citation)
        key = (
            citation.source_version_id,
            citation.clause_id or citation.heading,
            citation.page_number,
            None if citation.clause_id else citation.heading,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(citation)
    return deduped


def _safe_citation(citation: Citation) -> Citation:
    if not _safe_citation_url(citation.canonical_url, citation.source_title):
        return citation.model_copy(update={"canonical_url": None})
    return citation


def _safe_citation_url(url: str | None, source_title: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    host = parsed.hostname or ""
    if (
        host in {"localhost", "127.0.0.1", "example.com", "example.net", "example.org"}
        or host.endswith(".test")
        or host.endswith(".localhost")
    ):
        return False
    haystack = f"{source_title} {parsed.path}".lower()
    return "fixture" not in haystack and "/example-policy" not in haystack


def _requires_resolved_property_context(question: str) -> bool:
    lower = question.lower()
    if re.search(
        r"\b(?:does|will|would|can|could|should|is)\s+(?:my|our)\b.*"
        r"\b(?:approved|approval|build|comply|compliant|develop|pass|permit)\b",
        lower,
    ):
        return True
    if re.search(
        r"\b(?:can|could|should|may)\s+i\b.*"
        r"\b(?:build|construct|develop|subdivide|approval|approved|comply|compliant|pass|permit)\b",
        lower,
    ):
        return True
    if re.search(
        r"\b(?:my|our)\s+(?:application|design|development|drawings?|plans?|proposal)\b",
        lower,
    ) and re.search(r"\b(?:approved|approval|comply|compliant|pass|permit)\b", lower):
        return True
    if re.search(
        r"\b(?:my|our)\s+(?:front\s+|side\s+|rear\s+)?"
        r"(?:setbacks?|site\s+cover|open\s+space|zoning|zone|r[-\s]?code|height|"
        r"boundary\s+walls?|lot|block|property|parcel|address)\b",
        lower,
    ):
        return True
    query_tokens = set(_tokenize(question))
    asks_for_project_action = bool(
        query_tokens
        & {
            "add",
            "allow",
            "alter",
            "approval",
            "build",
            "compliance",
            "comply",
            "construct",
            "develop",
            "extend",
            "have",
            "permit",
        }
    )
    if asks_for_project_action and any(term in lower for term in _ACCESSORY_PROPOSAL_TERMS):
        return True
    if (
        asks_for_project_action
        and any(term in lower for term in _DWELLING_PROPOSAL_TERMS)
            and not _density_codes_from_tokens(query_tokens)
    ):
        return True
    if asks_for_project_action and _mentions_storey_or_height_context(lower, query_tokens):
        return True
    refers_to_specific_property = bool(
        re.search(r"\b(?:this|that)\s+(?:property|lot|block|site|parcel|address)\b", lower)
        or re.search(r"\bthe\s+(?:property|lot|block|parcel|address)\b", lower)
    )
    return bool(
        refers_to_specific_property
        and re.search(
            r"\b(?:setbacks?|site\s+cover|open\s+space|zoning|zone|r[-\s]?code|height|"
            r"boundary\s+walls?|build|subdivide|develop)\b",
            lower,
        )
    )


def _missing_rule_context_for(question: str) -> str | None:
    lower = question.lower()
    query_tokens = set(_tokenize(question))
    if "setback" in query_tokens and _is_broad_setback_question(lower, query_tokens):
        return (
            "Ask for a specific setback type, density code, and development context before relying on "
            "source-library search for setback requirements."
        )
    if _is_broad_storey_or_height_dwelling_question(lower, query_tokens):
        return (
            "Ask for a resolved property/profile, density code, applicable height or storey source context, "
            "and proposal facts before relying on source-library search for dwelling height controls."
        )
    return None


def _mentions_storey_or_height_context(lowered_question: str, query_tokens: set[str]) -> bool:
    return bool(
        query_tokens & {"height", "storey"}
        or any(term in lowered_question for term in ["second floor", "upper floor", "upstairs"])
    )


def _is_broad_setback_question(lowered_question: str, query_tokens: set[str]) -> bool:
    if _density_codes_from_tokens(query_tokens):
        return False
    if query_tokens & {"boundary", "primary", "rear", "secondary", "side", "street"}:
        return False
    if re.search(r"\b(?:front|primary|secondary|side|rear|boundary|lot)\s+setbacks?\b", lowered_question):
        return False
    return bool(
        re.search(r"\bwhat\s+(?:are|is)\s+(?:the\s+)?setbacks?\b", lowered_question)
        or query_tokens == {"setback"}
    )


def _is_broad_storey_or_height_dwelling_question(lowered_question: str, query_tokens: set[str]) -> bool:
    if not query_tokens & {"height", "storey"}:
        return False
    if _density_codes_from_tokens(query_tokens):
        return False
    if not (
        query_tokens & {"dwelling", "house"}
        or any(term in lowered_question for term in _DWELLING_PROPOSAL_TERMS)
    ):
        return False
    return True


def _select_evidence_results(question: str, results: list[SourceChunkResult]) -> list[SourceChunkResult]:
    query_tokens = _tokenize(question)
    query_set = set(query_tokens)
    require_direct_topic_sentence = _requires_direct_topic_sentence(query_set)
    evidence_results: list[SourceChunkResult] = []
    used_sentences: set[str] = set()
    used_citation_keys: set[tuple[str, str | None]] = set()
    for result in results:
        citation_key = (
            result.citation.source_version_id,
            result.citation.clause_id or result.citation.heading,
        )
        if citation_key in used_citation_keys:
            continue
        sentence = _best_evidence_sentence(result.text, query_tokens)
        if require_direct_topic_sentence and not _supports_required_topic_phrases(
            query_set,
            set(_tokenize(sentence)),
        ):
            continue
        normalized = " ".join(sentence.lower().split())
        if normalized in used_sentences:
            continue
        used_citation_keys.add(citation_key)
        used_sentences.add(normalized)
        evidence_results.append(result)
        if (
            _requires_threshold_evidence(query_set)
            and _is_interpreted_threshold_sentence(sentence)
            and not _asks_for_threshold_qualifiers(query_set)
        ):
            return evidence_results
        if len(evidence_results) >= 3:
            break

    if require_direct_topic_sentence:
        return evidence_results
    return evidence_results or results[:1]


def _compose_answer(question: str, results: list[SourceChunkResult]) -> str:
    query_tokens = _tokenize(question)
    evidence_items: list[tuple[str, Citation]] = []
    for result in results:
        sentence = _best_evidence_sentence(result.text, query_tokens)
        evidence_items.append((sentence, result.citation))

    display_items = _display_evidence_items(evidence_items, set(query_tokens))
    if not display_items:
        return _format_supported_answer(
            "Review the matched approved source chunk directly.",
            [results[0].citation],
        )

    statement = _primary_supported_statement(question, display_items[0][0], display_items[0][1])
    supporting_items = display_items[1:3]
    return _format_supported_answer(
        statement,
        [citation for _sentence, citation in display_items],
        supporting_items=supporting_items,
    )


def _display_evidence_results(
    question: str,
    results: list[SourceChunkResult],
) -> list[SourceChunkResult]:
    query_tokens = _tokenize(question)
    informative = [
        result
        for result in results
        if not _is_low_information_evidence_sentence(
            _best_evidence_sentence(result.text, query_tokens),
            result.citation,
            set(query_tokens),
        )
    ]
    return informative or results


def _display_evidence_items(
    evidence_items: list[tuple[str, Citation]],
    query_tokens: set[str],
) -> list[tuple[str, Citation]]:
    informative = [
        (sentence, citation)
        for sentence, citation in evidence_items
        if not _is_low_information_evidence_sentence(sentence, citation, query_tokens)
    ]
    return informative or evidence_items


def _is_low_information_evidence_sentence(
    sentence: str,
    citation: Citation,
    query_tokens: set[str],
) -> bool:
    if _has_threshold_evidence(sentence) or _is_interpreted_threshold_sentence(sentence):
        return False
    normalized = sentence.strip().lower().strip(" .:-")
    heading = (citation.heading or "").strip().lower().strip(" .:-")
    if heading and normalized == heading:
        return True
    sentence_tokens = set(_tokenize(sentence))
    if heading == "introductory material" and not sentence_tokens & _INFORMATIVE_EVIDENCE_TOKENS:
        return True
    if normalized and normalized in citation.source_title.strip().lower():
        if sentence_tokens and sentence_tokens.issubset(query_tokens | set(_tokenize(citation.source_title))):
            return True
    return len(sentence_tokens) <= 4 and not sentence_tokens & _INFORMATIVE_EVIDENCE_TOKENS


def _primary_supported_statement(question: str, sentence: str, citation: Citation) -> str:
    sentence = _clean_answer_sentence(sentence)
    query_tokens = set(_tokenize(question))
    lowered = sentence.lower()
    evidence_lowered = f"{lowered} {citation.quote or ''}".lower()

    if {"solar", "access"}.issubset(query_tokens) and "demonstrate" in query_tokens:
        if "clear and accurate information" in lowered and "solar access can be demonstrated" in lowered:
            return (
                "For solar access, proponents should provide clear and accurate information to demonstrate the "
                "Element Objectives; the guidance gives diagrams as examples of how solar access can be demonstrated."
            )
        if "solar access can be demonstrated" in lowered:
            return "The approved guidance shows how solar access can be demonstrated using examples."

    if {"natural", "ventilation"}.issubset(query_tokens) and "orient" in query_tokens:
        if "45 to 90 degrees" in lowered and "prevailing cooling wind" in lowered:
            return (
                "For natural ventilation, the approved guidance identifies 45 to 90 degrees of the prevailing "
                "cooling wind as optimum orientation for single aspect apartments, with 0 to 45 degrees described "
                "as fair orientation."
            )
        if "location and site context" in lowered:
            return "Natural ventilation orientation should consider location and site context."

    if {"average", "side", "setback"}.issubset(query_tokens) and "average side setback" in lowered:
        return "The approved guidance provides a method for calculating the average side setback."

    if "bal" in query_tokens and "report" in query_tokens:
        if "fire danger index" in evidence_lowered and "100 metres" in evidence_lowered and "bal-low" in evidence_lowered:
            return (
                "For a BAL Assessment (Basic) Report, the approved WA form asks for the Fire Danger Index, "
                "whether bushfire prone vegetation is within 100 metres of the proposed building, the distance "
                "to that vegetation, the slope under that vegetation, and the BAL for the proposed building or "
                "development. The basic report may support a relevant application only where the BAL is BAL-LOW; "
                "if the BAL is not BAL-LOW, the form says this report should not be used."
            )

    if "provided by the applicant for design review" in lowered:
        return (
            "For R-Codes Volume 2 design review, the A4 guidance identifies basic information that should be "
            "provided by the applicant for design review before development application."
        )

    if "materials when submitting a development application" in lowered:
        return (
            "For an R-Codes Volume 2 development application, the A5 guidance assists proponents in formulating "
            "the appropriate materials when submitting a development application."
        )

    if _is_interpreted_threshold_sentence(sentence):
        return _ensure_sentence_punctuation(sentence)

    if lowered.startswith("it includes ") and citation.heading:
        sentence = f"{citation.heading} includes {sentence[len('It includes '):]}"
    elif lowered.startswith("the diagram below ") and citation.heading:
        sentence = f"{citation.heading}: {sentence[:1].lower()}{sentence[1:]}"

    return f"The approved source library supports this limited answer: {_ensure_sentence_punctuation(sentence)}"


def _format_supported_answer(
    statement: str,
    citations: list[Citation],
    *,
    supporting_items: list[tuple[str, Citation]] | None = None,
) -> str:
    lines = [_ensure_sentence_punctuation(statement)]
    supporting_lines = _supporting_evidence_lines(supporting_items or [])
    if supporting_lines:
        lines.append("Supporting evidence:")
        lines.extend(supporting_lines)
    label = "Sources" if len(_unique_citation_labels(citations)) > 1 else "Source"
    lines.append(f"{label}: {'; '.join(_unique_citation_labels(citations))}.")
    lines.append(_ASSISTIVE_RELIANCE_NOTICE)
    return "\n".join(lines)


def _supporting_evidence_lines(items: list[tuple[str, Citation]]) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for sentence, citation in items:
        cleaned = _clean_answer_sentence(sentence)
        key = " ".join(cleaned.lower().split())
        if not key or key in seen:
            continue
        seen.add(key)
        lines.append(f"- {_ensure_sentence_punctuation(cleaned)} ({_citation_label(citation)})")
    return lines


def _unique_citation_labels(citations: list[Citation]) -> list[str]:
    labels: list[str] = []
    for citation in citations:
        label = _citation_label(citation)
        if label not in labels:
            labels.append(label)
    return labels


def _clean_answer_sentence(sentence: str) -> str:
    return " ".join(sentence.strip().split()).strip(" -")


def _ensure_sentence_punctuation(sentence: str) -> str:
    sentence = _clean_answer_sentence(sentence)
    if not sentence:
        return sentence
    if sentence[-1] in ".!?":
        return sentence
    return f"{sentence}."


def _best_evidence_sentence(text: str, query_tokens: list[str]) -> str:
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", text)
        if sentence.strip()
    ]
    if not sentences:
        return _clip_text(text)
    query_set = set(query_tokens)
    query_weights = _query_token_weights(query_tokens)
    scored: list[tuple[float, int, str]] = []
    for index, sentence in enumerate(sentences):
        candidate = _table_row_candidate(sentences, index, query_set) or sentence
        sentence_tokens = set(_tokenize(candidate))
        matched_weight = sum(query_weights[token] for token in query_set & sentence_tokens)
        if _requires_threshold_evidence(query_set) and _has_threshold_evidence(candidate):
            matched_weight += 2.0
        scored.append((matched_weight, -index, candidate))
    scored.sort(key=lambda item: item[:2], reverse=True)
    best = scored[0][2] if scored else sentences[0]
    interpreted = _interpreted_inline_threshold_value(text, query_set)
    if interpreted:
        return interpreted
    interpreted = _interpreted_density_table_value(best, query_set)
    if interpreted:
        return interpreted
    interpreted = _interpreted_inline_threshold_value(best, query_set)
    if interpreted:
        return interpreted
    if best in sentences:
        best_index = sentences.index(best)
        if _looks_like_clause_heading(best) and best_index + 1 < len(sentences):
            best = f"{best}: {sentences[best_index + 1]}"
    return _clip_text(best)


def _table_row_candidate(sentences: list[str], index: int, query_tokens: set[str]) -> str | None:
    if not _requires_threshold_evidence(query_tokens) or index + 1 >= len(sentences):
        return None
    sentence = sentences[index]
    next_sentence = sentences[index + 1]
    if not _density_codes(sentence) or not _has_threshold_evidence(next_sentence):
        return None
    if query_tokens & set(_tokenize(next_sentence)):
        return f"{sentence}: {next_sentence}"
    return None


def _interpreted_density_table_value(candidate: str, query_tokens: set[str]) -> str | None:
    requested_codes = sorted(_density_codes_from_tokens(query_tokens))
    if len(requested_codes) != 1 or ":" not in candidate:
        return None

    header, row = (part.strip() for part in candidate.split(":", 1))
    header_codes = _ordered_density_codes(header)
    if requested_codes[0] not in header_codes:
        return None

    values = _threshold_values(row)
    if len(values) < len(header_codes):
        return None

    index = header_codes.index(requested_codes[0])
    row_label = row.split(values[0], 1)[0].strip(" -:;,.").lower()
    if not row_label and {"site", "cover"}.issubset(query_tokens):
        row_label = "site cover"
    elif not row_label:
        return None

    label = _density_table_label(requested_codes[0], row_label, query_tokens)
    return f"{label}: {values[index]}"


def _interpreted_inline_threshold_value(candidate: str, query_tokens: set[str]) -> str | None:
    requested_codes = sorted(_density_codes_from_tokens(query_tokens))
    if len(requested_codes) != 1:
        return None

    if {"street", "setback"}.issubset(query_tokens):
        pattern = rf"\bprimary\s+street\s+{re.escape(requested_codes[0])}\s+(\d+(?:\.\d+)?\s*m)\b"
        match = re.search(pattern, candidate, flags=re.IGNORECASE)
        if match:
            return f"{requested_codes[0].upper()} primary street setback: {match.group(1)}"

    if {"site", "cover"}.issubset(query_tokens):
        pattern = rf"\b{re.escape(requested_codes[0])}\s+maximum\s+site\s+cover\s+(\d+(?:\.\d+)?\s*(?:%|per\s+cent))\b"
        match = re.search(pattern, candidate, flags=re.IGNORECASE)
        if match:
            return f"{requested_codes[0].upper()} site cover: {match.group(1)}"

    if {"open", "space"}.issubset(query_tokens):
        pattern = rf"\b{re.escape(requested_codes[0])}\s+[^.\n:]*minimum\s+open\s+space\s+(?:is\s+)?(\d+(?:\.\d+)?\s*(?:%|per\s+cent))\b"
        match = re.search(pattern, candidate, flags=re.IGNORECASE)
        if match:
            return f"{requested_codes[0].upper()} open space: {match.group(1)}"

    if {"outdoor", "liv"}.issubset(query_tokens):
        area_pattern = rf"\b{re.escape(requested_codes[0])}\s+[^.\n]*minimum\s+outdoor\s+living\s+area\s+(?:is\s+)?(\d+(?:\.\d+)?\s*m2)\b"
        area_match = re.search(area_pattern, candidate, flags=re.IGNORECASE)
        dimension_match = re.search(
            r"\bminimum\s+length\s+and\s+width\s+dimension\s+of\s+(\d+(?:\.\d+)?\s*m)\b",
            candidate,
            flags=re.IGNORECASE,
        )
        if area_match and dimension_match:
            return (
                f"{requested_codes[0].upper()} outdoor living area: "
                f"{area_match.group(1)} minimum area; {dimension_match.group(1)} minimum dimension"
            )
        if area_match:
            return f"{requested_codes[0].upper()} outdoor living area: {area_match.group(1)} minimum area"

    return None


def _density_table_label(density_code: str, row_label: str, query_tokens: set[str]) -> str:
    display_code = density_code.upper()
    if {"street", "setback"}.issubset(query_tokens):
        if "primary street" in row_label:
            return f"{display_code} primary street setback"
        if "secondary street" in row_label:
            return f"{display_code} secondary street setback"
        return f"{display_code} street setback"
    if {"site", "cover"}.issubset(query_tokens):
        return f"{display_code} site cover"
    if {"open", "space"}.issubset(query_tokens):
        return f"{display_code} open space"
    if {"outdoor", "liv"}.issubset(query_tokens):
        return f"{display_code} outdoor living area"
    return f"{display_code} {row_label}"


def _is_interpreted_threshold_sentence(sentence: str) -> bool:
    return bool(re.match(r"^R(?:AC|\d{2,3})\s+[^:]+:\s*\d", sentence, flags=re.IGNORECASE))


def _asks_for_threshold_qualifiers(query_tokens: set[str]) -> bool:
    return bool(
        query_tokens
        & {
            "average",
            "exception",
            "exceptions",
            "reduce",
            "reduction",
            "variation",
            "variations",
        }
    )


def _find_threshold_table_value(
    density_code: str,
    query_tokens: set[str],
    rows: list[tuple[SourceChunk, SourceCitation, SourceVersion, SourceDocument, Clause]],
) -> tuple[str, str, list[Citation]] | None:
    row_texts = [f"{chunk.heading or ''}\n{chunk.text}".strip() for chunk, *_rest in rows]
    for table_index, table_text in enumerate(row_texts):
        if not _is_threshold_table_context(table_text, query_tokens):
            continue

        search_end = min(len(rows), table_index + 12)
        for header_index in range(table_index, search_end):
            header_codes = _ordered_density_codes(row_texts[header_index])
            if density_code not in header_codes or len(set(header_codes)) < 2:
                continue

            for value_index in range(header_index + 1, search_end):
                values = _threshold_values(row_texts[value_index])
                if len(values) < len(header_codes):
                    continue

                value = " ".join(values[header_codes.index(density_code)].split())
                label = _density_table_label(
                    density_code,
                    _table_value_row_label(row_texts[value_index], values[0], query_tokens),
                    query_tokens,
                )
                citation_rows = [rows[table_index][1]]
                citations = _dedupe_citations(
                    [Citation(**from_json(citation_row.citation_json, {})) for citation_row in citation_rows]
                )
                return label, value, citations
    return None


def _is_threshold_table_context(text: str, query_tokens: set[str]) -> bool:
    lowered = text.lower()
    text_tokens = set(_tokenize(text))
    if {"site", "cover"}.issubset(query_tokens):
        return {"site", "cover"}.issubset(text_tokens) and (
            "table" in lowered or "maximum" in text_tokens or "percentage" in text_tokens
        )
    if {"street", "setback"}.issubset(query_tokens):
        return {"street", "setback"}.issubset(text_tokens) and (
            "table" in lowered or "minimum" in text_tokens
        )
    return False


def _table_value_row_label(row_text: str, first_value: str, query_tokens: set[str]) -> str:
    row_label = row_text.split(first_value, 1)[0].strip(" -:;,.").lower()
    if row_label:
        return row_label
    if {"site", "cover"}.issubset(query_tokens):
        return "site cover"
    if {"street", "setback"}.issubset(query_tokens):
        return "primary street"
    return "threshold"


def _is_site_cover_table_context(text: str) -> bool:
    lowered = text.lower()
    text_tokens = set(_tokenize(text))
    return {"site", "cover"}.issubset(text_tokens) and (
        "table" in lowered or "maximum" in text_tokens or "percentage" in text_tokens
    )


def _looks_like_clause_heading(sentence: str) -> bool:
    words = sentence.split()
    return len(words) <= 8 and bool(re.match(r"^(?:clause\s+|cl\.?\s*)?[A-Z]?\d", sentence, re.IGNORECASE))


def _clip_text(text: str, max_chars: int = 280) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    clipped = cleaned[: max_chars - 1].rsplit(" ", 1)[0]
    return f"{clipped}..."


def _citation_label(citation: Citation) -> str:
    parts = [citation.source_title]
    if citation.version_label:
        parts.append(citation.version_label)
    if citation.clause_id:
        parts.append(f"cl {citation.clause_id}")
    elif citation.heading:
        parts.append(citation.heading)
    if citation.page_number:
        parts.append(f"p {citation.page_number}")
    return ", ".join(parts)


def _missing_information_for(question: str) -> list[str]:
    missing = ["Project-specific facts and measurements are not proven by source-library search alone."]
    question_tokens = set(_tokenize(question))
    if question_tokens & {
        "allow",
        "allowed",
        "approval",
        "approve",
        "build",
        "compliance",
        "comply",
        "maximum",
        "minimum",
        "pass",
        "permit",
    }:
        missing.append(
            "A human reviewer must confirm the proposal details, applicable planning scheme, and current council interpretation."
        )
    return missing


def _requires_paid_standard_text(question: str) -> bool:
    lower = question.lower()
    references_standard = bool(re.search(r"\bas\s*\d{3,5}\b", lower)) or "australian standard" in lower
    if not references_standard:
        return False
    if any(term in lower for term in ["mentions", "referenced by", "reference to", "where cited"]):
        return False
    return any(
        term in lower
        for term in [
            "clause",
            "comply",
            "compliance",
            "full text",
            "requirement",
            "requirements",
            "rule",
            "rules",
            "what does",
        ]
    )


def _requires_bushfire_construction_standard_text(question: str) -> bool:
    query_tokens = set(_tokenize(question))
    if not query_tokens & {"bal", "bushfire"}:
        return False
    if query_tokens & {"assessment", "assessor", "report"}:
        return False
    return bool(
        query_tokens & {"build", "construct", "dwelling", "home", "house"}
        and query_tokens
        & {
            "compliance",
            "comply",
            "detail",
            "details",
            "method",
            "requirement",
            "standard",
            "threshold",
        }
    )
