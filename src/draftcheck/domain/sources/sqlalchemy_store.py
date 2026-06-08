"""PostgreSQL-backed V3 source library."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime
from hashlib import sha256
import json
import re
from typing import Any, cast
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from draftcheck.db.engine import create_session_factory
from draftcheck.db.models import (
    Artifact as DbArtifact,
    Source as DbSource,
    SourceChunk as DbSourceChunk,
    SourceCitation as DbSourceCitation,
    SourceFetchLog as DbSourceFetchLog,
    SourceReviewRecord as DbSourceReviewRecord,
    SourceVersion as DbSourceVersion,
)
from draftcheck.domain.sources.fetching import CandidateSourceLink, fetch_public_source, infer_source_type
from draftcheck.domain.sources.library import (
    _chunk_text,
    _hash_embedding,
    _safe_quote,
    default_embedding_config,
)
from draftcheck.domain.sources.models import (
    ArtifactKind,
    ArtifactSubjectType,
    ContentAddressedArtifact,
    EmbeddingConfig,
    LicenceStatus,
    SourceCitation,
    SourceChunk,
    SourceDocument,
    SourceFreshness,
    SourceImportResult,
    SourceNotFoundError,
    SourceRefreshResult,
    SourceReviewStatus,
    SourceVersion,
    content_addressed_path,
)


class SqlAlchemySourceLibrary:
    """Durable source library for the live V3 app.

    Retrieval stays conservative: only approved, non-metadata source versions
    with citations can support `/search/ask`.
    """

    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        embedding_config: EmbeddingConfig | None = None,
    ) -> None:
        self._session_factory = session_factory
        self.embedding_config = embedding_config or default_embedding_config()

    @classmethod
    def from_database_url(
        cls,
        database_url: str,
        *,
        embedding_config: EmbeddingConfig | None = None,
    ) -> SqlAlchemySourceLibrary:
        return cls(
            create_session_factory(database_url),
            embedding_config=embedding_config,
        )

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
        jurisdiction: str = "WA",
        authority: str | None = None,
        local_government: str | None = None,
        source_type: str = "uploaded_text",
        access_type: str = "public",
        licence_notes: str | None = None,
        version_label: str | None = None,
        source_metadata: Mapping[str, object] | None = None,
        version_metadata: Mapping[str, object] | None = None,
        effective_from: datetime | None = None,
        published_at: datetime | None = None,
    ) -> SourceImportResult:
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("source title is required")

        normalized_authority = (authority or publisher or "Unknown authority").strip()
        normalized_jurisdiction = jurisdiction.strip() or "WA"
        normalized_source_type = source_type.strip() or "uploaded_text"
        normalized_access_type = access_type.strip() or "public"
        licence_status = LicenceStatus(licence_status)
        review_status = SourceReviewStatus(review_status)
        stored_text = content.strip() if content and not metadata_only else ""
        payload = _artifact_payload(
            title=normalized_title,
            content=stored_text,
            uri=uri,
            publisher=publisher or normalized_authority,
            licence_status=licence_status,
            metadata_only=metadata_only or not bool(stored_text),
        )
        artifact_sha = sha256(payload).hexdigest()

        with self._session_factory() as session:
            try:
                with session.begin():
                    db_source = self._get_or_create_source(
                        session,
                        source_id=source_id,
                        title=normalized_title,
                        authority=normalized_authority,
                        jurisdiction=normalized_jurisdiction,
                        local_government=local_government,
                        source_type=normalized_source_type,
                        canonical_url=uri,
                        access_type=normalized_access_type,
                        licence_notes=licence_notes,
                        metadata=source_metadata,
                    )
                    duplicate_version = session.scalar(
                        select(DbSourceVersion).where(
                            DbSourceVersion.source_id == db_source.id,
                            DbSourceVersion.sha256 == artifact_sha,
                        )
                    )
                    if duplicate_version is not None:
                        return self._import_result(
                            session,
                            db_source,
                            duplicate_version,
                            duplicate=True,
                        )

                    version_id = uuid4()
                    metadata_only_version = metadata_only or not bool(stored_text)
                    artifact = ContentAddressedArtifact.from_bytes(
                        subject_type=ArtifactSubjectType.SOURCE_VERSION,
                        subject_id=str(version_id),
                        kind=(
                            ArtifactKind.METADATA_ONLY
                            if metadata_only_version
                            else ArtifactKind.CANONICAL_TEXT
                        ),
                        content=payload,
                        media_type=media_type if stored_text else "application/json",
                        parser_name="draftcheck.sources.sqlalchemy",
                        parser_version="v0",
                        metadata={"source_id": str(db_source.id)},
                    )
                    db_artifact = DbArtifact(
                        id=uuid4(),
                        org_id=db_source.org_id,
                        subject_type=artifact.subject_type.value,
                        subject_id=version_id,
                        kind=artifact.kind.value,
                        storage_path=artifact.storage_path,
                        sha256=artifact.sha256,
                        media_type=artifact.media_type,
                        size_bytes=artifact.size_bytes,
                        parser_name=artifact.parser_name,
                        parser_version=artifact.parser_version,
                        metadata_json=artifact.metadata,
                    )
                    db_version = DbSourceVersion(
                        id=version_id,
                        source_id=db_source.id,
                        version_label=version_label or f"sha256:{artifact_sha[:12]}",
                        sha256=artifact_sha,
                        storage_manifest_json={
                            "storage_path": content_addressed_path(artifact_sha),
                            "artifact_ids": [str(db_artifact.id)],
                            "metadata_only": metadata_only_version,
                        },
                        licence=licence_notes,
                        licence_status=licence_status.value,
                        review_status=review_status.value,
                        effective_from=effective_from,
                        published_at=published_at,
                        metadata_json={
                            **dict(version_metadata or {}),
                            "metadata_only": metadata_only_version,
                            "media_type": media_type,
                            "source_store": "sqlalchemy",
                        },
                    )
                    session.add(db_artifact)
                    session.add(db_version)
                    session.flush()
                    if stored_text:
                        self._insert_chunks_and_citations(
                            session,
                            db_source=db_source,
                            db_version=db_version,
                            text=stored_text,
                        )
                    session.flush()
                    return self._import_result(session, db_source, db_version, duplicate=False)
            except IntegrityError:
                session.rollback()
                with session.begin():
                    db_source = self._get_existing_source(
                        session,
                        source_id=source_id,
                        authority=normalized_authority,
                        canonical_url=uri,
                        title=normalized_title,
                    )
                    duplicate_db_version = session.scalar(
                        select(DbSourceVersion).where(
                            DbSourceVersion.source_id == db_source.id,
                            DbSourceVersion.sha256 == artifact_sha,
                        )
                    )
                    if duplicate_db_version is None:
                        raise
                    return self._import_result(session, db_source, duplicate_db_version, duplicate=True)

    def import_manifest_entry(self, entry: Mapping[str, Any]) -> SourceImportResult:
        title = str(entry.get("title") or "").strip()
        if not title:
            raise ValueError("manifest source title is required")
        version_label = str(entry.get("version_label") or "anchor-only")
        content = str(entry.get("content") or "")
        licence_notes = str(entry.get("licence_notes") or "")
        metadata_only = (
            not content.strip()
            or version_label == "anchor-only"
            or "metadata only" in licence_notes.lower()
            or "example fixture" in licence_notes.lower()
        )
        metadata = {
            "manifest_source": "data/seed/source_manifest.example.yaml",
            "scrape_allowed": bool(entry.get("scrape_allowed", False)),
            "licence_notes": licence_notes,
            "version_label": version_label,
            "pending_review_reason": "manifest anchor requires lawful fetch and human approval",
        }
        return self.import_source(
            title=title,
            content=content,
            uri=_optional_str(entry.get("canonical_url")),
            publisher=_optional_str(entry.get("authority")),
            licence_status=LicenceStatus.PENDING_REVIEW,
            review_status=SourceReviewStatus.PENDING_REVIEW,
            metadata_only=metadata_only,
            jurisdiction=str(entry.get("jurisdiction") or "WA"),
            authority=_optional_str(entry.get("authority")),
            local_government=_optional_str(entry.get("local_government")),
            source_type=str(entry.get("source_type") or "source_anchor"),
            access_type=str(entry.get("access_type") or "public"),
            licence_notes=licence_notes,
            version_label=version_label,
            source_metadata=metadata,
            version_metadata=metadata,
            effective_from=_parse_manifest_datetime(entry.get("effective_date")),
            published_at=_parse_manifest_datetime(entry.get("published_date")),
        )

    def seed_manifest(
        self,
        manifest: Mapping[str, Any],
        *,
        local_government: str | None = None,
        org_id: UUID | None = None,
        requested_by_user_id: UUID | None = None,
    ) -> dict[str, object]:
        sources = manifest.get("sources")
        if not isinstance(sources, list):
            raise ValueError("manifest must contain a sources list")
        imported = 0
        duplicates = 0
        skipped = 0
        fetch_logs = 0
        items: list[dict[str, object]] = []
        normalized_local_government = local_government.strip().lower() if local_government else None
        for entry in sources:
            if not isinstance(entry, Mapping):
                skipped += 1
                continue
            entry_local_government = str(entry.get("local_government") or "").strip()
            if normalized_local_government and entry_local_government.lower() != normalized_local_government:
                skipped += 1
                continue
            result = self.import_manifest_entry(entry)
            if result.duplicate:
                duplicates += 1
            else:
                imported += 1
            if org_id and requested_by_user_id:
                self.record_fetch_log(
                    source_id=result.source.id,
                    source_version_id=result.version.id,
                    org_id=org_id,
                    requested_by_user_id=requested_by_user_id,
                    fetch_kind="manifest_anchor",
                    status=_manifest_fetch_status(entry, result.metadata_only),
                    metadata={
                        "canonical_url": entry.get("canonical_url"),
                        "source_type": entry.get("source_type"),
                        "version_label": entry.get("version_label"),
                        "scrape_allowed": bool(entry.get("scrape_allowed", False)),
                        "note": "Manifest anchor recorded; full fetch/review remains gated.",
                    },
                )
                fetch_logs += 1
            items.append(
                {
                    "source_id": result.source.id,
                    "source_version_id": result.version.id,
                    "title": result.source.title,
                    "duplicate": result.duplicate,
                    "metadata_only": result.metadata_only,
                    "review_status": result.version.review_status.value,
                    "licence_status": result.version.licence_status.value,
                }
            )
        return {
            "imported": imported,
            "duplicates": duplicates,
            "skipped": skipped,
            "fetch_logs": fetch_logs,
            "items": items,
        }

    def fetch_pending_sources(
        self,
        *,
        local_government: str | None = None,
        limit: int = 5,
        org_id: UUID,
        requested_by_user_id: UUID,
        force: bool = False,
    ) -> dict[str, object]:
        candidates = self._pending_fetch_candidates(
            local_government=local_government,
            limit=limit,
            force=force,
        )
        fetched = 0
        failed = 0
        skipped = 0
        items: list[dict[str, object]] = []
        for candidate in candidates:
            if not candidate["canonical_url"]:
                skipped += 1
                continue
            try:
                public_source = fetch_public_source(
                    str(candidate["canonical_url"]),
                    licence_notes=str(candidate.get("licence_notes") or ""),
                )
                candidate_metadata = candidate.get("metadata")
                source_metadata = (
                    candidate_metadata
                    if isinstance(candidate_metadata, Mapping)
                    else {}
                )
                result = self.import_source(
                    title=str(candidate["title"]),
                    content=public_source.text,
                    uri=str(candidate["canonical_url"]),
                    publisher=str(candidate["authority"]),
                    licence_status=LicenceStatus.PENDING_REVIEW,
                    review_status=SourceReviewStatus.PENDING_REVIEW,
                    media_type="text/plain",
                    metadata_only=False,
                    jurisdiction=str(candidate["jurisdiction"]),
                    authority=str(candidate["authority"]),
                    local_government=_optional_str(candidate.get("local_government")),
                    source_type=str(candidate["source_type"]),
                    access_type=str(candidate["access_type"]),
                    licence_notes=str(candidate.get("licence_notes") or ""),
                    version_label=f"fetched:{public_source.sha256[:12]}",
                    source_metadata=source_metadata,
                    version_metadata=public_source.metadata,
                )
                self.record_fetch_log(
                    source_id=result.source.id,
                    source_version_id=result.version.id,
                    org_id=org_id,
                    requested_by_user_id=requested_by_user_id,
                    fetch_kind="public_source_fetch",
                    status="success",
                    metadata=public_source.metadata,
                    completed=True,
                )
                fetched += 1
                items.append(
                    {
                        "source_id": result.source.id,
                        "source_version_id": result.version.id,
                        "title": result.source.title,
                        "status": "success",
                        "duplicate": result.duplicate,
                        "chunk_count": len(result.chunks),
                        "citation_count": len(result.citations),
                        "review_status": result.version.review_status.value,
                    }
                )
            except (httpx.HTTPError, ValueError) as exc:
                self.record_fetch_log(
                    source_id=str(candidate["source_id"]),
                    source_version_id=_optional_str(candidate.get("source_version_id")),
                    org_id=org_id,
                    requested_by_user_id=requested_by_user_id,
                    fetch_kind="public_source_fetch",
                    status="failed",
                    metadata={"canonical_url": candidate["canonical_url"]},
                    error=str(exc),
                    completed=True,
                )
                failed += 1
                items.append(
                    {
                        "source_id": str(candidate["source_id"]),
                        "title": str(candidate["title"]),
                        "status": "failed",
                        "error": str(exc),
                    }
                )
        return {
            "fetched": fetched,
            "failed": failed,
            "skipped": skipped,
            "items": items,
        }

    def discover_child_sources(
        self,
        *,
        local_government: str | None = None,
        limit: int = 50,
        org_id: UUID,
        requested_by_user_id: UUID,
    ) -> dict[str, object]:
        """Register discovered child source links as pending-review fetch targets."""

        parents = self._child_discovery_candidates(local_government=local_government)
        links_seen = 0
        discovered = 0
        duplicates = 0
        skipped = 0
        items: list[dict[str, object]] = []
        for parent in parents:
            if discovered >= limit:
                break
            candidate_links = cast(tuple[CandidateSourceLink, ...], parent["candidate_links"])
            for link in candidate_links:
                links_seen += 1
                if discovered >= limit:
                    break
                if not isinstance(link, CandidateSourceLink) or not _is_public_http_url(link.url):
                    skipped += 1
                    continue
                if link.url == parent.get("canonical_url"):
                    skipped += 1
                    continue
                authority = _authority_for_discovered_link(
                    link.url,
                    fallback=str(parent["authority"]),
                )
                source_metadata = {
                    "discovery_source": "source_child_link",
                    "discovered_from_source_id": str(parent["source_id"]),
                    "discovered_from_source_version_id": str(parent["source_version_id"]),
                    "discovered_from_url": parent.get("canonical_url"),
                    "discovery_label": link.label,
                    "licence_notes": "Discovered from official public source page; fetch, licence, currency, and source-version review required before citation.",
                    "pending_review_reason": "Discovered child source requires lawful fetch and human approval.",
                }
                result = self.import_source(
                    title=link.label or _title_from_url(link.url),
                    content="",
                    uri=link.url,
                    publisher=authority,
                    licence_status=LicenceStatus.PENDING_REVIEW,
                    review_status=SourceReviewStatus.PENDING_REVIEW,
                    metadata_only=True,
                    jurisdiction=str(parent["jurisdiction"]),
                    authority=authority,
                    local_government=_optional_str(parent.get("local_government")),
                    source_type=link.source_type,
                    access_type=str(parent["access_type"]),
                    licence_notes=str(source_metadata["licence_notes"]),
                    version_label="discovered-anchor",
                    source_metadata=source_metadata,
                    version_metadata=source_metadata,
                )
                if result.duplicate:
                    duplicates += 1
                    status = "duplicate"
                else:
                    discovered += 1
                    status = "pending_fetch"
                self.record_fetch_log(
                    source_id=result.source.id,
                    source_version_id=result.version.id,
                    org_id=org_id,
                    requested_by_user_id=requested_by_user_id,
                    fetch_kind="source_link_discovery",
                    status=status,
                    metadata={
                        "url": link.url,
                        "label": link.label,
                        "source_type": link.source_type,
                        "discovered_from_source_id": str(parent["source_id"]),
                    },
                    completed=status == "duplicate",
                )
                items.append(
                    {
                        "source_id": result.source.id,
                        "source_version_id": result.version.id,
                        "title": result.source.title,
                        "canonical_url": link.url,
                        "source_type": link.source_type,
                        "status": status,
                    }
                )
        return {
            "discovered": discovered,
            "duplicates": duplicates,
            "skipped": skipped,
            "links_seen": links_seen,
            "items": items,
        }

    def list_sources(self) -> tuple[SourceDocument, ...]:
        with self._session_factory() as session:
            rows = session.scalars(select(DbSource).order_by(DbSource.title)).all()
            return tuple(self._source_document(session, row) for row in rows)

    def get_source(self, source_id: str) -> SourceDocument:
        with self._session_factory() as session:
            row = self._get_source_by_id(session, source_id)
            return self._source_document(session, row)

    def list_versions(self, source_id: str) -> tuple[SourceVersion, ...]:
        with self._session_factory() as session:
            row = self._get_source_by_id(session, source_id)
            versions = session.scalars(
                select(DbSourceVersion)
                .where(DbSourceVersion.source_id == row.id)
                .order_by(DbSourceVersion.fetched_at.desc(), DbSourceVersion.created_at.desc())
            ).all()
            return tuple(self._source_version(version) for version in versions)

    def get_version(self, source_version_id: str) -> SourceVersion:
        with self._session_factory() as session:
            row = self._get_version_by_id(session, source_version_id)
            return self._source_version(row)

    def get_chunks_for_version(self, source_version_id: str) -> tuple[SourceChunk, ...]:
        with self._session_factory() as session:
            version = self._get_version_by_id(session, source_version_id)
            chunks = session.scalars(
                select(DbSourceChunk)
                .where(DbSourceChunk.source_version_id == version.id)
                .order_by(DbSourceChunk.chunk_index)
            ).all()
            return tuple(self._source_chunk(chunk, version) for chunk in chunks)

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
        with self._session_factory() as session:
            with session.begin():
                source = self._get_source_by_id(session, source_id)
                version = (
                    self._get_version_by_id(session, source_version_id)
                    if source_version_id
                    else self._latest_version(session, source)
                )
                if version is None:
                    raise SourceNotFoundError(f"source has no versions: {source_id}")
                version.review_status = SourceReviewStatus(review_status).value
                if licence_status is not None:
                    version.licence_status = LicenceStatus(licence_status).value
                if SourceReviewStatus(version.review_status) is SourceReviewStatus.APPROVED:
                    self._supersede_older_approved_versions(session, version)
                session.add(
                    DbSourceReviewRecord(
                        id=uuid4(),
                        org_id=_uuid_from_string(org_id, "org_id"),
                        source_id=source.id,
                        source_version_id=version.id,
                        reviewer_user_id=_uuid_from_string(reviewer_id, "reviewer_id"),
                        review_status=version.review_status,
                        licence_status=version.licence_status,
                        notes=notes,
                        decision_metadata_json={
                            "review_path": "api",
                            "answer_policy": "cite_or_refuse",
                        },
                    )
                )
                session.flush()
                return self._source_version(version)

    def refresh_source(
        self,
        source_id: str,
        *,
        org_id: str | None = None,
        reviewer_id: str | None = None,
    ) -> SourceRefreshResult:
        with self._session_factory() as session:
            with session.begin():
                source = self._get_source_by_id(session, source_id)
                version = self._latest_version(session, source)
                requested_at = _utc_now()
                if org_id and reviewer_id:
                    session.add(
                        DbSourceFetchLog(
                            id=uuid4(),
                            org_id=_uuid_from_string(org_id, "org_id"),
                            source_id=source.id,
                            source_version_id=version.id if version else None,
                            requested_by_user_id=_uuid_from_string(reviewer_id, "reviewer_id"),
                            fetch_kind="refresh_requested",
                            status="pending_fetch",
                            requested_at=requested_at,
                            metadata_json={
                                "note": "Reviewer requested lawful source refresh.",
                                "answer_policy": "cite_or_refuse",
                            },
                        )
                    )
                else:
                    metadata = dict(source.metadata_json or {})
                    metadata["refresh_requested_at"] = requested_at.isoformat()
                    source.metadata_json = metadata
                session.flush()
                return SourceRefreshResult(
                    source_id=str(source.id),
                    status="refresh_recorded",
                    freshness_status="refresh_requested",
                    requested_at=requested_at,
                )

    def freshness(self) -> tuple[SourceFreshness, ...]:
        with self._session_factory() as session:
            rows: list[SourceFreshness] = []
            for source in session.scalars(select(DbSource).order_by(DbSource.title)).all():
                version = self._latest_version(session, source)
                fetch_log = self._latest_fetch_log(session, source)
                refresh_requested_at = (
                    fetch_log.requested_at
                    if fetch_log is not None and fetch_log.status in {"pending_fetch", "refresh_requested"}
                    else None
                )
                rows.append(
                    SourceFreshness(
                        source_id=str(source.id),
                        latest_version_id=str(version.id) if version else None,
                        freshness_status=(
                            "refresh_requested"
                            if refresh_requested_at is not None
                            else "current"
                            if version is not None
                            else "no_versions"
                        ),
                        fetched_at=version.fetched_at if version else None,
                        refresh_requested_at=refresh_requested_at,
                    )
                )
            return tuple(rows)

    def citable_chunks(self) -> tuple[tuple[SourceChunk, SourceCitation, SourceVersion], ...]:
        with self._session_factory() as session:
            rows = session.execute(
                select(DbSourceChunk, DbSourceCitation, DbSourceVersion, DbSource)
                .join(DbSourceVersion, DbSourceVersion.id == DbSourceChunk.source_version_id)
                .join(DbSource, DbSource.id == DbSourceVersion.source_id)
                .join(DbSourceCitation, DbSourceCitation.source_chunk_id == DbSourceChunk.id)
                .order_by(DbSourceChunk.chunk_index)
            ).all()
            citable: list[tuple[SourceChunk, SourceCitation, SourceVersion]] = []
            for chunk, citation, version, source in rows:
                domain_version = self._source_version(version)
                if not domain_version.can_support_citable_retrieval:
                    continue
                domain_chunk = self._source_chunk(chunk, version, citation_id=str(citation.id))
                citable.append(
                    (
                        domain_chunk,
                        self._source_citation(citation, chunk, version, source),
                        domain_version,
                    )
                )
            return tuple(citable)

    def record_fetch_log(
        self,
        *,
        source_id: str,
        source_version_id: str | None,
        org_id: UUID,
        requested_by_user_id: UUID,
        fetch_kind: str,
        status: str,
        metadata: Mapping[str, object] | None = None,
        error: str | None = None,
        completed: bool = False,
    ) -> None:
        with self._session_factory() as session:
            with session.begin():
                source = self._get_source_by_id(session, source_id)
                version = (
                    self._get_version_by_id(session, source_version_id)
                    if source_version_id
                    else self._latest_version(session, source)
                )
                session.add(
                    DbSourceFetchLog(
                        id=uuid4(),
                        org_id=org_id,
                        source_id=source.id,
                        source_version_id=version.id if version else None,
                        requested_by_user_id=requested_by_user_id,
                        fetch_kind=fetch_kind,
                        status=status,
                        completed_at=_utc_now() if completed else None,
                        error=error,
                        metadata_json=dict(metadata or {}),
                    )
                )

    def _pending_fetch_candidates(
        self,
        *,
        local_government: str | None,
        limit: int,
        force: bool,
    ) -> list[dict[str, object]]:
        with self._session_factory() as session:
            statement = select(DbSource).where(DbSource.canonical_url.is_not(None)).order_by(
                DbSource.authority,
                DbSource.title,
            )
            if local_government:
                statement = statement.where(DbSource.local_government == local_government)
            candidates: list[dict[str, object]] = []
            for source in session.scalars(statement).all():
                latest = self._latest_version(session, source)
                latest_fetch = self._latest_fetch_log(session, source)
                if not force:
                    latest_domain = self._source_version(latest) if latest else None
                    already_fetched = latest_domain is not None and not latest_domain.metadata_only
                    latest_succeeded = latest_fetch is not None and latest_fetch.status == "success"
                    if already_fetched or latest_succeeded:
                        continue
                candidates.append(
                    {
                        "source_id": str(source.id),
                        "source_version_id": str(latest.id) if latest else None,
                        "title": source.title,
                        "jurisdiction": source.jurisdiction,
                        "authority": source.authority,
                        "local_government": source.local_government,
                        "source_type": source.source_type,
                        "canonical_url": source.canonical_url,
                        "access_type": source.access_type,
                        "licence_notes": (source.metadata_json or {}).get("licence_notes"),
                        "metadata": dict(source.metadata_json or {}),
                    }
                )
                if len(candidates) >= limit:
                    break
            return candidates

    def _child_discovery_candidates(
        self,
        *,
        local_government: str | None,
    ) -> list[dict[str, object]]:
        with self._session_factory() as session:
            statement = select(DbSource).where(DbSource.canonical_url.is_not(None)).order_by(
                DbSource.authority,
                DbSource.title,
            )
            if local_government:
                statement = statement.where(DbSource.local_government == local_government)
            parents: list[dict[str, object]] = []
            for source in session.scalars(statement).all():
                latest = self._latest_version(session, source)
                if latest is None:
                    continue
                latest_domain = self._source_version(latest)
                if latest_domain.metadata_only:
                    continue
                candidate_links = _candidate_links_from_metadata(latest.metadata_json)
                if not candidate_links:
                    chunks = session.scalars(
                        select(DbSourceChunk)
                        .where(DbSourceChunk.source_version_id == latest.id)
                        .order_by(DbSourceChunk.chunk_index)
                    ).all()
                    candidate_links = _candidate_links_from_text(
                        "\n".join(chunk.text for chunk in chunks)
                    )
                if not candidate_links:
                    continue
                parents.append(
                    {
                        "source_id": source.id,
                        "source_version_id": latest.id,
                        "title": source.title,
                        "jurisdiction": source.jurisdiction,
                        "authority": source.authority,
                        "local_government": source.local_government,
                        "source_type": source.source_type,
                        "canonical_url": source.canonical_url,
                        "access_type": source.access_type,
                        "candidate_links": candidate_links,
                    }
                )
            return parents

    def ingestion_status(self, *, local_government: str | None = None) -> dict[str, object]:
        with self._session_factory() as session:
            statement = select(DbSource).order_by(DbSource.authority, DbSource.title)
            if local_government:
                statement = statement.where(DbSource.local_government == local_government)
            sources = session.scalars(statement).all()
            items: list[dict[str, object]] = []
            counts = {
                "sources": len(sources),
                "versions": 0,
                "pending_review_versions": 0,
                "approved_citable_versions": 0,
                "metadata_only_versions": 0,
                "chunks": 0,
                "citations": 0,
                "pending_fetches": 0,
            }
            for source in sources:
                version = self._latest_version(session, source)
                fetch_log = self._latest_fetch_log(session, source)
                chunk_count = 0
                citation_count = 0
                version_payload: dict[str, object] | None = None
                if version is not None:
                    counts["versions"] += 1
                    domain_version = self._source_version(version)
                    if domain_version.review_status is SourceReviewStatus.PENDING_REVIEW:
                        counts["pending_review_versions"] += 1
                    if domain_version.metadata_only:
                        counts["metadata_only_versions"] += 1
                    if domain_version.can_support_citable_retrieval:
                        counts["approved_citable_versions"] += 1
                    chunk_count = int(
                        session.scalar(
                            select(func.count()).select_from(DbSourceChunk).where(
                                DbSourceChunk.source_version_id == version.id,
                            )
                        )
                        or 0
                    )
                    citation_count = int(
                        session.scalar(
                            select(func.count()).select_from(DbSourceCitation).where(
                                DbSourceCitation.source_version_id == version.id,
                            )
                        )
                        or 0
                    )
                    counts["chunks"] += chunk_count
                    counts["citations"] += citation_count
                    version_payload = {
                        "id": str(version.id),
                        "version_label": version.version_label,
                        "licence_status": domain_version.licence_status.value,
                        "review_status": domain_version.review_status.value,
                        "metadata_only": domain_version.metadata_only,
                        "can_support_search": (
                            domain_version.can_support_citable_retrieval
                            and chunk_count > 0
                            and citation_count > 0
                        ),
                    }
                if fetch_log is not None and fetch_log.status == "pending_fetch":
                    counts["pending_fetches"] += 1
                items.append(
                    {
                        "source_id": str(source.id),
                        "title": source.title,
                        "authority": source.authority,
                        "local_government": source.local_government,
                        "source_type": source.source_type,
                        "canonical_url": source.canonical_url,
                        "access_type": source.access_type,
                        "status": source.status,
                        "latest_version": version_payload,
                        "chunk_count": chunk_count,
                        "citation_count": citation_count,
                        "latest_fetch": (
                            {
                                "status": fetch_log.status,
                                "fetch_kind": fetch_log.fetch_kind,
                                "requested_at": fetch_log.requested_at.isoformat(),
                            }
                            if fetch_log is not None
                            else None
                        ),
                        "pending_action": _pending_action(version, fetch_log),
                    }
                )
            return {
                "status": "ingestion_in_progress" if counts["sources"] else "not_started",
                "answer_policy": "cite_or_refuse",
                "local_government": local_government,
                "beta_status": "not_beta_accurate_yet",
                "counts": counts,
                "items": items,
                "blocked_outputs": [
                    "final_compliance_claims",
                    "uncited_regulatory_answers",
                    "unpromoted_measurement_verdicts",
                ],
                "pending": [
                    "lawful source fetch",
                    "human source approval",
                    "rule extraction review",
                    "deterministic check promotion",
                ],
            }

    def _get_or_create_source(
        self,
        session: Session,
        *,
        source_id: str | None,
        title: str,
        authority: str,
        jurisdiction: str,
        local_government: str | None,
        source_type: str,
        canonical_url: str | None,
        access_type: str,
        licence_notes: str | None,
        metadata: Mapping[str, object] | None,
    ) -> DbSource:
        existing = self._find_source(
            session,
            source_id=source_id,
            authority=authority,
            canonical_url=canonical_url,
            title=title,
        )
        source_metadata = {
            **dict(existing.metadata_json if existing is not None else {}),
            **dict(metadata or {}),
        }
        if licence_notes:
            source_metadata["licence_notes"] = licence_notes
        if existing is not None:
            existing.title = title
            existing.jurisdiction = jurisdiction
            existing.local_government = local_government
            existing.source_type = source_type
            existing.access_type = access_type
            existing.metadata_json = source_metadata
            return existing
        db_source = DbSource(
            id=_source_uuid(source_id, title=title, canonical_url=canonical_url),
            title=title,
            jurisdiction=jurisdiction,
            authority=authority,
            local_government=local_government,
            source_type=source_type,
            canonical_url=canonical_url,
            access_type=access_type,
            status="active",
            metadata_json=source_metadata,
        )
        session.add(db_source)
        session.flush()
        return db_source

    def _find_source(
        self,
        session: Session,
        *,
        source_id: str | None,
        authority: str,
        canonical_url: str | None,
        title: str,
    ) -> DbSource | None:
        if source_id:
            try:
                by_id = session.get(DbSource, UUID(source_id))
            except ValueError:
                by_id = session.get(
                    DbSource,
                    _source_uuid(source_id, title=title, canonical_url=canonical_url),
                )
            if by_id is not None:
                return by_id
        if canonical_url:
            by_url = session.scalar(
                select(DbSource).where(
                    DbSource.authority == authority,
                    DbSource.canonical_url == canonical_url,
                )
            )
            if by_url is not None:
                return by_url
        return session.scalar(
            select(DbSource).where(
                DbSource.title == title,
                DbSource.authority == authority,
            )
        )

    def _get_existing_source(
        self,
        session: Session,
        *,
        source_id: str | None,
        authority: str,
        canonical_url: str | None,
        title: str,
    ) -> DbSource:
        source = self._find_source(
            session,
            source_id=source_id,
            authority=authority,
            canonical_url=canonical_url,
            title=title,
        )
        if source is None:
            raise SourceNotFoundError(f"source not found: {source_id or canonical_url or title}")
        return source

    def _get_source_by_id(self, session: Session, source_id: str) -> DbSource:
        try:
            source_uuid = UUID(source_id)
        except ValueError as exc:
            raise SourceNotFoundError(f"source not found: {source_id}") from exc
        source = session.get(DbSource, source_uuid)
        if source is None:
            raise SourceNotFoundError(f"source not found: {source_id}")
        return source

    def _get_version_by_id(self, session: Session, source_version_id: str | None) -> DbSourceVersion:
        if not source_version_id:
            raise SourceNotFoundError("source version not found")
        try:
            version_uuid = UUID(source_version_id)
        except ValueError as exc:
            raise SourceNotFoundError(f"source version not found: {source_version_id}") from exc
        version = session.get(DbSourceVersion, version_uuid)
        if version is None:
            raise SourceNotFoundError(f"source version not found: {source_version_id}")
        return version

    def _latest_version(self, session: Session, source: DbSource) -> DbSourceVersion | None:
        return session.scalar(
            select(DbSourceVersion)
            .where(DbSourceVersion.source_id == source.id)
            .order_by(DbSourceVersion.fetched_at.desc(), DbSourceVersion.created_at.desc())
            .limit(1)
        )

    def _latest_fetch_log(self, session: Session, source: DbSource) -> DbSourceFetchLog | None:
        return session.scalar(
            select(DbSourceFetchLog)
            .where(DbSourceFetchLog.source_id == source.id)
            .order_by(DbSourceFetchLog.requested_at.desc())
            .limit(1)
        )

    def _source_document(self, session: Session, source: DbSource) -> SourceDocument:
        latest = self._latest_version(session, source)
        return SourceDocument(
            id=str(source.id),
            title=source.title,
            uri=source.canonical_url,
            publisher=source.authority,
            licence_status=(
                _licence_status(latest.licence_status)
                if latest is not None
                else LicenceStatus.UNKNOWN
            ),
            created_at=source.created_at,
            latest_version_id=str(latest.id) if latest is not None else None,
        )

    def _source_version(self, version: DbSourceVersion) -> SourceVersion:
        metadata = dict(version.metadata_json or {})
        storage_manifest = dict(version.storage_manifest_json or {})
        artifact_ids_raw = storage_manifest.get("artifact_ids", [])
        artifact_ids = artifact_ids_raw if isinstance(artifact_ids_raw, list) else []
        return SourceVersion(
            id=str(version.id),
            source_id=str(version.source_id),
            version_label=version.version_label or f"sha256:{version.sha256[:12]}",
            sha256=version.sha256,
            storage_path=str(storage_manifest.get("storage_path") or content_addressed_path(version.sha256)),
            licence_status=_licence_status(version.licence_status),
            review_status=_review_status(version.review_status),
            fetched_at=version.fetched_at,
            published_at=version.published_at,
            effective_from=version.effective_from,
            effective_to=version.effective_to,
            superseded_by_version_id=(
                str(version.superseded_by_version_id)
                if version.superseded_by_version_id
                else None
            ),
            artifact_ids=tuple(str(value) for value in artifact_ids),
            metadata_only=bool(metadata.get("metadata_only") or storage_manifest.get("metadata_only")),
        )

    def _source_chunk(
        self,
        chunk: DbSourceChunk,
        version: DbSourceVersion,
        *,
        citation_id: str = "",
    ) -> SourceChunk:
        embedding_values = chunk.embedding if chunk.embedding is not None else []
        return SourceChunk(
            id=str(chunk.id),
            source_id=str(version.source_id),
            source_version_id=str(version.id),
            ordinal=chunk.chunk_index,
            text=chunk.text,
            text_sha256=sha256(chunk.text.encode("utf-8")).hexdigest(),
            citation_id=citation_id,
            embedding_provider=chunk.embedding_provider,
            embedding_model=chunk.embedding_model,
            embedding_dimension=chunk.embedding_dimension,
            embedding=tuple(embedding_values),
        )

    def _source_citation(
        self,
        citation: DbSourceCitation,
        chunk: DbSourceChunk,
        version: DbSourceVersion,
        source: DbSource,
    ) -> SourceCitation:
        return SourceCitation(
            id=str(citation.id),
            source_id=str(source.id),
            source_version_id=str(version.id),
            chunk_id=str(chunk.id),
            source_title=source.title,
            locator=citation.section_ref or f"chunk {chunk.chunk_index}",
            quote=citation.quote or _safe_quote(chunk.text),
            uri=source.canonical_url,
        )

    def _insert_chunks_and_citations(
        self,
        session: Session,
        *,
        db_source: DbSource,
        db_version: DbSourceVersion,
        text: str,
    ) -> None:
        for ordinal, chunk_text in enumerate(_chunk_text(text), start=1):
            chunk = DbSourceChunk(
                id=uuid4(),
                source_version_id=db_version.id,
                chunk_index=ordinal,
                text=chunk_text,
                token_count=len(chunk_text.split()),
                embedding_provider=self.embedding_config.provider,
                embedding_model=self.embedding_config.model,
                embedding_dimension=self.embedding_config.dimension,
                embedding=list(_hash_embedding(chunk_text, self.embedding_config)),
                metadata_json={"source_id": str(db_source.id)},
            )
            session.add(chunk)
            session.flush()
            session.add(
                DbSourceCitation(
                    id=uuid4(),
                    source_chunk_id=chunk.id,
                    source_version_id=db_version.id,
                    citation_kind="source_chunk",
                    section_ref=f"chunk {ordinal}",
                    quote=_safe_quote(chunk_text),
                    citation_json={
                        "source_title": db_source.title,
                        "canonical_url": db_source.canonical_url,
                    },
                )
            )

    def _import_result(
        self,
        session: Session,
        db_source: DbSource,
        db_version: DbSourceVersion,
        *,
        duplicate: bool,
    ) -> SourceImportResult:
        domain_source = self._source_document(session, db_source)
        domain_version = self._source_version(db_version)
        artifacts = tuple(
            ContentAddressedArtifact(
                id=str(artifact.id),
                subject_type=ArtifactSubjectType(artifact.subject_type),
                subject_id=str(artifact.subject_id),
                kind=ArtifactKind(artifact.kind),
                storage_path=artifact.storage_path,
                sha256=artifact.sha256,
                media_type=artifact.media_type or "application/octet-stream",
                size_bytes=artifact.size_bytes or 0,
                parser_name=artifact.parser_name,
                parser_version=artifact.parser_version,
                metadata={str(key): str(value) for key, value in artifact.metadata_json.items()},
            )
            for artifact in session.scalars(
                select(DbArtifact).where(DbArtifact.subject_id == db_version.id)
            ).all()
        )
        chunk_rows = session.scalars(
            select(DbSourceChunk)
            .where(DbSourceChunk.source_version_id == db_version.id)
            .order_by(DbSourceChunk.chunk_index)
        ).all()
        citation_rows = session.execute(
            select(DbSourceCitation, DbSourceChunk)
            .join(DbSourceChunk, DbSourceChunk.id == DbSourceCitation.source_chunk_id)
            .where(DbSourceCitation.source_version_id == db_version.id)
            .order_by(DbSourceChunk.chunk_index)
        ).all()
        return SourceImportResult(
            source=domain_source,
            version=domain_version,
            artifacts=artifacts,
            chunks=tuple(self._source_chunk(chunk, db_version) for chunk in chunk_rows),
            citations=tuple(
                self._source_citation(citation, chunk, db_version, db_source)
                for citation, chunk in citation_rows
            ),
            duplicate=duplicate,
            metadata_only=domain_version.metadata_only,
        )

    def _supersede_older_approved_versions(
        self,
        session: Session,
        approved_version: DbSourceVersion,
    ) -> None:
        older_versions = session.scalars(
            select(DbSourceVersion).where(
                DbSourceVersion.source_id == approved_version.source_id,
                DbSourceVersion.id != approved_version.id,
                DbSourceVersion.review_status == SourceReviewStatus.APPROVED.value,
                DbSourceVersion.superseded_by_version_id.is_(None),
            )
        ).all()
        for older in older_versions:
            older.superseded_by_version_id = approved_version.id


def _artifact_payload(
    *,
    title: str,
    content: str,
    uri: str | None,
    publisher: str | None,
    licence_status: LicenceStatus,
    metadata_only: bool,
) -> bytes:
    if content and not metadata_only:
        return content.encode("utf-8")
    return json.dumps(
        {
            "title": title,
            "uri": uri,
            "publisher": publisher,
            "licence_status": licence_status.value,
            "metadata_only": True,
        },
        sort_keys=True,
    ).encode("utf-8")


def _source_uuid(source_id: str | None, *, title: str, canonical_url: str | None) -> UUID:
    if source_id:
        try:
            return UUID(source_id)
        except ValueError:
            return uuid5(NAMESPACE_URL, f"draftcheck.source:{source_id}")
    return uuid5(NAMESPACE_URL, f"draftcheck.source:{title}|{canonical_url or ''}")


def _uuid_from_string(value: str, field_name: str) -> UUID:
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a UUID for durable source review") from exc


def _licence_status(value: str) -> LicenceStatus:
    try:
        return LicenceStatus(value)
    except ValueError:
        return LicenceStatus.UNKNOWN


def _review_status(value: str) -> SourceReviewStatus:
    try:
        return SourceReviewStatus(value)
    except ValueError:
        return SourceReviewStatus.PENDING_REVIEW


_URL_IN_TEXT_RE = re.compile(r"https?://[^\s<>)\"']+")


def _candidate_links_from_metadata(metadata: Mapping[str, object]) -> tuple[CandidateSourceLink, ...]:
    raw_links = metadata.get("candidate_links")
    if not isinstance(raw_links, list):
        return ()
    links: list[CandidateSourceLink] = []
    seen: set[str] = set()
    for raw_link in raw_links:
        if not isinstance(raw_link, Mapping):
            continue
        url = _optional_str(raw_link.get("url"))
        if not url or url in seen:
            continue
        seen.add(url)
        label = _optional_str(raw_link.get("label")) or _title_from_url(url)
        source_type = _optional_str(raw_link.get("source_type")) or infer_source_type(url, label)
        links.append(CandidateSourceLink(url=url, label=label, source_type=source_type))
    return tuple(links)


def _candidate_links_from_text(text: str) -> tuple[CandidateSourceLink, ...]:
    links: list[CandidateSourceLink] = []
    seen: set[str] = set()
    in_candidate_block = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if in_candidate_block:
                in_candidate_block = False
            continue
        if line.lower().startswith("candidate public source links"):
            in_candidate_block = True
            continue
        if not in_candidate_block and "http" not in line.lower():
            continue
        match = _URL_IN_TEXT_RE.search(line)
        if match is None:
            continue
        url = match.group(0).rstrip(".,;]")
        if url in seen or not _is_public_http_url(url):
            continue
        label = line[: match.start()].strip().rstrip(":").strip() or _title_from_url(url)
        if not _looks_like_discovered_source(url, label):
            continue
        seen.add(url)
        links.append(
            CandidateSourceLink(
                url=url,
                label=label,
                source_type=infer_source_type(url, label),
            )
        )
    return tuple(links)


def _looks_like_discovered_source(url: str, label: str) -> bool:
    haystack = f"{url} {label}".lower()
    return any(
        term in haystack
        for term in (
            "planning",
            "policy",
            "scheme",
            "development",
            "structure-plan",
            "local-development-plan",
            "strategy",
            "map",
            "r-code",
            "rcode",
            "residential",
            ".pdf",
            ".doc",
            ".docx",
        )
    )


def _is_public_http_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        return False
    lowered = url.lower()
    return not any(
        restricted in lowered
        for restricted in ("login", "signin", "password", "private", "cart", "checkout", "captcha")
    )


def _authority_for_discovered_link(url: str, *, fallback: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.endswith("cockburn.wa.gov.au"):
        return "City of Cockburn"
    if host.endswith("wa.gov.au") or host.endswith("planning.wa.gov.au"):
        return "Department of Planning, Lands and Heritage"
    return fallback


def _title_from_url(url: str) -> str:
    parsed = urlparse(url)
    path_title = parsed.path.rstrip("/").split("/")[-1]
    if not path_title:
        return url
    for suffix in (".aspx", ".html", ".htm", ".pdf", ".docx", ".doc"):
        if path_title.lower().endswith(suffix):
            path_title = path_title[: -len(suffix)]
            break
    return path_title.replace("-", " ").replace("_", " ").replace("%20", " ").strip() or url


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _parse_manifest_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    normalized = str(value).strip()
    if not normalized:
        return None
    if len(normalized) == 10:
        parsed_date = date.fromisoformat(normalized)
        return datetime(parsed_date.year, parsed_date.month, parsed_date.day, tzinfo=UTC)
    parsed_datetime = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    return parsed_datetime if parsed_datetime.tzinfo else parsed_datetime.replace(tzinfo=UTC)


def _manifest_fetch_status(entry: Mapping[str, Any], metadata_only: bool) -> str:
    if not bool(entry.get("scrape_allowed", False)):
        return "blocked"
    if metadata_only:
        return "pending_fetch"
    return "pending_review"


def _pending_action(
    version: DbSourceVersion | None,
    fetch_log: DbSourceFetchLog | None,
) -> str:
    if version is None:
        return "record_source_version"
    review_status = _review_status(version.review_status)
    if fetch_log is not None and fetch_log.status == "pending_fetch":
        return "lawful_fetch"
    if review_status is SourceReviewStatus.PENDING_REVIEW:
        return "human_source_review"
    if review_status is SourceReviewStatus.APPROVED:
        return "ready_for_rule_extraction"
    return "review_follow_up"


def _utc_now() -> datetime:
    return datetime.now(UTC)
