"""Normalize legacy `licence_status` vocabulary drift.

Some prod rows carry licence_status values that predate the V3 LicenceStatus
enum (open, verified_open, pending_review, restricted, metadata_only,
prohibited, unknown). The runtime shim in
`domain/sources/library.py:_coerce_licence_status` tolerates these in
retrieval so a stray legacy value can't 500 the app, but that means silent
drift can hide real licence gaps. This migration rewrites the known legacy
aliases to the V3 vocabulary in place, then defaults anything else to
'unknown' (the conservative fallback) so the shim becomes a safety net, not
the mechanism.

Why we don't just CHECK the column into a single canonical set:
- The check is already a runtime responsibility (the Enum in the ORM), and
  the prod column is `String(40)` to keep migration simple.
- Other agents (e.g. WP4 acquisition worker) write into this column from
  other code paths; locking the vocabulary at the DB layer would break
  ingestion during a windowed rollout. The shim + this one-shot rewrite is
  the cheaper, safer path.

After this migration:
- `approved` -> `verified_open` (matches the runtime alias exactly).
- Any non-V3 value (other legacy strings, case variants, NULLs) ->
  `unknown` so retrieval excludes it from citation rather than guessing.
- A `gate_audit.sql` companion under `reports/` should be re-run after this
  migration to confirm 0 other_legacy / 0 NULLs in the audited tables.

Revision ID: 0016_normalize_licence_status_vocabulary
Revises: 0015_rules_council_scope
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0016_normalize_licence_status_vocabulary"
down_revision: str | None = "0015_rules_council_scope"
branch_labels = None
depends_on = None


# Mirrors `KNOWN_LEGACY_ALIASES` in `scripts/audit_licence_status.py` and
# `_LEGACY_LICENCE_ALIASES` in `domain/sources/library.py`. Kept as a literal
# so this migration is independent of any code-side alias changes.
_LEGACY_REWRITES: dict[str, str] = {
    "approved": "verified_open",
}

# All current V3 values (mirror of `LicenceStatus` enum). Anything outside
# this set AND outside the rewrite map is treated as drift and coerced to
# 'unknown' so the retrieval gate can exclude it.
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
        # Single UPDATE — uses a CASE to handle all branches in one statement.
        # NULLs are handled by the ELSE 'unknown' branch (CASE returns ELSE
        # for NULL, not the first WHEN, because the WHEN uses equality).
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
    """Best-effort downgrade: rewrite back to the legacy alias for any row
    whose value matches a known mapping. Rows that we coerced to 'unknown'
    cannot be recovered — they're recorded in the audit report as drift.
    """
    for table_name in ("source_versions", "spatial_datasets"):
        for legacy, target in _LEGACY_REWRITES.items():
            op.execute(
                sa.text(
                    f"UPDATE {table_name} SET licence_status = {legacy!r} "
                    f"WHERE licence_status = {target!r}"
                ),
            )
        # Anything we coerced to 'unknown' during upgrade is left as-is
        # because the original value cannot be reconstructed.
