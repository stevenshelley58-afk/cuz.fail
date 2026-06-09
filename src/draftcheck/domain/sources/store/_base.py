"""Type-checking-only base declaring attributes and methods the mixins share via ``self``."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from draftcheck.db.models import (
    Source as DbSource,
    SourceChunk as DbSourceChunk,
    SourceCitation as DbSourceCitation,
    SourceFetchLog as DbSourceFetchLog,
    SourceVersion as DbSourceVersion,
)
from draftcheck.domain.sources.models import (
    EmbeddingConfig,
    LicenceStatus,
    SourceChunk,
    SourceCitation,
    SourceDocument,
    SourceImportResult,
    SourceReviewStatus,
    SourceVersion,
)


class SourceStoreBase:
    """Shared surface of ``SqlAlchemySourceLibrary`` referenced across mixins.

    Imported only under ``TYPE_CHECKING``; at runtime the mixins subclass
    ``object`` and these names resolve through the composed class's MRO.
    """

    _session_factory: Callable[[], Session]
    embedding_config: EmbeddingConfig

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
        raise NotImplementedError

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
        raise NotImplementedError

    def _get_source_by_id(self, session: Session, source_id: str) -> DbSource:
        raise NotImplementedError

    def _get_version_by_id(self, session: Session, source_version_id: str | None) -> DbSourceVersion:
        raise NotImplementedError

    def _latest_version(self, session: Session, source: DbSource) -> DbSourceVersion | None:
        raise NotImplementedError

    def _latest_fetch_log(self, session: Session, source: DbSource) -> DbSourceFetchLog | None:
        raise NotImplementedError

    def _source_document(self, session: Session, source: DbSource) -> SourceDocument:
        raise NotImplementedError

    def _source_version(self, version: DbSourceVersion) -> SourceVersion:
        raise NotImplementedError

    def _source_chunk(
        self,
        chunk: DbSourceChunk,
        version: DbSourceVersion,
        *,
        citation_id: str = "",
    ) -> SourceChunk:
        raise NotImplementedError

    def _source_citation(
        self,
        citation: DbSourceCitation,
        chunk: DbSourceChunk,
        version: DbSourceVersion,
        source: DbSource,
    ) -> SourceCitation:
        raise NotImplementedError

    def _supersede_older_approved_versions(
        self,
        session: Session,
        approved_version: DbSourceVersion,
    ) -> None:
        raise NotImplementedError
