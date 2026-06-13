from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_non_db_launch_ops import (
    FetchResult,
    UPTIME_TARGETS_OK,
    assess_live_launch,
    assess_live_launch_json,
    assess_ops_guardrails_status,
    assess_restore_drill_log,
    assess_spend_persistence_evidence,
    assess_uptime_monitor_doc,
    build_report,
    load_spend_persistence_evidence,
    main,
    parse_vps_state,
    run_live_launch_verifier,
    validate_audit_report,
    validate_ops_runbook,
    validate_restore_drill_template,
    verify_report_artifact,
)


ROOT = Path(__file__).resolve().parents[1]


def _spend_persistence_ok() -> dict[str, object]:
    return assess_spend_persistence_evidence(
        {
            "job_traces": {"rows": 1, "total_tokens": 100, "cost_cents": 20},
            "spend_events": {"rows": 1, "total_tokens": 100, "cost_cents": 20},
        },
        {
            "job_traces": {"rows": 1, "total_tokens": 100, "cost_cents": 20},
            "spend_events": {"rows": 2, "total_tokens": 140, "cost_cents": 25},
        },
    )


def _passed_live_launch_json(origin: str = "https://lotfile.app") -> dict[str, object]:
    return {
        "status": "passed",
        "evidence": {
            "origin": origin,
            "strict": True,
            "checkout_checked": True,
            "routes": {
                "/": {"status": 200},
                "/privacy": {"status": 200},
                "/terms": {"status": 200},
                "/app": {"status": 200},
            },
            "public_assets": {
                "/robots.txt": {"status": 200},
                "/sitemap.xml": {"status": 200},
                "/favicon.svg": {"status": 200},
                "/og-image.svg": {"status": 200},
            },
            "api": {
                "/api/v1/health": {"status": 200, "service_status": "ok"},
                "/api/v1/ready": {"status": 200, "service_status": "ok"},
            },
            "bundles": [{"path": "/assets/index.js", "status": 200}],
        },
        "warnings": [],
        "failures": [],
    }


def test_parse_vps_state_extracts_missing_ops_state() -> None:
    output = """
BACKUP_ENV_MISSING
RESTIC_PASSWORD_FILE_MISSING
CRON_GUARDRAILS_MISSING
0 timers listed.
OPS_GUARDRAILS_MISSING
DISK_USAGE_UNKNOWN
WORKER_HEARTBEAT_UNKNOWN
SENTRY_CONFIG_CRITICAL
LOG_RETENTION_JOURNALD_MISSING
LOG_RETENTION_DOCKER_MISSING
LOG_RETENTION_CONFIG_CRITICAL
"""

    state = parse_vps_state(output)

    assert state["vps_checkout_env"] == "VITE_CHECKOUT_URL_MISSING"
    assert state["backup_env"] == "BACKUP_ENV_MISSING"
    assert state["restic_password_file"] == "RESTIC_PASSWORD_FILE_MISSING"
    assert state["backup_timer"] == "0 timers listed."
    assert state["guardrail_cron"] == "CRON_GUARDRAILS_MISSING"
    assert state["ops_guardrail_script"] == "OPS_GUARDRAILS_MISSING"
    assert state["disk_usage"] == "DISK_USAGE_UNKNOWN"
    assert state["worker_heartbeat"] == "WORKER_HEARTBEAT_UNKNOWN"
    assert state["sentry_dsn"] == "SENTRY_CONFIG_CRITICAL"
    assert state["log_retention_journald"] == "LOG_RETENTION_JOURNALD_MISSING"
    assert state["log_retention_docker"] == "LOG_RETENTION_DOCKER_MISSING"
    assert state["log_retention_config"] == "LOG_RETENTION_CONFIG_CRITICAL"


