"""Normalize legacy licence_status vocabulary drift.

Revision ID: 0016_normalize_licence_status_vocabulary
Revises: 0015_rules_council_scope
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision: str = "0016_normalize_licence_status_vocabulary"
down_revision: str | None = "0015_rules_council_scope"
branch_labels = None
depends_on = None


_LEGACY_REWRITES: dict[str, str] = {
    "approved": "verified_open",
    "CC BY 4.0": "verified_open",
    "cc by 4.0": "verified_open",
    "cc-by-4.0": "verified_open",
    "cc_by_4_0": "verified_open",
}

_V3_VALUES = (
    "open",
    "verified_open",
    "pending_review",
    "restricted",
    "metadata_only",
    "prohibited",
    "unknown",
)


def upgrade() -> None:
    for table_name in ("source_versions", "spatial_datasets"):
        stmt = sa.text(
            f"UPDATE {table_name} SET licence_status = "
            f"CASE "
            f"  WHEN licence_status IN ({', '.join(repr(v) for v in _V3_VALUES)}) THEN licence_status "
            f"  {' '.join(f'WHEN licence_status = {legacy!r} THEN {target!r} ' for legacy, target in _LEGACY_REWRITES.items())}"
            f"  ELSE 'unknown' "
            f"END "
            f"WHERE licence_status IS NULL "
            f"   OR licence_status NOT IN ({', '.join(repr(v) for v in _V3_VALUES)})"
        )
        op.execute(stmt)


def downgrade() -> None:
    for table_name in ("source_versions", "spatial_datasets"):
        for legacy, target in _LEGACY_REWRITES.items():
            op.execute(
                sa.text(
                    f"UPDATE {table_name} SET licence_status = {legacy!r} "
                    f"WHERE licence_status = {target!r}"
                ),
            )
