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
OPS_CRON_INSTALL_PATH = ROOT / "infra" / "v3" / "ops" / "install-guardrail-cron.sh"
OPS_LOG_RETENTION_INSTALL_PATH = ROOT / "infra" / "v3" / "ops" / "install-log-retention.sh"
OPS_SENTRY_INSTALL_PATH = ROOT / "infra" / "v3" / "ops" / "install-sentry-dsn.sh"
OPS_RUNBOOK_PATH = ROOT / "docs" / "ops" / "ops-guardrails.md"
WEB_ONLY_DEPLOY_PATH = ROOT / "infra" / "v3" / "deploy-web-only.sh"
JOURNALD_RETENTION_PATH = ROOT / "infra" / "v3" / "ops" / "journald-draftcheck.conf"
DOCKER_LOG_ROTATION_PATH = ROOT / "infra" / "v3" / "ops" / "docker-daemon-log-rotation.json"
CI_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "ci.yml"
WEB_PACKAGE_PATH = ROOT / "web" / "package.json"
WEB_LIGHTHOUSE_CONFIG_PATH = ROOT / "web" / "lighthouserc.cjs"
WEB_MOBILE_VERIFY_PATH = ROOT / "web" / "scripts" / "verify-mobile-launch.mjs"
WEB_LIVE_PREVIEW_VERIFY_PATH = ROOT / "web" / "scripts" / "test-live-launch-preview.mjs"
VPS_DEPLOY_PATH = ROOT / "infra" / "v3" / "deploy.sh"


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


def test_v3_compose_wires_sentry_dsn_for_runtime_services():
    prod_compose = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))

    for service_name in ("api", "worker", "hermes"):
        environment = prod_compose["services"][service_name]["environment"]
        assert environment["SENTRY_DSN"] == "${SENTRY_DSN:-}"


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
    assert "## Storage restore" in restore_script
    assert "storage_file_count:" in restore_script
    assert "storage_size_bytes:" in restore_script
    assert "storage_manifest_sha256:" in restore_script
    assert "source_versions: $SOURCE_VERSIONS" in restore_script
    assert "job_traces: $JOB_TRACES" in restore_script
    assert "status: PASS" in restore_script


def test_v3_ops_guardrails_are_operator_runnable_without_committed_secrets():
    install_script = BACKUP_INSTALL_PATH.read_text(encoding="utf-8")
    alert_script = OPS_ALERT_PATH.read_text(encoding="utf-8")
    cron_install_script = OPS_CRON_INSTALL_PATH.read_text(encoding="utf-8")
    log_retention_install_script = OPS_LOG_RETENTION_INSTALL_PATH.read_text(encoding="utf-8")
    sentry_install_script = OPS_SENTRY_INSTALL_PATH.read_text(encoding="utf-8")
    runbook = OPS_RUNBOOK_PATH.read_text(encoding="utf-8").lower()

    assert "systemctl enable --now draftcheck-backup.timer" in install_script
    assert "DRAFTCHECK_ALERT_WEBHOOK_URL" in alert_script
    assert "backup-freshness" in alert_script
    assert "disk-usage" in alert_script
    assert "worker-heartbeat" in alert_script
    assert "backup-config" in install_script
    assert "guardrail-cron" in cron_install_script
    assert "/etc/cron.d/draftcheck-guardrails" in cron_install_script
    assert "DRAFTCHECK_CRON_APP_DIR:-/srv/draftcheck/app" in cron_install_script
    assert "infra/v3/ops/guardrail-alerts.sh" in cron_install_script
    assert "log-retention-config" in log_retention_install_script
    assert "DRAFTCHECK_RESTART_DOCKER:-0" in log_retention_install_script
    assert "restart docker" in log_retention_install_script
    assert "sentry-config" in sentry_install_script
    assert "SENTRY_DSN is required" in sentry_install_script
    assert "DRAFTCHECK_RESTART_SERVICES:-0" in sentry_install_script
    assert "docker compose up -d api worker hermes" in sentry_install_script
    assert "<generated-restic-password>" in runbook
    assert "backup-config" in runbook
    assert "install-guardrail-cron.sh" in runbook
    assert "install-log-retention.sh" in runbook
    assert "install-sentry-dsn.sh" in runbook
    assert "guardrail-cron" in runbook
    assert "uptime-monitor-doc" in runbook
    assert "sentry-config" in runbook
    assert "log-retention-config" in runbook
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
        "npm run verify:launch:mobile",
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
        "infra/v3/ops/install-guardrail-cron.sh",
        "infra/v3/ops/install-log-retention.sh",
        "infra/v3/ops/install-sentry-dsn.sh",
        "infra/v3/backup/install-systemd.sh",
        "infra/v3/backup/restore-drill.sh",
        "infra/v3/deploy.sh",
        "infra/v3/deploy-web-only.sh",
    ):
        assert f"bash -n {script}" in syntax_step["run"]


def test_v3_ci_forbids_dynamic_schema_creation_in_v3_app_code():
    workflow = yaml.safe_load(CI_WORKFLOW_PATH.read_text(encoding="utf-8"))
    backend_steps = workflow["jobs"]["backend"]["steps"]
    forbidden_step = next(step for step in backend_steps if step.get("name") == "Forbidden V3 patterns")
    run = forbidden_step["run"]

    assert '! grep -RI "create_all" src web --exclude-dir=__pycache__' in run
    assert '! grep -RI "init_database\\|init_db" src web --exclude-dir=__pycache__' in run


