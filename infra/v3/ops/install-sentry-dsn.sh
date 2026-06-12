#!/usr/bin/env bash
# Install SENTRY_DSN into the VPS compose env without printing the DSN.

set -euo pipefail

APP_DIR="${DRAFTCHECK_APP_DIR:-/srv/draftcheck/app}"
ENV_PATH="${DRAFTCHECK_ENV_PATH:-$APP_DIR/infra/v3/.env}"
COMPOSE_PATH="${DRAFTCHECK_COMPOSE_PATH:-$APP_DIR/infra/v3/compose.yml}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
RESTART_SERVICES="${DRAFTCHECK_RESTART_SERVICES:-0}"

: "${SENTRY_DSN:?SENTRY_DSN is required}"

install -d "$(dirname "$ENV_PATH")"
if [[ ! -f "$ENV_PATH" ]]; then
    install -m 0600 /dev/null "$ENV_PATH"
fi

tmp="$(mktemp)"
cleanup() {
    rm -f "$tmp"
}
trap cleanup EXIT

if grep -q '^SENTRY_DSN=' "$ENV_PATH"; then
    awk -v dsn="$SENTRY_DSN" '
        BEGIN { replaced = 0 }
        /^SENTRY_DSN=/ {
            print "SENTRY_DSN=" dsn
            replaced = 1
            next
        }
        { print }
        END {
            if (!replaced) {
                print "SENTRY_DSN=" dsn
            }
        }
    ' "$ENV_PATH" >"$tmp"
else
    cat "$ENV_PATH" >"$tmp"
    printf '\nSENTRY_DSN=%s\n' "$SENTRY_DSN" >>"$tmp"
fi

install -m 0600 "$tmp" "$ENV_PATH"
"$PYTHON_BIN" "$APP_DIR/scripts/ops_guardrails.py" sentry-config \
    --env-path "$ENV_PATH" \
    --compose-path "$COMPOSE_PATH"

if [[ "$RESTART_SERVICES" == "1" ]]; then
    cd "$(dirname "$COMPOSE_PATH")"
    docker compose up -d api worker hermes
else
    echo "Sentry DSN installed; restart api worker hermes when ready."
fi
