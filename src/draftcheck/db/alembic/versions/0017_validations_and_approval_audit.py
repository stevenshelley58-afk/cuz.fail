"""Add automated validations and approval audit fields.

Revision ID: 0017_validations_and_approval_audit
Revises: 0016_normalize_licence_status_vocabulary
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0017_validations_and_approval_audit"
down_revision: str | None = "0016_normalize_licence_status_vocabulary"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


JSONB = postgresql.JSONB(astext_type=sa.Text())
UUID = sa.Uuid(as_uuid=True)
NOW = sa.text("now()")
EMPTY_JSON = sa.text("'{}'::jsonb")
EMPTY_ARRAY_JSON = sa.text("'[]'::jsonb")


def upgrade() -> None:
    op.add_column(
        "source_reviews",
        sa.Column(
            "reviewed_by_user_id",
            UUID,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_source_reviews_reviewed_by", "source_reviews", ["reviewed_by_user_id"])

    op.add_column(
        "rules",
        sa.Column(
            "approved_by_user_id",
            UUID,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("rules", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "rules",
        sa.Column("approval_metadata_json", JSONB, nullable=False, server_default=EMPTY_JSON),
    )
    op.create_index("ix_rules_approved_by_user_id", "rules", ["approved_by_user_id"])

    op.create_table(
        "validations",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "org_id",
            UUID,
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            UUID,
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "export_id",
            UUID,
            sa.ForeignKey("exports.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "check_run_id",
            UUID,
            sa.ForeignKey("check_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "job_trace_id",
            UUID,
            sa.ForeignKey("job_traces.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("gate_name", sa.String(120), nullable=False),
        sa.Column(
            "validation_type",
            sa.String(80),
            nullable=False,
            server_default="automated_export_gate",
        ),
        sa.Column("subject_type", sa.String(80), nullable=False),
        sa.Column("subject_id", UUID, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="blocked"),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("findings_json", JSONB, nullable=False, server_default=EMPTY_ARRAY_JSON),
        sa.Column("manifest_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint(
            "status IN ('passed', 'failed', 'blocked')",
            name="ck_validations_status",
        ),
    )
    op.create_index("ix_validations_org_id", "validations", ["org_id"])
    op.create_index("ix_validations_project_id", "validations", ["project_id"])
    op.create_index("ix_validations_export_id", "validations", ["export_id"])
    op.create_index("ix_validations_check_run_id", "validations", ["check_run_id"])
    op.create_index("ix_validations_export_status", "validations", ["export_id", "status"])
    op.create_index("ix_validations_check_run_status", "validations", ["check_run_id", "status"])
    op.create_index("ix_validations_subject", "validations", ["subject_type", "subject_id"])
    op.create_index("ix_validations_job_trace", "validations", ["job_trace_id"])


def downgrade() -> None:
    op.drop_table("validations")

    op.drop_index("ix_rules_approved_by_user_id", table_name="rules")
    op.drop_column("rules", "approval_metadata_json")
    op.drop_column("rules", "approved_at")
    op.drop_column("rules", "approved_by_user_id")

    op.drop_index("ix_source_reviews_reviewed_by", table_name="source_reviews")
    op.drop_column("source_reviews", "reviewed_by_user_id")
