"""Read-only launch and ops blocker audit for non-DB go-live work."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

try:
    from scripts.ops_guardrails import check_restore_drill_log, check_uptime_monitor_doc
except ModuleNotFoundError:  # pragma: no cover - direct `python scripts/...` execution
    from ops_guardrails import check_restore_drill_log, check_uptime_monitor_doc


LAUNCH_ROUTES = ("/", "/privacy", "/terms", "/app")
API_ROUTES = ("/api/v1/health", "/api/v1/ready")
LIVE_NEEDLES = (
    "LotFile - WA R-Code & Planning Compliance Checker",
    'name="description"',
    'property="og:title"',
    'data-domain="lotfile.app"',
)
BUNDLE_NEEDLES = (
    "/privacy",
    "/terms",
    "Check an address free",
    "Advisory research only",
    "signup_requested",
    "project_created",
    "compliance_run",
    "checkout_clicked",
    "AUD $29/month",
)
REQUIRED_OPS_EVIDENCE_KEYS = (
    "backup_env",
    "restic_password_file",
    "backup_timer",
    "restore_drill_log",
    "guardrail_cron",
    "ops_guardrail_script",
    "sentry_dsn",
    "uptime_targets",
    "uptime_monitor_doc",
    "log_retention_journald",
    "log_retention_docker",
    "log_retention_config",
)
RESTORE_TEMPLATE_NEEDLES = (
    "python scripts/ops_guardrails.py restore-drill-log --path docs/ops/restore-drill-YYYYMMDD.md --json",
    "dump_size_bytes:",
    "storage_path:",
    "storage_file_count:",
    "storage_size_bytes:",
    "storage_manifest_sha256:",
    "source_versions:",
    "job_traces:",
    "status: PASS / FAIL",
)
RUNBOOK_COMMAND_NEEDLES = (
    "sentry-config",
    "log-retention-config",
    "uptime-monitor-doc",
    "restore-drill-log",
    "--verify-report",
)
RAW_DSN_RE = re.compile(r"https://[^\s\"']+@[^\s\"']+", flags=re.IGNORECASE)
BLOCKED_EVIDENCE_VALUES = {"SSH_SKIPPED", "SSH_CHECK_FAILED"}


@dataclass(frozen=True)
class FetchResult:
    status: int
    text: str


def fetch_text(url: str, *, timeout_seconds: float = 20.0) -> FetchResult:
    try:
        with urlopen(url, timeout=timeout_seconds) as response:  # noqa: S310 - fixed/operator-supplied launch URL
            return FetchResult(
                status=response.status,
                text=response.read(5_000_000).decode("utf-8", errors="replace"),
            )
    except HTTPError as exc:
        body = exc.read(100_000).decode("utf-8", errors="replace")
        return FetchResult(status=exc.code, text=body)
    except (OSError, URLError) as exc:
        return FetchResult(status=0, text=str(exc))


def _asset_paths(index_html: str) -> list[str]:
    return sorted({match.group(0) for match in re.finditer(r"assets/[^\"']+\.js", index_html)})


def assess_live_launch(origin: str, pages: dict[str, FetchResult], bundle_text: str) -> dict[str, Any]:
    missing: list[str] = []
    for route in LAUNCH_ROUTES:
        page = pages.get(route)
        if page is None:
            missing.append(f"{route}: not fetched")
            continue
        if page.status != 200:
            missing.append(f"{route}: HTTP {page.status}")
        for needle in LIVE_NEEDLES:
            if needle not in page.text:
                missing.append(f"{route}: missing {needle}")
    for needle in BUNDLE_NEEDLES:
        if needle not in bundle_text:
            missing.append(f"bundle: missing {needle}")
    status = "blocked" if missing else "verified"
    return {
        "status": status,
        "evidence": {
            "live_origin": origin,
            "live_index_title": _title_of(pages.get("/", FetchResult(status=0, text="")).text),
            "live_verifier": "passed" if not missing else "failed: " + "; ".join(missing[:12]),
            "missing_count": len(missing),
        },
    }


def _title_of(html: str) -> str:
    match = re.search(r"<title>.*?</title>", html, flags=re.IGNORECASE | re.DOTALL)
    return match.group(0).strip() if match else "TITLE_MISSING"


def assess_api_targets(origin: str, responses: dict[str, FetchResult]) -> str:
    failures: list[str] = []
    for route in API_ROUTES:
        response = responses.get(route)
        if response is None:
            failures.append(f"{route}: not fetched")
            continue
        if response.status != 200:
            failures.append(f"{route}: HTTP {response.status}")
            continue
        try:
            body = json.loads(response.text)
        except json.JSONDecodeError as exc:
            failures.append(f"{route}: invalid JSON {exc}")
            continue
        if body.get("status") != "ok":
            failures.append(f"{route}: status={body.get('status')!r}")
    if failures:
        return f"{origin} API targets failed: " + "; ".join(failures)
    return "uv run python scripts/ops_guardrails.py uptime-targets --json returned status ok for lotfile.app health and ready"


def assess_uptime_monitor_doc(path: Path) -> str:
    result = check_uptime_monitor_doc(path)
    return f"{result.status}: {result.message}"


def assess_restore_drill_log(ops_doc_dir: Path) -> str:
    candidates = sorted(
        path for path in ops_doc_dir.glob("restore-drill-[0-9]*.md") if path.is_file()
    )
    if not candidates:
        return "critical: no docs/ops/restore-drill-YYYYMMDD.md log found"
    latest = candidates[-1]
    result = check_restore_drill_log(latest)
    return f"{result.status}: {result.message}"


def _checkout_env_verified(value: str) -> bool:
    return value.startswith("https://buy.stripe.com/")


def _timer_verified(value: str) -> bool:
    blocked_needles = (
        "0 timers listed",
        "SSH_CHECK_FAILED",
        "SSH_SKIPPED",
        "unknown",
    )
    return bool(value) and not any(needle in value for needle in blocked_needles)


def _field_present(value: str, expected: str) -> bool:
    return value == expected


def assess_launch_status(launch: dict[str, Any], checkout_env: str) -> str:
    if launch["status"] != "verified":
        return "blocked"
    if not _checkout_env_verified(checkout_env):
        return "blocked"
    return "verified"


def assess_ops_guardrails_status(evidence: dict[str, str]) -> str:
    required = (
        _field_present(evidence["backup_env"], "BACKUP_ENV_PRESENT"),
        _field_present(evidence["restic_password_file"], "RESTIC_PASSWORD_FILE_PRESENT"),
        _timer_verified(evidence["backup_timer"]),
        evidence["restore_drill_log"].startswith("ok:"),
        _field_present(evidence["guardrail_cron"], "CRON_GUARDRAILS_PRESENT"),
        _field_present(evidence["ops_guardrail_script"], "OPS_GUARDRAILS_PRESENT"),
        _field_present(evidence["sentry_dsn"], "SENTRY_DSN_PRESENT"),
        "status ok" in evidence["uptime_targets"],
        evidence["uptime_monitor_doc"].startswith("ok:"),
        _field_present(evidence["log_retention_journald"], "LOG_RETENTION_JOURNALD_PRESENT"),
        _field_present(evidence["log_retention_docker"], "LOG_RETENTION_DOCKER_PRESENT"),
    )
    return "verified" if all(required) else "blocked"


def launch_unblock_steps(launch: dict[str, Any], checkout_env: str) -> list[str]:
    steps: list[str] = []
    if not _checkout_env_verified(checkout_env):
        steps.append(
            "Set a real Stripe Payment Link in /srv/draftcheck/app/infra/v3/.env as VITE_CHECKOUT_URL=https://buy.stripe.com/..."
        )
    if launch["status"] != "verified" or steps:
        steps.append("Deploy the web bundle with: ssh draftcheck 'bash /srv/draftcheck/app/infra/v3/deploy-web-only.sh'")
        steps.append("Run: cd web && npm run verify:launch:live:strict")
    return steps


def ops_guardrail_unblock_steps(evidence: dict[str, str]) -> list[str]:
    steps: list[str] = []
    if not _field_present(evidence["ops_guardrail_script"], "OPS_GUARDRAILS_PRESENT"):
        steps.append(
            "Deploy latest non-DB ops scripts after DB jobs are idle so /srv/draftcheck/app/scripts/ops_guardrails.py is present."
        )
    if not _field_present(evidence["backup_env"], "BACKUP_ENV_PRESENT") or not _field_present(
        evidence["restic_password_file"], "RESTIC_PASSWORD_FILE_PRESENT"
    ):
        steps.append(
            "Provision RESTIC_REPOSITORY and RESTIC_PASSWORD_FILE outside git, then run the backup.env setup command in docs/ops/ops-guardrails.md."
        )
    if not _timer_verified(evidence["backup_timer"]):
        steps.append("Run: sudo bash /srv/draftcheck/app/infra/v3/backup/install-systemd.sh")
    if not evidence["restore_drill_log"].startswith("ok:"):
        steps.append(
            "Run the restore drill and verify the filled log with: python scripts/ops_guardrails.py restore-drill-log --path docs/ops/restore-drill-YYYYMMDD.md --json"
        )
    if not _field_present(evidence["guardrail_cron"], "CRON_GUARDRAILS_PRESENT"):
        steps.append("Run: sudo bash /srv/draftcheck/app/infra/v3/ops/install-guardrail-cron.sh")
    if not evidence["uptime_monitor_doc"].startswith("ok:"):
        steps.append("Provision the external uptime monitors and replace pending values in docs/ops/uptime-monitor.md.")
    if not _field_present(evidence["sentry_dsn"], "SENTRY_DSN_PRESENT"):
        steps.append(
            "Run: sudo SENTRY_DSN=<dsn> bash /srv/draftcheck/app/infra/v3/ops/install-sentry-dsn.sh, then rerun with DRAFTCHECK_RESTART_SERVICES=1 when api/worker/hermes can restart."
        )
    if not (
        _field_present(evidence["log_retention_journald"], "LOG_RETENTION_JOURNALD_PRESENT")
        and _field_present(evidence["log_retention_docker"], "LOG_RETENTION_DOCKER_PRESENT")
    ):
        steps.append(
            "Run: sudo bash /srv/draftcheck/app/infra/v3/ops/install-log-retention.sh, then rerun with DRAFTCHECK_RESTART_DOCKER=1 during a maintenance window."
        )
    return steps


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _report_text(report: dict[str, Any]) -> str:
    return json.dumps(report, sort_keys=True)


def validate_audit_report(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    launch = report.get("launch_surface", {})
    launch_evidence = launch.get("evidence", {})
    ops = report.get("ops_guardrails", {})
    ops_evidence = ops.get("evidence", {})

    if not isinstance(launch, dict) or not isinstance(launch_evidence, dict):
        failures.append("launch_surface.evidence missing or malformed")
    if not isinstance(ops, dict) or not isinstance(ops_evidence, dict):
        failures.append("ops_guardrails.evidence missing or malformed")
        return failures

    missing_ops_keys = [key for key in REQUIRED_OPS_EVIDENCE_KEYS if key not in ops_evidence]
    if missing_ops_keys:
        failures.append("ops_guardrails.evidence missing keys: " + ", ".join(missing_ops_keys))

    if RAW_DSN_RE.search(_report_text(report)):
        failures.append("report appears to contain a raw DSN or webhook URL with embedded credentials")

    if launch.get("status") == "verified":
        if launch_evidence.get("live_verifier") != "passed":
            failures.append("launch_surface.status verified but live_verifier is not passed")
        if _safe_int(launch_evidence.get("missing_count"), default=1) != 0:
            failures.append("launch_surface.status verified but missing_count is non-zero")
        if not _checkout_env_verified(str(launch_evidence.get("vps_checkout_env", ""))):
            failures.append("launch_surface.status verified without a buy.stripe.com checkout URL")

    if not missing_ops_keys:
        status_evidence = {
            key: str(ops_evidence.get(key, ""))
            for key in REQUIRED_OPS_EVIDENCE_KEYS
            if key != "log_retention_config"
        }
        expected_ops_status = assess_ops_guardrails_status(status_evidence)
        if ops.get("status") != expected_ops_status:
            failures.append(
                f"ops_guardrails.status is {ops.get('status')!r}, expected {expected_ops_status!r} from evidence"
            )

    if ops.get("status") == "verified" and any(
        str(value) in BLOCKED_EVIDENCE_VALUES for value in ops_evidence.values()
    ):
        failures.append("ops_guardrails.status verified with skipped or failed SSH evidence")

    return failures


def validate_restore_drill_template(path: Path) -> list[str]:
    if not path.exists():
        return [f"restore drill template missing: {path}"]
    text = path.read_text(encoding="utf-8")
    return [f"restore drill template missing {needle}" for needle in RESTORE_TEMPLATE_NEEDLES if needle not in text]


def validate_ops_runbook(path: Path) -> list[str]:
    if not path.exists():
        return [f"ops runbook missing: {path}"]
    text = path.read_text(encoding="utf-8")
    return [f"ops runbook missing {needle}" for needle in RUNBOOK_COMMAND_NEEDLES if needle not in text]


def verify_report_artifact(report_path: Path, *, restore_template: Path, ops_runbook: Path) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    failures = [
        *validate_audit_report(report),
        *validate_restore_drill_template(restore_template),
        *validate_ops_runbook(ops_runbook),
    ]
    return {
        "status": "ok" if not failures else "critical",
        "report_path": str(report_path),
        "restore_template": str(restore_template),
        "ops_runbook": str(ops_runbook),
        "failures": failures,
    }


def parse_vps_state(output: str) -> dict[str, str]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    checkout_line = next((line for line in lines if line.startswith("VITE_CHECKOUT_URL=")), "")
    checkout_value = checkout_line.split("=", 1)[1] if checkout_line else ""
    timer_lines = [line for line in lines if "timers listed" in line]
    sentry_lines = [line for line in lines if line.startswith("SENTRY_DSN_")]
    journald_lines = [line for line in lines if line.startswith("LOG_RETENTION_JOURNALD_")]
    docker_log_lines = [line for line in lines if line.startswith("LOG_RETENTION_DOCKER_")]
    return {
        "vps_checkout_env": checkout_value or "VITE_CHECKOUT_URL_MISSING",
        "backup_env": "BACKUP_ENV_PRESENT" if "BACKUP_ENV_PRESENT" in lines else "BACKUP_ENV_MISSING",
        "restic_password_file": "RESTIC_PASSWORD_FILE_PRESENT"
        if "RESTIC_PASSWORD_FILE_PRESENT" in lines
        else "RESTIC_PASSWORD_FILE_MISSING",
        "backup_timer": timer_lines[0] if timer_lines else "draftcheck-backup.timer status unknown",
        "guardrail_cron": "CRON_GUARDRAILS_PRESENT" if "CRON_GUARDRAILS_PRESENT" in lines else "CRON_GUARDRAILS_MISSING",
        "ops_guardrail_script": "OPS_GUARDRAILS_PRESENT" if "OPS_GUARDRAILS_PRESENT" in lines else "OPS_GUARDRAILS_MISSING",
        "sentry_dsn": sentry_lines[-1] if sentry_lines else "SENTRY_DSN_MISSING",
        "log_retention_journald": journald_lines[-1] if journald_lines else "LOG_RETENTION_JOURNALD_MISSING",
        "log_retention_docker": docker_log_lines[-1] if docker_log_lines else "LOG_RETENTION_DOCKER_MISSING",
    }


def collect_vps_state(host: str, *, timeout_seconds: int = 30) -> dict[str, str]:
    remote = r"""
