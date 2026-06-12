#!/usr/bin/env bash
# Idempotently install the non-security guardrail alert cron entry.

set -euo pipefail

APP_DIR="${DRAFTCHECK_APP_DIR:-/srv/draftcheck/app}"
CRON_APP_DIR="${DRAFTCHECK_CRON_APP_DIR:-/srv/draftcheck/app}"
CRON_PATH="${DRAFTCHECK_CRON_PATH:-/etc/cron.d/draftcheck-guardrails}"
LOG_PATH="${DRAFTCHECK_GUARDRAIL_LOG_PATH:-/var/log/draftcheck-guardrails.log}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SCHEDULE="${DRAFTCHECK_GUARDRAIL_CRON_SCHEDULE:-*/10 * * * *}"

tmp="$(mktemp)"
cleanup() {
    rm -f "$tmp"
}
trap cleanup EXIT

cat >"$tmp" <<EOF
$SCHEDULE root bash $CRON_APP_DIR/infra/v3/ops/guardrail-alerts.sh >> $LOG_PATH 2>&1
EOF

install -m 0644 "$tmp" "$CRON_PATH"
"$PYTHON_BIN" "$APP_DIR/scripts/ops_guardrails.py" guardrail-cron --path "$CRON_PATH"
echo "installed draftcheck guardrail cron at $CRON_PATH"
