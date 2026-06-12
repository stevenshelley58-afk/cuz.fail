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
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
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


REQUIRED_UPTIME_MONITORS = {
    "LotFile health": "https://lotfile.app/api/v1/health",
    "LotFile ready": "https://lotfile.app/api/v1/ready",
}
REQUIRED_UPTIME_DOC_NEEDLES = {
    "monitor_type_https": "Type: HTTPS",
    "monitor_interval_5_minutes": "Monitoring Interval: 5 minutes",
    "status_ok_keyword": 'Keyword: `"status":"ok"`',
    "keyword_missing_alert": "Alert if keyword not found",
    "down_alert_threshold": "after 2 consecutive failures",
    "recovery_alert_threshold": "on first success after a down event",
}


def _read_markdown_table_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells or all(set(cell) <= {"-"} for cell in cells):
            continue
        rows.append(cells)
    return rows


def check_uptime_monitor_doc(path: Path) -> GuardrailResult:
    """Verify the uptime monitor runbook records provisioned external monitors."""

    if not path.exists():
        return GuardrailResult(
            name="uptime_monitor_doc",
            status="critical",
            message=f"uptime monitor doc missing: {path}",
            metadata={"path": str(path)},
        )

    text = path.read_text(encoding="utf-8")
    failures: list[str] = []
    for monitor_name, target_url in REQUIRED_UPTIME_MONITORS.items():
        if target_url not in text:
            failures.append(f"{monitor_name} target URL missing")
    missing_contract = [
        name for name, needle in REQUIRED_UPTIME_DOC_NEEDLES.items() if needle not in text
    ]
    for name in missing_contract:
        failures.append(f"uptime monitor contract missing: {name}")

    rows = _read_markdown_table_rows(text)
    monitor_rows = {
        cells[0]: cells
        for cells in rows
        if len(cells) >= 3 and cells[0] in REQUIRED_UPTIME_MONITORS
    }
    pending_values: list[str] = []
    recorded_monitors: dict[str, dict[str, str]] = {}
    for monitor_name in REQUIRED_UPTIME_MONITORS:
        cells = monitor_rows.get(monitor_name)
        if cells is None:
            failures.append(f"{monitor_name} monitor ID row missing")
            continue
        provider_id = cells[1]
        alert_contact = cells[2]
        if not provider_id or provider_id.lower() == "pending":
            pending_values.append(f"{monitor_name}.provider_id")
        if not alert_contact or alert_contact.lower() == "pending":
            pending_values.append(f"{monitor_name}.alert_contact")
        recorded_monitors[monitor_name] = {
            "provider_id": provider_id,
            "alert_contact": alert_contact,
        }

    metadata = {
        "path": str(path),
        "required_monitors": REQUIRED_UPTIME_MONITORS,
        "required_contract": REQUIRED_UPTIME_DOC_NEEDLES,
        "missing_contract": missing_contract,
        "recorded_monitors": recorded_monitors,
        "pending_values": pending_values,
        "failures": failures,
    }
    if failures or pending_values:
        message_parts = [*failures]
        if pending_values:
            message_parts.append("pending monitor evidence: " + ", ".join(pending_values))
        return GuardrailResult(
            name="uptime_monitor_doc",
            status="critical",
            message="; ".join(message_parts),
            metadata=metadata,
        )

    return GuardrailResult(
        name="uptime_monitor_doc",
        status="ok",
        message="uptime monitor doc records provisioned monitor IDs and alert contacts",
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


def check_worker_heartbeat(
    required_services: list[str],
    running_services: set[str],
    *,
    compose_dir: Path | None = None,
) -> GuardrailResult:
    """Verify required compose worker services are reported running."""

    missing = [service for service in required_services if service not in running_services]
    metadata = {
        "required_services": required_services,
        "running_services": sorted(running_services),
        "missing_services": missing,
        "compose_dir": str(compose_dir) if compose_dir is not None else None,
    }
    if missing:
        return GuardrailResult(
            name="worker_heartbeat",
            status="critical",
            message="required compose services are not running: " + ", ".join(missing),
            metadata=metadata,
        )
    return GuardrailResult(
        name="worker_heartbeat",
        status="ok",
        message="required compose worker services are running",
        metadata=metadata,
    )


def docker_compose_running_services(compose_dir: Path) -> set[str]:
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--status", "running", "--services"],
            cwd=compose_dir,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"failed to list running compose services in {compose_dir}: {exc}") from exc
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip().lstrip("\ufeff")] = value.strip().strip("\"'")
    return values


