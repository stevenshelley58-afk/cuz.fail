"""Add rule coverage columns for full WA rule universe support.

Adds dwelling_type, effective_from/to, instrument_section, and table_reference
to the rules table. These support multi-density-code rule coverage (R2-R80),
time-limited provisions (e.g. C2.2.4 solar exemption expires 2030), and source
traceability back to specific instrument sections and tables.

Also backfills dwelling_type from condition_json->>'dwelling_type' for existing
approved rules.

Revision ID: 0020_add_rule_coverage_columns
Revises: 0019_rule_decode_logic
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0020_add_rule_coverage_columns"
down_revision: str | None = "0019_rule_decode_logic"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -- New columns on rules table --
    op.add_column(
        "rules",
        sa.Column(
            "dwelling_type",
            sa.String(80),
            nullable=True,
            comment=(
                "Dwelling type: single_house, grouped_dwelling, multiple_dwelling, "
                "ancillary_dwelling, small_dwelling, accessible_dwelling. NULL = any"
            ),
        ),
    )
    op.create_index("ix_rules_dwelling_type", "rules", ["dwelling_type"])

    op.add_column(
        "rules",
        sa.Column(
            "effective_from",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Rule effective from date (for time-limited provisions)",
        ),
    )
    op.add_column(
        "rules",
        sa.Column(
            "effective_to",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Rule expiry (e.g. C2.2.4 solar exemption expires 2030-04-10)",
        ),
    )
    op.add_column(
        "rules",
        sa.Column(
            "instrument_section",
            sa.String(120),
            nullable=True,
            comment="Source instrument section reference (e.g. 'Part B 2.1', 'Part C C3.1')",
        ),
    )
    op.create_index("ix_rules_instrument_section", "rules", ["instrument_section"])

    op.add_column(
        "rules",
        sa.Column(
            "table_reference",
            sa.String(120),
            nullable=True,
            comment="Specific table within instrument (e.g. 'Table 2.1a', 'Table B')",
        ),
    )

    # -- Backfill dwelling_type from condition_json for existing rules --
    op.execute("""
        UPDATE rules
        SET dwelling_type = condition_json->>'dwelling_type'
        WHERE condition_json->>'dwelling_type' IS NOT NULL
          AND dwelling_type IS NULL
    """)

    # -- Backfill instrument_section for existing approved rules --
    op.execute("""
        UPDATE rules
        SET instrument_section = 'Part B'
        WHERE lifecycle_status = 'approved'
          AND instrument_section IS NULL
    """)


def downgrade() -> None:
    op.drop_column("rules", "table_reference")
    op.drop_index("ix_rules_instrument_section", table_name="rules")
    op.drop_column("rules", "instrument_section")
    op.drop_column("rules", "effective_to")
    op.drop_column("rules", "effective_from")
    op.drop_index("ix_rules_dwelling_type", table_name="rules")
    op.drop_column("rules", "dwelling_type")
