"""Add source audit lookup indexes.

Revision ID: 0007_add_audit_lookup_indexes
Revises: 0006_backfill_source_licence_reviews
Create Date: 2026-06-06
"""

from __future__ import annotations

from alembic import op

revision = "0007_add_audit_lookup_indexes"
down_revision = "0006_backfill_source_licence_reviews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "create index if not exists ix_clauses_source_version_clause "
        "on clauses (source_version_id, clause_id)"
    )
    op.execute(
        "create index if not exists ix_clause_dispositions_clause_created "
        "on clause_dispositions (clause_id, created_at, id)"
    )
    op.execute(
        "create index if not exists ix_rule_rows_clause_created "
        "on rule_rows (clause_id, created_at, id)"
    )
    op.execute(
        "create index if not exists ix_rule_extraction_candidates_clause_created "
        "on rule_extraction_candidates (clause_id, created_at, id)"
    )
    op.execute(
        "create index if not exists ix_rule_carveouts_clause_created "
        "on rule_carveouts (clause_id, created_at, id)"
    )


def downgrade() -> None:
    op.execute("drop index if exists ix_rule_carveouts_clause_created")
    op.execute("drop index if exists ix_rule_extraction_candidates_clause_created")
    op.execute("drop index if exists ix_rule_rows_clause_created")
    op.execute("drop index if exists ix_clause_dispositions_clause_created")
    op.execute("drop index if exists ix_clauses_source_version_clause")