def check_sentry_config(env_path: Path, *, compose_path: Path | None = None) -> GuardrailResult:
    """Verify error reporting is configured without printing the DSN secret."""

    if not env_path.exists():
        return GuardrailResult(
            name="sentry_config",
            status="critical",
            message=f"Sentry env file missing: {env_path}",
            metadata={"env_path": str(env_path), "compose_path": str(compose_path) if compose_path else None},
        )

    values = read_env_file(env_path)
    dsn = values.get("SENTRY_DSN", "").strip()
    parsed = urlparse(dsn)
    failures: list[str] = []
    if not dsn:
        failures.append("SENTRY_DSN is missing or empty")
    elif parsed.scheme != "https" or not parsed.netloc or "@" not in parsed.netloc or parsed.path in ("", "/"):
        failures.append("SENTRY_DSN must be an HTTPS DSN with public key, host, and project ID")

    compose_mentions_sentry: bool | None = None
    if compose_path is not None:
        if not compose_path.exists():
            failures.append(f"compose file missing: {compose_path}")
            compose_mentions_sentry = False
        else:
            compose_text = compose_path.read_text(encoding="utf-8")
            compose_mentions_sentry = "SENTRY_DSN" in compose_text
            if not compose_mentions_sentry:
                failures.append("compose file does not wire SENTRY_DSN")

    sentry_host = None
    if parsed.netloc and "@" in parsed.netloc:
        sentry_host = parsed.netloc.split("@", 1)[1]

    metadata = {
        "env_path": str(env_path),
        "compose_path": str(compose_path) if compose_path else None,
        "present_keys": sorted(values),
        "dsn_present": bool(dsn),
        "dsn_scheme": parsed.scheme if dsn else None,
        "sentry_host": sentry_host,
        "project_id_present": bool(parsed.path and parsed.path != "/"),
        "compose_mentions_sentry": compose_mentions_sentry,
        "failures": failures,
    }
    if failures:
        return GuardrailResult(
            name="sentry_config",
            status="critical",
            message="Sentry config is incomplete: " + "; ".join(failures),
            metadata=metadata,
        )
    return GuardrailResult(
        name="sentry_config",
        status="ok",
        message="Sentry DSN is configured and compose wiring is present",
        metadata=metadata,
    )


REQUIRED_JOURNALD_RETENTION = {
    "SystemMaxUse": "1G",
    "SystemKeepFree": "2G",
    "MaxRetentionSec": "14day",
}
REQUIRED_DOCKER_LOG_ROTATION = {
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "50m",
        "max-file": "5",
    },
}
BACKUP_PLACEHOLDER_NEEDLES = (
    "example.invalid",
    "<",
    ">",
    "<generated",
    "<restic",
    "changeme",
    "placeholder",
)


def _read_simple_ini_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("[") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def check_log_retention_config(journald_path: Path, docker_daemon_path: Path) -> GuardrailResult:
    """Verify installed log-retention configs cap journald and Docker JSON logs."""

    failures: list[str] = []
    journald_values: dict[str, str] = {}
    docker_config: dict[str, Any] | None = None

    if not journald_path.exists():
        failures.append(f"journald config missing: {journald_path}")
    else:
        journald_text = journald_path.read_text(encoding="utf-8")
        if "[Journal]" not in journald_text:
            failures.append("journald config missing [Journal] section")
        journald_values = _read_simple_ini_values(journald_path)
        for key, expected in REQUIRED_JOURNALD_RETENTION.items():
            actual = journald_values.get(key)
            if actual != expected:
                failures.append(f"journald {key} must be {expected}, found {actual or 'missing'}")

    if not docker_daemon_path.exists():
        failures.append(f"Docker daemon config missing: {docker_daemon_path}")
    else:
        try:
            docker_config = json.loads(docker_daemon_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"Docker daemon config is not valid JSON: {exc}")
        else:
            if docker_config.get("log-driver") != REQUIRED_DOCKER_LOG_ROTATION["log-driver"]:
                failures.append("Docker log-driver must be json-file")
            log_opts = docker_config.get("log-opts")
            if not isinstance(log_opts, dict):
                failures.append("Docker log-opts must be an object")
                log_opts = {}
            for key, expected in REQUIRED_DOCKER_LOG_ROTATION["log-opts"].items():
                actual = log_opts.get(key)
                if actual != expected:
                    failures.append(f"Docker log-opts.{key} must be {expected}, found {actual or 'missing'}")

    metadata = {
        "journald_path": str(journald_path),
        "docker_daemon_path": str(docker_daemon_path),
        "journald_values": journald_values,
        "docker_config": docker_config,
        "failures": failures,
    }
    if failures:
        return GuardrailResult(
            name="log_retention_config",
            status="critical",
            message="log retention config is incomplete: " + "; ".join(failures),
            metadata=metadata,
        )
    return GuardrailResult(
        name="log_retention_config",
        status="ok",
        message="journald and Docker JSON log retention configs are installed",
        metadata=metadata,
    )