def test_parse_vps_state_records_sentry_presence_without_value() -> None:
    output = """
VITE_CHECKOUT_URL=https://buy.stripe.com/test_fixture
BACKUP_ENV_PRESENT
RESTIC_PASSWORD_FILE_PRESENT
CRON_GUARDRAILS_PRESENT
1 timers listed.
OPS_GUARDRAILS_PRESENT
DISK_USAGE_OK
WORKER_HEARTBEAT_OK
SENTRY_CONFIG_OK
LOG_RETENTION_JOURNALD_PRESENT
LOG_RETENTION_DOCKER_PRESENT
LOG_RETENTION_CONFIG_OK
"""

    state = parse_vps_state(output)

    assert state["sentry_dsn"] == "SENTRY_CONFIG_OK"
    assert state["disk_usage"] == "DISK_USAGE_OK"
    assert state["worker_heartbeat"] == "WORKER_HEARTBEAT_OK"
    assert state["log_retention_journald"] == "LOG_RETENTION_JOURNALD_PRESENT"
    assert state["log_retention_docker"] == "LOG_RETENTION_DOCKER_PRESENT"
    assert state["log_retention_config"] == "LOG_RETENTION_CONFIG_OK"
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


def test_assess_live_launch_json_verifies_strict_passed_evidence() -> None:
    result = assess_live_launch_json("https://lotfile.app", _passed_live_launch_json())

    assert result["status"] == "verified"
    assert result["evidence"]["live_verifier"] == "passed"
    assert result["evidence"]["missing_count"] == 0
    assert result["evidence"]["live_verifier_json_status"] == "passed"
    assert result["evidence"]["live_verifier_evidence"]["strict"] is True
    assert result["evidence"]["live_verifier_evidence"]["checkout_checked"] is True


def test_assess_live_launch_json_blocks_failed_verifier_evidence() -> None:
    verifier_result = _passed_live_launch_json()
    verifier_result["status"] = "failed"
    verifier_result["failures"] = ["LIVE_CHECKOUT_URL is required for strict live launch verification"]
    verifier_result["evidence"]["checkout_checked"] = False  # type: ignore[index]

    result = assess_live_launch_json("https://lotfile.app", verifier_result)

    assert result["status"] == "blocked"
    assert result["evidence"]["missing_count"] >= 1
    assert "checkout_checked" in result["evidence"]["live_verifier"]


def test_run_live_launch_verifier_uses_only_vps_checkout_env(monkeypatch, tmp_path: Path) -> None:
    seen_env: dict[str, str] = {}

    def fake_run(*args, **kwargs):
        nonlocal seen_env
        seen_env = kwargs["env"]

        class Result:
            returncode = 1
            stdout = json.dumps(
                {
                    "status": "failed",
                    "evidence": {
                        "origin": "https://lotfile.app",
                        "strict": True,
                        "checkout_checked": False,
                        "routes": {},
                        "api": {},
                    },
                    "warnings": [],
                    "failures": ["LIVE_CHECKOUT_URL or VITE_CHECKOUT_URL is required"],
                }
            )
            stderr = ""

        return Result()

    monkeypatch.setenv("LIVE_CHECKOUT_URL", "https://buy.stripe.com/local_should_not_count")
    monkeypatch.setenv("VITE_CHECKOUT_URL", "https://buy.stripe.com/local_should_not_count")
    monkeypatch.setattr("scripts.audit_non_db_launch_ops.subprocess.run", fake_run)

    result = run_live_launch_verifier(
        "https://lotfile.app",
        "VITE_CHECKOUT_URL_MISSING",
        web_dir=tmp_path,
    )

    assert result["status"] == "failed"
    assert "LIVE_CHECKOUT_URL" not in seen_env
    assert "VITE_CHECKOUT_URL" not in seen_env


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
        "disk_usage": "DISK_USAGE_OK",
        "worker_heartbeat": "WORKER_HEARTBEAT_OK",
        "sentry_dsn": "SENTRY_CONFIG_OK",
        "log_retention_journald": "LOG_RETENTION_JOURNALD_PRESENT",
        "log_retention_docker": "LOG_RETENTION_DOCKER_PRESENT",
        "log_retention_config": "LOG_RETENTION_CONFIG_OK",
    }

    report = build_report(
        "https://lotfile.app",
        vps_state,
        pages,
        api,
        bundle_text,
        uptime_monitor_doc="ok: uptime monitor doc records provisioned monitor IDs and alert contacts",
        live_launch_json=_passed_live_launch_json(),
    )

    assert report["launch_surface"]["status"] == "blocked"
    assert report["launch_surface"]["evidence"]["vps_checkout_env"] == "VITE_CHECKOUT_URL_MISSING"
    assert report["ops_guardrails"]["evidence"]["sentry_dsn"] == "SENTRY_CONFIG_OK"
    assert report["ops_guardrails"]["evidence"]["log_retention_journald"] == "LOG_RETENTION_JOURNALD_PRESENT"
    assert report["ops_guardrails"]["evidence"]["log_retention_docker"] == "LOG_RETENTION_DOCKER_PRESENT"
    assert report["ops_guardrails"]["evidence"]["log_retention_config"] == "LOG_RETENTION_CONFIG_OK"
    assert report["ops_guardrails"]["evidence"]["uptime_targets"] == UPTIME_TARGETS_OK
    assert report["ops_guardrails"]["evidence"]["uptime_monitor_doc"].startswith("ok:")
    assert report["ops_guardrails"]["status"] == "blocked"
    unblock = "\n".join(report["ops_guardrails"]["unblock"])
    assert "restore-drill-log" in unblock
    assert "install-sentry-dsn.sh" not in unblock
    assert "install-guardrail-cron.sh" not in unblock
    assert "install-log-retention.sh" not in unblock


