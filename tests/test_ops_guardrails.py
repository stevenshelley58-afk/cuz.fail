from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
import threading

import pytest

from scripts.ops_guardrails import (
    check_backup_config,
    check_backup_freshness,
    check_disk_usage,
    check_guardrail_cron,
    check_log_retention_config,
    check_restore_drill_log,
    check_sentry_config,
    check_uptime_targets,
    check_uptime_monitor_doc,
    check_worker_heartbeat,
    compare_spend_snapshots,
    normalise_database_url,
)


ROOT = Path(__file__).resolve().parents[1]
OPS_ALERT_PATH = ROOT / "infra" / "v3" / "ops" / "guardrail-alerts.sh"
OPS_CRON_INSTALL_PATH = ROOT / "infra" / "v3" / "ops" / "install-guardrail-cron.sh"
OPS_LOG_RETENTION_INSTALL_PATH = ROOT / "infra" / "v3" / "ops" / "install-log-retention.sh"
OPS_SENTRY_INSTALL_PATH = ROOT / "infra" / "v3" / "ops" / "install-sentry-dsn.sh"
BACKUP_INSTALL_PATH = ROOT / "infra" / "v3" / "backup" / "install-systemd.sh"
RESTORE_DRILL_PATH = ROOT / "infra" / "v3" / "backup" / "restore-drill.sh"


