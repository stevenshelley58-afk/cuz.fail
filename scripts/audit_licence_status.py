"""Audit legacy `licence_status` vocabulary drift in source_versions and spatial_datasets.

The V3 LicenceStatus enum is:
    open, verified_open, pending_review, restricted, metadata_only, prohibited, unknown

The runtime coercion shim in `domain/sources/library.py:_coerce_licence_status`
maps the known legacy alias 'approved' -> verified_open, and defaults anything
else to UNKNOWN. This audit reports what other legacy / NULL / odd values are
present so the migration can rewrite them in place — after which the runtime
shim becomes a safety net, not the mechanism.

Run on the VPS (prod Postgres) or against a snapshot. Writes a JSON report to
`reports/licence_status_audit.json` plus a human-readable summary on stdout.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Engine

# Make `scripts.*` imports work whether invoked as a module or a script.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from draftcheck.domain.sources.models import LicenceStatus  # noqa: E402

V3_VALUES = {member.value for member in LicenceStatus}
# Anything in this set is a known legacy alias and is safe to rewrite.
KNOWN_LEGACY_ALIASES = {
    "approved": LicenceStatus.VERIFIED_OPEN.value,
}


def _connect() -> Engine:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL must be set (e.g. postgres://... or postgresql+psycopg://...)")
    return sa.create_engine(url, future=True)


def _audit_table(conn: sa.engine.Connection, table: str) -> dict[str, Any]:
    """Return a per-value count plus a NULL count for `table.licence_status`."""
    counts = conn.execute(
        sa.text(
            f"SELECT licence_status, COUNT(*) AS n "
            f"FROM {table} GROUP BY licence_status ORDER BY n DESC"
        )
    ).mappings().all()
    null_count = conn.execute(
        sa.text(f"SELECT COUNT(*) AS n FROM {table} WHERE licence_status IS NULL")
    ).scalar_one()
    value_counts = {row["licence_status"]: int(row["n"]) for row in counts}
    # Distinguish V3 values from legacy / unknown.
    v3 = {k: v for k, v in value_counts.items() if k in V3_VALUES}
    legacy_known = {k: v for k, v in value_counts.items() if k in KNOWN_LEGACY_ALIASES}
    other_legacy = {
        k: v for k, v in value_counts.items()
        if k is not None and k not in V3_VALUES and k not in KNOWN_LEGACY_ALIASES
    }
    return {
        "table": table,
        "total_rows": sum(value_counts.values()),
        "value_count": len(value_counts),
        "v3_values": v3,
        "legacy_known_aliases": legacy_known,
        "other_legacy": other_legacy,
        "null_count": int(null_count),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=REPO_ROOT / "reports" / "licence_status_audit.json",
        help="Path to write the JSON report (default: reports/licence_status_audit.json)",
    )
    args = parser.parse_args()

    engine = _connect()
    with engine.connect() as conn:
        source_versions = _audit_table(conn, "source_versions")
        spatial_datasets = _audit_table(conn, "spatial_datasets")

    # Gate: any `other_legacy` values or NULLs require a normalization migration.
    drift_total = (
        sum(source_versions["other_legacy"].values())
        + source_versions["null_count"]
        + sum(spatial_datasets["other_legacy"].values())
        + spatial_datasets["null_count"]
    )
    legacy_alias_total = (
        sum(source_versions["legacy_known_aliases"].values())
        + sum(spatial_datasets["legacy_known_aliases"].values())
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "v3_values": sorted(V3_VALUES),
        "known_legacy_aliases": dict(sorted(KNOWN_LEGACY_ALIASES.items())),
        "tables": {
            "source_versions": source_versions,
            "spatial_datasets": spatial_datasets,
        },
        "summary": {
            "drift_rows_total": drift_total,
            "legacy_alias_rows_total": legacy_alias_total,
            "gate_passed": drift_total == 0,
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    # Human summary on stdout — one table per audited table.
    for label, payload in (("source_versions", source_versions), ("spatial_datasets", spatial_datasets)):
        print(f"== {label} ==")
        print(f"  total_rows       : {payload['total_rows']}")
        print(f"  distinct_values  : {payload['value_count']}")
        print(f"  null_count       : {payload['null_count']}")
        print(f"  v3_values        : {Counter(payload['v3_values']).total() if payload['v3_values'] else 0}")
        if payload["v3_values"]:
            for v, n in sorted(payload["v3_values"].items(), key=lambda kv: -kv[1]):
                print(f"    {v:<20} {n}")
        if payload["legacy_known_aliases"]:
            print("  legacy_known     :")
            for v, n in sorted(payload["legacy_known_aliases"].items(), key=lambda kv: -kv[1]):
                print(f"    {v:<20} {n}")
        if payload["other_legacy"]:
            print("  other_legacy     : (REQUIRES MIGRATION)")
            for v, n in sorted(payload["other_legacy"].items(), key=lambda kv: -kv[1]):
                print(f"    {v:<20} {n}")
        print()
    print(f"gate_passed       : {report['summary']['gate_passed']}")
    print(f"drift_rows_total  : {drift_total}")
    print(f"report            : {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
