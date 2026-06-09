"""In-memory V3 source library and safe search service."""

from __future__ import annotations

from typing import Any
from dataclasses import replace
from hashlib import sha256
import json
import os
import re
from threading import RLock

from draftcheck.domain.sources.models import (
    AnswerStatus,
    ArtifactKind,
    ArtifactSubjectType,
    ContentAddressedArtifact,
    EmbeddingConfig,
    LicenceStatus,
    SourceAnswer,
    SourceCitation,
    SourceChunk,
    SourceDocument,
    SourceFreshness,
    SourceImportResult,
    SourceNotFoundError,
    SourceRefreshResult,
    SourceReview,
    SourceReviewStatus,
    SourceSearchHit,
    SourceVersion,
    content_addressed_path,
    sha256_hex,
    utc_now,
)


TOKEN_RE = re.compile(r"[a-z0-9]+")
AUSTRALIAN_STANDARD_TITLE_RE = re.compile(
    r"\bAS(?:/NZS)?\s+\d{3,5}(?::\d{4})?\b",
    re.IGNORECASE,
)


def default_embedding_config() -> EmbeddingConfig:
    return EmbeddingConfig(
        provider=os.getenv("DRAFTCHECK_EMBEDDING_PROVIDER", "api"),
        model=os.getenv("DRAFTCHECK_EMBEDDING_MODEL", "text-embedding-3-small"),
        dimension=int(os.getenv("DRAFTCHECK_EMBEDDING_DIMENSION", "1536")),
    )


def _stable_id(prefix: str, *parts: str, length: int = 16) -> str:
    digest = sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:length]}"