def check_backup_config(env_path: Path) -> GuardrailResult:
    """Verify the backup env file is ready before arming the systemd timer."""

    if not env_path.exists():
        return GuardrailResult(
            name="backup_config",
            status="critical",
            message=f"backup env file missing: {env_path}",
            metadata={"env_path": str(env_path)},
        )

    values = read_env_file(env_path)
    required_keys = ["RESTIC_REPOSITORY", "RESTIC_PASSWORD_FILE", "POSTGRES_USER", "POSTGRES_DB", "COMPOSE_FILE"]
    missing = [key for key in required_keys if not values.get(key)]
    password_file = Path(values.get("RESTIC_PASSWORD_FILE", ""))
    compose_file = Path(values.get("COMPOSE_FILE", ""))
    missing_paths: list[str] = []
    invalid_values: list[str] = []
    if password_file and not password_file.exists():
        missing_paths.append(f"RESTIC_PASSWORD_FILE={password_file}")
    if compose_file and not compose_file.exists():
        missing_paths.append(f"COMPOSE_FILE={compose_file}")
    restic_repository = values.get("RESTIC_REPOSITORY", "").lower()
    if any(needle in restic_repository for needle in BACKUP_PLACEHOLDER_NEEDLES):
        invalid_values.append("RESTIC_REPOSITORY appears to be a placeholder")

    metadata = {
        "env_path": str(env_path),
        "present_keys": sorted(values),
        "missing_keys": missing,
        "missing_paths": missing_paths,
        "invalid_values": invalid_values,
    }
    if missing or missing_paths or invalid_values:
        return GuardrailResult(
            name="backup_config",
            status="critical",
            message="backup config is incomplete: " + ", ".join([*missing, *missing_paths, *invalid_values]),
            metadata=metadata,
        )
    return GuardrailResult(
        name="backup_config",
        status="ok",
        message="backup config contains required restic and compose settings",
        metadata=metadata,
    )


