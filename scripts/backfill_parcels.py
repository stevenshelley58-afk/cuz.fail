"""WP-G: backfill ``address_points.parcel_id`` from containing parcels.

Links every G-NAF address point that has no parcel yet to the cadastral parcel
whose polygon contains the point (PostGIS ``ST_Contains``).  This is the first
step of spatial enrichment: without a parcel link, an address cannot resolve to
zone / R-code / measurement facts.

Idempotent and DRY-RUN BY DEFAULT — it only writes when invoked with ``--apply``.
In dry-run it reports the count of rows that *would* be linked.

    # dry run (default): report only
    python scripts/backfill_parcels.py

    # apply the UPDATE
    python scripts/backfill_parcels.py --apply

A JSON report with before/after counts is written to
``reports/backfill_parcels.json`` (override with ``--report``).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import Connection  # noqa: E402

DEFAULT_REPORT = Path(__file__).resolve().parent.parent / "reports" / "backfill_parcels.json"

# Rows that would be linked: an unlinked address point sitting inside a parcel.
_CANDIDATE_COUNT_SQL = text(
    """
    SELECT count(*)
    FROM address_points ap
    JOIN parcels p ON ST_Contains(p.geom, ap.geom)
    WHERE ap.parcel_id IS NULL
    """
)

_UNLINKED_COUNT_SQL = text("SELECT count(*) FROM address_points WHERE parcel_id IS NULL")
_LINKED_COUNT_SQL = text("SELECT count(*) FROM address_points WHERE parcel_id IS NOT NULL")

_BACKFILL_SQL = text(
    """
    UPDATE address_points ap
    SET parcel_id = p.id, updated_at = now()
    FROM parcels p
    WHERE ap.parcel_id IS NULL AND ST_Contains(p.geom, ap.geom)
    """
)


def database_url() -> str:
    url = os.environ["DATABASE_URL"]
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")


def _scalar(conn: Connection, stmt: Any) -> int:
    return int(conn.execute(stmt).scalar_one())


def run_backfill(conn: Connection, *, apply: bool) -> dict[str, Any]:
    """Run the backfill (or count candidates in dry-run) and return a report."""
    before_unlinked = _scalar(conn, _UNLINKED_COUNT_SQL)
    before_linked = _scalar(conn, _LINKED_COUNT_SQL)
    candidates = _scalar(conn, _CANDIDATE_COUNT_SQL)

    updated = 0
    if apply:
        result = conn.execute(_BACKFILL_SQL)
        updated = int(result.rowcount or 0)

    after_unlinked = _scalar(conn, _UNLINKED_COUNT_SQL)
    after_linked = _scalar(conn, _LINKED_COUNT_SQL)

    return {
        "wp": "WP-G",
        "mode": "apply" if apply else "dry_run",
        "before": {"linked": before_linked, "unlinked": before_unlinked},
        "candidates_would_link": candidates,
        "updated": updated,
        "after": {"linked": after_linked, "unlinked": after_unlinked},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write parcel_id links")
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help="JSON report output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if "DATABASE_URL" not in os.environ:
        raise SystemExit("DATABASE_URL is required")

    engine = create_engine(database_url())
    with engine.begin() as conn:
        report = run_backfill(conn, apply=args.apply)
        if not args.apply:
            # Dry-run never persists; the engine.begin() block would commit, so
            # explicitly roll back to leave the database untouched.
            conn.rollback()

    output = json.dumps(report, indent=2, sort_keys=True)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(output, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
