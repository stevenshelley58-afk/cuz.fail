"""Indexes for fast predictive address suggestions.

A trigram GIN index makes both the ILIKE prefix/contains predicates and the
`%` similarity operator index-backed, keeping /addresses/suggest in the
low-millisecond range even at full G-NAF scale.
"""

from __future__ import annotations

from alembic import op


revision: str = "0014_address_suggest_indexes"
down_revision: str | None = "0013_guest_usage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_address_points_address_text_trgm "
        "ON address_points USING gin (address_text gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_address_points_address_text_trgm")
