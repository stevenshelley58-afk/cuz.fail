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
import re
import shutil
import sys
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
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


def _fetch_status_ok(url: str, *, timeout_seconds: float) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=timeout_seconds) as response:  # noqa: S310 - operator-supplied monitor URL
            status_code = response.status
            raw = response.read(1_000_000).decode("utf-8", errors="replace")
    except HTTPError as exc:
        return {
            "url": url,
            "ok": False,
            "http_status": exc.code,
            "error": str(exc),
        }
    except (OSError, URLError) as exc:
        return {
            "url": url,
            "ok": False,
            "error": str(exc),
        }

    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "url": url,
            "ok": False,
            "http_status": status_code,
            "error": f"response was not JSON: {exc}",
            "body_preview": raw[:200],
        }

    service_status = body.get("status")
    return {
        "url": url,
        "ok": status_code == 200 and service_status == "ok",
        "http_status": status_code,
        "service_status": service_status,
    }


def check_uptime_targets(
    targets: dict[str, str],
    *,
    timeout_seconds: float = 10.0,
) -> GuardrailResult:
    """Verify launch uptime monitor targets match the expected status contract."""

    checks = {
        name: _fetch_status_ok(url, timeout_seconds=timeout_seconds)
        for name, url in targets.items()
    }
    failures = [name for name, check in checks.items() if not check["ok"]]
    metadata = {"targets": checks, "timeout_seconds": timeout_seconds}
    if not failures:
        return GuardrailResult(
            name="uptime_targets",
            status="ok",
            message="all uptime targets returned status ok",
            metadata=metadata,
        )
    return GuardrailResult(
        name="uptime_targets",
        status="critical",
        message="uptime targets failed: " + ", ".join(failures),
        metadata=metadata,
    )


def check_disk_usage(
    paths: list[Path],
    *,
    max_used_percent: float = 80.0,
    usage_provider: Any = shutil.disk_usage,
) -> GuardrailResult:
    """Verify configured disk paths are below the used-space threshold."""

    checked: list[dict[str, Any]] = []
    skipped: list[str] = []
    breaches: list[str] = []
    invalid: list[str] = []

    for path in paths:
        if not path.exists():
            skipped.append(str(path))
            continue
        usage = usage_provider(path)
        total = int(usage.total)
        used = int(usage.used)
        free = int(usage.free)
        if total <= 0:
            invalid.append(str(path))
            continue
        used_percent = round((used / total) * 100, 2)
        item = {
            "path": str(path),
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "used_percent": used_percent,
            "max_used_percent": max_used_percent,
        }
        checked.append(item)
        if used_percent > max_used_percent:
            breaches.append(f"{path}: {used_percent}% used")

    metadata = {
        "checked": checked,
        "skipped_missing_paths": skipped,
        "invalid_paths": invalid,
        "max_used_percent": max_used_percent,
    }
    if breaches or invalid:
        return GuardrailResult(
            name="disk_usage",
            status="critical",
            message="disk usage guardrail failed: " + ", ".join([*breaches, *invalid]),
            metadata=metadata,
        )
    if not checked:
        return GuardrailResult(
            name="disk_usage",
            status="warning",
            message="no configured disk paths existed",
            metadata=metadata,
        )
    return GuardrailResult(
        name="disk_usage",
        status="ok",
        message="disk usage is below threshold",
        metadata=metadata,
    )


PLACEHOLDER_PATTERNS = (
    r"YYYY-MM-DD",
    r"PASS / FAIL",
    r"\(paste ",
    r"\(short ID",
    r"notes: \(any anomalies",
)


def _first_int(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        return None
    return int(match.group(1))


def check_restore_drill_log(path: Path) -> GuardrailResult:
    """Verify a committed restore-drill log contains accepted evidence."""

    if not path.exists():
        return GuardrailResult(
            name="restore_drill_log",
            status="critical",
            message=f"restore drill log missing: {path}",
            metadata={"path": str(path)},
        )

    text = path.read_text(encoding="utf-8")
    failures: list[str] = []
    placeholders = [pattern for pattern in PLACEHOLDER_PATTERNS if re.search(pattern, text)]
    if placeholders:
        failures.append("placeholder text remains")

    if not re.search(r"^status:\s*PASS\s*$", text, flags=re.MULTILINE):
        failures.append("status must be PASS")
    if len(re.findall(r"^result:\s*PASS\s*$", text, flags=re.MULTILINE)) < 2:
        failures.append("restic and DB restore results must be PASS")

    snapshot = re.search(r"^snapshot_id:\s*(\S+)\s*$", text, flags=re.MULTILINE)
    if not snapshot or snapshot.group(1).startswith("("):
        failures.append("snapshot_id is required")

    dump_size = _first_int(r"^dump_size_bytes:\s*(\d+)\s*$", text)
    if dump_size is None or dump_size <= 0:
        failures.append("dump_size_bytes must be greater than zero")

    source_versions = _first_int(r"^source_versions:\s*(\d+)\s*$", text)
    if source_versions is None or source_versions <= 0:
        failures.append("source_versions sanity count must be greater than zero")

    job_traces = _first_int(r"^job_traces:\s*(\d+)\s*$", text)
    if job_traces is None or job_traces <= 0:
        failures.append("job_traces sanity count must be greater than zero")

    metadata = {
        "path": str(path),
        "placeholder_patterns": placeholders,
        "dump_size_bytes": dump_size,
        "source_versions": source_versions,
        "job_traces": job_traces,
    }
    if failures:
        return GuardrailResult(
            name="restore_drill_log",
            status="critical",
            message="; ".join(failures),
            metadata=metadata,
        )
    return GuardrailResult(
        name="restore_drill_log",
        status="ok",
        message="restore drill log has accepted PASS evidence",
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

    uptime_parser = subparsers.add_parser("uptime-targets")
    uptime_parser.add_argument("--health-url", default="https://lotfile.app/api/v1/health")
    uptime_parser.add_argument("--ready-url", default="https://lotfile.app/api/v1/ready")
    uptime_parser.add_argument("--timeout-seconds", type=float, default=10.0)
    uptime_parser.add_argument("--json", action="store_true")

    disk_parser = subparsers.add_parser("disk-usage")
    disk_parser.add_argument("--path", action="append", default=[])
    disk_parser.add_argument("--max-used-percent", type=float, default=80.0)
    disk_parser.add_argument("--json", action="store_true")

    restore_parser = subparsers.add_parser("restore-drill-log")
    restore_parser.add_argument("--path", required=True)
    restore_parser.add_argument("--json", action="store_true")

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

    if args.command == "uptime-targets":
        result = check_uptime_targets(
            {
                "health": args.health_url,
                "ready": args.ready_url,
            },
            timeout_seconds=args.timeout_seconds,
        )
        _print_result(result, as_json=args.json)
        return status_exit_code(result.status)

    if args.command == "restore-drill-log":
        result = check_restore_drill_log(Path(args.path))
        _print_result(result, as_json=args.json)
        return status_exit_code(result.status)

    if args.command == "disk-usage":
        paths = [Path(value) for value in (args.path or ["/srv", "/var/lib/docker"])]
        result = check_disk_usage(paths, max_used_percent=args.max_used_percent)
        _print_result(result, as_json=args.json)
        return status_exit_code(result.status)

    before = _read_snapshot(args.before)
    after = _read_snapshot(args.after)
    result = compare_spend_snapshots(before, after)
    _print_result(result, as_json=args.json)
    return status_exit_code(result.status)


if __name__ == "__main__":
    raise SystemExit(main())
