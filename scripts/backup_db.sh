#!/usr/bin/env bash
# backup_db.sh — pg_dump the DraftCheck database and rotate to keep last 7 daily backups.
#
# Usage:
#   DATABASE_URL=postgresql://... bash scripts/backup_db.sh
#
# Override defaults via env:
#   BACKUP_DIR  — directory for backup files (default: backups/)
#   KEEP_DAYS   — number of daily backups to retain (default: 7)
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/draftcheck_${TIMESTAMP}.sql.gz"

if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "ERROR: DATABASE_URL is not set." >&2
    exit 1
fi

mkdir -p "${BACKUP_DIR}"

echo "[backup] Starting pg_dump at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
pg_dump "${DATABASE_URL}" | gzip > "${BACKUP_FILE}"

SIZE="$(du -sh "${BACKUP_FILE}" | cut -f1)"
echo "[backup] Wrote ${BACKUP_FILE} (${SIZE})"

# Rotate: delete backups older than KEEP_DAYS days
echo "[backup] Rotating — keeping last ${KEEP_DAYS} daily backups"
find "${BACKUP_DIR}" -maxdepth 1 -name 'draftcheck_*.sql.gz' \
    | sort \
    | head -n "-${KEEP_DAYS}" \
    | while IFS= read -r OLD; do
        echo "[backup] Removing old backup: ${OLD}"
        rm -f "${OLD}"
    done

echo "[backup] Done. Current backups in ${BACKUP_DIR}:"
ls -lh "${BACKUP_DIR}"/draftcheck_*.sql.gz 2>/dev/null || echo "  (none)"
