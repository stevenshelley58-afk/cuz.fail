"""Add nullable canonical rule key columns.

Revision ID: 0018_rule_canonical_keys
Revises: 0017_validations_and_approval_audit
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0018_rule_canonical_keys"
down_revision: str | None = "0017_validations_and_approval_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("rule_candidates", sa.Column("canonical_rule_key", sa.String(160), nullable=True))
    op.create_index(
        "ix_rule_candidates_canonical_rule_key",
        "rule_candidates",
        ["canonical_rule_key"],
    )

    op.add_column("rules", sa.Column("canonical_rule_key", sa.String(160), nullable=True))
    op.create_index("ix_rules_canonical_rule_key", "rules", ["canonical_rule_key"])


def downgrade() -> None:
    op.drop_index("ix_rules_canonical_rule_key", table_name="rules")
    op.drop_column("rules", "canonical_rule_key")

    op.drop_index("ix_rule_candidates_canonical_rule_key", table_name="rule_candidates")
    op.drop_column("rule_candidates", "canonical_rule_key")
