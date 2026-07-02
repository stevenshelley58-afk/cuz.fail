#!/bin/bash
# DB backup script for DraftCheck VPS
# Dumps PostgreSQL to /srv/draftcheck/backups/

set -euo pipefail

BACKUP_DIR="/srv/draftcheck/backups"
TIMESTAMP=$(date +%F-%H%M)
DB_NAME="draftcheck"
DB_USER="draftcheck"
CONTAINER="$(cd /srv/draftcheck/app/infra/v3 && sudo docker compose ps -q db)"

mkdir -p "$BACKUP_DIR"

# Run pg_dump inside the db container
sudo docker exec "$CONTAINER" pg_dump -U "$DB_USER" -Fc "$DB_NAME" > "$BACKUP_DIR/draftcheck-${TIMESTAMP}.dump"

# Compress and keep last 7 days
find "$BACKUP_DIR" -name "draftcheck-*.dump" -mtime +7 -delete

echo "Backup complete: $BACKUP_DIR/draftcheck-${TIMESTAMP}.dump"
