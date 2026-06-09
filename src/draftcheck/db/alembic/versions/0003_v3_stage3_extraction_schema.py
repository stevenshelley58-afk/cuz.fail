"""V3 Stage 3 extraction schema — rule_candidates and clauses delta columns.

Revision ID: 0003_v3_stage3_extraction_schema
Revises: 0002_v3_complete_target_schema
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0003_v3_stage3_extraction_schema"
down_revision: str | None = "0002_v3_complete_target_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMPTY_JSON = sa.text("'{}'::jsonb")


def upgrade() -> None:
    # rule_candidates — 6 new columns
    op.add_column(
        "rule_candidates",
        sa.Column("extraction_group_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "rule_candidates",
        sa.Column("extraction_pass", sa.SmallInteger(), nullable=True),
    )
    op.add_column(
        "rule_candidates",
        sa.Column("quote_char_start", sa.Integer(), nullable=True),
    )
    op.add_column(
        "rule_candidates",
        sa.Column("quote_char_end", sa.Integer(), nullable=True),
    )
    op.add_column(
        "rule_candidates",
        sa.Column(
            "validator_results_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=EMPTY_JSON,
        ),
    )
    op.add_column(
        "rule_candidates",
        sa.Column("auto_promoted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # clauses — 1 new column
    op.add_column(
        "clauses",
        sa.Column(
            "classification_skill_version_id",
            sa.String(160),
            sa.ForeignKey("skill_versions.id"),
            nullable=True,
        ),
    )

    # indexes
    op.create_index(
        "ix_rule_candidates_group",
        "rule_candidates",
        ["extraction_group_id", "extraction_pass"],
    )
    op.create_index(
        "ix_clauses_classification_skill",
        "clauses",
        ["classification_skill_version_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_clauses_classification_skill", table_name="clauses")
    op.drop_index("ix_rule_candidates_group", table_name="rule_candidates")

    op.drop_column("clauses", "classification_skill_version_id")

    op.drop_column("rule_candidates", "auto_promoted_at")
    op.drop_column("rule_candidates", "validator_results_json")
    op.drop_column("rule_candidates", "quote_char_end")
    op.drop_column("rule_candidates", "quote_char_start")
    op.drop_column("rule_candidates", "extraction_pass")
    op.drop_column("rule_candidates", "extraction_group_id")
