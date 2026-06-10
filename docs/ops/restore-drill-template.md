# LotFile V3 Restore Drill

<!-- Copy this file to restore-drill-YYYYMMDD.md, fill in all fields, commit. -->

date: YYYY-MM-DDTHH:MM:SSZ

## restic check

result: PASS / FAIL
output: |
  (paste restic check output here)

## Restore latest snapshot

snapshot_id: (short ID from `restic snapshots --last`)

## Dump

dump_path: /tmp/draftcheck-v3-restore-YYYYMMDDTHHMMSSZ/srv/draftcheck/backups/YYYYMMDDTHHMMSSZ/postgres.dump
dump_size_bytes: 0

## DB restore

result: PASS / FAIL

## Sanity counts

source_versions: 0
job_traces: 0

## Timing

drill_start: YYYY-MM-DDTHH:MM:SSZ
drill_end: YYYY-MM-DDTHH:MM:SSZ

## Result

status: PASS / FAIL
notes: (any anomalies or follow-up items)
