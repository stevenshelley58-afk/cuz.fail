#!/usr/bin/env bash
#
# Redeploy the live V3 stack on the VPS from the current checkout.
# The caller (.github/workflows/deploy.yml) has already reset
# /srv/draftcheck/app to origin/main before invoking this script.
# See docs/PRODUCTION_DEPLOYMENT.md and docs/INFRASTRUCTURE.md.
set -euo pipefail

APP_DIR="/srv/draftcheck/app"
cd "$APP_DIR"

deploy_sha="$(git rev-parse HEAD)"
echo "== deploying ${deploy_sha} =="

# Back up the compiled web bundle so a failed rebuild can roll back.
backup_dir=""
if [ -d web/dist ]; then
  backup_dir="$(mktemp -d /tmp/draftcheck-web-dist.XXXXXX)"
  cp -a web/dist/. "${backup_dir}/" || true
fi

# Backend: rebuild + restart. The api container command runs
# `alembic upgrade head` on start, so schema migrations apply automatically.
echo "== backend: docker compose up -d --build (infra/v3) =="
cd "${APP_DIR}/infra/v3"
docker compose up -d --build

# Frontend: Caddy serves the compiled static bundle at web/dist.
echo "== frontend: npm ci && npm run build (web) =="
cd "${APP_DIR}/web"
npm ci
if npm run build; then
  [ -n "${backup_dir}" ] && rm -rf "${backup_dir}" || true
else
  rc=$?
  echo "web build failed (rc=${rc}) -- restoring previous web/dist"
  if [ -n "${backup_dir}" ] && [ -d "${backup_dir}" ]; then
    rm -rf dist && mkdir -p dist && cp -a "${backup_dir}/." dist/ && rm -rf "${backup_dir}"
  fi
  exit "${rc}"
fi

echo "== deployed ${deploy_sha} =="