set -e
test -f /srv/draftcheck/app/infra/v3/.env && (grep -E '^VITE_CHECKOUT_URL=' /srv/draftcheck/app/infra/v3/.env || true)
test -f /etc/draftcheck/backup.env && echo BACKUP_ENV_PRESENT || echo BACKUP_ENV_MISSING
if test -f /etc/draftcheck/backup.env; then
  password_file="$(grep -E '^RESTIC_PASSWORD_FILE=' /etc/draftcheck/backup.env | cut -d= -f2- || true)"
  test -n "$password_file" && test -f "$password_file" && echo RESTIC_PASSWORD_FILE_PRESENT || echo RESTIC_PASSWORD_FILE_MISSING
else
  echo RESTIC_PASSWORD_FILE_MISSING
fi
test -f /etc/cron.d/draftcheck-guardrails && echo CRON_GUARDRAILS_PRESENT || echo CRON_GUARDRAILS_MISSING
systemctl list-timers --all draftcheck-backup.timer --no-pager 2>/dev/null || true
test -f /srv/draftcheck/app/scripts/ops_guardrails.py && echo OPS_GUARDRAILS_PRESENT || echo OPS_GUARDRAILS_MISSING
if test -f /srv/draftcheck/app/infra/v3/.env && grep -q '^SENTRY_DSN=' /srv/draftcheck/app/infra/v3/.env; then
  sentry_dsn="$(grep -E '^SENTRY_DSN=' /srv/draftcheck/app/infra/v3/.env | tail -n 1 | cut -d= -f2-)"
  test -n "$sentry_dsn" && echo SENTRY_DSN_PRESENT || echo SENTRY_DSN_EMPTY