def test_build_report_uses_live_launch_json_when_present() -> None:
    api = {
        "/api/v1/health": FetchResult(status=200, text='{"status":"ok"}'),
        "/api/v1/ready": FetchResult(status=200, text='{"status":"ok"}'),
    }
    vps_state = {
        "vps_checkout_env": "https://buy.stripe.com/live_link_123",
        "backup_env": "SSH_SKIPPED",
        "restic_password_file": "SSH_SKIPPED",
        "backup_timer": "SSH_SKIPPED",
        "guardrail_cron": "SSH_SKIPPED",
        "ops_guardrail_script": "SSH_SKIPPED",
        "disk_usage": "SSH_SKIPPED",
        "worker_heartbeat": "SSH_SKIPPED",
        "sentry_dsn": "SSH_SKIPPED",
        "log_retention_journald": "SSH_SKIPPED",
        "log_retention_docker": "SSH_SKIPPED",
        "log_retention_config": "SSH_SKIPPED",
    }

    report = build_report(
        "https://lotfile.app",
        vps_state,
        pages={"/": FetchResult(status=500, text="legacy fetch failed")},
        api=api,
        bundle_text="",
        uptime_monitor_doc="critical: pending monitor evidence",
        live_launch_json=_passed_live_launch_json(),
    )

    assert report["launch_surface"]["status"] == "verified"
    assert report["launch_surface"]["evidence"]["live_verifier_json_status"] == "passed"
    assert report["ops_guardrails"]["status"] == "blocked"


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
        "vps_checkout_env": "https://buy.stripe.com/live_link_123",
        "backup_env": "BACKUP_ENV_PRESENT",
        "restic_password_file": "RESTIC_PASSWORD_FILE_PRESENT",
        "backup_timer": "1 timers listed.",
        "guardrail_cron": "CRON_GUARDRAILS_PRESENT",
        "ops_guardrail_script": "OPS_GUARDRAILS_PRESENT",
        "disk_usage": "DISK_USAGE_OK",
        "worker_heartbeat": "WORKER_HEARTBEAT_OK",
        "sentry_dsn": "SENTRY_CONFIG_OK",
        "log_retention_journald": "LOG_RETENTION_JOURNALD_PRESENT",
        "log_retention_docker": "LOG_RETENTION_DOCKER_PRESENT",
        "log_retention_config": "LOG_RETENTION_CONFIG_OK",
    }

    report = build_report(
        "https://lotfile.app",
        vps_state,
        pages,
        api,
        bundle_text,
        uptime_monitor_doc="ok: uptime monitor doc records provisioned monitor IDs and alert contacts",
        restore_drill_log="ok: restore drill log accepted",
        live_launch_json=_passed_live_launch_json(),
        spend_persistence_evidence=_spend_persistence_ok(),
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
        "disk_usage": "SSH_SKIPPED",
        "worker_heartbeat": "SSH_SKIPPED",
        "sentry_dsn": "SSH_SKIPPED",
        "log_retention_journald": "SSH_SKIPPED",
        "log_retention_docker": "SSH_SKIPPED",
        "log_retention_config": "SSH_SKIPPED",
    }

    report = build_report(
        "https://lotfile.app",
        vps_state,
        pages,
        api,
        bundle_text,
        uptime_monitor_doc="ok: uptime monitor doc records provisioned monitor IDs and alert contacts",
        restore_drill_log="ok: restore drill log accepted",
        live_launch_json=_passed_live_launch_json(),
    )

    assert report["launch_surface"]["status"] == "blocked"
    assert report["ops_guardrails"]["status"] == "blocked"


