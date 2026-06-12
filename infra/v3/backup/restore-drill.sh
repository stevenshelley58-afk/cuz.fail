#!/usr/bin/env bash
# Monthly LotFile V3 restore drill.
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

echo "# LotFile V3 Restore Drill"
echo ""
echo "date: $DRILL_START"
echo ""

# --- 1. restic check ---
echo "## restic check"
restic check
echo "result: PASS"
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

# --- 4. Verify restored storage tree ---
RESTORED_STORAGE="$DRILL_DIR/srv/draftcheck/storage"
if [[ ! -d "$RESTORED_STORAGE" ]]; then
    echo "ERROR: restored storage tree not found at $RESTORED_STORAGE" >&2
    exit 1
fi
echo "## Storage restore"
python3 - "$RESTORED_STORAGE" <<'PY'
import hashlib
from pathlib import Path
import sys

root = Path(sys.argv[1])
files = sorted(path for path in root.rglob("*") if path.is_file())
manifest = hashlib.sha256()
total_size = 0
for path in files:
    relative = path.relative_to(root).as_posix()
    payload = path.read_bytes()
    total_size += len(payload)
    manifest.update(relative.encode("utf-8"))
    manifest.update(b"\0")
    manifest.update(hashlib.sha256(payload).hexdigest().encode("ascii"))
    manifest.update(b"\0")
print(f"storage_path: {root}")
print(f"storage_file_count: {len(files)}")
print(f"storage_size_bytes: {total_size}")
print(f"storage_manifest_sha256: {manifest.hexdigest()}")
PY
echo "result: PASS"
echo ""

# --- 5. Restore into scratch DB ---
echo "## DB restore"
docker compose -f "$COMPOSE_FILE" exec -T db \
    dropdb -U "$POSTGRES_USER" --if-exists "$SCRATCH_DB"
docker compose -f "$COMPOSE_FILE" exec -T db \
    createdb -U "$POSTGRES_USER" "$SCRATCH_DB"
docker compose -f "$COMPOSE_FILE" exec -T db \
    pg_restore -U "$POSTGRES_USER" -d "$SCRATCH_DB" --clean --if-exists \
    < "$RESTORED_DUMP"
echo "result: PASS"
echo ""

# --- 6. Sanity check ---
echo "## Sanity counts"
SOURCE_VERSIONS="$(
    docker compose -f "$COMPOSE_FILE" exec -T db \
    psql -U "$POSTGRES_USER" -d "$SCRATCH_DB" \
        -At -c "SELECT count(*) FROM source_versions;"
)"
JOB_TRACES="$(
    docker compose -f "$COMPOSE_FILE" exec -T db \
    psql -U "$POSTGRES_USER" -d "$SCRATCH_DB" \
        -At -c "SELECT count(*) FROM job_traces;"
)"
echo "source_versions: $SOURCE_VERSIONS"
echo "job_traces: $JOB_TRACES"
echo ""

# --- 7. Clean up ---
docker compose -f "$COMPOSE_FILE" exec -T db \
    dropdb -U "$POSTGRES_USER" --if-exists "$SCRATCH_DB"
rm -rf "$DRILL_DIR"

DRILL_END="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "## Result"
echo "drill_start: $DRILL_START"
echo "drill_end: $DRILL_END"
echo "status: PASS"
