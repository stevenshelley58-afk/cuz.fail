"""WP6 rule coverage report.

Reports why rule-bearing clauses still have no approved/rejected rule row. This
is a read-only gate/report helper; extraction or decode workers consume the
source_version ids from its output.

Run inside the api container:
    python /app/scripts/wp6_coverage_report.py --report /app/reports/wp6_coverage.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

DEFAULT_REPORT = Path(__file__).resolve().parent.parent / "reports" / "wp6_coverage.json"


@dataclass(frozen=True)
class ClauseCoverage:
    clause_id: str
    source_version_id: str
    source_title: str
    clause_path: str | None
    rules_count: int
    candidates_count: int
    decode_candidates_count: int
    rejected_candidates_count: int


def classify_clause(row: ClauseCoverage) -> str:
    if row.rules_count > 0:
        return "covered"
    if row.decode_candidates_count > 0:
        return "decode_not_promoted"
    if row.candidates_count > 0:
        return "candidate_not_promoted"
    return "no_candidate"


def database_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql+psycopg://")


def load_clause_coverage(database_url_value: str) -> list[ClauseCoverage]:
    engine = create_engine(database_url_value)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT c.id::text AS clause_id,
                       c.source_version_id::text AS source_version_id,
                       sd.title AS source_title,
                       c.clause_path,
                       count(DISTINCT r.id) AS rules_count,
                       count(DISTINCT rc.id) AS candidates_count,
                       count(DISTINCT rc.id) FILTER (
                           WHERE rc.extractor_model LIKE 'openai%%decode'
                       ) AS decode_candidates_count,
                       count(DISTINCT rc.id) FILTER (
                           WHERE rc.review_status IN ('rejected', 'failed_validators')
                       ) AS rejected_candidates_count
                FROM clauses c
                JOIN source_versions sv ON sv.id = c.source_version_id
                JOIN source_documents sd ON sd.id = sv.source_id
                LEFT JOIN rules r ON r.clause_id = c.id
                LEFT JOIN rule_candidates rc ON rc.clause_id = c.id
                WHERE c.disposition = 'rule_bearing'
                GROUP BY c.id, c.source_version_id, sd.title, c.clause_path
                ORDER BY sd.title, c.clause_path NULLS LAST, c.id
                """
            )
        ).mappings()
        return [
            ClauseCoverage(
                clause_id=str(row["clause_id"]),
                source_version_id=str(row["source_version_id"]),
                source_title=str(row["source_title"]),
                clause_path=row["clause_path"],
                rules_count=int(row["rules_count"]),
                candidates_count=int(row["candidates_count"]),
                decode_candidates_count=int(row["decode_candidates_count"]),
                rejected_candidates_count=int(row["rejected_candidates_count"]),
            )
            for row in rows
        ]


def build_report(rows: list[ClauseCoverage], *, sample_limit: int) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    uncovered_by_source: dict[str, dict[str, Any]] = {}
    samples: list[dict[str, Any]] = []
    for row in rows:
        status = classify_clause(row)
        by_status[status] = by_status.get(status, 0) + 1
        if status == "covered":
            continue
        entry = uncovered_by_source.setdefault(
            row.source_version_id,
            {"source_version_id": row.source_version_id, "source_title": row.source_title, "uncovered": 0},
        )
        entry["uncovered"] += 1
        if len(samples) < sample_limit:
            samples.append({**row.__dict__, "coverage_status": status})

    source_shards = sorted(
        uncovered_by_source.values(),
        key=lambda item: (-int(item["uncovered"]), str(item["source_title"])),
    )
    return {
        "wp": "WP6",
        "total_rule_bearing_clauses": len(rows),
        "by_status": by_status,
        "uncovered_total": sum(count for status, count in by_status.items() if status != "covered"),
        "source_shards": source_shards,
        "samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--sample-limit", type=int, default=100)
    args = parser.parse_args()

    rows = load_clause_coverage(database_url())
    report = build_report(rows, sample_limit=args.sample_limit)
    output = json.dumps(report, indent=2, default=str)
    print(output)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
