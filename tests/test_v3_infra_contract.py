from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = ROOT / "infra" / "v3" / "compose.yml"
CADDYFILE_PATH = ROOT / "infra" / "v3" / "Caddyfile"
DB_INIT_PATH = ROOT / "infra" / "v3" / "db" / "init-extensions.sql"
BACKUP_README_PATH = ROOT / "infra" / "v3" / "backup" / "README.md"
BACKUP_INSTALL_PATH = ROOT / "infra" / "v3" / "backup" / "install-systemd.sh"
OPS_ALERT_PATH = ROOT / "infra" / "v3" / "ops" / "guardrail-alerts.sh"
OPS_RUNBOOK_PATH = ROOT / "docs" / "ops" / "ops-guardrails.md"


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


def test_v3_ops_guardrails_are_operator_runnable_without_committed_secrets():
    install_script = BACKUP_INSTALL_PATH.read_text(encoding="utf-8")
    alert_script = OPS_ALERT_PATH.read_text(encoding="utf-8")
    runbook = OPS_RUNBOOK_PATH.read_text(encoding="utf-8").lower()

    assert "systemctl enable --now draftcheck-backup.timer" in install_script
    assert "DRAFTCHECK_ALERT_WEBHOOK_URL" in alert_script
    assert "backup-freshness" in alert_script
    assert "<generated-restic-password>" in runbook
    assert "sentry_dsn" in runbook
    assert "spend-snapshot" in runbook
