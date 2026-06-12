# LotFile V3 Ops Guardrails

Scope: non-security go-live guardrails for backups, restore evidence, uptime
checks, alerts, Sentry wiring, log retention, and spend persistence. Do not put
real secrets in this repo.

## 1. Arm backups

Backups need an off-site restic repository before the timer can be armed.

One-command unblock from local PowerShell, with values supplied from the
operator shell:

```powershell
$env:RESTIC_REPOSITORY='s3:s3.example.invalid/draftcheck-v3-backups'; $env:RESTIC_PASSWORD='<generated-restic-password>'; ssh draftcheck "sudo install -d -m 700 /etc/draftcheck && printf '%s\n' '$env:RESTIC_PASSWORD' | sudo tee /etc/draftcheck/restic-password >/dev/null && sudo chmod 600 /etc/draftcheck/restic-password && sudo tee /etc/draftcheck/backup.env >/dev/null <<'EOF'
RESTIC_REPOSITORY=$env:RESTIC_REPOSITORY
RESTIC_PASSWORD_FILE=/etc/draftcheck/restic-password
POSTGRES_USER=draftcheck
POSTGRES_DB=draftcheck
COMPOSE_FILE=/srv/draftcheck/app/infra/v3/compose.yml
EOF
sudo bash /srv/draftcheck/app/infra/v3/backup/install-systemd.sh"
```

Verify:

```powershell
ssh draftcheck 'python3 /srv/draftcheck/app/scripts/ops_guardrails.py backup-config --env-path /etc/draftcheck/backup.env --json'
ssh draftcheck 'sudo systemctl status draftcheck-backup.timer --no-pager && sudo systemctl list-timers --all draftcheck-backup.timer'
```

Run the first backup manually:

```powershell
ssh draftcheck 'sudo systemctl start draftcheck-backup.service && sudo journalctl -u draftcheck-backup.service -n 80 --no-pager'
```

## 2. Restore drill evidence

Run monthly after a successful backup:

```powershell
ssh draftcheck 'cd /srv/draftcheck/app && sudo bash infra/v3/backup/restore-drill.sh' > docs/ops/restore-drill-$(Get-Date -Format yyyyMMdd).md
```

Verify the filled log before committing it:

```powershell
python scripts/ops_guardrails.py restore-drill-log --path docs/ops/restore-drill-YYYYMMDD.md --json
```

Commit the filled restore drill log only if it contains `status: PASS`. If
restic credentials are missing, record this blocker:

```text
BLOCKED: off-site backups pending RESTIC_REPOSITORY and RESTIC_PASSWORD_FILE.
Unblock: run the one-command backup.env setup in docs/ops/ops-guardrails.md.
```

## 3. Backup freshness and alert cron

Local dry run against a repo fixture or the VPS backup directory:

```powershell
python scripts/ops_guardrails.py backup-freshness --backup-dir C:\path\to\backups --json
ssh draftcheck 'python3 /srv/draftcheck/app/scripts/ops_guardrails.py backup-freshness --backup-dir /srv/draftcheck/backups --json'
```

Disk usage alert dry runs use the same Python guardrail as the cron wrapper:

```powershell
python scripts/ops_guardrails.py disk-usage --path . --max-used-percent 100 --json
ssh draftcheck 'python3 /srv/draftcheck/app/scripts/ops_guardrails.py disk-usage --path /srv --path /var/lib/docker --max-used-percent 80 --json'
```

Worker heartbeat checks can be tested locally without Docker by injecting the
running service names; the VPS command reads Docker Compose directly:

```powershell
python scripts/ops_guardrails.py worker-heartbeat --running-service worker --running-service hermes --json
ssh draftcheck 'python3 /srv/draftcheck/app/scripts/ops_guardrails.py worker-heartbeat --compose-dir /srv/draftcheck/app/infra/v3 --json'
```

Install the checked cron entry on the VPS:

```powershell
ssh draftcheck 'sudo bash /srv/draftcheck/app/infra/v3/ops/install-guardrail-cron.sh'
```

Verify the installed cron entry before relying on it:

```powershell
ssh draftcheck 'python3 /srv/draftcheck/app/scripts/ops_guardrails.py guardrail-cron --path /etc/cron.d/draftcheck-guardrails --json'
```

Optional webhook setup, without committing the URL:

```powershell
$env:DRAFTCHECK_ALERT_WEBHOOK_URL='https://hooks.example.invalid/...'; ssh draftcheck "sudo install -d -m 700 /etc/draftcheck && sudo tee /etc/draftcheck/ops-alerts.env >/dev/null <<EOF
DRAFTCHECK_ALERT_WEBHOOK_URL=$env:DRAFTCHECK_ALERT_WEBHOOK_URL
EOF
sudo chmod 600 /etc/draftcheck/ops-alerts.env"
```

