"""WP7 DB fixes — pg_trgm, address trigram index, CHECK constraints, council_scope column,
rules zone/r_code columns, property_facts composite index.

Revision ID: 0008_wp7_db_fixes
Revises: 0007_nullable_org_job_traces
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0008_wp7_db_fixes"
down_revision: str | None = "0007_nullable_org_job_traces"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Enable pg_trgm extension
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # 2. GIN trigram index on address_points.address_text
    op.create_index(
        "ix_address_points_address_text_trgm",
        "address_points",
        ["address_text"],
        postgresql_ops={"address_text": "gin_trgm_ops"},
        postgresql_using="gin",
    )

    # 3. CHECK constraints on status/review_status columns
    op.create_check_constraint(
        "ck_rules_lifecycle_status",
        "rules",
        "lifecycle_status IN ('pending_review', 'approved', 'rejected', 'auto_accepted')",
    )
    op.create_check_constraint(
        "ck_rule_candidates_review_status",
        "rule_candidates",
        "review_status IN ('pending_review', 'pending_extraction', 'auto_promoted', "
        "'validators_passed', 'validator_failed', 'eval_failed', 'rejected')",
    )
    op.create_check_constraint(
        "ck_check_results_status",
        "check_results",
        "status IN ('likely_pass', 'likely_fail', 'needs_more_info', 'unsupported')",
    )
    op.create_check_constraint(
        "ck_document_facts_review_status",
        "document_facts",
        "review_status IN ('pending_review', 'confirmed')",
    )

    # 4. Promote projects.council_scope from metadata_json to a real column
    op.add_column(
        "projects",
        sa.Column("council_scope", sa.String(120), nullable=True),
    )
    op.execute(
        "UPDATE projects SET council_scope = metadata_json->>'council_scope' "
        "WHERE metadata_json ? 'council_scope'"
    )
    op.create_index("ix_projects_council_scope", "projects", ["council_scope"])

    # 5. Add applicable_zones and applicable_r_codes JSONB columns to rules
    op.add_column(
        "rules",
        sa.Column(
            "applicable_zones",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "rules",
        sa.Column(
            "applicable_r_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # 6. Composite index on property_facts(project_id, review_status)
    op.create_index(
        "ix_property_facts_project_review",
        "property_facts",
        ["project_id", "review_status"],
    )

    # 7. planning_features.layer_type — no existing CHECK constraint in prior migrations;
    #    step skipped as instructed.


def downgrade() -> None:
    # 7. (skipped — no constraint was added)

    # 6. Drop property_facts composite index
    op.drop_index("ix_property_facts_project_review", table_name="property_facts")

    # 5. Drop rules zone/r_code columns
    op.drop_column("rules", "applicable_r_codes")
    op.drop_column("rules", "applicable_zones")

    # 4. Drop projects.council_scope column (and its index)
    op.drop_index("ix_projects_council_scope", table_name="projects")
    op.drop_column("projects", "council_scope")

    # 3. Drop CHECK constraints
    op.drop_constraint("ck_document_facts_review_status", "document_facts", type_="check")
    op.drop_constraint("ck_check_results_status", "check_results", type_="check")
    op.drop_constraint("ck_rule_candidates_review_status", "rule_candidates", type_="check")
    op.drop_constraint("ck_rules_lifecycle_status", "rules", type_="check")

    # 2. Drop address_points trigram index
    op.drop_index("ix_address_points_address_text_trgm", table_name="address_points")

    # 1. Drop pg_trgm extension — skipped; other code may depend on it.
    #    To remove: op.execute("DROP EXTENSION IF EXISTS pg_trgm")
