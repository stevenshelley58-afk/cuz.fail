"""Extend identity_role CHECK constraint to allow the guest role."""

from __future__ import annotations

from alembic import op

revision: str = "0012_add_guest_role"
down_revision: str | None = "0011_corpus_buildout_support"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("identity_role", "users", type_="check")
    op.create_check_constraint(
        "identity_role",
        "users",
        "role IN ('owner', 'operator', 'compliance_owner', 'guest')",
    )


def downgrade() -> None:
    op.drop_constraint("identity_role", "users", type_="check")
    op.create_check_constraint(
        "identity_role",
        "users",
        "role IN ('owner', 'operator', 'compliance_owner')",
    )