def test_build_report_blocks_placeholder_checkout_env_even_when_launch_pages_pass() -> None:
    api = {
        "/api/v1/health": FetchResult(status=200, text='{"status":"ok"}'),
        "/api/v1/ready": FetchResult(status=200, text='{"status":"ok"}'),
    }
    vps_state = {
        "vps_checkout_env": "https://buy.stripe.com/test_fixture",
        "backup_env": "SSH_SKIPPED",
        "restic_password_file": "SSH_SKIPPED",
        "backup_timer": "SSH_SKIPPED",
        "guardrail_cron": "SSH_SKIPPED",
        "ops_guardrail_script": "SSH_SKIPPED",
        "disk_usage": "SSH_SKIPPED",
        "worker_heartbeat": "SSH_SKIPPED",
        "sentry_dsn": "SSH_SKIPPED",
        "log_retention_journald": "SSH_SKIPPED",
        "log_retention_docker": "SSH_SKIPPED",
        "log_retention_config": "SSH_SKIPPED",
    }

    report = build_report(
        "https://lotfile.app",
        vps_state,
        pages={"/": FetchResult(status=500, text="legacy fetch failed")},
        api=api,
        bundle_text="",
        uptime_monitor_doc="critical: pending monitor evidence",
        live_launch_json=_passed_live_launch_json(),
    )

    assert report["launch_surface"]["status"] == "blocked"
    assert report["launch_surface"]["evidence"]["vps_checkout_env"] == "https://buy.stripe.com/test_fixture"


def test_main_skip_ssh_writes_blocked_report_without_required_key_crash(monkeypatch, tmp_path: Path) -> None:
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
    output = tmp_path / "non-db-launch-ops.json"

    monkeypatch.setattr("scripts.audit_non_db_launch_ops.collect_live_pages", lambda origin: (pages, bundle_text))
    monkeypatch.setattr("scripts.audit_non_db_launch_ops.collect_api", lambda origin: api)
    monkeypatch.setattr(
        "scripts.audit_non_db_launch_ops.assess_uptime_monitor_doc",
        lambda path: "critical: pending monitor evidence",
    )
    monkeypatch.setattr(
        "scripts.audit_non_db_launch_ops.assess_restore_drill_log",
        lambda path: "critical: no docs/ops/restore-drill-YYYYMMDD.md log found",
    )
    monkeypatch.setattr(
        "scripts.audit_non_db_launch_ops.run_live_launch_verifier",
        lambda origin, checkout_env: {
            "status": "failed",
            "evidence": {
                "origin": origin,
                "strict": True,
                "checkout_checked": False,
                "routes": {},
                "api": {},
            },
            "warnings": [],
            "failures": [f"checkout not verified from VPS: {checkout_env}"],
        },
    )
    monkeypatch.setattr(
        "sys.argv",
        ["audit_non_db_launch_ops.py", "--skip-ssh", "--output", str(output)],
    )

    assert main() == 0
    report = json.loads(output.read_text(encoding="utf-8"))

    assert report["launch_surface"]["status"] == "blocked"
    assert report["ops_guardrails"]["status"] == "blocked"
    assert report["ops_guardrails"]["evidence"]["disk_usage"] == "SSH_SKIPPED"
    assert report["ops_guardrails"]["evidence"]["worker_heartbeat"] == "SSH_SKIPPED"
    assert report["ops_guardrails"]["evidence"]["log_retention_config"] == "SSH_SKIPPED"
    assert validate_audit_report(report) == []


