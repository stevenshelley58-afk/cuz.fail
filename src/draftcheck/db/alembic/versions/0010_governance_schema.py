"""Governance schema — process-control / source-governance feature.

Adds the governance tables, indexes, and additive columns required by
docs/process-control/implementation-map.md (PR-2).

Alembic owns schema creation for V3 (enforced by
tests/test_v3_schema_contract.py). This revision is the schema authority
for PR-2.

The inline ``op.create_table`` calls in ``upgrade()`` and ``downgrade()``
are kept at the top level so the
``tests/test_migrations.py::test_v3_revisions_are_explicit_and_legacy_free``
metadata-consistency check (which parses those call sites) can validate
this revision without false negatives.

Revision ID: 0010_governance_schema
Revises: 0009_wp7_db_fixes
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0010_governance_schema"
down_revision: str | None = "0009_wp7_db_fixes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


JSONB = postgresql.JSONB(astext_type=sa.Text())
UUID = sa.Uuid(as_uuid=True)
NOW = sa.text("now()")
EMPTY_JSON = sa.text("'{}'::jsonb")
EMPTY_ARRAY_JSON = sa.text("'[]'::jsonb")


def _metadata_json(name: str = "metadata_json") -> sa.Column:
    return sa.Column(name, JSONB, nullable=False, server_default=EMPTY_JSON)


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    # 1. Role enum extension — add COMPLIANCE_OWNER
    # users.role uses a CHECK constraint (native_enum=False in models.py).
    op.drop_constraint("identity_role", "users", type_="check")
    op.create_check_constraint(
        "identity_role",
        "users",
        "role IN ('owner', 'operator', 'compliance_owner')",
    )

    # 2. governance_pipeline_steps
    op.create_table(
        "governance_pipeline_steps",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("stage", sa.String(80), nullable=False),
        sa.Column("function_path", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_critical", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("owner_role", sa.String(40), nullable=False, server_default="operator"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )
    op.create_index(
        "ix_governance_pipeline_steps_stage",
        "governance_pipeline_steps",
        ["stage"],
    )
    op.create_index(
        "ix_governance_pipeline_steps_critical",
        "governance_pipeline_steps",
        ["is_critical"],
    )
    op.create_unique_constraint(
        "uq_governance_pipeline_steps_function",
        "governance_pipeline_steps",
        ["function_path"],
    )

    # 3. governance_risks
    op.create_table(
        "governance_risks",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("severity", sa.String(40), nullable=False, server_default="major"),
        sa.Column("default_owner_role", sa.String(40), nullable=False, server_default="operator"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )
    op.create_index(
        "ix_governance_risks_severity",
        "governance_risks",
        ["severity"],
    )

    # 4. governance_controls
    op.create_table(
        "governance_controls",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "code",
            sa.String(80),
            sa.ForeignKey("governance_risks.code", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("control_type", sa.String(40), nullable=False, server_default="detective"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("control_function_path", sa.String(300), nullable=True),
        sa.Column("owner_role", sa.String(40), nullable=False, server_default="operator"),
        sa.Column("test_frequency_days", sa.Integer, nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        _metadata_json(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint(
            "control_type IN ('preventive', 'detective', 'corrective')",
            name="ck_governance_controls_type",
        ),
    )
    op.create_index(
        "ix_governance_controls_risk",
        "governance_controls",
        ["code"],
    )
    op.create_index(
        "ix_governance_controls_last_tested",
        "governance_controls",
        ["last_tested_at"],
    )
    op.create_unique_constraint(
        "uq_governance_controls_name",
        "governance_controls",
        ["name"],
    )

    # 5. governance_kpis
    op.create_table(
        "governance_kpis",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("sql_template", sa.Text, nullable=False),
        sa.Column("warning_threshold", sa.Numeric(18, 6), nullable=True),
        sa.Column("breach_threshold", sa.Numeric(18, 6), nullable=True),
        sa.Column("review_cadence_days", sa.Integer, nullable=True),
        sa.Column("owner_role", sa.String(40), nullable=False, server_default="operator"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )

    # 6. governance_kpi_results
    op.create_table(
        "governance_kpi_results",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "kpi_id",
            UUID,
            sa.ForeignKey("governance_kpis.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("value", sa.Numeric(18, 6), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="green"),
        sa.Column(
            "evidence_id",
            UUID,
            sa.ForeignKey("artifacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint(
            "status IN ('green', 'amber', 'red')",
            name="ck_governance_kpi_results_status",
        ),
    )
    op.create_index(
        "ix_governance_kpi_results_kpi_period",
        "governance_kpi_results",
        ["kpi_id", sa.text("period_end DESC")],
    )
    op.create_index(
        "ix_governance_kpi_results_status",
        "governance_kpi_results",
        ["status"],
    )

    # 7. governance_findings
    op.create_table(
        "governance_findings",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "org_id",
            UUID,
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "risk_code",
            sa.String(80),
            sa.ForeignKey("governance_risks.code", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("severity", sa.String(40), nullable=False, server_default="major"),
        sa.Column("subject_type", sa.String(80), nullable=False),
        sa.Column("subject_id", UUID, nullable=True),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("evidence_refs_json", JSONB, nullable=False, server_default=EMPTY_ARRAY_JSON),
        sa.Column("proposed_remediation", sa.Text, nullable=True),
        sa.Column(
            "proposed_by_job_trace_id",
            UUID,
            sa.ForeignKey("job_traces.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("proposed_by_model", sa.String(200), nullable=True),
        sa.Column("skill_version_id", sa.String(160), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="proposed"),
        sa.Column(
            "decision_user_id",
            UUID,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decision_reason", sa.Text, nullable=True),
        sa.Column(
            "decision_evidence_id",
            UUID,
            sa.ForeignKey("artifacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "linked_capa_id",
            UUID,
            sa.ForeignKey("review_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint(
            "status IN ('proposed', 'accepted', 'rejected', 'converted_to_capa', 'superseded')",
            name="ck_governance_findings_status",
        ),
        sa.CheckConstraint(
            "severity IN ('critical', 'major', 'minor')",
            name="ck_governance_findings_severity",
        ),
    )
    op.create_index(
        "ix_governance_findings_status_severity",
        "governance_findings",
        ["status", "severity"],
    )
    op.create_index(
        "ix_governance_findings_org_status",
        "governance_findings",
        ["org_id", "status"],
    )
    op.create_index(
        "ix_governance_findings_proposed_by_job_trace",
        "governance_findings",
        ["proposed_by_job_trace_id"],
    )
    op.create_index(
        "ix_governance_findings_subject",
        "governance_findings",
        ["subject_type", "subject_id"],
    )
    op.create_index(
        "ix_governance_findings_created_at",
        "governance_findings",
        ["created_at"],
    )
    # Partial unique index: same (subject, risk) cannot be in 'proposed' state twice.
    op.create_index(
        "uq_governance_findings_subject_risk_proposed",
        "governance_findings",
        ["subject_type", "subject_id", "risk_code"],
        unique=True,
        postgresql_where=sa.text("status = 'proposed'"),
    )

    # 8. governance_reviews
    op.create_table(
        "governance_reviews",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("review_type", sa.String(40), nullable=False, server_default="ad_hoc"),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column(
            "chair_user_id",
            UUID,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("decisions_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("open_actions_json", JSONB, nullable=False, server_default=EMPTY_ARRAY_JSON),
        sa.Column("evidence_pack_refs_json", JSONB, nullable=False, server_default=EMPTY_ARRAY_JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint(
            "review_type IN ('monthly', 'quarterly', 'annual', 'ad_hoc')",
            name="ck_governance_reviews_type",
        ),
    )
    op.create_index(
        "ix_governance_reviews_period",
        "governance_reviews",
        ["period_start", "period_end"],
    )
    op.create_index(
        "ix_governance_reviews_chair",
        "governance_reviews",
        ["chair_user_id"],
    )

    # 9. Additive columns on source_versions
    op.add_column(
        "source_versions",
        sa.Column(
            "owner_user_id",
            UUID,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "source_versions",
        sa.Column("review_due_date", sa.Date, nullable=True),
    )
    op.add_column(
        "source_versions",
        sa.Column("next_required_action", sa.String(200), nullable=True),
    )
    op.create_index(
        "ix_source_versions_owner",
        "source_versions",
        ["owner_user_id"],
    )
    op.create_index(
        "ix_source_versions_review_due",
        "source_versions",
        ["review_due_date"],
    )

    # 10. Additive columns on review_items
    op.add_column(
        "review_items",
        sa.Column("severity", sa.String(40), nullable=True),
    )
    op.add_column(
        "review_items",
        sa.Column("root_cause", sa.Text, nullable=True),
    )
    op.add_column(
        "review_items",
        sa.Column(
            "closure_evidence_id",
            UUID,
            sa.ForeignKey("artifacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "review_items",
        sa.Column("effectiveness_check_due_date", sa.Date, nullable=True),
    )
    op.add_column(
        "review_items",
        sa.Column("effectiveness_result", sa.Text, nullable=True),
    )
    op.add_column(
        "review_items",
        sa.Column(
            "proposed_by_finding_id",
            UUID,
            sa.ForeignKey("governance_findings.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_review_items_severity",
        "review_items",
        ["severity"],
    )
    op.create_index(
        "ix_review_items_closure_evidence",
        "review_items",
        ["closure_evidence_id"],
    )


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    # Reverse of upgrade(), in reverse order.

    # 10. review_items additive columns
    op.drop_index("ix_review_items_closure_evidence", table_name="review_items")
    op.drop_index("ix_review_items_severity", table_name="review_items")
    op.drop_column("review_items", "proposed_by_finding_id")
    op.drop_column("review_items", "effectiveness_result")
    op.drop_column("review_items", "effectiveness_check_due_date")
    op.drop_column("review_items", "closure_evidence_id")
    op.drop_column("review_items", "root_cause")
    op.drop_column("review_items", "severity")

    # 9. source_versions additive columns
    op.drop_index("ix_source_versions_review_due", table_name="source_versions")
    op.drop_index("ix_source_versions_owner", table_name="source_versions")
    op.drop_column("source_versions", "next_required_action")
    op.drop_column("source_versions", "review_due_date")
    op.drop_column("source_versions", "owner_user_id")

    # 8. governance_reviews
    op.drop_table("governance_reviews")

    # 7. governance_findings
    op.drop_table("governance_findings")

    # 6. governance_kpi_results
    op.drop_table("governance_kpi_results")

    # 5. governance_kpis
    op.drop_table("governance_kpis")

    # 4. governance_controls
    op.drop_table("governance_controls")

    # 3. governance_risks
    op.drop_table("governance_risks")

    # 2. governance_pipeline_steps
    op.drop_table("governance_pipeline_steps")

    # 1. role enum — reverse of extension
    op.execute("DELETE FROM users WHERE role = 'compliance_owner'")
    op.drop_constraint("identity_role", "users", type_="check")
    op.create_check_constraint(
        "identity_role",
        "users",
        "role IN ('owner', 'operator')",
    )
