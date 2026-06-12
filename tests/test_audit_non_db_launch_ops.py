from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_non_db_launch_ops import (
    FetchResult,
    assess_live_launch,
    assess_ops_guardrails_status,
    assess_restore_drill_log,
    assess_uptime_monitor_doc,
    build_report,
    parse_vps_state,
    validate_audit_report,
    validate_ops_runbook,
    validate_restore_drill_template,
    verify_report_artifact,
)


ROOT = Path(__file__).resolve().parents[1]


def test_parse_vps_state_extracts_missing_ops_state() -> None:
    output = """
BACKUP_ENV_MISSING
RESTIC_PASSWORD_FILE_MISSING
CRON_GUARDRAILS_MISSING
0 timers listed.
OPS_GUARDRAILS_MISSING
SENTRY_DSN_MISSING
LOG_RETENTION_JOURNALD_MISSING
LOG_RETENTION_DOCKER_MISSING
"""

    state = parse_vps_state(output)

    assert state["vps_checkout_env"] == "VITE_CHECKOUT_URL_MISSING"
    assert state["backup_env"] == "BACKUP_ENV_MISSING"
    assert state["restic_password_file"] == "RESTIC_PASSWORD_FILE_MISSING"
    assert state["backup_timer"] == "0 timers listed."
    assert state["guardrail_cron"] == "CRON_GUARDRAILS_MISSING"
    assert state["ops_guardrail_script"] == "OPS_GUARDRAILS_MISSING"
    assert state["sentry_dsn"] == "SENTRY_DSN_MISSING"
    assert state["log_retention_journald"] == "LOG_RETENTION_JOURNALD_MISSING"
    assert state["log_retention_docker"] == "LOG_RETENTION_DOCKER_MISSING"


def test_parse_vps_state_records_sentry_presence_without_value() -> None:
    output = """
VITE_CHECKOUT_URL=https://buy.stripe.com/test_fixture
BACKUP_ENV_PRESENT
RESTIC_PASSWORD_FILE_PRESENT
CRON_GUARDRAILS_PRESENT
1 timers listed.
OPS_GUARDRAILS_PRESENT
SENTRY_DSN_PRESENT
LOG_RETENTION_JOURNALD_PRESENT
LOG_RETENTION_DOCKER_PRESENT
"""

    state = parse_vps_state(output)

    assert state["sentry_dsn"] == "SENTRY_DSN_PRESENT"
    assert state["log_retention_journald"] == "LOG_RETENTION_JOURNALD_PRESENT"
    assert state["log_retention_docker"] == "LOG_RETENTION_DOCKER_PRESENT"
    assert "ingest.sentry.io" not in str(state)
    assert "examplePublicKey" not in str(state)


def test_assess_live_launch_reports_bundle_and_page_gaps() -> None:
    pages = {
        "/": FetchResult(status=200, text="<title>LotFile</title>"),
        "/privacy": FetchResult(status=200, text="<title>LotFile</title>"),
        "/terms": FetchResult(status=200, text="<title>LotFile</title>"),
        "/app": FetchResult(status=200, text="<title>LotFile</title>"),
    }

    result = assess_live_launch("https://lotfile.app", pages, bundle_text="")

    assert result["status"] == "blocked"
    assert result["evidence"]["live_index_title"] == "<title>LotFile</title>"
    assert result["evidence"]["missing_count"] > 0


