"""Add source chunk embedding storage.

Revision ID: 0009_source_chunk_embeddings
Revises: 0008_require_postgis_pgvector
Create Date: 2026-06-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from draftcheck_core import models  # noqa: F401
from draftcheck_core.database import Base

revision = "0009_source_chunk_embeddings"
down_revision = "0008_require_postgis_pgvector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_table("source_chunk_embeddings"):
        Base.metadata.tables["source_chunk_embeddings"].create(bind=bind, checkfirst=True)

    if bind.dialect.name == "sqlite":
        return

    op.execute(
        """
        alter table source_chunk_embeddings
        add column if not exists embedding_vector vector(16)
        """
    )
    op.execute(
        """
        create index if not exists ix_source_chunk_embeddings_vector_hnsw
        on source_chunk_embeddings
        using hnsw (embedding_vector vector_cosine_ops)
        """
    )


def downgrade() -> None:
    if _has_table("source_chunk_embeddings"):
        op.drop_table("source_chunk_embeddings")


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)