def check_guardrail_cron(path: Path) -> GuardrailResult:
    """Verify the guardrail cron entry will run the checked alert wrapper."""

    if not path.exists():
        return GuardrailResult(
            name="guardrail_cron",
            status="critical",
            message=f"guardrail cron file missing: {path}",
            metadata={"path": str(path)},
        )

    text = path.read_text(encoding="utf-8")
    failures: list[str] = []
    if "guardrail-alerts.sh" not in text:
        failures.append("guardrail-alerts.sh command missing")
    if "/srv/draftcheck/app/infra/v3/ops/guardrail-alerts.sh" not in text:
        failures.append("expected production guardrail-alerts.sh path missing")
    if not re.search(r"^\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+root\s+", text, flags=re.MULTILINE):
        failures.append("root cron schedule entry missing")
    if "draftcheck-guardrails.log" not in text:
        failures.append("local guardrail log redirection missing")

    metadata = {"path": str(path), "failures": failures}
    if failures:
        return GuardrailResult(
            name="guardrail_cron",
            status="critical",
            message="guardrail cron is incomplete: " + "; ".join(failures),
            metadata=metadata,
        )
    return GuardrailResult(
        name="guardrail_cron",
        status="ok",
        message="guardrail cron entry is installed with the checked wrapper",
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
    if len(re.findall(r"^result:\s*PASS\s*$", text, flags=re.MULTILINE)) < 3:
        failures.append("restic, storage, and DB restore results must be PASS")

    snapshot = re.search(r"^snapshot_id:\s*(\S+)\s*$", text, flags=re.MULTILINE)
    if not snapshot or snapshot.group(1).startswith("("):
        failures.append("snapshot_id is required")

    dump_size = _first_int(r"^dump_size_bytes:\s*(\d+)\s*$", text)
    if dump_size is None or dump_size <= 0:
        failures.append("dump_size_bytes must be greater than zero")

    storage_path = re.search(r"^storage_path:\s*(\S+)\s*$", text, flags=re.MULTILINE)
    if not storage_path or storage_path.group(1).startswith("("):
        failures.append("storage_path is required")

    storage_file_count = _first_int(r"^storage_file_count:\s*(\d+)\s*$", text)
    if storage_file_count is None or storage_file_count <= 0:
        failures.append("storage_file_count must be greater than zero")

    storage_size = _first_int(r"^storage_size_bytes:\s*(\d+)\s*$", text)
    if storage_size is None or storage_size <= 0:
        failures.append("storage_size_bytes must be greater than zero")

    storage_manifest = re.search(
        r"^storage_manifest_sha256:\s*([a-fA-F0-9]{64})\s*$",
        text,
        flags=re.MULTILINE,
    )
    if not storage_manifest:
        failures.append("storage_manifest_sha256 must be a SHA-256 hex digest")

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
        "storage_path": storage_path.group(1) if storage_path else None,
        "storage_file_count": storage_file_count,
        "storage_size_bytes": storage_size,
        "storage_manifest_sha256": storage_manifest.group(1) if storage_manifest else None,
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

    uptime_doc_parser = subparsers.add_parser("uptime-monitor-doc")
    uptime_doc_parser.add_argument("--path", default="docs/ops/uptime-monitor.md")
    uptime_doc_parser.add_argument("--json", action="store_true")

    disk_parser = subparsers.add_parser("disk-usage")
    disk_parser.add_argument("--path", action="append", default=[])
    disk_parser.add_argument("--max-used-percent", type=float, default=80.0)
    disk_parser.add_argument("--json", action="store_true")

    heartbeat_parser = subparsers.add_parser("worker-heartbeat")
    heartbeat_parser.add_argument("--compose-dir", default="/srv/draftcheck/app/infra/v3")
    heartbeat_parser.add_argument("--service", action="append", default=[])
    heartbeat_parser.add_argument("--running-service", action="append", default=[])
    heartbeat_parser.add_argument("--json", action="store_true")

    backup_config_parser = subparsers.add_parser("backup-config")
    backup_config_parser.add_argument("--env-path", default="/etc/draftcheck/backup.env")
    backup_config_parser.add_argument("--json", action="store_true")

    guardrail_cron_parser = subparsers.add_parser("guardrail-cron")
    guardrail_cron_parser.add_argument("--path", default="/etc/cron.d/draftcheck-guardrails")
    guardrail_cron_parser.add_argument("--json", action="store_true")

    sentry_parser = subparsers.add_parser("sentry-config")
    sentry_parser.add_argument("--env-path", default="/srv/draftcheck/app/infra/v3/.env")
    sentry_parser.add_argument("--compose-path", default="/srv/draftcheck/app/infra/v3/compose.yml")
    sentry_parser.add_argument("--json", action="store_true")

    log_retention_parser = subparsers.add_parser("log-retention-config")
    log_retention_parser.add_argument("--journald-path", default="/etc/systemd/journald.conf.d/draftcheck.conf")
    log_retention_parser.add_argument("--docker-daemon-path", default="/etc/docker/daemon.json")
    log_retention_parser.add_argument("--json", action="store_true")

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

    if args.command == "uptime-monitor-doc":
        result = check_uptime_monitor_doc(Path(args.path))
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

    if args.command == "worker-heartbeat":
        required_services = args.service or ["worker", "hermes"]
        compose_dir = Path(args.compose_dir)
        try:
            running_services = (
                set(args.running_service)
                if args.running_service
                else docker_compose_running_services(compose_dir)
            )
        except RuntimeError as exc:
            result = GuardrailResult(
                name="worker_heartbeat",
                status="critical",
                message=str(exc),
                metadata={"compose_dir": str(compose_dir), "required_services": required_services},
            )
        else:
            result = check_worker_heartbeat(
                required_services,
                running_services,
                compose_dir=compose_dir,
            )
        _print_result(result, as_json=args.json)
        return status_exit_code(result.status)

    if args.command == "backup-config":
        result = check_backup_config(Path(args.env_path))
        _print_result(result, as_json=args.json)
        return status_exit_code(result.status)

    if args.command == "guardrail-cron":
        result = check_guardrail_cron(Path(args.path))
        _print_result(result, as_json=args.json)
        return status_exit_code(result.status)

    if args.command == "sentry-config":
        result = check_sentry_config(Path(args.env_path), compose_path=Path(args.compose_path))
        _print_result(result, as_json=args.json)
        return status_exit_code(result.status)

    if args.command == "log-retention-config":
        result = check_log_retention_config(
            Path(args.journald_path),
            Path(args.docker_daemon_path),
        )
        _print_result(result, as_json=args.json)
        return status_exit_code(result.status)

    before = _read_snapshot(args.before)
    after = _read_snapshot(args.after)
    result = compare_spend_snapshots(before, after)
    _print_result(result, as_json=args.json)
    return status_exit_code(result.status)


if __name__ == "__main__":
    raise SystemExit(main())
