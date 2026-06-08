"""Persist assessment context on compliance runs and results.

Revision ID: 0003_compliance_assessment_context
Revises: 0002_foundation_schema
Create Date: 2026-06-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_compliance_assessment_context"
down_revision = "0002_foundation_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if _has_table("check_runs"):
        _add_column_if_missing(
            "check_runs",
            sa.Column("as_of_date", sa.String(), nullable=False, server_default="unknown"),
        )
        _add_column_if_missing(
            "check_runs",
            sa.Column("assessment_basis", sa.String(), nullable=False, server_default="current_rules"),
        )
        _drop_server_default("check_runs", "as_of_date")
        _drop_server_default("check_runs", "assessment_basis")

    if _has_table("check_results"):
        _add_column_if_missing(
            "check_results",
            sa.Column("as_of_date", sa.String(), nullable=False, server_default="unknown"),
        )
        _add_column_if_missing(
            "check_results",
            sa.Column("assessment_basis", sa.String(), nullable=False, server_default="current_rules"),
        )
        _drop_server_default("check_results", "as_of_date")
        _drop_server_default("check_results", "assessment_basis")


def downgrade() -> None:
    if _has_table("check_results"):
        _drop_column_if_present("check_results", "assessment_basis")
        _drop_column_if_present("check_results", "as_of_date")
    if _has_table("check_runs"):
        _drop_column_if_present("check_runs", "assessment_basis")
        _drop_column_if_present("check_runs", "as_of_date")


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


def _drop_server_default(table_name: str, column_name: str) -> None:
    if op.get_bind().dialect.name != "sqlite" and _has_column(table_name, column_name):
        op.alter_column(table_name, column_name, server_default=None)
