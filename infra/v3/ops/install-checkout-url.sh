#!/usr/bin/env bash
# Install the Stripe checkout URL into the VPS web env without committing it.

set -euo pipefail

APP_DIR="${DRAFTCHECK_APP_DIR:-/srv/draftcheck/app}"
ENV_PATH="${DRAFTCHECK_ENV_PATH:-$APP_DIR/infra/v3/.env}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
DEPLOY_WEB_ONLY="${DRAFTCHECK_DEPLOY_WEB_ONLY:-0}"

: "${VITE_CHECKOUT_URL:?VITE_CHECKOUT_URL is required}"

install -d "$(dirname "$ENV_PATH")"
if [[ ! -f "$ENV_PATH" ]]; then
    install -m 0600 /dev/null "$ENV_PATH"
fi

tmp="$(mktemp)"
cleanup() {
    rm -f "$tmp"
}
trap cleanup EXIT

upsert_env_key() {
    local key="$1"
    local value="$2"

    awk -v key="$key" -v value="$value" '
        BEGIN { replaced = 0 }
        $0 ~ "^" key "=" {
            print key "=" value
            replaced = 1
            next
        }
        { print }
        END {
            if (!replaced) {
                print key "=" value
            }
        }
    ' "$ENV_PATH" >"$tmp"
    install -m 0600 "$tmp" "$ENV_PATH"
}

upsert_env_key "VITE_CHECKOUT_URL" "$VITE_CHECKOUT_URL"
if [[ -n "${VITE_PRICE_LABEL:-}" ]]; then
    upsert_env_key "VITE_PRICE_LABEL" "$VITE_PRICE_LABEL"
fi
if [[ -n "${VITE_PRICE_SUBLABEL:-}" ]]; then
    upsert_env_key "VITE_PRICE_SUBLABEL" "$VITE_PRICE_SUBLABEL"
fi

"$PYTHON_BIN" "$APP_DIR/scripts/ops_guardrails.py" checkout-config --env-path "$ENV_PATH"

if [[ "$DEPLOY_WEB_ONLY" == "1" ]]; then
    bash "$APP_DIR/infra/v3/deploy-web-only.sh"
else
    echo "Checkout URL installed; run deploy-web-only.sh when ready."
fi