If the webhook is missing, the cron still logs failures locally and exits
non-zero.

## 4. Uptime monitor checklist

External monitor targets:

- `https://lotfile.app/api/v1/health` with body keyword `"status":"ok"`
- `https://lotfile.app/api/v1/ready` with body keyword `"status":"ok"`

Repo-local verification uses the same status contract and exits non-zero if
either target is not JSON or does not return `status: ok`:

```powershell
python scripts/ops_guardrails.py uptime-targets --json
ssh draftcheck 'python3 /srv/draftcheck/app/scripts/ops_guardrails.py uptime-targets --json'
```

Record monitor IDs in `docs/ops/uptime-monitor.md` after provisioning. If the
third-party monitor account is not available, leave this blocker:

```text
BLOCKED: uptime monitor pending UptimeRobot (or equivalent) credentials.
Unblock: create the two HTTPS keyword monitors listed in docs/ops/uptime-monitor.md.
```

After the monitor IDs are recorded, verify the committed evidence:

```powershell
python scripts/ops_guardrails.py uptime-monitor-doc --path docs/ops/uptime-monitor.md --json
```

## 5. Sentry or equivalent

Code already reads `SENTRY_DSN` for api, worker, and hermes. Provision the DSN
outside the repo and write it only to the VPS compose env:

```powershell
$env:SENTRY_DSN='https://examplePublicKey@o0.ingest.sentry.io/0'; ssh draftcheck "cd /srv/draftcheck/app/infra/v3 && grep -q '^SENTRY_DSN=' .env && sudo sed -i 's|^SENTRY_DSN=.*|SENTRY_DSN=$env:SENTRY_DSN|' .env || printf '\nSENTRY_DSN=%s\n' '$env:SENTRY_DSN' | sudo tee -a .env >/dev/null && sudo docker compose up -d api worker hermes"
```

Verify the env and compose wiring without printing the DSN:

```powershell
ssh draftcheck 'python3 /srv/draftcheck/app/scripts/ops_guardrails.py sentry-config --env-path /srv/draftcheck/app/infra/v3/.env --compose-path /srv/draftcheck/app/infra/v3/compose.yml --json'
```

If no DSN is available:

```text
BLOCKED: error reporting pending SENTRY_DSN.
Unblock: set SENTRY_DSN in /srv/draftcheck/app/infra/v3/.env and restart api worker hermes.
```

## 6. Log retention

Install the checked journald and Docker log-retention configs:
the script copies `infra/v3/ops/journald-draftcheck.conf` and
`infra/v3/ops/docker-daemon-log-rotation.json`, then validates the installed
targets with `log-retention-config`.

```powershell
ssh draftcheck 'sudo bash /srv/draftcheck/app/infra/v3/ops/install-log-retention.sh'
```

The default command does not restart Docker. During the maintenance window, apply
the Docker daemon config to running containers:

```powershell
ssh draftcheck 'sudo DRAFTCHECK_RESTART_DOCKER=1 bash /srv/draftcheck/app/infra/v3/ops/install-log-retention.sh'
```

This restarts Docker, so run it during a maintenance window and verify the stack after:

```powershell
ssh draftcheck 'cd /srv/draftcheck/app/infra/v3 && sudo docker compose ps'
```

Verify the installed retention files before closing the blocker:

```powershell
ssh draftcheck 'python3 /srv/draftcheck/app/scripts/ops_guardrails.py log-retention-config --journald-path /etc/systemd/journald.conf.d/draftcheck.conf --docker-daemon-path /etc/docker/daemon.json --json'
```

## 7. Audit artifact verification

After refreshing `reports/non_db_launch_ops_blockers.json`, verify the report,
restore-drill template, and runbook contract locally before using the artifact
as go-live evidence:

```powershell
python scripts/audit_non_db_launch_ops.py --verify-report reports/non_db_launch_ops_blockers.json
```

## 8. Spend persistence restart check

Run this after at least one governed LLM call has written `job_traces` or
`spend_events` today:

```powershell
ssh draftcheck 'cd /srv/draftcheck/app/infra/v3 && sudo docker compose exec -T api python scripts/ops_guardrails.py spend-snapshot --json > /tmp/draftcheck-spend-before.json && sudo docker compose restart api && sudo docker compose exec -T api python -c "import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8000/api/v1/ready\", timeout=10).read()" && sudo docker compose exec -T api python scripts/ops_guardrails.py spend-snapshot --json > /tmp/draftcheck-spend-after.json && sudo docker compose exec -T api python scripts/ops_guardrails.py compare-spend-snapshots --before /tmp/draftcheck-spend-before.json --after /tmp/draftcheck-spend-after.json --json'
```

Gate result must be `status: ok`. `status: warning` means there was no
pre-restart spend evidence; run a governed LLM path first, then repeat.