def test_v3_ci_migration_job_proves_full_local_db_roundtrip_and_extensions():
    workflow = yaml.safe_load(CI_WORKFLOW_PATH.read_text(encoding="utf-8"))
    migration_steps = workflow["jobs"]["migrations"]["steps"]
    roundtrip_step = next(step for step in migration_steps if step.get("name") == "Migration roundtrip")
    run = roundtrip_step["run"]

    assert "alembic upgrade head" in run
    assert "alembic current" in run
    assert "pg_extension" in run
    assert "pg_trgm,postgis,vector" in run
    assert "alembic downgrade base" in run
    assert "alembic downgrade -1" in run


def test_v3_ci_verifies_non_db_launch_ops_report_artifact():
    workflow = yaml.safe_load(CI_WORKFLOW_PATH.read_text(encoding="utf-8"))
    backend_steps = workflow["jobs"]["backend"]["steps"]

    assert any(
        step.get("name") == "Verify non-DB launch ops report"
        and step.get("run") == "python scripts/audit_non_db_launch_ops.py --verify-report reports/non_db_launch_ops_blockers.json"
        for step in backend_steps
    )


def test_v3_ci_runs_launch_action_behavior_test():
    workflow = yaml.safe_load(CI_WORKFLOW_PATH.read_text(encoding="utf-8"))
    web_steps = workflow["jobs"]["web"]["steps"]
    package_json = json.loads(WEB_PACKAGE_PATH.read_text(encoding="utf-8"))
    launch_actions = package_json["scripts"]["test:launch-actions"]

    assert any(step.get("run") == "npm run test:launch-actions" for step in web_steps)
    assert "src/components/modals.launch.test.tsx" in launch_actions
    assert "src/App.launch.test.tsx" in launch_actions


def test_v3_ci_runs_mobile_launch_sweep():
    workflow = yaml.safe_load(CI_WORKFLOW_PATH.read_text(encoding="utf-8"))
    web_steps = workflow["jobs"]["web"]["steps"]
    package_json = json.loads(WEB_PACKAGE_PATH.read_text(encoding="utf-8"))
    mobile_verify = WEB_MOBILE_VERIFY_PATH.read_text(encoding="utf-8")

    assert package_json["scripts"]["verify:launch:mobile"] == "node scripts/verify-mobile-launch.mjs"
    assert any(step.get("run") == "npm run verify:launch:mobile" for step in web_steps)
    assert "Mobile tabbar must render exactly 5 tabs" in mobile_verify
    assert "grid-template-columns:repeat(5,minmax(0,1fr))" in mobile_verify
    assert "@media (max-width:390px)" in mobile_verify
    assert "wizard-stepper" in mobile_verify
    assert 'aria-label="Send address or question"' in mobile_verify


def test_v3_ci_runs_live_launch_preview_harness():
    workflow = yaml.safe_load(CI_WORKFLOW_PATH.read_text(encoding="utf-8"))
    web_steps = workflow["jobs"]["web"]["steps"]
    package_json = json.loads(WEB_PACKAGE_PATH.read_text(encoding="utf-8"))
    preview_verify = WEB_LIVE_PREVIEW_VERIFY_PATH.read_text(encoding="utf-8")

    assert package_json["scripts"]["test:live-launch-preview"] == "node scripts/test-live-launch-preview.mjs"
    assert any(step.get("run") == "npm run test:live-launch-preview" for step in web_steps)
    assert "scripts/verify-live-launch.mjs" in preview_verify
    assert "LIVE_CHECKOUT_URL" in preview_verify
    assert "/api/v1/health" in preview_verify
    assert "/api/v1/ready" in preview_verify


def test_v3_ci_runs_lighthouse_seo_gate():
    workflow = yaml.safe_load(CI_WORKFLOW_PATH.read_text(encoding="utf-8"))
    web_steps = workflow["jobs"]["web"]["steps"]
    package_json = json.loads(WEB_PACKAGE_PATH.read_text(encoding="utf-8"))
    lighthouse_config = WEB_LIGHTHOUSE_CONFIG_PATH.read_text(encoding="utf-8")

    assert package_json["scripts"]["verify:launch:lighthouse"] == "lhci autorun --config=./lighthouserc.cjs"
    assert any(step.get("name") == "Resolve Chrome for Lighthouse" for step in web_steps)
    assert any(step.get("run") == "npm run verify:launch:lighthouse" for step in web_steps)
    assert 'staticDistDir: "./dist"' in lighthouse_config
    assert 'isSinglePageApplication: true' in lighthouse_config
    assert '"categories:seo": ["error", { minScore: 0.9' in lighthouse_config
    assert 'target: "filesystem"' in lighthouse_config


def test_v3_deploy_reloads_caddy_and_runs_live_launch_verification():
    deploy_script = VPS_DEPLOY_PATH.read_text(encoding="utf-8")

    assert "up -d --force-recreate --no-deps internal_caddy" in deploy_script
    assert 'npm run verify:launch:live' in deploy_script
