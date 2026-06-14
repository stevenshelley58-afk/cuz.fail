"""Add rich rule-decode columns (non-numeric rule support).

Stores the LLM "decode" of each rule beyond a numeric threshold: what kind of
check it is, how it can be evaluated, and the structured logic (what it is /
what it means / how to query) so the engine can evaluate categorical, presence,
conditional and qualitative/performance rules — not just numeric comparisons.

Revision ID: 0019_rule_decode_logic
Revises: 0018_rule_canonical_keys
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "0019_rule_decode_logic"
down_revision: str | None = "0018_rule_canonical_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLES = ("rules", "rule_candidates")


def upgrade() -> None:
    for table in _TABLES:
        # numeric_threshold | categorical | boolean_presence |
        # qualitative_performance | conditional | not_a_rule
        op.add_column(table, sa.Column("check_type", sa.String(40), nullable=True))
        op.create_index(f"ix_{table}_check_type", table, ["check_type"])
        # auto_numeric | auto_presence | ai_judgement | needs_more_info
        op.add_column(table, sa.Column("evaluable", sa.String(40), nullable=True))
        # {what_it_is, what_it_means, requirement, applies_when, how_to_query}
        op.add_column(
            table,
            sa.Column("rule_logic_json", JSONB, nullable=False, server_default="{}"),
        )


def downgrade() -> None:
    for table in _TABLES:
        op.drop_column(table, "rule_logic_json")
        op.drop_column(table, "evaluable")
        op.drop_index(f"ix_{table}_check_type", table_name=table)
        op.drop_column(table, "check_type")
