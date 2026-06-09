"""Drop human review gate: signoffs table, reviewer FK columns, collapse users.role to owner only.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-09

Decision (2026-06-09): pipeline is fully AI — no human reviewer or signoff gate.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_drop_human_review"
down_revision = "0002_v3_complete_target_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop the signoffs table (human signoff gate).
    op.drop_index("ix_signoffs_signer_user_id", table_name="signoffs")
    op.drop_index("ix_signoffs_export", table_name="signoffs")
    op.drop_index("ix_signoffs_project", table_name="signoffs")
    op.drop_index("ix_signoffs_check_run_id", table_name="signoffs")
    op.drop_index("ix_signoffs_export_id", table_name="signoffs")
    op.drop_index("ix_signoffs_project_id", table_name="signoffs")
    op.drop_index("ix_signoffs_org_id", table_name="signoffs")
    op.drop_table("signoffs")

    # 2. Drop rules.approved_by_user_id (human approver FK).
    op.drop_index("ix_rules_approved_by_user_id", table_name="rules")
    op.drop_column("rules", "approved_by_user_id")
    op.drop_column("rules", "approved_at")

    # 3. Drop source_reviews.reviewer_user_id (human reviewer FK).
    op.drop_index("ix_source_reviews_reviewer_user_id", table_name="source_reviews")
    op.drop_column("source_reviews", "reviewer_user_id")

    # 4. Collapse users.role to owner-only: update any leftover 'reviewer' rows, then
    #    replace the check constraint to only allow 'owner'.
    op.execute("UPDATE users SET role = 'owner' WHERE role = 'reviewer'")
    op.drop_constraint("identity_role", "users", type_="check")
    op.create_check_constraint(
        "identity_role",
        "users",
        "role IN ('owner')",
    )


def downgrade() -> None:
    # Restore the two-value role constraint (rows cannot be un-promoted).
    op.drop_constraint("identity_role", "users", type_="check")
    op.create_check_constraint(
        "identity_role",
        "users",
        "role IN ('owner', 'reviewer')",
    )

    # Restore source_reviews.reviewer_user_id as nullable (cannot recover original values).
    op.add_column(
        "source_reviews",
        sa.Column(
            "reviewer_user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index("ix_source_reviews_reviewer_user_id", "source_reviews", ["reviewer_user_id"])

    # Restore rules.approved_by_user_id and approved_at as nullable.
    op.add_column(
        "rules",
        sa.Column(
            "approved_by_user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "rules",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_rules_approved_by_user_id", "rules", ["approved_by_user_id"])

    # Restore the signoffs table (empty — data is not recoverable).
    op.create_table(
        "signoffs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.UUID(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("export_id", sa.UUID(), sa.ForeignKey("exports.id", ondelete="SET NULL")),
        sa.Column("check_run_id", sa.UUID(), sa.ForeignKey("check_runs.id", ondelete="SET NULL")),
        sa.Column("signer_user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("signoff_type", sa.String(80), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="signed"),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_signoffs_org_id", "signoffs", ["org_id"])
    op.create_index("ix_signoffs_project_id", "signoffs", ["project_id"])
    op.create_index("ix_signoffs_export_id", "signoffs", ["export_id"])
    op.create_index("ix_signoffs_check_run_id", "signoffs", ["check_run_id"])
    op.create_index("ix_signoffs_signer_user_id", "signoffs", ["signer_user_id"])
    op.create_index("ix_signoffs_project", "signoffs", ["project_id"])
    op.create_index("ix_signoffs_export", "signoffs", ["export_id"])
