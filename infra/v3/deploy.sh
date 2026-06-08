#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${DRAFTCHECK_APP_DIR:-/opt/draftcheck-v3}"
COMPOSE_FILE="${DRAFTCHECK_COMPOSE_FILE:-infra/v3/compose.yml}"
EXTRA_COMPOSE_FILE="${DRAFTCHECK_EXTRA_COMPOSE_FILE:-infra/v3/compose.shared-caddy.yml}"
ENV_FILE="${DRAFTCHECK_ENV_FILE:-.env}"

cd "$APP_DIR"

git fetch origin
git reset --hard origin/main

(cd web && npm ci && npm run build)

cd infra/v3
compose_args=(--env-file "$ENV_FILE" -f "../../$COMPOSE_FILE")
scale_args=()
if [ -f "../../$EXTRA_COMPOSE_FILE" ]; then
  compose_args+=(-f "../../$EXTRA_COMPOSE_FILE")
  scale_args+=(--scale caddy=0)
fi

docker compose "${compose_args[@]}" build api
docker compose "${compose_args[@]}" up -d --wait "${scale_args[@]}"
docker compose "${compose_args[@]}" exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/ready', timeout=5).read()"

echo "deployed $(git -C "$APP_DIR" rev-parse --short HEAD)"
