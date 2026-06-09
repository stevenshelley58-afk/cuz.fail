"""Make job_traces.org_id nullable for system-level adapter traces."""

from __future__ import annotations

from alembic import op

revision: str = "0007_nullable_org_job_traces"
down_revision: str | None = "0006_fix_role_constraint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The LocalDeterministicModelAdapter writes system-level traces with no org context.
    # DROP NOT NULL so those rows can use org_id = NULL while org-owned rows keep the FK.
    op.alter_column("job_traces", "org_id", nullable=True)


def downgrade() -> None:
    # Delete system rows before re-adding NOT NULL, otherwise the migration will fail
    # on any existing NULL rows.
    op.execute("DELETE FROM job_traces WHERE org_id IS NULL")
    op.alter_column("job_traces", "org_id", nullable=False)
