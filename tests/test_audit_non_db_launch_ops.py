from __future__ import annotations

from scripts.audit_non_db_launch_ops import FetchResult, assess_live_launch, build_report, parse_vps_state


def test_parse_vps_state_extracts_missing_ops_state() -> None:
    output = """
BACKUP_ENV_MISSING
RESTIC_PASSWORD_FILE_MISSING
CRON_GUARDRAILS_MISSING
0 timers listed.
OPS_GUARDRAILS_MISSING
SENTRY_DSN_MISSING
"""

    state = parse_vps_state(output)

    assert state["vps_checkout_env"] == "VITE_CHECKOUT_URL_MISSING"
    assert state["backup_env"] == "BACKUP_ENV_MISSING"
    assert state["restic_password_file"] == "RESTIC_PASSWORD_FILE_MISSING"
    assert state["backup_timer"] == "0 timers listed."
    assert state["guardrail_cron"] == "CRON_GUARDRAILS_MISSING"
    assert state["ops_guardrail_script"] == "OPS_GUARDRAILS_MISSING"
    assert state["sentry_dsn"] == "SENTRY_DSN_MISSING"


def test_parse_vps_state_records_sentry_presence_without_value() -> None:
    output = """
VITE_CHECKOUT_URL=https://buy.stripe.com/test_fixture
BACKUP_ENV_PRESENT
RESTIC_PASSWORD_FILE_PRESENT
CRON_GUARDRAILS_PRESENT
1 timers listed.
OPS_GUARDRAILS_PRESENT
SENTRY_DSN_PRESENT
"""

    state = parse_vps_state(output)

    assert state["sentry_dsn"] == "SENTRY_DSN_PRESENT"
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
    }

    report = build_report("https://lotfile.app", vps_state, pages, api, bundle_text)

    assert report["launch_surface"]["status"] == "blocked"
    assert report["launch_surface"]["evidence"]["vps_checkout_env"] == "VITE_CHECKOUT_URL_MISSING"
    assert report["ops_guardrails"]["evidence"]["sentry_dsn"] == "SENTRY_DSN_PRESENT"
    assert "status ok" in report["ops_guardrails"]["evidence"]["uptime_targets"]
