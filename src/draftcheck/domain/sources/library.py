"""In-memory V3 source library and safe search service."""

from __future__ import annotations

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
        reviewer_id: str = "system",
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
                    id=_stable_id("sr", source_id, version_id, reviewer_id, str(len(self.reviews))),
                    org_id=org_id,
                    source_id=source_id,
                    source_version_id=version_id,
                    review_status=updated.review_status,
                    licence_status=updated.licence_status,
                    reviewer_id=reviewer_id,
                    reviewed_at=utc_now(),
                    notes=notes,
                )
            )
            return updated

    def refresh_source(self, source_id: str) -> SourceRefreshResult:
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
                human_review_required=True,
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
            human_review_required=True,
            risk_level="unknown",
        )