def _require_bash() -> str:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is unavailable")
    try:
        subprocess.run(
            [bash, "--version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        pytest.skip(f"bash is unavailable or unusable: {exc}")
    return bash


def _write_fake_ops_guardrails(app_dir: Path, *, failing: set[str] | None = None) -> Path:
    script = app_dir / "scripts" / "ops_guardrails.py"
    script.parent.mkdir(parents=True)
    script.write_text(
        f"""\
from __future__ import annotations

import json
import os
import sys

failing = {sorted(failing or set())!r}
command = sys.argv[1]
with open(os.environ["DRAFTCHECK_GUARDRAIL_CALLS"], "a", encoding="utf-8") as handle:
    handle.write(command + "\\n")
if command in failing:
    print(f"{{command}} critical fixture", file=sys.stderr)
    raise SystemExit(2)
print(json.dumps({{"name": command.replace("-", "_"), "status": "ok"}}))
""",
        encoding="utf-8",
    )
    return script


def _run_guardrail_alerts(tmp_path: Path, *, failing: set[str] | None = None, webhook: bool = False) -> subprocess.CompletedProcess[str]:
    bash = _require_bash()
    app_dir = tmp_path / "app"
    calls_path = tmp_path / "guardrail-calls.txt"
    _write_fake_ops_guardrails(app_dir, failing=failing)
    (tmp_path / "compose").mkdir()
    (tmp_path / "backups").mkdir()

    env = os.environ.copy()
    env.update(
        {
            "DRAFTCHECK_APP_DIR": str(app_dir),
            "DRAFTCHECK_COMPOSE_DIR": str(tmp_path / "compose"),
            "DRAFTCHECK_BACKUP_DIR": str(tmp_path / "backups"),
            "DRAFTCHECK_GUARDRAIL_CALLS": str(calls_path),
            "DRAFTCHECK_HEALTH_URL": "http://127.0.0.1:65535/health",
            "DRAFTCHECK_READY_URL": "http://127.0.0.1:65535/ready",
            "PYTHON_BIN": sys.executable,
        }
    )
    if webhook:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        curl = bin_dir / "curl"
        curl.write_text(
            """\
#!/usr/bin/env bash
set -euo pipefail
payload=""
while (($#)); do
    if [[ "$1" == "--data" ]]; then
        shift
        payload="$1"
    fi
    shift || true
done
printf '%s' "$payload" > "$DRAFTCHECK_FAKE_CURL_PAYLOAD"
""",
            encoding="utf-8",
        )
        curl.chmod(0o755)
        env["DRAFTCHECK_ALERT_WEBHOOK_URL"] = "https://alerts.example.invalid/draftcheck"
        env["DRAFTCHECK_FAKE_CURL_PAYLOAD"] = str(tmp_path / "curl-payload.json")
        env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]

    return subprocess.run(
        [bash, str(OPS_ALERT_PATH)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


def _write_fake_systemctl(bin_dir: Path) -> Path:
    systemctl = bin_dir / "systemctl"
    systemctl.write_text(
        """\
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$DRAFTCHECK_FAKE_SYSTEMCTL_LOG"
""",
        encoding="utf-8",
    )
    systemctl.chmod(0o755)
    return systemctl


def _write_backup_install_fixture(app_dir: Path) -> None:
    backup_dir = app_dir / "infra" / "v3" / "backup"
    backup_dir.mkdir(parents=True)
    (backup_dir / "draftcheck-backup.service").write_text(
        "[Unit]\nDescription=DraftCheck backup fixture\n",
        encoding="utf-8",
    )
    (backup_dir / "draftcheck-backup.timer").write_text(
        "[Timer]\nOnCalendar=daily\n",
        encoding="utf-8",
    )


def _run_backup_installer(tmp_path: Path, *, backup_env_exists: bool) -> subprocess.CompletedProcess[str]:
    bash = _require_bash()
    app_dir = tmp_path / "app"
    unit_dir = tmp_path / "systemd"
    bin_dir = tmp_path / "bin"
    backup_env = tmp_path / "backup.env"
    calls_path = tmp_path / "guardrail-calls.txt"
    systemctl_log = tmp_path / "systemctl.log"
    unit_dir.mkdir()
    bin_dir.mkdir()
    _write_backup_install_fixture(app_dir)
    _write_fake_ops_guardrails(app_dir)
    _write_fake_systemctl(bin_dir)

    if backup_env_exists:
        password_file = tmp_path / "restic-password"
        compose_file = tmp_path / "compose.yml"
        password_file.write_text("fixture-password\n", encoding="utf-8")
        compose_file.write_text("services: {}\n", encoding="utf-8")
        backup_env.write_text(
            f"""\
RESTIC_REPOSITORY=s3:s3.example.invalid/draftcheck-v3-backups
RESTIC_PASSWORD_FILE={password_file}
POSTGRES_USER=draftcheck
POSTGRES_DB=draftcheck
COMPOSE_FILE={compose_file}
""",
            encoding="utf-8",
        )

    env = os.environ.copy()
    env.update(
        {
            "DRAFTCHECK_APP_DIR": str(app_dir),
            "DRAFTCHECK_BACKUP_ENV": str(backup_env),
            "DRAFTCHECK_SYSTEMD_DIR": str(unit_dir),
            "DRAFTCHECK_GUARDRAIL_CALLS": str(calls_path),
            "DRAFTCHECK_FAKE_SYSTEMCTL_LOG": str(systemctl_log),
            "PYTHON_BIN": sys.executable,
            "PATH": str(bin_dir) + os.pathsep + env["PATH"],
        }
    )

    return subprocess.run(
        [bash, str(BACKUP_INSTALL_PATH)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


def _run_guardrail_cron_installer(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    bash = _require_bash()
    app_dir = tmp_path / "app"
    cron_path = tmp_path / "draftcheck-guardrails"
    calls_path = tmp_path / "guardrail-calls.txt"
    _write_fake_ops_guardrails(app_dir)

    env = os.environ.copy()
    env.update(
        {
            "DRAFTCHECK_APP_DIR": str(app_dir),
            "DRAFTCHECK_CRON_PATH": str(cron_path),
            "DRAFTCHECK_GUARDRAIL_CALLS": str(calls_path),
            "PYTHON_BIN": sys.executable,
        }
    )

    return subprocess.run(
        [bash, str(OPS_CRON_INSTALL_PATH)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


def _write_restore_drill_fakes(bin_dir: Path) -> None:
    restic = bin_dir / "restic"
    restic.write_text(
        """\
#!/usr/bin/env bash
set -euo pipefail
printf 'restic %s\n' "$*" >> "$DRAFTCHECK_RESTORE_DRILL_CALLS"
case "$1" in
    check)
        exit 0
        ;;
    snapshots)
        printf '[{"short_id":"abc123ef"}]\n'
        exit 0
        ;;
    restore)
        target=""
        while (($#)); do
            if [[ "$1" == "--target" ]]; then
                shift
                target="$1"
            fi
            shift || true
        done
        mkdir -p "$target/srv/draftcheck/backups/fixture" "$target/srv/draftcheck/storage/a"
        printf 'postgres fixture\n' > "$target/srv/draftcheck/backups/fixture/postgres.dump"
        printf 'storage fixture\n' > "$target/srv/draftcheck/storage/a/blob.txt"
        exit 0
        ;;
esac
echo "unexpected restic command: $*" >&2
exit 2
""",
        encoding="utf-8",
    )
    restic.chmod(0o755)

    docker = bin_dir / "docker"
    docker.write_text(
        """\
#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\n' "$*" >> "$DRAFTCHECK_RESTORE_DRILL_CALLS"
if [[ "$*" == *"SELECT count(*) FROM source_versions;"* ]]; then
    printf '286\n'
    exit 0
fi
if [[ "$*" == *"SELECT count(*) FROM job_traces;"* ]]; then
    printf '4\n'
    exit 0
fi
exit 0
""",
        encoding="utf-8",
    )
    docker.chmod(0o755)


def _write_fake_docker(bin_dir: Path) -> None:
    docker = bin_dir / "docker"
    docker.write_text(
        """\
#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\n' "$*" >> "$DRAFTCHECK_FAKE_DOCKER_LOG"
exit 0
""",
        encoding="utf-8",
    )
    docker.chmod(0o755)


def _run_restore_drill(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    bash = _require_bash()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_restore_drill_fakes(bin_dir)
    password_file = tmp_path / "restic-password"
    compose_file = tmp_path / "compose.yml"
    password_file.write_text("fixture-password\n", encoding="utf-8")
    compose_file.write_text("services: {}\n", encoding="utf-8")

    env = os.environ.copy()
    env.update(
        {
            "RESTIC_REPOSITORY": "s3:s3.example.invalid/draftcheck-v3-backups",
            "RESTIC_PASSWORD_FILE": str(password_file),
            "POSTGRES_USER": "draftcheck",
            "POSTGRES_DB": "draftcheck",
            "COMPOSE_FILE": str(compose_file),
            "DRAFTCHECK_RESTORE_DRILL_CALLS": str(tmp_path / "restore-drill-calls.txt"),
            "PATH": str(bin_dir) + os.pathsep + env["PATH"],
        }
    )
    return subprocess.run(
        [bash, str(RESTORE_DRILL_PATH)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _run_sentry_installer(
    tmp_path: Path,
    *,
    dsn: str | None = "https://public@example.ingest.sentry.io/123",
    restart_services: bool = False,
) -> subprocess.CompletedProcess[str]:
    bash = _require_bash()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_docker(bin_dir)
    env_path = tmp_path / ".env"
    env_path.write_text("POSTGRES_USER=draftcheck\nSENTRY_DSN=https://old@example.ingest.sentry.io/1\n", encoding="utf-8")

    env = os.environ.copy()
    env.update(
        {
            "DRAFTCHECK_APP_DIR": str(ROOT),
            "DRAFTCHECK_ENV_PATH": str(env_path),
            "DRAFTCHECK_COMPOSE_PATH": str(ROOT / "infra" / "v3" / "compose.yml"),
            "DRAFTCHECK_RESTART_SERVICES": "1" if restart_services else "0",
            "DRAFTCHECK_FAKE_DOCKER_LOG": str(tmp_path / "docker.log"),
            "PYTHON_BIN": sys.executable,
            "PATH": str(bin_dir) + os.pathsep + env["PATH"],
        }
    )
    if dsn is not None:
        env["SENTRY_DSN"] = dsn
    else:
        env.pop("SENTRY_DSN", None)

    return subprocess.run(
        [bash, str(OPS_SENTRY_INSTALL_PATH)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


def _run_log_retention_installer(tmp_path: Path, *, restart_docker: bool = False) -> subprocess.CompletedProcess[str]:
    bash = _require_bash()
    bin_dir = tmp_path / "bin"
    journald_target = tmp_path / "journald" / "draftcheck.conf"
    docker_target = tmp_path / "docker" / "daemon.json"
    systemctl_log = tmp_path / "systemctl.log"
    bin_dir.mkdir()
    _write_fake_systemctl(bin_dir)

    env = os.environ.copy()
    env.update(
        {
            "DRAFTCHECK_APP_DIR": str(ROOT),
            "DRAFTCHECK_JOURNALD_TARGET": str(journald_target),
            "DRAFTCHECK_DOCKER_DAEMON_TARGET": str(docker_target),
            "DRAFTCHECK_SYSTEMCTL_BIN": str(bin_dir / "systemctl"),
            "DRAFTCHECK_FAKE_SYSTEMCTL_LOG": str(systemctl_log),
            "DRAFTCHECK_RESTART_DOCKER": "1" if restart_docker else "0",
            "PYTHON_BIN": sys.executable,
            "PATH": str(bin_dir) + os.pathsep + env["PATH"],
        }
    )
    return subprocess.run(
        [bash, str(OPS_LOG_RETENTION_INSTALL_PATH)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_guardrail_alert_wrapper_reports_ok_when_all_checks_pass(tmp_path: Path) -> None:
    result = _run_guardrail_alerts(tmp_path)

    assert result.returncode == 0
    assert "draftcheck guardrails ok" in result.stdout
    assert (tmp_path / "guardrail-calls.txt").read_text(encoding="utf-8").splitlines() == [
        "backup-freshness",
        "disk-usage",
        "uptime-targets",
        "worker-heartbeat",
    ]


def test_guardrail_alert_wrapper_aggregates_failing_check(tmp_path: Path) -> None:
    result = _run_guardrail_alerts(tmp_path, failing={"disk-usage"})

    assert result.returncode == 2
    assert "draftcheck guardrail failures:" in result.stderr
    assert "disk_usage:" in result.stderr
    assert "disk-usage critical fixture" in result.stderr
    assert "draftcheck guardrails ok" not in result.stdout


def test_guardrail_alert_wrapper_posts_webhook_payload(tmp_path: Path) -> None:
    result = _run_guardrail_alerts(
        tmp_path,
        failing={"worker-heartbeat"},
        webhook=True,
    )

    assert result.returncode == 2
    payload = json.loads((tmp_path / "curl-payload.json").read_text(encoding="utf-8"))
    assert "DraftCheck guardrail failures:" in payload["text"]
    assert "worker_heartbeat:" in payload["text"]
    assert "worker-heartbeat critical fixture" in payload["text"]


def test_backup_installer_explains_missing_backup_env(tmp_path: Path) -> None:
    result = _run_backup_installer(tmp_path, backup_env_exists=False)

    assert result.returncode == 2
    assert "Missing" in result.stderr
    assert "RESTIC_REPOSITORY" in result.stderr
    assert "RESTIC_PASSWORD_FILE" in result.stderr
    assert not (tmp_path / "systemd" / "draftcheck-backup.service").exists()


def test_backup_installer_validates_config_and_enables_timer(tmp_path: Path) -> None:
    result = _run_backup_installer(tmp_path, backup_env_exists=True)

    assert result.returncode == 0
    assert (tmp_path / "guardrail-calls.txt").read_text(encoding="utf-8").splitlines() == [
        "backup-config",
    ]
    assert (tmp_path / "systemd" / "draftcheck-backup.service").read_text(encoding="utf-8") == (
        "[Unit]\nDescription=DraftCheck backup fixture\n"
    )
    assert (tmp_path / "systemd" / "draftcheck-backup.timer").read_text(encoding="utf-8") == (
        "[Timer]\nOnCalendar=daily\n"
    )
    assert (tmp_path / "systemctl.log").read_text(encoding="utf-8").splitlines() == [
        "daemon-reload",
        "enable --now draftcheck-backup.timer",
        "list-timers --all draftcheck-backup.timer",
    ]


def test_guardrail_cron_installer_writes_checked_cron_entry(tmp_path: Path) -> None:
    result = _run_guardrail_cron_installer(tmp_path)

    assert result.returncode == 0
    assert "installed draftcheck guardrail cron" in result.stdout
    assert (tmp_path / "guardrail-calls.txt").read_text(encoding="utf-8").splitlines() == [
        "guardrail-cron",
    ]
    cron = (tmp_path / "draftcheck-guardrails").read_text(encoding="utf-8")
    assert cron == (
        "*/10 * * * * root bash /srv/draftcheck/app/infra/v3/ops/guardrail-alerts.sh "
        ">> /var/log/draftcheck-guardrails.log 2>&1\n"
    )


def test_restore_drill_script_emits_guardrail_accepted_log(tmp_path: Path) -> None:
    result = _run_restore_drill(tmp_path)

    assert result.returncode == 0, result.stderr
    log = tmp_path / "restore-drill-20260613.md"
    log.write_text(result.stdout, encoding="utf-8")
    accepted = check_restore_drill_log(log)
    assert accepted.status == "ok", accepted.message
    assert "snapshot_id: abc123ef" in result.stdout
    assert "source_versions: 286" in result.stdout
    assert "job_traces: 4" in result.stdout
    assert "storage_manifest_sha256:" in result.stdout
    calls = (tmp_path / "restore-drill-calls.txt").read_text(encoding="utf-8")
    assert "restic check" in calls
    assert "restic restore latest" in calls
    assert "docker compose" in calls


def test_log_retention_installer_validates_configs_without_docker_restart(tmp_path: Path) -> None:
    result = _run_log_retention_installer(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "Docker log rotation config installed" in result.stdout
    assert "installed draftcheck log retention configs" in result.stdout
    assert (tmp_path / "journald" / "draftcheck.conf").read_text(encoding="utf-8") == (
        "[Journal]\nSystemMaxUse=1G\nSystemKeepFree=2G\nMaxRetentionSec=14day\n"
    )
    assert json.loads((tmp_path / "docker" / "daemon.json").read_text(encoding="utf-8")) == {
        "log-driver": "json-file",
        "log-opts": {
            "max-size": "50m",
            "max-file": "5",
        },
    }
    assert (tmp_path / "systemctl.log").read_text(encoding="utf-8").splitlines() == [
        "restart systemd-journald",
    ]


def test_log_retention_installer_can_restart_docker_explicitly(tmp_path: Path) -> None:
    result = _run_log_retention_installer(tmp_path, restart_docker=True)

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "systemctl.log").read_text(encoding="utf-8").splitlines() == [
        "restart systemd-journald",
        "restart docker",
    ]


def test_sentry_installer_writes_dsn_without_printing_secret(tmp_path: Path) -> None:
    result = _run_sentry_installer(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "Sentry DSN installed" in result.stdout
    assert "public@example.ingest.sentry.io" not in result.stdout
    assert "public@example.ingest.sentry.io" not in result.stderr
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "POSTGRES_USER=draftcheck" in env_text
    assert "SENTRY_DSN=https://public@example.ingest.sentry.io/123" in env_text
    assert not (tmp_path / "docker.log").exists()


def test_sentry_installer_requires_dsn(tmp_path: Path) -> None:
    result = _run_sentry_installer(tmp_path, dsn=None)

    assert result.returncode != 0
    assert "SENTRY_DSN is required" in result.stderr


def test_sentry_installer_can_restart_services_explicitly(tmp_path: Path) -> None:
    result = _run_sentry_installer(tmp_path, restart_services=True)

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "docker.log").read_text(encoding="utf-8").splitlines() == [
        "docker compose up -d api worker hermes",
    ]


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


def test_backup_config_requires_restic_password_and_compose_paths(tmp_path: Path) -> None:
    password_file = tmp_path / "restic-password"
    compose_file = tmp_path / "compose.yml"
    password_file.write_text("secret\n", encoding="utf-8")
    compose_file.write_text("services: {}\n", encoding="utf-8")
    env_path = tmp_path / "backup.env"
    env_path.write_text(
        f"""RESTIC_REPOSITORY=s3:s3.example.invalid/draftcheck-v3-backups
RESTIC_PASSWORD_FILE={password_file}
POSTGRES_USER=draftcheck
POSTGRES_DB=draftcheck
COMPOSE_FILE={compose_file}
""",
        encoding="utf-8",
    )

    result = check_backup_config(env_path)

    assert result.status == "ok"
    assert result.metadata["missing_keys"] == []
    assert result.metadata["missing_paths"] == []


def test_backup_config_flags_missing_fields_and_paths(tmp_path: Path) -> None:
    env_path = tmp_path / "backup.env"
    env_path.write_text(
        f"""RESTIC_REPOSITORY=s3:s3.example.invalid/draftcheck-v3-backups
RESTIC_PASSWORD_FILE={tmp_path / "missing-password"}
POSTGRES_USER=draftcheck
COMPOSE_FILE={tmp_path / "missing-compose.yml"}
""",
        encoding="utf-8",
    )

    result = check_backup_config(env_path)

    assert result.status == "critical"
    assert "POSTGRES_DB" in result.metadata["missing_keys"]
    assert any("RESTIC_PASSWORD_FILE" in path for path in result.metadata["missing_paths"])
    assert any("COMPOSE_FILE" in path for path in result.metadata["missing_paths"])


def test_guardrail_cron_requires_checked_wrapper_and_log(tmp_path: Path) -> None:
    cron = tmp_path / "draftcheck-guardrails"
    cron.write_text(
        "*/10 * * * * root bash /srv/draftcheck/app/infra/v3/ops/guardrail-alerts.sh >> "
        "/var/log/draftcheck-guardrails.log 2>&1\n",
        encoding="utf-8",
    )

    result = check_guardrail_cron(cron)

    assert result.status == "ok"


def test_guardrail_cron_flags_incomplete_entry(tmp_path: Path) -> None:
    cron = tmp_path / "draftcheck-guardrails"
    cron.write_text("*/10 * * * * root echo ok\n", encoding="utf-8")

    result = check_guardrail_cron(cron)

    assert result.status == "critical"
    assert "guardrail-alerts.sh command missing" in result.message
    assert "local guardrail log redirection missing" in result.message


def test_sentry_config_accepts_https_dsn_and_compose_wiring(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\ufeffSENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0\n",
        encoding="utf-8",
    )
    compose_path = tmp_path / "compose.yml"
    compose_path.write_text(
        """services:
  api:
    environment:
      SENTRY_DSN: ${SENTRY_DSN:-}
""",
        encoding="utf-8",
    )

    result = check_sentry_config(env_path, compose_path=compose_path)

    assert result.status == "ok"
    assert result.metadata["dsn_present"] is True
    assert result.metadata["sentry_host"] == "o0.ingest.sentry.io"
    assert result.metadata["compose_mentions_sentry"] is True
    assert "examplePublicKey" not in str(result.metadata)


def test_sentry_config_flags_missing_or_malformed_dsn(tmp_path: Path) -> None:
    missing = check_sentry_config(tmp_path / "missing.env")
    assert missing.status == "critical"
    assert "missing" in missing.message

    env_path = tmp_path / ".env"
    env_path.write_text("SENTRY_DSN=http://localhost/0\n", encoding="utf-8")
    malformed = check_sentry_config(env_path)

    assert malformed.status == "critical"
    assert "HTTPS DSN" in malformed.message
    assert malformed.metadata["dsn_present"] is True


def test_sentry_config_flags_missing_compose_wiring(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0\n",
        encoding="utf-8",
    )
    compose_path = tmp_path / "compose.yml"
    compose_path.write_text("services: {}\n", encoding="utf-8")

    result = check_sentry_config(env_path, compose_path=compose_path)

    assert result.status == "critical"
    assert "compose file does not wire SENTRY_DSN" in result.message
    assert result.metadata["compose_mentions_sentry"] is False


def test_log_retention_config_accepts_journald_and_docker_rotation(tmp_path: Path) -> None:
    journald = tmp_path / "draftcheck.conf"
    journald.write_text(
        """[Journal]
SystemMaxUse=1G
SystemKeepFree=2G
MaxRetentionSec=14day
""",
        encoding="utf-8",
    )
    docker_daemon = tmp_path / "daemon.json"
    docker_daemon.write_text(
        """{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  }
}
""",
        encoding="utf-8",
    )

    result = check_log_retention_config(journald, docker_daemon)

    assert result.status == "ok"
    assert result.metadata["journald_values"]["SystemMaxUse"] == "1G"
    assert result.metadata["docker_config"]["log-opts"]["max-file"] == "5"


def test_log_retention_config_flags_missing_files(tmp_path: Path) -> None:
    result = check_log_retention_config(
        tmp_path / "missing-journald.conf",
        tmp_path / "missing-daemon.json",
    )

    assert result.status == "critical"
    assert "journald config missing" in result.message
    assert "Docker daemon config missing" in result.message


def test_log_retention_config_flags_malformed_values(tmp_path: Path) -> None:
    journald = tmp_path / "draftcheck.conf"
    journald.write_text(
        """[Journal]
SystemMaxUse=10G
SystemKeepFree=2G
""",
        encoding="utf-8",
    )
    docker_daemon = tmp_path / "daemon.json"
    docker_daemon.write_text(
        """{
  "log-driver": "journald",
  "log-opts": {
    "max-size": "500m"
  }
}
""",
        encoding="utf-8",
    )

    result = check_log_retention_config(journald, docker_daemon)

    assert result.status == "critical"
    assert "SystemMaxUse must be 1G" in result.message
    assert "MaxRetentionSec must be 14day" in result.message
    assert "Docker log-driver must be json-file" in result.message
    assert "log-opts.max-file must be 5" in result.message


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


def test_uptime_monitor_doc_requires_recorded_monitor_ids(tmp_path: Path) -> None:
    doc = tmp_path / "uptime-monitor.md"
    doc.write_text(
        """# Uptime Monitoring

| URL | Purpose | Expected response |
|-----|---------|-------------------|
| `https://lotfile.app/api/v1/health` | Primary health probe | HTTP 200 |
| `https://lotfile.app/api/v1/ready` | Deep-ready probe | HTTP 200 |

| Monitor | Provider ID | Alert contact |
|---------|-------------|---------------|
| LotFile health | 123456789 | stevenshelley58@gmail.com |
| LotFile ready | 987654321 | stevenshelley58@gmail.com |
""",
        encoding="utf-8",
    )

    result = check_uptime_monitor_doc(doc)

    assert result.status == "ok"
    assert result.metadata["recorded_monitors"]["LotFile health"]["provider_id"] == "123456789"


def test_uptime_monitor_doc_flags_pending_or_missing_evidence(tmp_path: Path) -> None:
    pending_doc = tmp_path / "uptime-monitor.md"
    pending_doc.write_text(
        """# Uptime Monitoring

| URL | Purpose | Expected response |
|-----|---------|-------------------|
| `https://lotfile.app/api/v1/health` | Primary health probe | HTTP 200 |

| Monitor | Provider ID | Alert contact |
|---------|-------------|---------------|
| LotFile health | pending | pending |
""",
        encoding="utf-8",
    )

    result = check_uptime_monitor_doc(pending_doc)

    assert result.status == "critical"
    assert "LotFile ready target URL missing" in result.message
    assert "LotFile ready monitor ID row missing" in result.message
    assert "LotFile health.provider_id" in result.message


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

## Storage restore

storage_path: /tmp/draftcheck-v3-restore/srv/draftcheck/storage
storage_file_count: 12
storage_size_bytes: 345678
storage_manifest_sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
result: PASS

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
storage_file_count: 0
storage_size_bytes: 0
storage_manifest_sha256: (64 hex chars from restore-drill.sh)
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
    assert "storage_path is required" in failed.message
    assert "storage_file_count" in failed.message
    assert "storage_manifest_sha256" in failed.message
