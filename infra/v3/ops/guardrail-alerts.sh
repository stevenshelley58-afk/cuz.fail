#!/usr/bin/env bash
# Cron-friendly non-security guardrail alert checks for the V3 VPS.

set -euo pipefail

APP_DIR="${DRAFTCHECK_APP_DIR:-/srv/draftcheck/app}"
COMPOSE_DIR="${DRAFTCHECK_COMPOSE_DIR:-$APP_DIR/infra/v3}"
BACKUP_DIR="${DRAFTCHECK_BACKUP_DIR:-/srv/draftcheck/backups}"
MAX_BACKUP_AGE_HOURS="${DRAFTCHECK_MAX_BACKUP_AGE_HOURS:-26}"
DISK_THRESHOLD="${DRAFTCHECK_DISK_THRESHOLD:-80}"
HEALTH_URL="${DRAFTCHECK_HEALTH_URL:-https://lotfile.app/api/v1/health}"
READY_URL="${DRAFTCHECK_READY_URL:-https://lotfile.app/api/v1/ready}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

[[ -f /etc/draftcheck/ops-alerts.env ]] && source /etc/draftcheck/ops-alerts.env

failures=()

backup_output="$("$PYTHON_BIN" "$APP_DIR/scripts/ops_guardrails.py" backup-freshness \
    --backup-dir "$BACKUP_DIR" \
    --max-age-hours "$MAX_BACKUP_AGE_HOURS" \
    --json 2>&1)" || failures+=("backup_freshness: $backup_output")

disk_output="$("$PYTHON_BIN" "$APP_DIR/scripts/ops_guardrails.py" disk-usage \
    --path /srv \
    --path /var/lib/docker \
    --max-used-percent "$DISK_THRESHOLD" \
    --json 2>&1)" || failures+=("disk_usage: $disk_output")

uptime_output="$("$PYTHON_BIN" "$APP_DIR/scripts/ops_guardrails.py" uptime-targets \
    --health-url "$HEALTH_URL" \
    --ready-url "$READY_URL" \
    --json 2>&1)" || failures+=("uptime_targets: $uptime_output")

heartbeat_output="$("$PYTHON_BIN" "$APP_DIR/scripts/ops_guardrails.py" worker-heartbeat \
    --compose-dir "$COMPOSE_DIR" \
    --service worker \
    --service hermes \
    --json 2>&1)" || failures+=("worker_heartbeat: $heartbeat_output")

if ((${#failures[@]} == 0)); then
    echo "draftcheck guardrails ok"
    exit 0
fi

printf 'draftcheck guardrail failures:\n' >&2
printf ' - %s\n' "${failures[@]}" >&2

if [[ -n "${DRAFTCHECK_ALERT_WEBHOOK_URL:-}" ]]; then
    payload="$("$PYTHON_BIN" -c 'import json,sys; print(json.dumps({"text": "DraftCheck guardrail failures:\n" + "\n".join(sys.argv[1:])}))' "${failures[@]}")"
    curl -fsS -X POST -H 'Content-Type: application/json' --data "$payload" \
        "$DRAFTCHECK_ALERT_WEBHOOK_URL" >/dev/null
fi

exit 2
