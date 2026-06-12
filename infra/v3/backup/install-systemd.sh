#!/usr/bin/env bash
# Idempotently install and enable the V3 backup systemd timer on the VPS.

set -euo pipefail

APP_DIR="${DRAFTCHECK_APP_DIR:-/srv/draftcheck/app}"
BACKUP_ENV="${DRAFTCHECK_BACKUP_ENV:-/etc/draftcheck/backup.env}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
UNIT_DIR="${DRAFTCHECK_SYSTEMD_DIR:-/etc/systemd/system}"

if [[ ! -f "$BACKUP_ENV" ]]; then
    cat >&2 <<MSG
Missing $BACKUP_ENV.

Create it with RESTIC_REPOSITORY and RESTIC_PASSWORD_FILE before arming backups.
Example unblock:
  sudo install -d -m 700 /etc/draftcheck
  sudo install -m 600 /dev/null /etc/draftcheck/restic-password
  sudo tee /etc/draftcheck/backup.env >/dev/null <<'EOF'
RESTIC_REPOSITORY=s3:s3.example.invalid/draftcheck-v3-backups
RESTIC_PASSWORD_FILE=/etc/draftcheck/restic-password
POSTGRES_USER=draftcheck
POSTGRES_DB=draftcheck
COMPOSE_FILE=/srv/draftcheck/app/infra/v3/compose.yml
EOF
MSG
    exit 2
fi

"$PYTHON_BIN" "$APP_DIR/scripts/ops_guardrails.py" backup-config --env-path "$BACKUP_ENV"

install -m 0644 "$APP_DIR/infra/v3/backup/draftcheck-backup.service" \
    "$UNIT_DIR/draftcheck-backup.service"
install -m 0644 "$APP_DIR/infra/v3/backup/draftcheck-backup.timer" \
    "$UNIT_DIR/draftcheck-backup.timer"

systemctl daemon-reload
systemctl enable --now draftcheck-backup.timer
systemctl list-timers --all draftcheck-backup.timer
