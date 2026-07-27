"""Revalidate bulk-approved rules and quarantine approvals that fail evidence gates.

The command is dry-run by default. It never deletes rules. With ``--apply``,
failing approvals move to ``pending_review`` and receive an immutable audit
event so the original load remains traceable.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

from draftcheck.extraction.validators import run_all_validators  # noqa: E402


def _database_url() -> str:
    return (
        os.environ["DATABASE_URL"]
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
    )


def _validate(row: dict[str, Any]) -> dict[str, dict[str, object]]:
    return run_all_validators(
        quote=str(row["quote"] or ""),
        clause_text=str(row["clause_text"] or ""),
        disposition=str(row["disposition"] or ""),
        value_json=row["value_json"] or {},
        unit=row["unit"],
        rule_key=str(row["rule_key"] or ""),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Revalidate bulk approvals and quarantine invalid rules."
    )
    parser.add_argument(
        "--since",
        required=True,
        help="Only inspect bulk-approved rules approved at or after this ISO timestamp.",
    )
    parser.add_argument(
        "--batch",
        action="append",
        required=True,
        help="Exact approval_metadata_json batch name to inspect; repeat for multiple batches.",
    )
    parser.add_argument(
        "--actor-user-id",
        help="User performing the quarantine. Omit for an explicit system/script actor.",
    )
    parser.add_argument("--apply", action="store_true", help="Apply quarantine changes.")
    args = parser.parse_args()

    failure_counts: Counter[str] = Counter()
    invalid_rows: list[dict[str, object]] = []
    valid_count = 0

    with psycopg.connect(_database_url(), row_factory=dict_row) as conn:
        rows = conn.execute(
            """
            SELECT r.id, r.org_id, r.approved_by_user_id, r.candidate_id,
                   r.rule_key, r.quote, r.value_json, r.unit,
                   r.lifecycle_status, r.approval_metadata_json,
                   c.text AS clause_text, c.disposition
            FROM rules r
            JOIN clauses c ON c.id = r.clause_id
            WHERE r.lifecycle_status = 'approved'
              AND r.approval_metadata_json->>'batch' = ANY(%s)
              AND r.approved_at >= %s::timestamptz
            ORDER BY r.created_at, r.id
            """,
            (args.batch, args.since),
        ).fetchall()

        for row in rows:
            results = _validate(row)
            failed = [name for name, result in results.items() if not result.get("pass")]
            if not failed:
                valid_count += 1
                continue

            failure_counts.update(failed)
            invalid_rows.append(
                {
                    "rule_id": str(row["id"]),
                    "rule_key": row["rule_key"],
                    "failed_validators": failed,
                }
            )
            if not args.apply:
                continue

            revalidation = {
                "at": datetime.now(UTC).isoformat(),
                "result": "quarantined",
                "failed_validators": failed,
                "validator_results": results,
                "script": "revalidate_bulk_approved_rules.py",
                "actor": (
                    f"user:{args.actor_user_id}"
                    if args.actor_user_id
                    else "system:revalidate_bulk_approved_rules"
                ),
            }
            conn.execute(
                """
                UPDATE rules
                SET lifecycle_status = 'pending_review',
                    approval_metadata_json =
                        approval_metadata_json || %s::jsonb,
                    updated_at = now()
                WHERE id = %s AND lifecycle_status = 'approved'
                """,
                (json.dumps({"revalidation": revalidation}), row["id"]),
            )
            if row["candidate_id"]:
                conn.execute(
                    """
                    UPDATE rule_candidates
                    SET review_status = 'pending_review',
                        metadata_json = metadata_json || %s::jsonb,
                        validator_results_json = %s::json,
                        updated_at = now()
                    WHERE id = %s
                    """,
                    (
                        json.dumps({"revalidation": revalidation}),
                        json.dumps(results),
                        row["candidate_id"],
                    ),
                )
            conn.execute(
                """
                INSERT INTO audit_events
                    (id, org_id, actor_user_id, event_type, action, subject_type,
                     subject_id, before_json, after_json, metadata_json, created_at)
                VALUES
                    (%s, %s, %s, 'rule_revalidation', 'quarantine', 'rule',
                     %s, %s, %s, %s, now())
                """,
                (
                    str(uuid4()),
                    row["org_id"],
                    args.actor_user_id,
                    row["id"],
                    json.dumps({"lifecycle_status": "approved"}),
                    json.dumps({"lifecycle_status": "pending_review"}),
                    json.dumps(revalidation),
                ),
            )

        if args.apply:
            conn.commit()
        else:
            conn.rollback()

    report = {
        "mode": "apply" if args.apply else "dry_run",
        "since": args.since,
        "batches": sorted(set(args.batch)),
        "inspected": valid_count + len(invalid_rows),
        "valid": valid_count,
        "quarantined": len(invalid_rows) if args.apply else 0,
        "would_quarantine": len(invalid_rows),
        "failure_counts": dict(sorted(failure_counts.items())),
        "sample": invalid_rows[:20],
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
