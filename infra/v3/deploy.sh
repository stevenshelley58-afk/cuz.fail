#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${DRAFTCHECK_APP_DIR:-/srv/draftcheck/app}"
COMPOSE_FILE="${DRAFTCHECK_COMPOSE_FILE:-infra/v3/compose.yml}"
EXTRA_COMPOSE_FILE="${DRAFTCHECK_EXTRA_COMPOSE_FILE:-infra/v3/compose.shared-caddy.yml}"
ENV_FILE="${DRAFTCHECK_ENV_FILE:-.env}"

cd "$APP_DIR"

git fetch origin
git reset --hard origin/main

# Ensure lotfile.app is in CORS_ALLOWED_ORIGINS in the env file.
if [ -f "$ENV_FILE" ] && grep -q "^CORS_ALLOWED_ORIGINS=" "$ENV_FILE"; then
  if ! grep "^CORS_ALLOWED_ORIGINS=" "$ENV_FILE" | grep -q "lotfile\.app"; then
    sed -i 's|^CORS_ALLOWED_ORIGINS=.*|&,https://lotfile.app|' "$ENV_FILE"
    echo "Patched CORS_ALLOWED_ORIGINS to include lotfile.app"
  fi
fi

# --include=dev: vite/tsc are devDependencies; a production npm config on the
# host would otherwise omit them and break the build.
(cd web && npm ci --include=dev && npm run build)

cd infra/v3
compose_args=(--env-file "$ENV_FILE" -f "../../$COMPOSE_FILE")
if [ -f "../../$EXTRA_COMPOSE_FILE" ]; then
  compose_args+=(-f "../../$EXTRA_COMPOSE_FILE")
fi

docker compose "${compose_args[@]}" build api
docker compose "${compose_args[@]}" up -d --wait --remove-orphans
docker compose "${compose_args[@]}" exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/ready', timeout=5).read()"

# Post-deploy: re-adjudicate stored WP6 rule candidates with the family-aware
# core-vote policy (scripts/wp6_adjudicate.py). Pure DB pass, no LLM calls,
# idempotent (already-promoted cores are skipped). Non-fatal on purpose:
# a promotion hiccup must never block a deploy.
docker compose "${compose_args[@]}" exec -T api \
  python scripts/wp6_adjudicate.py --apply --report /app/reports/wp6_adjudication.json \
  || echo "WARN: wp6_adjudicate failed (non-fatal; run manually to investigate)"

echo "deployed $(git -C "$APP_DIR" rev-parse --short HEAD)"
