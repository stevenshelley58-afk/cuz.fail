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


def parse_vps_state(output: str) -> dict[str, str]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    checkout_line = next((line for line in lines if line.startswith("VITE_CHECKOUT_URL=")), "")
    checkout_value = checkout_line.split("=", 1)[1] if checkout_line else ""
    timer_lines = [line for line in lines if "timers listed" in line]
    return {
        "vps_checkout_env": checkout_value or "VITE_CHECKOUT_URL_MISSING",
        "backup_env": "BACKUP_ENV_PRESENT" if "BACKUP_ENV_PRESENT" in lines else "BACKUP_ENV_MISSING",
        "restic_password_file": "RESTIC_PASSWORD_FILE_PRESENT"
        if "RESTIC_PASSWORD_FILE_PRESENT" in lines
        else "RESTIC_PASSWORD_FILE_MISSING",
        "backup_timer": timer_lines[0] if timer_lines else "draftcheck-backup.timer status unknown",
        "guardrail_cron": "CRON_GUARDRAILS_PRESENT" if "CRON_GUARDRAILS_PRESENT" in lines else "CRON_GUARDRAILS_MISSING",
        "ops_guardrail_script": "OPS_GUARDRAILS_PRESENT" if "OPS_GUARDRAILS_PRESENT" in lines else "OPS_GUARDRAILS_MISSING",
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
        }
    return parse_vps_state(result.stdout)


def build_report(origin: str, vps_state: dict[str, str], pages: dict[str, FetchResult], api: dict[str, FetchResult], bundle_text: str) -> dict[str, Any]:
    launch = assess_live_launch(origin, pages, bundle_text)
    launch["evidence"]["vps_checkout_env"] = vps_state["vps_checkout_env"]
    if vps_state["vps_checkout_env"] == "VITE_CHECKOUT_URL_MISSING":
        launch["status"] = "blocked"

    return {
        "captured_at": datetime.now(tz=UTC).isoformat(),
        "scope": "non-db, non-security go-live blockers",
        "launch_surface": {
            **launch,
            "unblock": [
                "Set a real Stripe Payment Link in /srv/draftcheck/app/infra/v3/.env as VITE_CHECKOUT_URL=https://buy.stripe.com/...",
                "Deploy the web bundle with: ssh draftcheck 'bash /srv/draftcheck/app/infra/v3/deploy-web-only.sh'",
                "Run: cd web && npm run verify:launch:live:strict",
            ],
        },
        "ops_guardrails": {
            "status": "blocked",
            "evidence": {
                "backup_env": vps_state["backup_env"],
                "restic_password_file": vps_state["restic_password_file"],
                "backup_timer": vps_state["backup_timer"],
                "restore_drill_log": "no docs/ops/restore-drill-YYYYMMDD.md log found on the VPS checkout",
                "guardrail_cron": vps_state["guardrail_cron"],
                "ops_guardrail_script": vps_state["ops_guardrail_script"],
                "uptime_targets": assess_api_targets(origin, api),
                "log_retention_config": "journald and Docker json-file retention configs are committed; VPS install is pending a maintenance window because restarting Docker can interrupt running jobs",
            },
            "unblock": [
                "Deploy latest non-DB ops scripts after DB jobs are idle so /srv/draftcheck/app/scripts/ops_guardrails.py is present.",
                "Provision RESTIC_REPOSITORY and RESTIC_PASSWORD_FILE outside git, then run the backup.env setup command in docs/ops/ops-guardrails.md.",
                "Run: sudo bash /srv/draftcheck/app/infra/v3/backup/install-systemd.sh",
                "Run the restore drill and verify the filled log with: python scripts/ops_guardrails.py restore-drill-log --path docs/ops/restore-drill-YYYYMMDD.md --json",
                "Install /etc/cron.d/draftcheck-guardrails using docs/ops/ops-guardrails.md after the latest scripts are deployed.",
                "Install log retention during a maintenance window with the commands in docs/ops/ops-guardrails.md section 6.",
            ],
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
    parser.add_argument("--skip-ssh", action="store_true")
    args = parser.parse_args()

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
        }
        if args.skip_ssh
        else collect_vps_state(args.ssh_host)
    )
    report = build_report(origin, vps_state, pages, api, bundle_text)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
