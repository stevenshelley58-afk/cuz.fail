from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = ROOT / "infra" / "v3" / "compose.yml"
LOCAL_COMPOSE_PATH = ROOT / "docker-compose.yml"
CADDYFILE_PATH = ROOT / "infra" / "v3" / "Caddyfile"
DB_INIT_PATH = ROOT / "infra" / "v3" / "db" / "init-extensions.sql"
BACKUP_README_PATH = ROOT / "infra" / "v3" / "backup" / "README.md"
BACKUP_INSTALL_PATH = ROOT / "infra" / "v3" / "backup" / "install-systemd.sh"
RESTORE_DRILL_PATH = ROOT / "infra" / "v3" / "backup" / "restore-drill.sh"
OPS_ALERT_PATH = ROOT / "infra" / "v3" / "ops" / "guardrail-alerts.sh"
OPS_RUNBOOK_PATH = ROOT / "docs" / "ops" / "ops-guardrails.md"
WEB_ONLY_DEPLOY_PATH = ROOT / "infra" / "v3" / "deploy-web-only.sh"
JOURNALD_RETENTION_PATH = ROOT / "infra" / "v3" / "ops" / "journald-draftcheck.conf"
DOCKER_LOG_ROTATION_PATH = ROOT / "infra" / "v3" / "ops" / "docker-daemon-log-rotation.json"
CI_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "ci.yml"


def _active_caddy_text() -> str:
    caddyfile = CADDYFILE_PATH.read_text(encoding="utf-8")
    return "\n".join(
        line for line in caddyfile.splitlines() if not line.strip().startswith("#")
    )


def test_v3_compose_has_target_services_and_no_legacy_backends():
    compose_text = COMPOSE_PATH.read_text(encoding="utf-8")
    compose = yaml.safe_load(compose_text)

    assert set(compose["services"]) == {"db", "api", "worker", "hermes", "internal_caddy"}
    assert compose["services"]["db"]["build"]["dockerfile"] == "infra/v3/db/Dockerfile"

    lowered = compose_text.lower()
    for forbidden in ("redis", "minio", "nginx", "vercel"):
        assert forbidden not in lowered

    assert "procrastinate" in lowered
    assert "postgresql" in lowered


def test_v3_compose_aligns_document_storage_env_for_api_and_workers():
    local_compose = yaml.safe_load(LOCAL_COMPOSE_PATH.read_text(encoding="utf-8"))
    prod_compose = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))

    for service_name in ("api", "worker"):
        environment = local_compose["services"][service_name]["environment"]
        assert environment["DRAFTCHECK_STORAGE_ROOT"] == "/app/.storage"
        assert environment["OBJECT_STORAGE_ROOT"] == "/app/.storage"

    for service_name in ("api", "worker", "hermes"):
        environment = prod_compose["services"][service_name]["environment"]
        assert environment["DRAFTCHECK_STORAGE_ROOT"] == "${DRAFTCHECK_STORAGE_ROOT:-/srv/draftcheck/storage}"
        assert environment["OBJECT_STORAGE_ROOT"] == "${DRAFTCHECK_STORAGE_ROOT:-/srv/draftcheck/storage}"


def test_v3_caddy_routes_api_v1_and_static_web_dist():
    active_caddy = _active_caddy_text()

    assert "/api/v1" in active_caddy
    assert "reverse_proxy api:8000" in active_caddy
    assert "root * /srv/draftcheck/app/web/dist" in active_caddy
    assert "/v1" not in active_caddy.replace("/api/v1", "")


def test_v3_db_init_creates_postgis_and_pgvector_extensions():
    init_sql = DB_INIT_PATH.read_text(encoding="utf-8")

    assert "CREATE EXTENSION IF NOT EXISTS postgis" in init_sql
    assert "CREATE EXTENSION IF NOT EXISTS vector" in init_sql


def test_v3_backup_docs_cover_pg_dump_restic_and_restore_drill():
    backup_docs = BACKUP_README_PATH.read_text(encoding="utf-8").lower()

    assert "pg_dump" in backup_docs
    assert "restic" in backup_docs
    assert "pg_restore" in backup_docs
    assert "restore drill" in backup_docs


