"""Initial metadata migration.

Revision ID: 0001_initial_metadata
Revises:
Create Date: 2026-06-05
"""
from __future__ import annotations

from alembic import op

from draftcheck_core.database import Base
from draftcheck_core import models  # noqa: F401

revision = "0001_initial_metadata"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
