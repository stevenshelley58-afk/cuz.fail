"""Guest usage counters for server-enforced guest budgets."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision: str = "0013_guest_usage"
down_revision: str | None = "0012_add_guest_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guest_usage",
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("feature", sa.String(20), primary_key=True),
        sa.Column("used", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("feature IN ('address', 'chat')", name="ck_guest_usage_feature"),
    )


def downgrade() -> None:
    op.drop_table("guest_usage")
