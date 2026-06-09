"""Fix identity_role CHECK constraint to allow owner and operator."""

from __future__ import annotations

from alembic import op

revision: str = "0006_fix_identity_role_constraint"
down_revision: str | None = "0005_v3_stage3_extraction_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Migration 0001 generated CHECK (role = 'owner') instead of IN ('owner', 'reviewer').
    # Plan §5.1 specifies role ∈ {owner, operator}. Fix both: drop the broken constraint,
    # add the correct two-value one.
    op.drop_constraint("identity_role", "users", type_="check")
    op.create_check_constraint(
        "identity_role",
        "users",
        "role IN ('owner', 'operator')",
    )


def downgrade() -> None:
    op.drop_constraint("identity_role", "users", type_="check")
    op.create_check_constraint(
        "identity_role",
        "users",
        "role = 'owner'",
    )