def test_v3_restore_drill_emits_guardrail_accepted_fields():
    restore_script = RESTORE_DRILL_PATH.read_text(encoding="utf-8")

    assert "result: PASS" in restore_script
    assert "-At -c \"SELECT count(*) FROM source_versions;\"" in restore_script
    assert "-At -c \"SELECT count(*) FROM job_traces;\"" in restore_script
    assert "source_versions: $SOURCE_VERSIONS" in restore_script
    assert "job_traces: $JOB_TRACES" in restore_script
    assert "status: PASS" in restore_script


def test_v3_ops_guardrails_are_operator_runnable_without_committed_secrets():
    install_script = BACKUP_INSTALL_PATH.read_text(encoding="utf-8")
    alert_script = OPS_ALERT_PATH.read_text(encoding="utf-8")
    runbook = OPS_RUNBOOK_PATH.read_text(encoding="utf-8").lower()

    assert "systemctl enable --now draftcheck-backup.timer" in install_script
    assert "DRAFTCHECK_ALERT_WEBHOOK_URL" in alert_script
    assert "backup-freshness" in alert_script
    assert "disk-usage" in alert_script
    assert "worker-heartbeat" in alert_script
    assert "backup-config" in install_script
    assert "<generated-restic-password>" in runbook
    assert "backup-config" in runbook
    assert "guardrail-cron" in runbook
    assert "uptime-monitor-doc" in runbook
    assert "sentry_dsn" in runbook
    assert "spend-snapshot" in runbook


def test_v3_web_only_deploy_is_guarded_and_never_touches_db_or_containers():
    deploy_script = WEB_ONLY_DEPLOY_PATH.read_text(encoding="utf-8")

    for required in (
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "/srv/draftcheck/app",
        "git fetch origin",
        "git restore --source \"$WEB_REF\" -- web",
        "VITE_CHECKOUT_URL",
        "https://buy.stripe.com/*",
        "example",
        "placeholder",
        "change_me",
        "todo",
        "npm ci --include=dev",
        "npm run build",
        "verify-launch.mjs --strict",
        "mktemp -d",
        "cp -a",
        "rollback()",
        "rm -rf web/dist",
        "without container restart",
    ):
        assert required in deploy_script

    lowered = deploy_script.lower()
    for forbidden in (
        "docker compose",
        "alembic",
        "psql",
        "pg_dump",
        "wp6_adjudicate",
        "scripts/wp6_adjudicate.py",
        "create_all",
    ):
        assert forbidden not in lowered


def test_v3_log_retention_configs_cap_journald_and_docker_json_logs():
    journald = JOURNALD_RETENTION_PATH.read_text(encoding="utf-8")
    docker_logs = json.loads(DOCKER_LOG_ROTATION_PATH.read_text(encoding="utf-8"))
    runbook = OPS_RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "[Journal]" in journald
    assert "SystemMaxUse=1G" in journald
    assert "SystemKeepFree=2G" in journald
    assert "MaxRetentionSec=14day" in journald

    assert docker_logs == {
        "log-driver": "json-file",
        "log-opts": {
            "max-size": "50m",
            "max-file": "5",
        },
    }

    assert "journald-draftcheck.conf" in runbook
    assert "docker-daemon-log-rotation.json" in runbook


def test_v3_ci_runs_bash_syntax_gate_for_ops_scripts():
    workflow = yaml.safe_load(CI_WORKFLOW_PATH.read_text(encoding="utf-8"))
    backend_steps = workflow["jobs"]["backend"]["steps"]
    syntax_step = next(step for step in backend_steps if step.get("name") == "Ops shell syntax")

    assert syntax_step["shell"] == "bash"
    for script in (
        "infra/v3/ops/guardrail-alerts.sh",
        "infra/v3/backup/install-systemd.sh",
        "infra/v3/backup/restore-drill.sh",
        "infra/v3/deploy-web-only.sh",
    ):
        assert f"bash -n {script}" in syntax_step["run"]
