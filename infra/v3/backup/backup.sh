#!/usr/bin/env bash
# Nightly LotFile V3 backup: pg_dump → timestamped file → restic.
# Run as: bash infra/v3/backup/backup.sh
# Env (from /etc/draftcheck/backup.env or exported by caller):
#   RESTIC_REPOSITORY, RESTIC_PASSWORD_FILE, POSTGRES_USER, POSTGRES_DB,
#   COMPOSE_FILE (default: infra/v3/compose.yml relative to repo root)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Load backup env if available (not present in tests).
[[ -f /etc/draftcheck/backup.env ]] && source /etc/draftcheck/backup.env

: "${RESTIC_REPOSITORY:?RESTIC_REPOSITORY is required}"
: "${RESTIC_PASSWORD_FILE:?RESTIC_PASSWORD_FILE is required}"
: "${POSTGRES_USER:=draftcheck}"
: "${POSTGRES_DB:=draftcheck}"
COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/infra/v3/compose.yml}"
BACKUP_DIR="/srv/draftcheck/backups/$(date -u +%Y%m%dT%H%M%SZ)"

echo "[backup] Starting at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[backup] Dump dir: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# --- 1. pg_dump ---
echo "[backup] Running pg_dump..."
docker compose -f "$COMPOSE_FILE" exec -T db \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
    > "$BACKUP_DIR/postgres.dump"

DUMP_SIZE=$(stat -c%s "$BACKUP_DIR/postgres.dump" 2>/dev/null || stat -f%z "$BACKUP_DIR/postgres.dump")
echo "[backup] pg_dump done: ${DUMP_SIZE} bytes"

# --- 2. restic backup ---
echo "[backup] Running restic backup..."
restic backup "$BACKUP_DIR/postgres.dump" /srv/draftcheck/storage \
    --tag draftcheck-nightly \
    --verbose

echo "[backup] restic backup done"
echo "[backup] Completed at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
