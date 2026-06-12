#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${DRAFTCHECK_APP_DIR:-/srv/draftcheck/app}"
WEB_REF="${DRAFTCHECK_WEB_REF:-origin/main}"
ENV_FILE="${DRAFTCHECK_ENV_FILE:-}"

cd "$APP_DIR"
git config --global --add safe.directory "$APP_DIR"
git fetch origin

non_web_delta="$(git diff --name-only HEAD "$WEB_REF" | grep -v '^web/' || true)"
if [ -n "$non_web_delta" ]; then
  echo "Refusing UI-only deploy: $WEB_REF contains non-web changes relative to this checkout:" >&2
  echo "$non_web_delta" >&2
  exit 1
fi

if [ -n "$(git status --porcelain -- web)" ]; then
  git stash push -m "pre-ui-only web deploy $(date -Is)" -- web
fi

backup_dir="$(mktemp -d /tmp/draftcheck-web-dist.XXXXXX)"
if [ -d web/dist ]; then
  cp -a web/dist/. "$backup_dir"/
fi

rollback() {
  status=$?
  rm -rf web/dist
  mkdir -p web/dist
  cp -a "$backup_dir"/. web/dist/ 2>/dev/null || true
  rm -rf "$backup_dir"
  exit "$status"
}
trap rollback ERR

git restore --source "$WEB_REF" -- web

if [ -z "$ENV_FILE" ]; then
  if [ -f infra/v3/.env ]; then
    ENV_FILE="infra/v3/.env"
  elif [ -f .env ]; then
    ENV_FILE=".env"
  fi
fi

if [ -z "$ENV_FILE" ] || [ ! -f "$ENV_FILE" ]; then
  echo "Refusing UI-only deploy: no .env or infra/v3/.env found for VITE_CHECKOUT_URL" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

: "${VITE_CHECKOUT_URL:?VITE_CHECKOUT_URL must be set before paid UI deploy}"

lower_checkout="$(printf '%s' "$VITE_CHECKOUT_URL" | tr '[:upper:]' '[:lower:]')"
case "$VITE_CHECKOUT_URL" in
  https://buy.stripe.com/*) ;;
  *)
    echo "Refusing UI-only deploy: VITE_CHECKOUT_URL is not a Stripe Payment Link" >&2
    exit 1
    ;;
esac
case "$lower_checkout" in
  *example*|*placeholder*|*change_me*|*todo*|*/test_*)
    echo "Refusing UI-only deploy: VITE_CHECKOUT_URL looks like a placeholder or test value" >&2
    exit 1
    ;;
esac

(cd web && npm ci --include=dev && npm run verify:launch:mobile && npm run build && node scripts/verify-launch.mjs --strict)

grep -R -I -F "$VITE_CHECKOUT_URL" web/dist/assets >/dev/null
if grep -R -I -E 'example\.invalid|placeholder|change[_-]?me|TODO|buy\.stripe\.com/test_' web/dist >/dev/null; then
  echo "Refusing UI-only deploy: built web/dist contains placeholder launch text" >&2
  exit 1
fi

rm -rf "$backup_dir"
trap - ERR
echo "UI deployed from $WEB_REF $(git rev-parse --short "$WEB_REF") without container restart"
