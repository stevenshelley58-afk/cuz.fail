"""Require PostGIS and pgvector extensions on PostgreSQL.

Revision ID: 0008_require_postgis_pgvector
Revises: 0007_add_audit_lookup_indexes
Create Date: 2026-06-06
"""

from __future__ import annotations

from alembic import op

revision = "0008_require_postgis_pgvector"
down_revision = "0007_add_audit_lookup_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Do not drop shared database extensions on downgrade; other schemas may depend on them.
    return
