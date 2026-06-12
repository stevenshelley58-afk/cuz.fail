from __future__ import annotations

from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
from types import SimpleNamespace
import threading

from scripts.ops_guardrails import (
    check_backup_freshness,
    check_disk_usage,
    check_restore_drill_log,
    check_uptime_targets,
    check_worker_heartbeat,
    compare_spend_snapshots,
    normalise_database_url,
)


def test_backup_freshness_accepts_recent_postgres_dump(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups" / "20260612T020000Z"
    backup_dir.mkdir(parents=True)
    dump = backup_dir / "postgres.dump"
    dump.write_bytes(b"fixture")
    now = datetime(2026, 6, 12, 12, 0, tzinfo=UTC)
    mtime = (now - timedelta(hours=2)).timestamp()
    os.utime(dump, (mtime, mtime))

    result = check_backup_freshness(tmp_path / "backups", now=now)

    assert result.status == "ok"
    assert result.metadata["latest_dump"] == str(dump)
    assert result.metadata["latest_dump_size_bytes"] == 7


def test_backup_freshness_flags_stale_or_missing_dump(tmp_path: Path) -> None:
    now = datetime(2026, 6, 12, 12, 0, tzinfo=UTC)
    missing = check_backup_freshness(tmp_path / "missing", now=now)
    assert missing.status == "critical"

    backup_dir = tmp_path / "backups" / "20260610T020000Z"
    backup_dir.mkdir(parents=True)
    dump = backup_dir / "postgres.dump"
    dump.write_bytes(b"fixture")
    mtime = (now - timedelta(hours=30)).timestamp()
    os.utime(dump, (mtime, mtime))

    stale = check_backup_freshness(tmp_path / "backups", now=now)

    assert stale.status == "critical"
    assert "stale" in stale.message


def test_compare_spend_snapshots_requires_non_decreasing_counters() -> None:
    before = {
        "job_traces": {"rows": 3, "total_tokens": 100, "cost_cents": 20},
        "spend_events": {"rows": 2, "total_tokens": 100, "cost_cents": 20},
    }
    after = {
        "job_traces": {"rows": 3, "total_tokens": 100, "cost_cents": 20},
        "spend_events": {"rows": 3, "total_tokens": 140, "cost_cents": 25},
    }

    assert compare_spend_snapshots(before, after).status == "ok"

    decreased = {
        "job_traces": {"rows": 2, "total_tokens": 90, "cost_cents": 20},
        "spend_events": {"rows": 2, "total_tokens": 100, "cost_cents": 20},
    }
    result = compare_spend_snapshots(before, decreased)

    assert result.status == "critical"
    assert "job_traces.rows" in result.metadata["decreases"][0]


def test_compare_spend_snapshots_warns_without_pre_restart_evidence() -> None:
    empty = {
        "job_traces": {"rows": 0, "total_tokens": 0, "cost_cents": 0},
        "spend_events": {"rows": 0, "total_tokens": 0, "cost_cents": 0},
    }

    result = compare_spend_snapshots(empty, empty)

    assert result.status == "warning"


def test_database_url_normalisation_accepts_sqlalchemy_driver_urls() -> None:
    assert (
        normalise_database_url("postgresql+psycopg://user:pw@db:5432/app")
        == "postgresql://user:pw@db:5432/app"
    )


def test_disk_usage_accepts_paths_below_threshold(tmp_path: Path) -> None:
    def usage_provider(_path: Path) -> SimpleNamespace:
        return SimpleNamespace(total=100, used=70, free=30)

    result = check_disk_usage(
        [tmp_path],
        max_used_percent=80,
        usage_provider=usage_provider,
    )

    assert result.status == "ok"
    assert result.metadata["checked"][0]["used_percent"] == 70


def test_disk_usage_flags_threshold_breach(tmp_path: Path) -> None:
    def usage_provider(_path: Path) -> SimpleNamespace:
        return SimpleNamespace(total=100, used=81, free=19)

    result = check_disk_usage(
        [tmp_path],
        max_used_percent=80,
        usage_provider=usage_provider,
    )

    assert result.status == "critical"
    assert str(tmp_path) in result.message
    assert result.metadata["checked"][0]["used_percent"] == 81


def test_disk_usage_warns_when_no_paths_exist(tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    result = check_disk_usage([missing], max_used_percent=80)

    assert result.status == "warning"
    assert result.metadata["skipped_missing_paths"] == [str(missing)]


def test_worker_heartbeat_accepts_required_running_services(tmp_path: Path) -> None:
    result = check_worker_heartbeat(
        ["worker", "hermes"],
        {"api", "worker", "hermes"},
        compose_dir=tmp_path,
    )

    assert result.status == "ok"
    assert result.metadata["missing_services"] == []
    assert result.metadata["compose_dir"] == str(tmp_path)


def test_worker_heartbeat_flags_missing_required_services(tmp_path: Path) -> None:
    result = check_worker_heartbeat(
        ["worker", "hermes"],
        {"api", "worker"},
        compose_dir=tmp_path,
    )

    assert result.status == "critical"
    assert result.metadata["missing_services"] == ["hermes"]
    assert "hermes" in result.message


def test_uptime_targets_require_json_status_ok() -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
            if self.path == "/health":
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
                return
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"degraded"}')

        def log_message(self, format: str, *args: object) -> None:
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"

        ok = check_uptime_targets(
            {
                "health": f"{base_url}/health",
            },
            timeout_seconds=1,
        )
        failed = check_uptime_targets(
            {
                "health": f"{base_url}/health",
                "ready": f"{base_url}/ready",
            },
            timeout_seconds=1,
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert ok.status == "ok"
    assert failed.status == "critical"
    assert failed.metadata["targets"]["ready"]["service_status"] == "degraded"


def test_restore_drill_log_requires_pass_evidence(tmp_path: Path) -> None:
    log = tmp_path / "restore-drill-20260612.md"
    log.write_text(
        """# LotFile V3 Restore Drill

date: 2026-06-12T08:00:00Z

## restic check

result: PASS
output: |
  no errors were found

## Restore latest snapshot

snapshot_id: abc123ef

## Dump

dump_path: /tmp/draftcheck-v3-restore/srv/draftcheck/backups/20260612T020000Z/postgres.dump
dump_size_bytes: 123456

## DB restore

result: PASS

## Sanity counts

source_versions: 286
job_traces: 4

## Result

status: PASS
notes: none
""",
        encoding="utf-8",
    )
    placeholder = tmp_path / "restore-drill-placeholder.md"
    placeholder.write_text(
        """# LotFile V3 Restore Drill
date: YYYY-MM-DDTHH:MM:SSZ
result: PASS / FAIL
snapshot_id: (short ID from `restic snapshots --last`)
dump_size_bytes: 0
source_versions: 0
job_traces: 0
status: PASS / FAIL
""",
        encoding="utf-8",
    )

    assert check_restore_drill_log(log).status == "ok"
    failed = check_restore_drill_log(placeholder)

    assert failed.status == "critical"
    assert "placeholder text remains" in failed.message
    assert "dump_size_bytes" in failed.message
