"""Import and manifest-seed operations for the SQLAlchemy source library."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from hashlib import sha256
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from draftcheck.db.models import (
    Artifact as DbArtifact,
    Source as DbSource,
    SourceChunk as DbSourceChunk,
    SourceCitation as DbSourceCitation,
    SourceVersion as DbSourceVersion,
)
from draftcheck.domain.sources.library import _chunk_text, _embed, _safe_quote
from draftcheck.domain.sources.models import (
    ArtifactKind,
    ArtifactSubjectType,
    ContentAddressedArtifact,
    LicenceStatus,
    SourceImportResult,
    SourceNotFoundError,
    SourceReviewStatus,
    content_addressed_path,
)
from draftcheck.domain.sources.store._helpers import (
    _artifact_payload,
    _manifest_fetch_status,
    _optional_str,
    _parse_manifest_datetime,
    _source_uuid,
)

if TYPE_CHECKING:
    from draftcheck.domain.sources.store._base import SourceStoreBase
else:  # pragma: no cover - typing-only base; mixins compose at runtime
    SourceStoreBase = object


class SourceImportOps(SourceStoreBase):
    """Import and manifest-seed methods for ``SqlAlchemySourceLibrary``."""

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
                embedding=list(_embed(chunk_text, self.embedding_config)),
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
