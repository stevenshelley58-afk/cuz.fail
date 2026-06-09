"""Add approval_status to spatial_datasets (Stage 2 delta).

Revision ID: 0003_spatial_approval_status
Revises: 0002_v3_complete_target_schema

The in-memory SpatialDatasetMetadata.is_authoritative() checks approval_status
independently from licence_status. The PostGIS-backed store needs the same field
so dataset rows can be marked authoritative without requiring a full source-version
review join on every resolver call.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0003_spatial_approval_status"
down_revision: str | None = "0002_v3_complete_target_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "spatial_datasets",
        sa.Column(
            "approval_status",
            sa.String(40),
            nullable=False,
            server_default="pending_review",
        ),
    )
    op.create_index(
        "ix_spatial_datasets_approval_status",
        "spatial_datasets",
        ["approval_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_spatial_datasets_approval_status", table_name="spatial_datasets")
    op.drop_column("spatial_datasets", "approval_status")
