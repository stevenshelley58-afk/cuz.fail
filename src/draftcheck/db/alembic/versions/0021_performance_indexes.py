"""Performance indexes and constraints from DeepSeek schema review.

Verified against actual models.py — only adds what's genuinely missing.
Skips: ix_rules_rule_key (exists), planning_features GiST (exists),
address_points trigram (mig 0009), property_facts FK (exists),
check_results property_id (column doesn't exist).

Revision ID: 0021_performance_indexes
Revises: 0020_add_rule_coverage_columns
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0021_performance_indexes"
down_revision: str | None = "0020_add_rule_coverage_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Composite index on source_versions for effective-date rule lookups.
    #    Engine loads rules from source versions effective as-of a date.
    #    Individual indexes on review_status exist but not on the temporal columns.
    op.create_index(
        "ix_source_versions_source_effective",
        "source_versions",
        ["source_id", "effective_from", "effective_to"],
    )

    # 2. GIN expression index on rules.value_json->>'base_rule_key'.
    #    Engine's _base_rule_key() reads this JSONB path for WP6 rule resolution.
    #    Expression index (not full GIN on value_json) — targeted and small.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_rules_base_rule_key_expr "
        "ON rules ((value_json->>'base_rule_key'))"
    )

    # 3. Composite index on spatial_datasets for the common join pattern:
    #    resolver filters to approved + licensed datasets in a single predicate.
    #    Individual indexes on approval_status and licence_status exist (models.py:716-717)
    #    but a composite avoids two index scans + bitmap AND.
    op.create_index(
        "ix_spatial_datasets_approved_licensed",
        "spatial_datasets",
        ["approval_status", "licence_status"],
    )

    # 4. Composite index on rules for the engine's primary load path:
    #    lifecycle_status is indexed alone, but the engine always filters
    #    lifecycle_status='approved' AND loads by rule_key in the same query.
    op.create_index(
        "ix_rules_lifecycle_rule_key",
        "rules",
        ["lifecycle_status", "rule_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_rules_lifecycle_rule_key", table_name="rules")
    op.drop_index("ix_spatial_datasets_approved_licensed", table_name="spatial_datasets")
    op.execute("DROP INDEX IF EXISTS ix_rules_base_rule_key_expr")
    op.drop_index("ix_source_versions_source_effective", table_name="source_versions")