def test_build_report_blocks_without_checkout_even_when_launch_pages_pass() -> None:
    page_text = (
        '<title>LotFile - WA R-Code & Planning Compliance Checker</title>'
        '<meta name="description">'
        '<meta property="og:title">'
        '<script data-domain="lotfile.app"></script>'
    )
    bundle_text = "\n".join(
        [
            "/privacy",
            "/terms",
            "Check an address free",
            "Advisory research only",
            "signup_requested",
            "project_created",
            "compliance_run",
            "checkout_clicked",
            "AUD $29/month",
        ]
    )
    pages = {route: FetchResult(status=200, text=page_text) for route in ["/", "/privacy", "/terms", "/app"]}
    api = {
        "/api/v1/health": FetchResult(status=200, text='{"status":"ok"}'),
        "/api/v1/ready": FetchResult(status=200, text='{"status":"ok"}'),
    }
    vps_state = {
        "vps_checkout_env": "VITE_CHECKOUT_URL_MISSING",
        "backup_env": "BACKUP_ENV_PRESENT",
        "restic_password_file": "RESTIC_PASSWORD_FILE_PRESENT",
        "backup_timer": "draftcheck-backup.timer active",
        "guardrail_cron": "CRON_GUARDRAILS_PRESENT",
        "ops_guardrail_script": "OPS_GUARDRAILS_PRESENT",
        "sentry_dsn": "SENTRY_DSN_PRESENT",
        "log_retention_journald": "LOG_RETENTION_JOURNALD_PRESENT",
        "log_retention_docker": "LOG_RETENTION_DOCKER_PRESENT",
    }

    report = build_report(
        "https://lotfile.app",
        vps_state,
        pages,
        api,
        bundle_text,
        uptime_monitor_doc="ok: uptime monitor doc records provisioned monitor IDs and alert contacts",
    )

    assert report["launch_surface"]["status"] == "blocked"
    assert report["launch_surface"]["evidence"]["vps_checkout_env"] == "VITE_CHECKOUT_URL_MISSING"
    assert report["ops_guardrails"]["evidence"]["sentry_dsn"] == "SENTRY_DSN_PRESENT"
    assert report["ops_guardrails"]["evidence"]["log_retention_journald"] == "LOG_RETENTION_JOURNALD_PRESENT"
    assert report["ops_guardrails"]["evidence"]["log_retention_docker"] == "LOG_RETENTION_DOCKER_PRESENT"
    assert "status ok" in report["ops_guardrails"]["evidence"]["uptime_targets"]
    assert report["ops_guardrails"]["evidence"]["uptime_monitor_doc"].startswith("ok:")
    assert report["ops_guardrails"]["status"] == "blocked"
    unblock = "\n".join(report["ops_guardrails"]["unblock"])
    assert "install-guardrail-cron.sh" in unblock
    assert "install-sentry-dsn.sh" in unblock
    assert "install-log-retention.sh" in unblock


def test_build_report_verifies_when_all_launch_and_ops_evidence_passes() -> None:
    page_text = (
        '<title>LotFile - WA R-Code & Planning Compliance Checker</title>'
        '<meta name="description">'
        '<meta property="og:title">'
        '<script data-domain="lotfile.app"></script>'
    )
    bundle_text = "\n".join(
        [
            "/privacy",
            "/terms",
            "Check an address free",
            "Advisory research only",
            "signup_requested",
            "project_created",
            "compliance_run",
            "checkout_clicked",
            "AUD $29/month",
        ]
    )
    pages = {route: FetchResult(status=200, text=page_text) for route in ["/", "/privacy", "/terms", "/app"]}
    api = {
        "/api/v1/health": FetchResult(status=200, text='{"status":"ok"}'),
        "/api/v1/ready": FetchResult(status=200, text='{"status":"ok"}'),
    }
    vps_state = {
        "vps_checkout_env": "https://buy.stripe.com/test_fixture",
        "backup_env": "BACKUP_ENV_PRESENT",
        "restic_password_file": "RESTIC_PASSWORD_FILE_PRESENT",
        "backup_timer": "1 timers listed.",
        "guardrail_cron": "CRON_GUARDRAILS_PRESENT",
        "ops_guardrail_script": "OPS_GUARDRAILS_PRESENT",
        "sentry_dsn": "SENTRY_DSN_PRESENT",
        "log_retention_journald": "LOG_RETENTION_JOURNALD_PRESENT",
        "log_retention_docker": "LOG_RETENTION_DOCKER_PRESENT",
    }

    report = build_report(
        "https://lotfile.app",
        vps_state,
        pages,
        api,
        bundle_text,
        uptime_monitor_doc="ok: uptime monitor doc records provisioned monitor IDs and alert contacts",
        restore_drill_log="ok: restore drill log accepted",
    )

    assert report["launch_surface"]["status"] == "verified"
    assert report["ops_guardrails"]["status"] == "verified"
    assert validate_audit_report(report) == []