else
  echo SENTRY_DSN_MISSING
fi
test -f /etc/systemd/journald.conf.d/draftcheck.conf && echo LOG_RETENTION_JOURNALD_PRESENT || echo LOG_RETENTION_JOURNALD_MISSING
test -f /etc/docker/daemon.json && echo LOG_RETENTION_DOCKER_PRESENT || echo LOG_RETENTION_DOCKER_MISSING
"""
    result = subprocess.run(
        ["ssh", host, remote],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if result.returncode != 0:
        return {
            "vps_checkout_env": "SSH_CHECK_FAILED",
            "backup_env": "SSH_CHECK_FAILED",
            "restic_password_file": "SSH_CHECK_FAILED",
            "backup_timer": result.stderr.strip() or "SSH_CHECK_FAILED",
            "guardrail_cron": "SSH_CHECK_FAILED",
            "ops_guardrail_script": "SSH_CHECK_FAILED",
            "sentry_dsn": "SSH_CHECK_FAILED",
            "log_retention_journald": "SSH_CHECK_FAILED",
            "log_retention_docker": "SSH_CHECK_FAILED",
        }
    return parse_vps_state(result.stdout)


def build_report(
    origin: str,
    vps_state: dict[str, str],
    pages: dict[str, FetchResult],
    api: dict[str, FetchResult],
    bundle_text: str,
    *,
    uptime_monitor_doc: str,
    restore_drill_log: str = "critical: no docs/ops/restore-drill-YYYYMMDD.md log found",
) -> dict[str, Any]:
    launch = assess_live_launch(origin, pages, bundle_text)
    launch["evidence"]["vps_checkout_env"] = vps_state["vps_checkout_env"]
    launch["status"] = assess_launch_status(launch, vps_state["vps_checkout_env"])

    ops_evidence = {
        "backup_env": vps_state["backup_env"],
        "restic_password_file": vps_state["restic_password_file"],
        "backup_timer": vps_state["backup_timer"],
        "restore_drill_log": restore_drill_log,
        "guardrail_cron": vps_state["guardrail_cron"],
        "ops_guardrail_script": vps_state["ops_guardrail_script"],
        "sentry_dsn": vps_state["sentry_dsn"],
        "uptime_targets": assess_api_targets(origin, api),
        "uptime_monitor_doc": uptime_monitor_doc,
        "log_retention_journald": vps_state["log_retention_journald"],
        "log_retention_docker": vps_state["log_retention_docker"],
        "log_retention_config": "journald and Docker json-file retention configs are committed; VPS install is pending a maintenance window because restarting Docker can interrupt running jobs",
    }

    return {
        "captured_at": datetime.now(tz=UTC).isoformat(),
        "scope": "non-db, non-security go-live blockers",
        "launch_surface": {
            **launch,
            "unblock": launch_unblock_steps(launch, vps_state["vps_checkout_env"]),
        },
        "ops_guardrails": {
            "status": assess_ops_guardrails_status(ops_evidence),
            "evidence": ops_evidence,
            "unblock": ops_guardrail_unblock_steps(ops_evidence),
        },
    }


def collect_live_pages(origin: str) -> tuple[dict[str, FetchResult], str]:
    pages = {route: fetch_text(f"{origin}{route}") for route in LAUNCH_ROUTES}
    root = pages.get("/")
    bundle_parts: list[str] = []
    if root is not None:
        for asset in _asset_paths(root.text):
            bundle_parts.append(fetch_text(f"{origin}/{asset}").text)
    return pages, "\n".join(bundle_parts)


def collect_api(origin: str) -> dict[str, FetchResult]:
    return {route: fetch_text(f"{origin}{route}") for route in API_ROUTES}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default="https://lotfile.app")
    parser.add_argument("--ssh-host", default="draftcheck")
    parser.add_argument("--output", default="reports/non_db_launch_ops_blockers.json")
    parser.add_argument("--uptime-monitor-doc", default="docs/ops/uptime-monitor.md")
    parser.add_argument("--ops-doc-dir", default="docs/ops")
    parser.add_argument("--skip-ssh", action="store_true")
    parser.add_argument("--verify-report", default="")
    parser.add_argument("--restore-template", default="docs/ops/restore-drill-template.md")
    parser.add_argument("--ops-runbook", default="docs/ops/ops-guardrails.md")
    args = parser.parse_args()

    if args.verify_report:
        verification = verify_report_artifact(
            Path(args.verify_report),
            restore_template=Path(args.restore_template),
            ops_runbook=Path(args.ops_runbook),
        )
        print(json.dumps(verification, sort_keys=True))
        return 0 if verification["status"] == "ok" else 2

    origin = args.origin.rstrip("/")
    pages, bundle_text = collect_live_pages(origin)
    api = collect_api(origin)
    vps_state = (
        {
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
        if args.skip_ssh
        else collect_vps_state(args.ssh_host)
    )
    report = build_report(
        origin,
        vps_state,
        pages,
        api,
        bundle_text,
        uptime_monitor_doc=assess_uptime_monitor_doc(Path(args.uptime_monitor_doc)),
        restore_drill_log=assess_restore_drill_log(Path(args.ops_doc_dir)),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
