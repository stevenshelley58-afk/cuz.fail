#!/usr/bin/env bash
set -euo pipefail
cd /srv/draftcheck/app
git fetch origin && git reset --hard origin/main
(cd web && npm ci && npm run build)
cd infra/v3
docker compose build api
docker compose up -d --wait
docker compose exec api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/ready', timeout=5)"
echo "deployed $(git -C /srv/draftcheck/app rev-parse --short HEAD)"
