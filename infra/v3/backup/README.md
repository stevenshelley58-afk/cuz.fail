# V3 Backup And Restore Drills

V3 backs up the PostgreSQL database with `pg_dump` and the local
content-addressed storage tree with `restic`. These commands are operator drill
notes for the single-VPS target; they are not a submission-ready export or a
legal compliance claim.

Set the repository and credentials in the operator shell or service manager.
Do not commit the real values:

```sh
export RESTIC_REPOSITORY='s3:s3.example.invalid/draftcheck-v3-backups'
export RESTIC_PASSWORD_FILE='/etc/draftcheck/restic-password'
export POSTGRES_USER="${POSTGRES_USER:-draftcheck}"
export POSTGRES_DB="${POSTGRES_DB:-draftcheck}"
export BACKUP_DIR="/srv/draftcheck/backups/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"
```

Nightly database and storage backup:

```sh
docker compose -f infra/v3/compose.yml exec -T db \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
  > "$BACKUP_DIR/postgres.dump"

restic backup "$BACKUP_DIR/postgres.dump" /srv/draftcheck/storage
```

Weekly repository check:

```sh
restic check
```

Monthly restore drill into a scratch database:

```sh
export DRILL_DIR="/tmp/draftcheck-v3-restore-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$DRILL_DIR"

restic restore latest --target "$DRILL_DIR"
RESTORED_DUMP="$(
  find "$DRILL_DIR/srv/draftcheck/backups" -name postgres.dump -print -quit
)"
test -n "$RESTORED_DUMP"

docker compose -f infra/v3/compose.yml exec -T db \
  dropdb -U "$POSTGRES_USER" --if-exists draftcheck_restore_drill

docker compose -f infra/v3/compose.yml exec -T db \
  createdb -U "$POSTGRES_USER" draftcheck_restore_drill

docker compose -f infra/v3/compose.yml exec -T db \
  pg_restore -U "$POSTGRES_USER" -d draftcheck_restore_drill \
  --clean --if-exists \
  < "$RESTORED_DUMP"

docker compose -f infra/v3/compose.yml exec -T db \
  psql -U "$POSTGRES_USER" -d draftcheck_restore_drill \
  -c "SELECT count(*) AS source_versions FROM source_versions;"
```

Storage drill:

```sh
restic restore latest --target "$DRILL_DIR" --include /srv/draftcheck/storage
test -d "$DRILL_DIR/srv/draftcheck/storage"
```

Record the backup timestamp, restic snapshot ID, `pg_dump` artifact path,
`restic check` result, scratch restore duration, checksum or manifest hash, and
row-count sanity output in the operations audit trail before treating the drill
as accepted evidence.

## Systemd install

After `/etc/draftcheck/backup.env` and `RESTIC_PASSWORD_FILE` exist on the VPS,
arm the timer idempotently:

```sh
sudo bash /srv/draftcheck/app/infra/v3/backup/install-systemd.sh
```

The script installs the checked-in unit files, reloads systemd, enables the
timer, and prints `systemctl list-timers` evidence.

## Freshness probe

The go-live freshness guard is a timestamp check over restored dump artifacts:

```sh
python3 /srv/draftcheck/app/scripts/ops_guardrails.py backup-freshness \
  --backup-dir /srv/draftcheck/backups \
  --max-age-hours 26 \
  --json
```

The command exits `0` when the newest dump is fresh and non-zero when no dump is
found or the newest dump is older than 26 hours.
