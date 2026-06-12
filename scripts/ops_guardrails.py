"""Operator checks for non-security go-live guardrails.

The commands here are intentionally small and idempotent. They verify evidence
that already exists on the VPS: backup freshness and persisted daily LLM spend.
No third-party credentials are created or stored by this script.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
import json
import os
from pathlib import Path
import sys
from typing import Any


Status = str


@dataclass(frozen=True)
class GuardrailResult:
    name: str
    status: Status
    message: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "metadata": self.metadata,
        }


def status_exit_code(status: Status) -> int:
    if status == "ok":
        return 0
    if status == "warning":
        return 1
    return 2


def normalise_database_url(database_url: str) -> str:
    return (
        database_url.replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
    )


def backup_dump_candidates(backup_root: Path) -> list[Path]:
    if not backup_root.exists():
        return []
    candidates: dict[Path, None] = {}
    for pattern in ("postgres.dump", "*.dump"):
        for path in backup_root.rglob(pattern):
            if path.is_file():
                candidates[path] = None
    return list(candidates)


def check_backup_freshness(
    backup_root: Path,
    *,
    now: datetime | None = None,
    max_age: timedelta = timedelta(hours=26),
) -> GuardrailResult:
    now = now or datetime.now(tz=UTC)
    candidates = backup_dump_candidates(backup_root)
    if not candidates:
        return GuardrailResult(
            name="backup_freshness",
            status="critical",
            message=f"no postgres dump found under {backup_root}",
            metadata={"backup_root": str(backup_root), "max_age_seconds": max_age.total_seconds()},
        )

    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    latest_mtime = datetime.fromtimestamp(latest.stat().st_mtime, tz=UTC)
    age = now - latest_mtime
    metadata = {
        "backup_root": str(backup_root),
        "latest_dump": str(latest),
        "latest_dump_mtime": latest_mtime.isoformat(),
        "latest_dump_size_bytes": latest.stat().st_size,
        "age_seconds": int(age.total_seconds()),
        "max_age_seconds": int(max_age.total_seconds()),
    }
    if age <= max_age:
        return GuardrailResult(
            name="backup_freshness",
            status="ok",
            message=f"latest postgres dump is {age} old",
            metadata=metadata,
        )
    return GuardrailResult(
        name="backup_freshness",
        status="critical",
        message=f"latest postgres dump is stale ({age} old)",
        metadata=metadata,
    )


def utc_day_start(day: date | None = None) -> datetime:
    day = day or datetime.now(tz=UTC).date()
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def spend_snapshot(database_url: str, *, day: date | None = None) -> dict[str, Any]:
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - exercised on VPS image, not unit tests
        raise RuntimeError("psycopg is required for spend snapshot checks") from exc

    start = utc_day_start(day)
    dsn = normalise_database_url(database_url)
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  COUNT(*),
                  COALESCE(SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)), 0),
                  COALESCE(ROUND(SUM(COALESCE(cost_usd, 0)) * 100), 0)
                FROM job_traces
                WHERE started_at >= %s
                """,
                (start,),
            )
            job_trace_rows = cur.fetchone() or (0, 0, 0)
            cur.execute(
                """
                SELECT
                  COUNT(*),
                  COALESCE(SUM(COALESCE(total_tokens, 0)), 0),
                  COALESCE(ROUND(SUM(COALESCE(cost_usd, 0)) * 100), 0)
                FROM spend_events
                WHERE created_at >= %s
                """,
                (start,),
            )
            spend_event_rows = cur.fetchone() or (0, 0, 0)

    return {
        "utc_day_start": start.isoformat(),
        "captured_at": datetime.now(tz=UTC).isoformat(),
        "job_traces": {
            "rows": int(job_trace_rows[0]),
            "total_tokens": int(job_trace_rows[1]),
            "cost_cents": int(job_trace_rows[2]),
        },
        "spend_events": {
            "rows": int(spend_event_rows[0]),
            "total_tokens": int(spend_event_rows[1]),
            "cost_cents": int(spend_event_rows[2]),
        },
    }


def compare_spend_snapshots(before: dict[str, Any], after: dict[str, Any]) -> GuardrailResult:
    decreases: list[str] = []
    evidence = False
    for table_name in ("job_traces", "spend_events"):
        before_table = before.get(table_name, {})
        after_table = after.get(table_name, {})
        for field in ("rows", "total_tokens", "cost_cents"):
            before_value = int(before_table.get(field, 0) or 0)
            after_value = int(after_table.get(field, 0) or 0)
            if before_value > 0:
                evidence = True
            if after_value < before_value:
                decreases.append(f"{table_name}.{field}: {before_value} -> {after_value}")

    metadata = {"before": before, "after": after, "decreases": decreases}
    if decreases:
        return GuardrailResult(
            name="spend_persistence",
            status="critical",
            message="daily spend counters decreased across restart",
            metadata=metadata,
        )
    if not evidence:
        return GuardrailResult(
            name="spend_persistence",
            status="warning",
            message="no pre-restart spend evidence found; run after at least one governed LLM call",
            metadata=metadata,
        )
    return GuardrailResult(
        name="spend_persistence",
        status="ok",
        message="daily spend counters persisted across restart",
        metadata=metadata,
    )


def _print_result(result: GuardrailResult, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result.to_dict(), sort_keys=True))
        return
    print(f"{result.status.upper()}: {result.name}: {result.message}")


def _read_snapshot(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup_parser = subparsers.add_parser("backup-freshness")
    backup_parser.add_argument("--backup-dir", default="/srv/draftcheck/backups")
    backup_parser.add_argument("--max-age-hours", type=float, default=26)
    backup_parser.add_argument("--json", action="store_true")

    snapshot_parser = subparsers.add_parser("spend-snapshot")
    snapshot_parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    snapshot_parser.add_argument("--json", action="store_true")

    compare_parser = subparsers.add_parser("compare-spend-snapshots")
    compare_parser.add_argument("--before", required=True)
    compare_parser.add_argument("--after", required=True)
    compare_parser.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "backup-freshness":
        result = check_backup_freshness(
            Path(args.backup_dir),
            max_age=timedelta(hours=args.max_age_hours),
        )
        _print_result(result, as_json=args.json)
        return status_exit_code(result.status)

    if args.command == "spend-snapshot":
        if not args.database_url:
            print("DATABASE_URL is required for spend snapshot checks", file=sys.stderr)
            return 2
        snapshot = spend_snapshot(args.database_url)
        if args.json:
            print(json.dumps(snapshot, sort_keys=True))
        else:
            print(
                "job_traces={rows}/{tokens} tokens/{cost} cents "
                "spend_events={spend_rows}/{spend_tokens} tokens/{spend_cost} cents".format(
                    rows=snapshot["job_traces"]["rows"],
                    tokens=snapshot["job_traces"]["total_tokens"],
                    cost=snapshot["job_traces"]["cost_cents"],
                    spend_rows=snapshot["spend_events"]["rows"],
                    spend_tokens=snapshot["spend_events"]["total_tokens"],
                    spend_cost=snapshot["spend_events"]["cost_cents"],
                )
            )
        return 0

    before = _read_snapshot(args.before)
    after = _read_snapshot(args.after)
    result = compare_spend_snapshots(before, after)
    _print_result(result, as_json=args.json)
    return status_exit_code(result.status)


if __name__ == "__main__":
    raise SystemExit(main())
