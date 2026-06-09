"""Read, review, refresh, freshness, and row-mapping operations for the source library."""

from __future__ import annotations

from collections.abc import Iterator
from hashlib import sha256
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck.db.models import (
    Source as DbSource,
    SourceChunk as DbSourceChunk,
    SourceCitation as DbSourceCitation,
    SourceFetchLog as DbSourceFetchLog,
    SourceReviewRecord as DbSourceReviewRecord,
    SourceVersion as DbSourceVersion,
)
from draftcheck.domain.sources.library import _safe_quote
from draftcheck.domain.sources.models import (
    LicenceStatus,
    SourceCitation,
    SourceChunk,
    SourceDocument,
    SourceFreshness,
    SourceNotFoundError,
    SourceRefreshResult,
    SourceReviewStatus,
    SourceVersion,
    content_addressed_path,
)
from draftcheck.domain.sources.store._helpers import (
    _licence_status,
    _review_status,
    _utc_now,
    _uuid_from_string,
)

if TYPE_CHECKING:
    from draftcheck.domain.sources.store._base import SourceStoreBase
else:  # pragma: no cover - typing-only base; mixins compose at runtime
    SourceStoreBase = object


class SourceReadOps(SourceStoreBase):
    """Read, review, refresh, and row-mapping methods for ``SqlAlchemySourceLibrary``."""

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
        actor_id: str = "system",
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
                        review_status=version.review_status,
                        licence_status=version.licence_status,
                        notes=notes,
                        decision_metadata_json={
                            "review_path": "api",
                            "answer_policy": "cite_or_refuse",
                            "actor_id": actor_id,
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
        actor_id: str | None = None,
    ) -> SourceRefreshResult:
        with self._session_factory() as session:
            with session.begin():
                source = self._get_source_by_id(session, source_id)
                version = self._latest_version(session, source)
                requested_at = _utc_now()
                if org_id and actor_id:
                    session.add(
                        DbSourceFetchLog(
                            id=uuid4(),
                            org_id=_uuid_from_string(org_id, "org_id"),
                            source_id=source.id,
                            source_version_id=version.id if version else None,
                            requested_by_user_id=_uuid_from_string(actor_id, "actor_id"),
                            fetch_kind="refresh_requested",
                            status="pending_fetch",
                            requested_at=requested_at,
                            metadata_json={
                                "note": "Actor requested lawful source refresh.",
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

    def citable_chunks_paginated(
        self,
        session: Session,
        *,
        page_size: int = 200,
        after_id: UUID | None = None,
    ) -> Iterator[tuple[SourceChunk, SourceCitation, SourceVersion]]:
        """Keyset-cursor generator — never loads the full table into memory."""
        while True:
            q = (
                session.query(DbSourceChunk, DbSourceCitation, DbSourceVersion, DbSource)
                .join(DbSourceVersion, DbSourceVersion.id == DbSourceChunk.source_version_id)
                .join(DbSource, DbSource.id == DbSourceVersion.source_id)
                .join(DbSourceCitation, DbSourceCitation.source_chunk_id == DbSourceChunk.id)
                .order_by(DbSourceChunk.id)
            )
            if after_id is not None:
                q = q.filter(DbSourceChunk.id > after_id)
            rows = q.limit(page_size).all()
            if not rows:
                break
            for chunk, citation, version, source in rows:
                domain_version = self._source_version(version)
                if not domain_version.can_support_citable_retrieval:
                    continue
                domain_chunk = self._source_chunk(chunk, version, citation_id=str(citation.id))
                yield (
                    domain_chunk,
                    self._source_citation(citation, chunk, version, source),
                    domain_version,
                )
            after_id = rows[-1][0].id
            if len(rows) < page_size:
                break

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
