#!/usr/bin/env bash
#
# Redeploy the live V3 stack on the VPS from the current checkout.
# The caller (.github/workflows/deploy.yml) has already reset
# /srv/draftcheck/app to origin/main before invoking this script.
# See docs/PRODUCTION_DEPLOYMENT.md and docs/INFRASTRUCTURE.md.
#
# Delegates to infra/v3/deploy.sh which combines compose.yml and
# compose.shared-caddy.yml (internal_caddy owns ports 80/443).
set -euo pipefail

APP_DIR="/srv/draftcheck/app"
exec bash "${APP_DIR}/infra/v3/deploy.sh"
