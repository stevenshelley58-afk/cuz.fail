"""Check a SQLite database before harvest or archive."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


HARVEST_TABLES = (
    "source_documents",
    "source_versions",
    "source_licence_reviews",
    "clauses",
    "source_chunks",
    "source_citations",
    "rule_rows",
    "rule_extraction_candidates",
    "clause_dispositions",
    "review_queue_items",
    "golden_eval_cases",
    "golden_eval_runs",
    "audit_events",
)


def table_count(connection: sqlite3.Connection, table_name: str) -> int | None:
    exists = connection.execute(
        "select 1 from sqlite_master where type = 'table' and name = ?",
        (table_name,),
    ).fetchone()
    if not exists:
        return None
    return int(connection.execute(f"select count(*) from {table_name}").fetchone()[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", nargs="?", default="draftcheck.db")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    args = parser.parse_args()

    database = Path(args.database).resolve()
    uri = f"file:{database.as_posix()}?mode=ro"
    result: dict[str, object] = {"database": str(database), "exists": database.exists()}

    if not database.exists():
        result["status"] = "missing"
        result["integrity_check"] = None
    else:
        with sqlite3.connect(uri, uri=True) as connection:
            integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
            result["integrity_check"] = integrity
            result["status"] = "ok" if integrity.lower() == "ok" else "failed"
            result["table_counts"] = {
                table: count
                for table in HARVEST_TABLES
                if (count := table_count(connection, table)) is not None
            }

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"database: {result['database']}")
        print(f"exists: {result['exists']}")
        print(f"integrity_check: {result.get('integrity_check')}")
        print(f"status: {result['status']}")
        for table, count in (result.get("table_counts") or {}).items():
            print(f"{table}: {count}")

    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