def test_build_report_blocks_when_ssh_state_is_skipped() -> None:
    page_text = (
        '<title>LotFile - WA R-Code & Planning Compliance Checker</title>'
        '<meta name="description">'
        '<meta property="og:title">'
        '<script data-domain="lotfile.app"></script>'
    )
    bundle_text = "\n".join(
        [
            "/privacy",
            "/terms",
            "Check an address free",
            "Advisory research only",
            "signup_requested",
            "project_created",
            "compliance_run",
            "checkout_clicked",
            "AUD $29/month",
        ]
    )
    pages = {route: FetchResult(status=200, text=page_text) for route in ["/", "/privacy", "/terms", "/app"]}
    api = {
        "/api/v1/health": FetchResult(status=200, text='{"status":"ok"}'),
        "/api/v1/ready": FetchResult(status=200, text='{"status":"ok"}'),
    }
    vps_state = {
        "vps_checkout_env": "SSH_SKIPPED",
        "backup_env": "SSH_SKIPPED",
        "restic_password_file": "SSH_SKIPPED",
        "backup_timer": "SSH_SKIPPED",
        "guardrail_cron": "SSH_SKIPPED",
        "ops_guardrail_script": "SSH_SKIPPED",
        "sentry_dsn": "SSH_SKIPPED",
        "log_retention_journald": "SSH_SKIPPED",
        "log_retention_docker": "SSH_SKIPPED",
    }

    report = build_report(
        "https://lotfile.app",
        vps_state,
        pages,
        api,
        bundle_text,
        uptime_monitor_doc="ok: uptime monitor doc records provisioned monitor IDs and alert contacts",
        restore_drill_log="ok: restore drill log accepted",
    )

    assert report["launch_surface"]["status"] == "blocked"
    assert report["ops_guardrails"]["status"] == "blocked"


def test_ops_guardrails_status_blocks_pending_fields() -> None:
    evidence = {
        "backup_env": "BACKUP_ENV_PRESENT",
        "restic_password_file": "RESTIC_PASSWORD_FILE_PRESENT",
        "backup_timer": "0 timers listed.",
        "restore_drill_log": "ok: restore drill log accepted",
        "guardrail_cron": "CRON_GUARDRAILS_PRESENT",
        "ops_guardrail_script": "OPS_GUARDRAILS_PRESENT",
        "sentry_dsn": "SENTRY_DSN_PRESENT",
        "uptime_targets": "uv run python scripts/ops_guardrails.py uptime-targets --json returned status ok for lotfile.app health and ready",
        "uptime_monitor_doc": "ok: uptime monitor doc records provisioned monitor IDs and alert contacts",
        "log_retention_journald": "LOG_RETENTION_JOURNALD_PRESENT",
        "log_retention_docker": "LOG_RETENTION_DOCKER_PRESENT",
    }

    assert assess_ops_guardrails_status(evidence) == "blocked"


