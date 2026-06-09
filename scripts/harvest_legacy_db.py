"""Harvest human-labelled data from the legacy draftcheck.db SQLite into JSONL eval seeds.

Extracts:
  rule_rows         → evals/seeds/rule_rows.jsonl
  clause_dispositions → evals/seeds/clause_dispositions.jsonl
  golden_eval_cases → evals/seeds/golden_eval_cases.jsonl
  golden_eval_runs  → evals/seeds/golden_eval_runs.jsonl

Usage:
    uv run python scripts/harvest_legacy_db.py [path/to/draftcheck.db] [--out-dir evals/seeds]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


HARVEST_TABLES = [
    "rule_rows",
    "clause_dispositions",
    "golden_eval_cases",
    "golden_eval_runs",
]


def _rows_as_dicts(conn: sqlite3.Connection, table: str) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cur = conn.execute(f"SELECT * FROM {table}")  # noqa: S608 — read-only legacy harvest
    return [dict(row) for row in cur.fetchall()]


def harvest(db_path: Path, out_dir: Path) -> None:
    if not db_path.exists():
        print(f"ERROR: {db_path} not found", file=sys.stderr)
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    # Integrity check first.
    result = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if result != "ok":
        print(f"ERROR: integrity_check failed: {result}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    present_tables: set[str] = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }

    total = 0
    for table in HARVEST_TABLES:
        if table not in present_tables:
            print(f"SKIP  {table} — not found in legacy DB")
            continue
        rows = _rows_as_dicts(conn, table)
        out_path = out_dir / f"{table}.jsonl"
        with out_path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, default=str) + "\n")
        print(f"OK    {table}: {len(rows)} rows -> {out_path}")
        total += len(rows)

    conn.close()
    print(f"\nHarvest complete — {total} rows across {len(HARVEST_TABLES)} tables.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "db_path",
        nargs="?",
        default="draftcheck.db",
        help="Path to legacy draftcheck.db (default: ./draftcheck.db)",
    )
    parser.add_argument(
        "--out-dir",
        default="evals/seeds",
        help="Output directory for JSONL seed files (default: evals/seeds)",
    )
    args = parser.parse_args()
    harvest(Path(args.db_path).resolve(), Path(args.out_dir))


if __name__ == "__main__":
    main()
