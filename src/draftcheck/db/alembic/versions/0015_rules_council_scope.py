"""Add rules.council_scope — model/DB drift fix.

The Rule model gained council_scope (engine filters rules by council) but no
migration shipped it; production rules table lacked the column and any ORM
SELECT against rules failed with UndefinedColumn.

Revision ID: 0015_rules_council_scope
Revises: 0014_address_suggest_indexes
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0015_rules_council_scope"
down_revision: str | None = "0014_address_suggest_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rules",
        sa.Column(
            "council_scope",
            sa.String(length=120),
            nullable=True,
            comment="Council/LGA this rule applies to; NULL = global (all councils)",
        ),
    )
    op.create_index("ix_rules_council_scope", "rules", ["council_scope"])


def downgrade() -> None:
    op.drop_index("ix_rules_council_scope", table_name="rules")
    op.drop_column("rules", "council_scope")
