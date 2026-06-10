"""Rename check_results.human_review_reason -> review_reason.

The model was renamed when the human-review gate was dropped (0003) but the
column rename never shipped; production inserts into check_results failed
with UndefinedColumn. Found by the WP9 golden-fixture engine run.

Revision ID: 0016_rename_check_results_review_reason
Revises: 0015_rules_council_scope
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0016_rename_check_results_review_reason"
down_revision: str | None = "0015_rules_council_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fresh databases (created from models via 0002) already have the new
    # name; only rename where the legacy column is present.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'check_results'
                  AND column_name = 'human_review_reason'
            ) THEN
                ALTER TABLE check_results
                    RENAME COLUMN human_review_reason TO review_reason;
            ELSIF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'check_results'
                  AND column_name = 'review_reason'
            ) THEN
                ALTER TABLE check_results ADD COLUMN review_reason TEXT;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.alter_column(
        "check_results", "review_reason", new_column_name="human_review_reason"
    )