def test_ops_guardrails_status_blocks_pending_fields() -> None:
    evidence = {
        "backup_env": "BACKUP_ENV_PRESENT",
        "restic_password_file": "RESTIC_PASSWORD_FILE_PRESENT",
        "backup_timer": "0 timers listed.",
        "restore_drill_log": "ok: restore drill log accepted",
        "guardrail_cron": "CRON_GUARDRAILS_PRESENT",
        "ops_guardrail_script": "OPS_GUARDRAILS_PRESENT",
        "disk_usage": "DISK_USAGE_OK",
        "worker_heartbeat": "WORKER_HEARTBEAT_OK",
        "sentry_dsn": "SENTRY_CONFIG_OK",
        "uptime_targets": UPTIME_TARGETS_OK,
        "uptime_monitor_doc": "ok: uptime monitor doc records provisioned monitor IDs and alert contacts",
        "spend_persistence": _spend_persistence_ok(),
        "log_retention_journald": "LOG_RETENTION_JOURNALD_PRESENT",
        "log_retention_docker": "LOG_RETENTION_DOCKER_PRESENT",
        "log_retention_config": "LOG_RETENTION_CONFIG_OK",
    }

    assert assess_ops_guardrails_status(evidence) == "blocked"
    evidence["backup_timer"] = "1 timers listed."
    evidence["sentry_dsn"] = "SENTRY_DSN_PRESENT"
    assert assess_ops_guardrails_status(evidence) == "blocked"


def test_spend_persistence_evidence_uses_snapshot_comparison() -> None:
    result = assess_spend_persistence_evidence(
        {
            "job_traces": {"rows": 1, "total_tokens": 100, "cost_cents": 20},
            "spend_events": {"rows": 1, "total_tokens": 100, "cost_cents": 20},
        },
        {
            "job_traces": {"rows": 1, "total_tokens": 90, "cost_cents": 20},
            "spend_events": {"rows": 1, "total_tokens": 100, "cost_cents": 20},
        },
    )

    assert result["status"] == "critical"
    assert "decreased" in result["message"]
    assert result["details"]["decreases"] == ["job_traces.total_tokens: 100 -> 90"]


def test_load_spend_persistence_evidence_reads_offline_snapshots(tmp_path: Path) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text(
        json.dumps(
            {
                "job_traces": {"rows": 1, "total_tokens": 100, "cost_cents": 20},
                "spend_events": {"rows": 1, "total_tokens": 100, "cost_cents": 20},
            }
        ),
        encoding="utf-8",
    )
    after.write_text(
        json.dumps(
            {
                "job_traces": {"rows": 1, "total_tokens": 100, "cost_cents": 20},
                "spend_events": {"rows": 2, "total_tokens": 140, "cost_cents": 25},
            }
        ),
        encoding="utf-8",
    )

    result = load_spend_persistence_evidence(str(before), str(after))

    assert result["status"] == "ok"
    assert result["message"] == "daily spend counters persisted across restart"


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
                "disk_usage": "DISK_USAGE_OK",
                "worker_heartbeat": "WORKER_HEARTBEAT_OK",
                "sentry_dsn": "https://public@example.ingest.sentry.io/123",
                "uptime_targets": UPTIME_TARGETS_OK,
                "uptime_monitor_doc": "ok: uptime monitor doc records provisioned monitor IDs and alert contacts",
                "spend_persistence": _spend_persistence_ok(),
                "log_retention_journald": "LOG_RETENTION_JOURNALD_PRESENT",
                "log_retention_docker": "LOG_RETENTION_DOCKER_PRESENT",
                "log_retention_config": "LOG_RETENTION_CONFIG_OK",
            },
        },
    }

    failures = validate_audit_report(report)

    assert any("raw DSN" in failure for failure in failures)
    assert any("checkout URL" in failure for failure in failures)
    assert any("expected 'blocked'" in failure for failure in failures)