def _tokens(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


def _hash_embedding(text: str, config: EmbeddingConfig) -> tuple[float, ...]:
    digest = sha256(f"{config.provider}:{config.model}:{text}".encode("utf-8")).digest()
    values: list[float] = []
    for index in range(config.dimension):
        byte = digest[index % len(digest)]
        values.append(round((byte / 255.0) * 2.0 - 1.0, 6))
    return tuple(values)


def _api_embedding(text: str, config: EmbeddingConfig) -> tuple[float, ...]:
    """Call OpenAI /v1/embeddings via urllib (no SDK dependency)."""
    import json
    import time
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    api_key = os.environ.get("OPENAI_API_KEY", "")
    body = json.dumps({
        "model": config.model,
        "input": text,
        "encoding_format": "float",
        "dimensions": config.dimension,
    }).encode()
    req = Request(
        "https://api.openai.com/v1/embeddings",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    delays = [1.0, 2.0, 4.0]
    last_exc: Exception | None = None
    for delay in [0.0, *delays]:
        if delay:
            time.sleep(delay)
        try:
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            return tuple(data["data"][0]["embedding"])
        except (HTTPError, URLError) as exc:
            last_exc = exc
    raise RuntimeError(f"Embedding API failed after retries: {last_exc}") from last_exc


def _embed(text: str, config: EmbeddingConfig) -> tuple[float, ...]:
    import logging
    provider = os.environ.get("DRAFTCHECK_EMBEDDING_PROVIDER", config.provider)
    app_env = os.environ.get("APP_ENV", "development")
    if provider == "stub" or not os.environ.get("OPENAI_API_KEY"):
        if app_env == "production":
            raise RuntimeError(
                "Real embeddings required in production. "
                "Set OPENAI_API_KEY or DRAFTCHECK_EMBEDDING_PROVIDER=stub to override."
            )
        logging.getLogger(__name__).warning(
            "Using hash embeddings stub (OPENAI_API_KEY not set or DRAFTCHECK_EMBEDDING_PROVIDER=stub). "
            "Vector search will not be meaningful."
        )
        return _hash_embedding(text, config)
    return _api_embedding(text, config)


def _batch_embed(texts: list[str], config: EmbeddingConfig) -> list[tuple[float, ...]]:
    """Embed multiple texts in one API call (up to 100 per batch)."""
    import json
    import time
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    MAX_BATCH = 100
    results: list[tuple[float, ...]] = []
    for i in range(0, len(texts), MAX_BATCH):
        batch = texts[i:i + MAX_BATCH]
        api_key = os.environ.get("OPENAI_API_KEY", "")
        body = json.dumps({
            "model": config.model,
            "input": batch,
            "encoding_format": "float",
            "dimensions": config.dimension,
        }).encode()
        req = Request(
            "https://api.openai.com/v1/embeddings",
            data=body,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        delays = [1.0, 2.0, 4.0]
        last_exc: Exception | None = None
        for delay in [0.0, *delays]:
            if delay:
                time.sleep(delay)
            try:
                with urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read())
                for item in sorted(data["data"], key=lambda x: x["index"]):
                    results.append(tuple(item["embedding"]))
                break
            except (HTTPError, URLError) as exc:
                last_exc = exc
        else:
            raise RuntimeError(f"Batch embedding API failed: {last_exc}") from last_exc
    return results


def _chunk_text(text: str, *, max_chars: int = 1200) -> tuple[str, ...]:
    normalized = text.strip()
    if not normalized:
        return ()
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if not current:
            current = paragraph
            continue
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}"
        else:
            chunks.append(current)
            current = paragraph
    if current:
        chunks.append(current)
    return tuple(chunks)


def _chunk_by_clauses(
    text: str,
    clause_offsets: list[tuple[int, int]],
    *,
    max_chars: int = 1200,
) -> list[str]:
    """Split text at clause boundaries instead of paragraph breaks.

    clause_offsets: list of (start, end) character offsets for each clause body.
    Falls back to paragraph splitting if no offsets provided.
    """
    if not clause_offsets:
        return list(_chunk_text(text, max_chars=max_chars))

    chunks = []
    for start, end in clause_offsets:
        body = text[start:end].strip()
        if not body:
            continue
        # If this clause is longer than max_chars, sub-split by paragraph
        if len(body) <= max_chars:
            chunks.append(body)
        else:
            sub = _chunk_text(body, max_chars=max_chars)
            chunks.extend(sub)
    return chunks


def _safe_quote(text: str, *, max_chars: int = 240) -> str:
    one_line = " ".join(text.split())
    return one_line[:max_chars]


def _looks_like_standards_australia_source(
    *,
    title: str,
    publisher: str | None,
    uri: str | None,
) -> bool:
    normalized_text = " ".join(TOKEN_RE.findall(f"{title} {publisher or ''}".lower()))
    normalized_uri = (uri or "").lower()
    return (
        "standards australia" in normalized_text
        or bool(AUSTRALIAN_STANDARD_TITLE_RE.search(title))
        or "standards org au" in " ".join(TOKEN_RE.findall(normalized_uri))
        or "standards.org.au" in normalized_uri
    )


class InMemorySourceLibrary:
    """Small source library for V3 tests and local contract work."""

    def __init__(self, *, embedding_config: EmbeddingConfig | None = None) -> None:
        self.embedding_config = embedding_config or default_embedding_config()
        self._lock = RLock()
        self.sources: dict[str, SourceDocument] = {}
        self.versions: dict[str, SourceVersion] = {}
        self.version_ids_by_source: dict[str, list[str]] = {}
        self.artifacts: dict[str, ContentAddressedArtifact] = {}
        self.chunks: dict[str, SourceChunk] = {}
        self.chunk_ids_by_version: dict[str, list[str]] = {}
        self.citations: dict[str, SourceCitation] = {}
        self.reviews: list[SourceReview] = []
        self.refresh_requested_at: dict[str, object] = {}

    def import_source(
        self,
        *,
        title: str,
        content: str = "",
        source_id: str | None = None,
        uri: str | None = None,
        publisher: str | None = None,
        licence_status: LicenceStatus = LicenceStatus.OPEN,
        review_status: SourceReviewStatus = SourceReviewStatus.PENDING_REVIEW,
        media_type: str = "text/plain",
        metadata_only: bool = False,
    ) -> SourceImportResult:
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("source title is required")

        licence_status = LicenceStatus(licence_status)
        review_status = SourceReviewStatus(review_status)
        source_id = source_id or _stable_id("src", normalized_title, uri or "")

        standards_australia = _looks_like_standards_australia_source(
            title=normalized_title,
            publisher=publisher,
            uri=uri,
        )
        forced_metadata_only = (
            metadata_only
            or standards_australia
            or not licence_status.can_store_full_text
        )
        stored_text = "" if forced_metadata_only else content.strip()
        artifact_payload = (
            stored_text.encode("utf-8")
            if stored_text
            else json.dumps(
                {
                    "title": normalized_title,
                    "uri": uri,
                    "publisher": publisher,
                    "licence_status": licence_status.value,
                    "metadata_only": True,
                },
                sort_keys=True,
            ).encode("utf-8")
        )
        artifact_sha = sha256_hex(artifact_payload)
        version_id = _stable_id("sv", source_id, artifact_sha)
        now = utc_now()

        with self._lock:
            source = self.sources.get(source_id)
            if source is None:
                source = SourceDocument(
                    id=source_id,
                    title=normalized_title,
                    uri=uri,
                    publisher=publisher,
                    licence_status=licence_status,
                    created_at=now,
                    latest_version_id=None,
                )
                self.sources[source_id] = source

            existing_version = self.versions.get(version_id)
            if existing_version is not None:
                return SourceImportResult(
                    source=self.sources[source_id],
                    version=existing_version,
                    artifacts=tuple(
                        self.artifacts[artifact_id] for artifact_id in existing_version.artifact_ids
                    ),
                    chunks=tuple(
                        self.chunks[chunk_id]
                        for chunk_id in self.chunk_ids_by_version.get(existing_version.id, [])
                    ),
                    citations=tuple(
                        self.citations[self.chunks[chunk_id].citation_id]
                        for chunk_id in self.chunk_ids_by_version.get(existing_version.id, [])
                    ),
                    duplicate=True,
                    metadata_only=existing_version.metadata_only,
                )

            artifact = ContentAddressedArtifact.from_bytes(
                subject_type=ArtifactSubjectType.SOURCE_VERSION,
                subject_id=version_id,
                kind=ArtifactKind.METADATA_ONLY if forced_metadata_only else ArtifactKind.CANONICAL_TEXT,
                content=artifact_payload,
                media_type=media_type if stored_text else "application/json",
                parser_name="draftcheck.sources.in_memory",
                parser_version="v0",
                metadata={"source_id": source_id},
            )
            self.artifacts[artifact.id] = artifact

            version = SourceVersion(
                id=version_id,
                source_id=source_id,
                version_label=f"sha256:{artifact_sha[:12]}",
                sha256=artifact_sha,
                storage_path=content_addressed_path(artifact_sha),
                licence_status=licence_status,
                review_status=review_status,
                fetched_at=now,
                artifact_ids=(artifact.id,),
                metadata_only=forced_metadata_only or not bool(stored_text),
            )
            self.versions[version.id] = version
            self.version_ids_by_source.setdefault(source_id, []).append(version.id)
            self.sources[source_id] = replace(
                source,
                licence_status=licence_status,
                latest_version_id=version.id,
            )

            chunks: list[SourceChunk] = []
            citations: list[SourceCitation] = []
            if stored_text:
                for ordinal, chunk_text in enumerate(_chunk_text(stored_text), start=1):
                    chunk_digest = sha256_hex(chunk_text.encode("utf-8"))
                    chunk_id = f"chk_{version.id}_{ordinal:04d}"
                    citation_id = f"cit_{chunk_id}"
                    chunk = SourceChunk(
                        id=chunk_id,
                        source_id=source_id,
                        source_version_id=version.id,
                        ordinal=ordinal,
                        text=chunk_text,
                        text_sha256=chunk_digest,
                        citation_id=citation_id,
                        embedding_provider=self.embedding_config.provider,
                        embedding_model=self.embedding_config.model,
                        embedding_dimension=self.embedding_config.dimension,
                        embedding=_hash_embedding(chunk_text, self.embedding_config),
                    )
                    citation = SourceCitation(
                        id=citation_id,
                        source_id=source_id,
                        source_version_id=version.id,
                        chunk_id=chunk.id,
                        source_title=normalized_title,
                        locator=f"chunk {ordinal}",
                        quote=_safe_quote(chunk_text),
                        uri=uri,
                    )
                    self.chunks[chunk.id] = chunk
                    self.citations[citation.id] = citation
                    self.chunk_ids_by_version.setdefault(version.id, []).append(chunk.id)
                    chunks.append(chunk)
                    citations.append(citation)

            return SourceImportResult(
                source=self.sources[source_id],
                version=version,
                artifacts=(artifact,),
                chunks=tuple(chunks),
                citations=tuple(citations),
                duplicate=False,
                metadata_only=version.metadata_only,
            )

    def list_sources(self) -> tuple[SourceDocument, ...]:
        with self._lock:
            return tuple(sorted(self.sources.values(), key=lambda source: source.title.lower()))

    def get_source(self, source_id: str) -> SourceDocument:
        with self._lock:
            source = self.sources.get(source_id)
            if source is None:
                raise SourceNotFoundError(f"source not found: {source_id}")
            return source

    def list_versions(self, source_id: str) -> tuple[SourceVersion, ...]:
        with self._lock:
            if source_id not in self.sources:
                raise SourceNotFoundError(f"source not found: {source_id}")
            return tuple(self.versions[version_id] for version_id in self.version_ids_by_source[source_id])

    def get_version(self, source_version_id: str) -> SourceVersion:
        with self._lock:
            version = self.versions.get(source_version_id)
            if version is None:
                raise SourceNotFoundError(f"source version not found: {source_version_id}")
            return version

    def get_chunks_for_version(self, source_version_id: str) -> tuple[SourceChunk, ...]:
        with self._lock:
            if source_version_id not in self.versions:
                raise SourceNotFoundError(f"source version not found: {source_version_id}")
            return tuple(
                self.chunks[chunk_id] for chunk_id in self.chunk_ids_by_version.get(source_version_id, [])
            )

    def review_source(
        self,
        *,
        source_id: str,
        source_version_id: str | None = None,
        review_status: SourceReviewStatus = SourceReviewStatus.APPROVED,
        licence_status: LicenceStatus | None = None,
        org_id: str = "system",
        actor_id: str = "system",
        notes: str | None = None,
    ) -> SourceVersion:
        with self._lock:
            source = self.get_source(source_id)
            version_id = source_version_id or source.latest_version_id
            if version_id is None:
                raise SourceNotFoundError(f"source has no versions: {source_id}")
            version = self.get_version(version_id)
            updated = replace(
                version,
                review_status=SourceReviewStatus(review_status),
                licence_status=LicenceStatus(licence_status) if licence_status else version.licence_status,
            )
            self.versions[version_id] = updated
            if updated.review_status is SourceReviewStatus.APPROVED:
                source_version_ids = self.version_ids_by_source[source.id]
                approved_index = source_version_ids.index(version_id)
                later_approved_ids = [
                    candidate_version_id
                    for candidate_version_id in source_version_ids[approved_index + 1 :]
                    if self.versions[candidate_version_id].review_status is SourceReviewStatus.APPROVED
                ]
                if later_approved_ids:
                    newest_later_approved_id = later_approved_ids[-1]
                    updated = replace(updated, superseded_by_version_id=newest_later_approved_id)
                    self.versions[version_id] = updated
                    superseding_version_id = newest_later_approved_id
                else:
                    superseding_version_id = version_id
                for previous_version_id in source_version_ids[:approved_index]:
                    previous_version = self.versions[previous_version_id]
                    if previous_version.superseded_by_version_id != superseding_version_id:
                        self.versions[previous_version_id] = replace(
                            previous_version,
                            superseded_by_version_id=superseding_version_id,
                        )
            self.sources[source_id] = replace(source, licence_status=updated.licence_status)
            self.reviews.append(
                SourceReview(
                    id=_stable_id("sr", source_id, version_id, actor_id, str(len(self.reviews))),
                    org_id=org_id,
                    source_id=source_id,
                    source_version_id=version_id,
                    review_status=updated.review_status,
                    licence_status=updated.licence_status,
                    actor_id=actor_id,
                    reviewed_at=utc_now(),
                    notes=notes,
                )
            )
            return updated

    def refresh_source(
        self,
        source_id: str,
        *,
        org_id: str | None = None,
        actor_id: str | None = None,
    ) -> SourceRefreshResult:
        del org_id, actor_id
        with self._lock:
            self.get_source(source_id)
            requested_at = utc_now()
            self.refresh_requested_at[source_id] = requested_at
            return SourceRefreshResult(
                source_id=source_id,
                status="refresh_recorded",
                freshness_status="refresh_requested",
                requested_at=requested_at,
            )

    def freshness(self) -> tuple[SourceFreshness, ...]:
        with self._lock:
            rows: list[SourceFreshness] = []
            for source in self.list_sources():
                version = self.versions.get(source.latest_version_id or "")
                refresh_requested_at = self.refresh_requested_at.get(source.id)
                rows.append(
                    SourceFreshness(
                        source_id=source.id,
                        latest_version_id=source.latest_version_id,
                        freshness_status=(
                            "refresh_requested"
                            if refresh_requested_at is not None
                            else "current"
                            if version is not None
                            else "no_versions"
                        ),
                        fetched_at=version.fetched_at if version else None,
                        refresh_requested_at=refresh_requested_at,  # type: ignore[arg-type]
                    )
                )
            return tuple(rows)

    def citable_chunks(self) -> tuple[tuple[SourceChunk, SourceCitation, SourceVersion], ...]:
        with self._lock:
            rows: list[tuple[SourceChunk, SourceCitation, SourceVersion]] = []
            for chunk in self.chunks.values():
                version = self.versions[chunk.source_version_id]
                if not version.can_support_citable_retrieval:
                    continue
                rows.append((chunk, self.citations[chunk.citation_id], version))
            return tuple(rows)


class InMemorySourceSearchService:
    """Simple lexical retrieval with cite-or-refuse answer composition."""

    def __init__(self, library: InMemorySourceLibrary) -> None:
        self.library = library

    def search_chunks(self, query: str, *, limit: int = 8) -> tuple[SourceSearchHit, ...]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return ()
        hits: list[SourceSearchHit] = []
        for chunk, citation, version in self.library.citable_chunks():
            chunk_tokens = _tokens(chunk.text)
            overlap = query_tokens & chunk_tokens
            if not overlap:
                continue
            score = len(overlap) / max(len(query_tokens), 1)
            if query.lower() in chunk.text.lower():
                score += 0.25
            hits.append(SourceSearchHit(chunk=chunk, citation=citation, version=version, score=score))
        hits.sort(key=lambda hit: (-hit.score, hit.chunk.source_version_id, hit.chunk.ordinal))
        return tuple(hits[:limit])

    def ask(self, question: str, *, limit: int = 4) -> SourceAnswer:
        hits = self.search_chunks(question, limit=limit)
        if not hits:
            return SourceAnswer(
                status=AnswerStatus.UNSUPPORTED,
                answer=(
                    "Unsupported: no approved source version citations were found for this question."
                ),
                citations=(),
                source_version_ids=(),
                missing_information=("approved source version citation",),
                needs_verification=True,
            )

        citations = tuple(hit.citation for hit in hits)
        source_version_ids = tuple(dict.fromkeys(hit.version.id for hit in hits))
        excerpts = " ".join(_safe_quote(hit.chunk.text, max_chars=180) for hit in hits)
        return SourceAnswer(
            status=AnswerStatus.SUPPORTED_BY_APPROVED_SOURCES,
            answer=f"Based on the matched approved source chunks: {excerpts}",
            citations=citations,
            source_version_ids=source_version_ids,
            assumptions=(),
            missing_information=(),
            confidence=min(0.95, 0.5 + sum(hit.score for hit in hits) / max(len(hits), 1) / 2),
            needs_verification=True,
            risk_level="unknown",
        )


class SqlAlchemySourceSearchService:
    """Hybrid FTS + pgvector search backed by PostgreSQL."""

    def __init__(
        self,
        session_factory: Any,
        embedding_config: EmbeddingConfig | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._embedding_config = embedding_config or default_embedding_config()

    def search_chunks(self, query: str, *, limit: int = 8) -> tuple[SourceSearchHit, ...]:
        from sqlalchemy import text as sqla_text

        if not query or not query.strip():
            return ()

        session = self._session_factory()
        try:
            recall_limit = limit * 5

            fts_sql = sqla_text("""
                SELECT
                    sc.id AS chunk_id,
                    sc.source_version_id,
                    sc.chunk_index,
                    sc.text AS chunk_text,
                    sc.embedding,
                    sc.embedding_provider,
                    sc.embedding_model,
                    sc.embedding_dimension,
                    sc.section_ref AS chunk_section_ref,
                    sv.id AS version_id,
                    sv.source_id,
                    sv.version_label,
                    sv.sha256 AS version_sha256,
                    sv.storage_manifest_json,
                    sv.licence_status,
                    sv.review_status,
                    sv.fetched_at,
                    sv.published_at,
                    sv.effective_from,
                    sv.effective_to,
                    sv.superseded_by_version_id,
                    sv.metadata_json AS version_metadata_json,
                    sd.title AS source_title,
                    sd.canonical_url,
                    scit.id AS citation_id,
                    scit.section_ref AS citation_section_ref,
                    scit.quote AS citation_quote,
                    ts_rank_cd(
                        to_tsvector('english', sc.text),
                        websearch_to_tsquery('english', :q)
                    ) AS fts_score
                FROM source_chunks sc
                JOIN source_versions sv ON sv.id = sc.source_version_id
                JOIN source_documents sd ON sd.id = sv.source_id
                LEFT JOIN source_citations scit ON scit.source_chunk_id = sc.id
                WHERE sv.review_status = 'approved'
                  AND to_tsvector('english', sc.text) @@ websearch_to_tsquery('english', :q)
                ORDER BY fts_score DESC
                LIMIT :recall_limit
            """)
            fts_rows = session.execute(fts_sql, {"q": query, "recall_limit": recall_limit}).fetchall()

            if not fts_rows:
                return ()

            # Vector re-rank using stored embeddings and a hash-based query vector
            query_vec = _hash_embedding(query, self._embedding_config)
            max_fts = max((float(r.fts_score) for r in fts_rows), default=1.0) or 1.0

            scored: list[tuple[Any, float]] = []
            for r in fts_rows:
                fts_norm = float(r.fts_score) / max_fts
                emb = r.embedding
                if emb:
                    vec = list(emb)
                    qv = list(query_vec)
                    min_len = min(len(vec), len(qv))
                    dot = sum(vec[i] * qv[i] for i in range(min_len))
                    norm_v = sum(x * x for x in vec[:min_len]) ** 0.5 or 1.0
                    norm_q = sum(x * x for x in qv[:min_len]) ** 0.5 or 1.0
                    cosine_sim = dot / (norm_v * norm_q)
                    hybrid = 0.4 * fts_norm + 0.6 * max(0.0, cosine_sim)
                else:
                    hybrid = fts_norm
                scored.append((r, hybrid))

            scored.sort(key=lambda x: x[1], reverse=True)
            top_rows = scored[:limit]

            hits: list[SourceSearchHit] = []
            for r, score in top_rows:
                storage_manifest = dict(r.storage_manifest_json or {})
                artifact_ids_raw = storage_manifest.get("artifact_ids", [])
                artifact_ids = artifact_ids_raw if isinstance(artifact_ids_raw, list) else []
                version_meta = dict(r.version_metadata_json or {})
                storage_path = str(
                    storage_manifest.get("storage_path")
                    or content_addressed_path(r.version_sha256)
                )

                version = SourceVersion(
                    id=str(r.version_id),
                    source_id=str(r.source_id),
                    version_label=r.version_label or f"sha256:{r.version_sha256[:12]}",
                    sha256=r.version_sha256,
                    storage_path=storage_path,
                    licence_status=LicenceStatus(r.licence_status),
                    review_status=SourceReviewStatus(r.review_status),
                    fetched_at=r.fetched_at,
                    published_at=r.published_at,
                    effective_from=r.effective_from,
                    effective_to=r.effective_to,
                    superseded_by_version_id=(
                        str(r.superseded_by_version_id) if r.superseded_by_version_id else None
                    ),
                    artifact_ids=tuple(str(v) for v in artifact_ids),
                    metadata_only=bool(
                        version_meta.get("metadata_only")
                        or storage_manifest.get("metadata_only")
                    ),
                )

                citation_id = str(r.citation_id) if r.citation_id else _stable_id(
                    "cit", str(r.chunk_id)
                )
                chunk_text_val: str = r.chunk_text
                chunk = SourceChunk(
                    id=str(r.chunk_id),
                    source_id=str(r.source_id),
                    source_version_id=str(r.version_id),
                    ordinal=r.chunk_index,
                    text=chunk_text_val,
                    text_sha256=sha256(chunk_text_val.encode("utf-8")).hexdigest(),
                    citation_id=citation_id,
                    embedding_provider=r.embedding_provider,
                    embedding_model=r.embedding_model,
                    embedding_dimension=r.embedding_dimension,
                    embedding=tuple(list(r.embedding) if r.embedding else []),
                )

                locator = r.citation_section_ref or r.chunk_section_ref or f"chunk {r.chunk_index}"
                quote = r.citation_quote or _safe_quote(chunk_text_val)
                citation = SourceCitation(
                    id=citation_id,
                    source_id=str(r.source_id),
                    source_version_id=str(r.version_id),
                    chunk_id=str(r.chunk_id),
                    source_title=r.source_title,
                    locator=locator,
                    quote=quote,
                    uri=r.canonical_url,
                )

                hits.append(SourceSearchHit(chunk=chunk, citation=citation, version=version, score=score))

            return tuple(hits)
        finally:
            session.close()

    def ask(self, question: str, *, limit: int = 4) -> SourceAnswer:
        hits = self.search_chunks(question, limit=limit)
        if not hits:
            return SourceAnswer(
                status=AnswerStatus.UNSUPPORTED,
                answer=(
                    "Unsupported: no approved source version citations were found for this question."
                ),
                citations=(),
                source_version_ids=(),
                missing_information=("approved source version citation",),
                needs_verification=True,
            )

        citations = tuple(hit.citation for hit in hits)
        source_version_ids = tuple(dict.fromkeys(hit.version.id for hit in hits))
        excerpts = " ".join(_safe_quote(hit.chunk.text, max_chars=180) for hit in hits)
        return SourceAnswer(
            status=AnswerStatus.SUPPORTED_BY_APPROVED_SOURCES,
            answer=f"Based on the matched approved source chunks: {excerpts}",
            citations=citations,
            source_version_ids=source_version_ids,
            assumptions=(),
            missing_information=(),
            confidence=min(0.95, 0.5 + sum(hit.score for hit in hits) / max(len(hits), 1) / 2),
            needs_verification=True,
            risk_level="unknown",
        )
