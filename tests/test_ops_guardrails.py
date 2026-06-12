from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from pathlib import Path

from scripts.ops_guardrails import (
    check_backup_freshness,
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