def test_validate_audit_report_rejects_spoofed_ops_evidence() -> None:
    report = {
        "launch_surface": {
            "status": "blocked",
            "evidence": {
                "live_verifier": "passed",
                "missing_count": 0,
                "vps_checkout_env": "VITE_CHECKOUT_URL_MISSING",
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
                "disk_usage": "DISK_USAGE_OK",
                "worker_heartbeat": "WORKER_HEARTBEAT_OK",
                "sentry_dsn": "present, probably",
                "uptime_targets": "status ok",
                "uptime_monitor_doc": "ok: uptime monitor doc records provisioned monitor IDs and alert contacts",
                "spend_persistence": {"status": "probably", "message": "fixture", "source": "fixture"},
                "log_retention_journald": "present",
                "log_retention_docker": "LOG_RETENTION_DOCKER_PRESENT",
                "log_retention_config": "retention exists",
            },
        },
    }

    failures = validate_audit_report(report)

    assert any("sentry_dsn has unrecognized state" in failure for failure in failures)
    assert any("uptime_targets is not recognized verifier output" in failure for failure in failures)
    assert any("spend_persistence has unrecognized status" in failure for failure in failures)
    assert any("log_retention_journald has unrecognized state" in failure for failure in failures)
    assert any("log_retention_config has unrecognized state" in failure for failure in failures)
    assert any("expected 'blocked'" in failure for failure in failures)


def test_validate_audit_report_rejects_spoofed_launch_json_evidence() -> None:
    launch_json = _passed_live_launch_json()
    launch_json["evidence"]["strict"] = False  # type: ignore[index]
    launch_json["evidence"]["checkout_checked"] = False  # type: ignore[index]
    report = {
        "launch_surface": {
            "status": "verified",
            "evidence": {
                **assess_live_launch_json("https://lotfile.app", launch_json)["evidence"],
                "live_verifier": "passed",
                "missing_count": 0,
                "vps_checkout_env": "https://buy.stripe.com/live_link_123",
            },
        },
        "ops_guardrails": {
            "status": "blocked",
            "evidence": {
                "backup_env": "SSH_SKIPPED",
                "restic_password_file": "SSH_SKIPPED",
                "backup_timer": "SSH_SKIPPED",
                "restore_drill_log": "critical: pending",
                "guardrail_cron": "SSH_SKIPPED",
                "ops_guardrail_script": "SSH_SKIPPED",
                "disk_usage": "SSH_SKIPPED",
                "worker_heartbeat": "SSH_SKIPPED",
                "sentry_dsn": "SSH_SKIPPED",
                "uptime_targets": UPTIME_TARGETS_OK,
                "uptime_monitor_doc": "critical: pending monitor evidence",
                "spend_persistence": assess_spend_persistence_evidence(),
                "log_retention_journald": "SSH_SKIPPED",
                "log_retention_docker": "SSH_SKIPPED",
                "log_retention_config": "SSH_SKIPPED",
            },
        },
    }

    failures = validate_audit_report(report)

    assert any("strict JSON verifier evidence" in failure for failure in failures)
    assert any("strict evidence was not true" in failure for failure in failures)
    assert any("checkout_checked evidence was not true" in failure for failure in failures)


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
                "disk_usage": "SSH_SKIPPED",
                "worker_heartbeat": "SSH_SKIPPED",
                "sentry_dsn": "SSH_SKIPPED",
                "uptime_targets": UPTIME_TARGETS_OK,
                "uptime_monitor_doc": "critical: pending monitor evidence",
                "spend_persistence": assess_spend_persistence_evidence(),
                "log_retention_journald": "SSH_SKIPPED",
                "log_retention_docker": "SSH_SKIPPED",
                "log_retention_config": "SSH_SKIPPED",
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
