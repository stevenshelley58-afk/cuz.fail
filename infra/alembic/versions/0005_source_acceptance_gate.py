"""Add source version review status for acceptance gate.

Revision ID: 0005_source_acceptance_gate
Revises: 0004_review_queue_evals
Create Date: 2026-06-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_source_acceptance_gate"
down_revision = "0004_review_queue_evals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not _has_table("source_versions"):
        return
    _add_column_if_missing(
        "source_versions",
        sa.Column("review_status", sa.String(), nullable=False, server_default="pending_review"),
    )
    _add_column_if_missing("source_versions", sa.Column("reviewed_by", sa.String(), nullable=True))
    _add_column_if_missing("source_versions", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    _drop_server_default("source_versions", "review_status")


def downgrade() -> None:
    if not _has_table("source_versions"):
        return
    _drop_column_if_present("source_versions", "reviewed_at")
    _drop_column_if_present("source_versions", "reviewed_by")
    _drop_column_if_present("source_versions", "review_status")


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
