#!/usr/bin/env bash
# Monthly DraftCheck V3 restore drill.
# Restores the latest restic snapshot into a scratch DB and prints a structured summary.
#
# Usage:
#   bash infra/v3/backup/restore-drill.sh | tee docs/ops/restore-drill-$(date +%Y%m%d).md
#
# Env (from /etc/draftcheck/backup.env or exported by caller):
#   RESTIC_REPOSITORY, RESTIC_PASSWORD_FILE, POSTGRES_USER, POSTGRES_DB,
#   COMPOSE_FILE (default: infra/v3/compose.yml relative to repo root)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

[[ -f /etc/draftcheck/backup.env ]] && source /etc/draftcheck/backup.env

: "${RESTIC_REPOSITORY:?RESTIC_REPOSITORY is required}"
: "${RESTIC_PASSWORD_FILE:?RESTIC_PASSWORD_FILE is required}"
: "${POSTGRES_USER:=draftcheck}"
: "${POSTGRES_DB:=draftcheck}"
COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/infra/v3/compose.yml}"

DRILL_START="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DRILL_DIR="/tmp/draftcheck-v3-restore-$(date -u +%Y%m%dT%H%M%SZ)"
SCRATCH_DB="draftcheck_restore_drill"

echo "# DraftCheck V3 Restore Drill"
echo ""
echo "date: $DRILL_START"
echo ""

# --- 1. restic check ---
echo "## restic check"
restic check
echo ""

# --- 2. restic restore latest ---
echo "## Restore latest snapshot"
mkdir -p "$DRILL_DIR"
SNAPSHOT_ID=$(restic snapshots --last --json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['short_id'])")
echo "snapshot_id: $SNAPSHOT_ID"
restic restore latest --target "$DRILL_DIR"
echo ""

# --- 3. Locate dump ---
RESTORED_DUMP="$(find "$DRILL_DIR/srv/draftcheck/backups" -name postgres.dump -print -quit)"
if [[ -z "$RESTORED_DUMP" ]]; then
    echo "ERROR: postgres.dump not found under $DRILL_DIR" >&2
    exit 1
fi
DUMP_SIZE=$(stat -c%s "$RESTORED_DUMP" 2>/dev/null || stat -f%z "$RESTORED_DUMP")
echo "## Dump"
echo "dump_path: $RESTORED_DUMP"
echo "dump_size_bytes: $DUMP_SIZE"
echo ""

# --- 4. Restore into scratch DB ---
echo "## DB restore"
docker compose -f "$COMPOSE_FILE" exec -T db \
    dropdb -U "$POSTGRES_USER" --if-exists "$SCRATCH_DB"
docker compose -f "$COMPOSE_FILE" exec -T db \
    createdb -U "$POSTGRES_USER" "$SCRATCH_DB"
docker compose -f "$COMPOSE_FILE" exec -T db \
    pg_restore -U "$POSTGRES_USER" -d "$SCRATCH_DB" --clean --if-exists \
    < "$RESTORED_DUMP"
echo ""

# --- 5. Sanity check ---
echo "## Sanity counts"
docker compose -f "$COMPOSE_FILE" exec -T db \
    psql -U "$POSTGRES_USER" -d "$SCRATCH_DB" \
    -c "SELECT count(*) AS source_versions FROM source_versions;"
docker compose -f "$COMPOSE_FILE" exec -T db \
    psql -U "$POSTGRES_USER" -d "$SCRATCH_DB" \
    -c "SELECT count(*) AS job_traces FROM job_traces;"
echo ""

# --- 6. Clean up ---
docker compose -f "$COMPOSE_FILE" exec -T db \
    dropdb -U "$POSTGRES_USER" --if-exists "$SCRATCH_DB"
rm -rf "$DRILL_DIR"

DRILL_END="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "## Result"
echo "drill_start: $DRILL_START"
echo "drill_end: $DRILL_END"
echo "status: PASS"
