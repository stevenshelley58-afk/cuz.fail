#!/usr/bin/env bash
# Idempotently install checked journald and Docker log-retention configs.

set -euo pipefail

APP_DIR="${DRAFTCHECK_APP_DIR:-/srv/draftcheck/app}"
JOURNALD_TARGET="${DRAFTCHECK_JOURNALD_TARGET:-/etc/systemd/journald.conf.d/draftcheck.conf}"
DOCKER_DAEMON_TARGET="${DRAFTCHECK_DOCKER_DAEMON_TARGET:-/etc/docker/daemon.json}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SYSTEMCTL_BIN="${DRAFTCHECK_SYSTEMCTL_BIN:-systemctl}"
RESTART_DOCKER="${DRAFTCHECK_RESTART_DOCKER:-0}"

install -d "$(dirname "$JOURNALD_TARGET")"
install -m 0644 "$APP_DIR/infra/v3/ops/journald-draftcheck.conf" "$JOURNALD_TARGET"
"$SYSTEMCTL_BIN" restart systemd-journald

install -d "$(dirname "$DOCKER_DAEMON_TARGET")"
install -m 0644 "$APP_DIR/infra/v3/ops/docker-daemon-log-rotation.json" "$DOCKER_DAEMON_TARGET"
if [[ "$RESTART_DOCKER" == "1" ]]; then
    "$SYSTEMCTL_BIN" restart docker
else
    echo "Docker log rotation config installed; restart docker during the maintenance window."
fi

"$PYTHON_BIN" "$APP_DIR/scripts/ops_guardrails.py" log-retention-config \
    --journald-path "$JOURNALD_TARGET" \
    --docker-daemon-path "$DOCKER_DAEMON_TARGET"
echo "installed draftcheck log retention configs"
