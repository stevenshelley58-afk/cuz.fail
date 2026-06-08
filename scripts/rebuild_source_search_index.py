from __future__ import annotations

import json

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from draftcheck_core.database import engine, init_database
from draftcheck_core.source_support import (
    ACCEPTABLE_SOURCE_PARSE_STATUSES,
    OPEN_REVIEW_STATUSES,
    SOURCE_SUPPORT_BLOCKING_QUEUES,
    source_version_can_support_citable_retrieval,
)


def rebuild_source_search_index(target_engine: Engine) -> int | None:
    if target_engine.dialect.name != "sqlite":
        return None

    with target_engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS source_chunk_fts"))
        conn.execute(
            text(
                """
                CREATE VIRTUAL TABLE source_chunk_fts
                USING fts5(chunk_id UNINDEXED, content, tokenize='unicode61')
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO source_chunk_fts(chunk_id, content)
                SELECT
                    source_chunks.id,
                    coalesce(source_chunks.heading, '') || ' ' ||
                    source_chunks.text || ' ' ||
                    coalesce(source_documents.title, '') || ' ' ||
                    coalesce(source_documents.authority, '') || ' ' ||
                    coalesce(source_documents.local_government, '') || ' ' ||
                    coalesce(source_documents.source_type, '')
                FROM source_chunks
                JOIN source_versions ON source_versions.id = source_chunks.source_version_id
                JOIN source_documents ON source_documents.id = source_versions.source_document_id
                WHERE source_versions.review_status = 'accepted'
                  AND source_versions.is_superseded = 0
                  AND source_versions.parse_status IN :parse_statuses
                  AND source_documents.is_active = 1
                  AND EXISTS (
                      SELECT 1
                      FROM source_licence_reviews
                      WHERE source_licence_reviews.source_version_id = source_versions.id
                        AND source_licence_reviews.review_status = 'approved'
                        AND source_licence_reviews.allowed_storage = 1
                        AND source_licence_reviews.allowed_ai_processing = 1
                  )
                  AND NOT EXISTS (
                      SELECT 1
                      FROM review_queue_items
                      WHERE review_queue_items.source_version_id = source_versions.id
                        AND review_queue_items.queue IN :blocking_queues
                        AND review_queue_items.status IN :open_statuses
                        AND review_queue_items.blocking_level = 'blocking'
                  )
                """
            ).bindparams(
                bindparam("parse_statuses", expanding=True),
                bindparam("blocking_queues", expanding=True),
                bindparam("open_statuses", expanding=True),
            ),
            {
                "parse_statuses": tuple(sorted(ACCEPTABLE_SOURCE_PARSE_STATUSES)),
                "blocking_queues": tuple(sorted(SOURCE_SUPPORT_BLOCKING_QUEUES)),
                "open_statuses": tuple(sorted(OPEN_REVIEW_STATUSES)),
            },
        )

    _prune_uncitable_index_rows(target_engine)

    with target_engine.connect() as conn:
        indexed = conn.execute(text("SELECT count(*) FROM source_chunk_fts")).scalar_one()
        return int(indexed)


def _prune_uncitable_index_rows(target_engine: Engine) -> None:
    with Session(target_engine) as db:
        indexed_chunks = db.execute(
            text(
                """
                SELECT source_chunks.id, source_chunks.source_version_id
                FROM source_chunks
                JOIN source_chunk_fts ON source_chunk_fts.chunk_id = source_chunks.id
                """
            )
        ).all()
        support_cache: dict[str, bool] = {}
        unsupported_chunk_ids: list[str] = []
        for chunk_id, source_version_id in indexed_chunks:
            if source_version_id not in support_cache:
                support_cache[source_version_id] = source_version_can_support_citable_retrieval(
                    db,
                    source_version_id,
                )
            if not support_cache[source_version_id]:
                unsupported_chunk_ids.append(chunk_id)
        if unsupported_chunk_ids:
            db.execute(
                text("DELETE FROM source_chunk_fts WHERE chunk_id IN :chunk_ids").bindparams(
                    bindparam("chunk_ids", expanding=True)
                ),
                {"chunk_ids": tuple(unsupported_chunk_ids)},
            )
            db.commit()


def main() -> None:
    init_database()
    indexed = rebuild_source_search_index(engine)
    if indexed is None:
        print(json.dumps({"status": "skipped", "reason": "FTS index is only used for SQLite"}))
        return

    print(json.dumps({"status": "rebuilt", "indexed_chunks": indexed}))


if __name__ == "__main__":
    main()
