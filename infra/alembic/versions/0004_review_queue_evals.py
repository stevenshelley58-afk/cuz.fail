"""Add review queue and golden eval foundations.

Revision ID: 0004_review_queue_evals
Revises: 0003_compliance_assessment_context
Create Date: 2026-06-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from draftcheck_core import models  # noqa: F401
from draftcheck_core.database import Base

revision = "0004_review_queue_evals"
down_revision = "0003_compliance_assessment_context"
branch_labels = None
depends_on = None


NEW_TABLES = [
    "review_queue_items",
    "golden_eval_cases",
    "golden_eval_runs",
]


def upgrade() -> None:
    bind = op.get_bind()
    metadata = Base.metadata
    for table_name in NEW_TABLES:
        if not _has_table(table_name):
            metadata.tables[table_name].create(bind=bind, checkfirst=True)


def downgrade() -> None:
    for table_name in reversed(NEW_TABLES):
        if _has_table(table_name):
            op.drop_table(table_name)


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)
