#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${DRAFTCHECK_APP_DIR:-/srv/draftcheck/app}"
UNIT_DIR="${DRAFTCHECK_SYSTEMD_DIR:-/etc/systemd/system}"

install -m 0644 \
  "$APP_DIR/infra/v3/planwa-refresh/draftcheck-planwa-refresh.service" \
  "$UNIT_DIR/draftcheck-planwa-refresh.service"
install -m 0644 \
  "$APP_DIR/infra/v3/planwa-refresh/draftcheck-planwa-refresh.timer" \
  "$UNIT_DIR/draftcheck-planwa-refresh.timer"

systemctl daemon-reload
systemctl enable --now draftcheck-planwa-refresh.timer
systemctl list-timers --all draftcheck-planwa-refresh.timer
