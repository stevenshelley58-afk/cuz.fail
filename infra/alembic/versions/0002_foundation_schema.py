"""Add source, spatial, rule, and decision trace foundations.

Revision ID: 0002_foundation_schema
Revises: 0001_initial_metadata
Create Date: 2026-06-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from draftcheck_core import models  # noqa: F401
from draftcheck_core.database import Base

revision = "0002_foundation_schema"
down_revision = "0001_initial_metadata"
branch_labels = None
depends_on = None


FOUNDATION_TABLES = [
    "project_proposals",
    "spatial_datasets",
    "parcels",
    "address_points",
    "planning_layer_features",
    "local_government_boundaries",
    "address_profiles",
    "address_facts",
    "local_government_facts",
    "source_artifacts",
    "source_licence_reviews",
    "source_supersessions",
    "source_references",
    "clause_references",
    "clause_dispositions",
    "rule_extraction_candidates",
    "rule_rows",
    "rule_to_clauses",
    "rule_overrides",
    "rule_carveouts",
    "resolved_rules",
    "decision_traces",
]


def upgrade() -> None:
    bind = op.get_bind()
    metadata = Base.metadata

    for table_name in FOUNDATION_TABLES:
        if not _has_table(table_name):
            metadata.tables[table_name].create(bind=bind, checkfirst=True)

    if _has_table("projects"):
        _add_column_if_missing("projects", sa.Column("as_of_date", sa.String(), nullable=True))
        _add_column_if_missing("projects", sa.Column("lodgement_date", sa.String(), nullable=True))
        _add_column_if_missing(
            "projects",
            sa.Column(
                "assessment_basis",
                sa.String(),
                nullable=False,
                server_default="current_rules",
            ),
        )
        if bind.dialect.name != "sqlite":
            op.alter_column("projects", "assessment_basis", server_default=None)

    if _has_table("properties"):
        address_profile_column = sa.Column("address_profile_id", sa.String(), nullable=True)
        if bind.dialect.name != "sqlite":
            address_profile_column = sa.Column(
                "address_profile_id",
                sa.String(),
                sa.ForeignKey("address_profiles.id"),
                nullable=True,
            )
        _add_column_if_missing("properties", address_profile_column)


def downgrade() -> None:
    if _has_table("properties"):
        _drop_column_if_present("properties", "address_profile_id")

    if _has_table("projects"):
        _drop_column_if_present("projects", "assessment_basis")
        _drop_column_if_present("projects", "lodgement_date")
        _drop_column_if_present("projects", "as_of_date")

    for table_name in reversed(FOUNDATION_TABLES):
        if _has_table(table_name):
            op.drop_table(table_name)


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def _drop_column_if_present(table_name: str, column_name: str) -> None:
    if _has_column(table_name, column_name):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column(column_name)
