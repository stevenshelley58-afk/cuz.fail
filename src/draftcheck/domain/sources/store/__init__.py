"""PostgreSQL-backed V3 source library, composed from focused mixin modules."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from draftcheck.db.engine import create_session_factory
from draftcheck.domain.sources.library import default_embedding_config
from draftcheck.domain.sources.models import EmbeddingConfig
from draftcheck.domain.sources.store.fetching import SourceFetchOps
from draftcheck.domain.sources.store.importing import SourceImportOps
from draftcheck.domain.sources.store.reading import SourceReadOps
from draftcheck.domain.sources.store.reporting import SourceReportingOps


class SqlAlchemySourceLibrary(SourceImportOps, SourceFetchOps, SourceReadOps, SourceReportingOps):
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


__all__ = ["SqlAlchemySourceLibrary"]
