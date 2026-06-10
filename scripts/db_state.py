"""Build reports/db_state.json: a snapshot of the local V3 source library.

Reads draftcheck-corpus.db (sqlite), counts source rows / version rows /
chunks / citations, and the breakdown by review_status + licence_status.
This is the answer to "is the DB actually built and queryable?"

Usage:  python scripts/db_state.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DB = REPO_ROOT / "draftcheck-corpus.db"
REPORTS = REPO_ROOT / "reports"
OUT = REPORTS / "db_state.json"


def main() -> None:
    if not DB.exists():
        print(f"no db at {DB}")
        return
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    out: dict = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "db_path": str(DB.relative_to(REPO_ROOT)),
        "tables": {},
    }
    # list tables
    rows = cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    tables = [r["name"] for r in rows]
    out["tables_present"] = tables
    for t in tables:
        if t.startswith("sqlite_") or t.startswith("alembic_"):
            continue
        n = cur.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
        out["tables"][t] = n
    # break down the source library specifically
    if "source_versions" in tables:
        out["source_versions_by_review"] = {
            r["review_status"]: r["n"]
            for r in cur.execute(
                "SELECT review_status, COUNT(*) AS n FROM source_versions GROUP BY review_status"
            ).fetchall()
        }
        out["source_versions_by_licence"] = {
            r["licence_status"]: r["n"]
            for r in cur.execute(
                "SELECT licence_status, COUNT(*) AS n FROM source_versions GROUP BY licence_status"
            ).fetchall()
        }
    if "sources" in tables:
        out["sources_total"] = cur.execute("SELECT COUNT(*) AS n FROM sources").fetchone()["n"]
        out["sources_by_jurisdiction"] = {
            r["jurisdiction"]: r["n"]
            for r in cur.execute(
                "SELECT jurisdiction, COUNT(*) AS n FROM sources GROUP BY jurisdiction"
            ).fetchall()
        }
        out["sources_by_type"] = {
            r["source_type"]: r["n"]
            for r in cur.execute(
                "SELECT source_type, COUNT(*) AS n FROM sources GROUP BY source_type"
            ).fetchall()
        }
    if "source_chunks" in tables:
        out["source_chunks_total"] = cur.execute("SELECT COUNT(*) AS n FROM source_chunks").fetchone()["n"]
    if "source_citations" in tables:
        out["source_citations_total"] = cur.execute("SELECT COUNT(*) AS n FROM source_citations").fetchone()["n"]
    # citable = approved + verified_open
    out["citable_count"] = (
        out.get("source_versions_by_review", {}).get("approved", 0)
    )
    out["queryable"] = out["citable_count"] > 0
    conn.close()
    REPORTS.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    print(f"wrote: {OUT}")


if __name__ == "__main__":
    main()