def test_validate_audit_report_rejects_raw_dsn_and_false_green_status() -> None:
    report = {
        "launch_surface": {
            "status": "verified",
            "evidence": {
                "live_verifier": "passed",
                "missing_count": 0,
                "vps_checkout_env": "SSH_SKIPPED",
            },
        },
        "ops_guardrails": {
            "status": "verified",
            "evidence": {
                "backup_env": "BACKUP_ENV_PRESENT",
                "restic_password_file": "RESTIC_PASSWORD_FILE_PRESENT",
                "backup_timer": "1 timers listed.",
                "restore_drill_log": "ok: restore drill log accepted",
                "guardrail_cron": "CRON_GUARDRAILS_PRESENT",
                "ops_guardrail_script": "OPS_GUARDRAILS_PRESENT",
                "sentry_dsn": "https://public@example.ingest.sentry.io/123",
                "uptime_targets": "uv run python scripts/ops_guardrails.py uptime-targets --json returned status ok for lotfile.app health and ready",
                "uptime_monitor_doc": "ok: uptime monitor doc records provisioned monitor IDs and alert contacts",
                "log_retention_journald": "LOG_RETENTION_JOURNALD_PRESENT",
                "log_retention_docker": "LOG_RETENTION_DOCKER_PRESENT",
                "log_retention_config": "journald and Docker json-file retention configs are installed",
            },
        },
    }

    failures = validate_audit_report(report)

    assert any("raw DSN" in failure for failure in failures)
    assert any("checkout URL" in failure for failure in failures)
    assert any("expected 'blocked'" in failure for failure in failures)


def test_restore_template_and_runbook_keep_audit_verifier_contract() -> None:
    assert validate_restore_drill_template(ROOT / "docs" / "ops" / "restore-drill-template.md") == []
    assert validate_ops_runbook(ROOT / "docs" / "ops" / "ops-guardrails.md") == []


def test_verify_report_artifact_combines_report_template_and_runbook_checks(tmp_path: Path) -> None:
    report = {
        "launch_surface": {
            "status": "blocked",
            "evidence": {
                "live_verifier": "failed: fixture",
                "missing_count": 1,
                "vps_checkout_env": "SSH_SKIPPED",
            },
        },
        "ops_guardrails": {
            "status": "blocked",
            "evidence": {
                "backup_env": "SSH_SKIPPED",
                "restic_password_file": "SSH_SKIPPED",
                "backup_timer": "SSH_SKIPPED",
                "restore_drill_log": "critical: no docs/ops/restore-drill-YYYYMMDD.md log found",
                "guardrail_cron": "SSH_SKIPPED",
                "ops_guardrail_script": "SSH_SKIPPED",
                "sentry_dsn": "SSH_SKIPPED",
                "uptime_targets": "uv run python scripts/ops_guardrails.py uptime-targets --json returned status ok for lotfile.app health and ready",
                "uptime_monitor_doc": "critical: pending monitor evidence",
                "log_retention_journald": "SSH_SKIPPED",
                "log_retention_docker": "SSH_SKIPPED",
                "log_retention_config": "journald and Docker json-file retention configs are committed",
            },
        },
    }
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    result = verify_report_artifact(
        report_path,
        restore_template=ROOT / "docs" / "ops" / "restore-drill-template.md",
        ops_runbook=ROOT / "docs" / "ops" / "ops-guardrails.md",
    )

    assert result["status"] == "ok"
    assert result["failures"] == []


def test_assess_uptime_monitor_doc_reports_pending_evidence(tmp_path: Path) -> None:
    doc = tmp_path / "uptime-monitor.md"
    doc.write_text(
        """# Uptime Monitoring

| URL | Purpose | Expected response |
|-----|---------|-------------------|
| `https://lotfile.app/api/v1/health` | Primary health probe | HTTP 200 |
| `https://lotfile.app/api/v1/ready` | Deep-ready probe | HTTP 200 |

| Monitor | Provider ID | Alert contact |
|---------|-------------|---------------|
| LotFile health | pending | pending |
| LotFile ready | pending | pending |
""",
        encoding="utf-8",
    )

    result = assess_uptime_monitor_doc(doc)

    assert result.startswith("critical:")
    assert "pending monitor evidence" in result


def test_assess_restore_drill_log_reports_missing_log(tmp_path: Path) -> None:
    result = assess_restore_drill_log(tmp_path)

    assert result.startswith("critical:")
    assert "restore-drill-YYYYMMDD.md" in result
