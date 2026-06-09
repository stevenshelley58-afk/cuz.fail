"""Add partial index on property_facts for confirmed promoted facts."""

from __future__ import annotations

from alembic import op

revision: str = "0008_property_facts_confirmed_index"
down_revision: str | None = "0007_nullable_org_job_traces"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_property_facts_project_review
        ON property_facts (project_id, review_status)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_property_facts_project_review")
