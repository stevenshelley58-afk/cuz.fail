# Infrastructure Foundation

The V3 repository includes the backend core and the LotFile web UI under `web/`. Caddy serves the
production web UI from the compiled static artifact at `/srv/draftcheck/app/web/dist` on the VPS.
See `docs/PRODUCTION_DEPLOYMENT.md` for the current `lotfile.app` deploy procedure.

## Local stack

Start the foundation services from the repository root:

```powershell
docker compose up -d --build
```

The stack includes:

- `db`: custom `postgis/postgis:16-3.5` image with pgvector `0.8.0` built and installed.
- `redis`: Redis with append-only persistence for RQ-compatible queue state.
- `minio`: object storage with private `raw-sources`, `parsed-sources`, `uploads`, and `exports` buckets.
- `api` and `worker`: backend containers using the existing Python image.
- `caddy`: reverse proxy for API routes and a static frontend artifact path.

Runtime storage writes are bucket-specific: project uploads use `uploads`, generated export files use
`exports`, and source artifact helpers are reserved for `raw-sources` and `parsed-sources`.

Validate the local stack:

```powershell
.\scripts\infra-health.ps1
```

`/health` is a lightweight API liveness endpoint. `/ready` is the dependency gate and checks
database connectivity/schema, Alembic migration head, required PostgreSQL extensions (`postgis` and
`vector`) when the runtime database is PostgreSQL, object-storage read/write, every configured S3
bucket when `S3_ENDPOINT_URL` is set, and Redis/RQ when `RQ_ENABLED=true`. Compose health checks use
`/ready`, and the worker health check runs
`python -m draftcheck_worker.main --check-ready`.

## Database extensions

The DB image is intentionally custom because `postgis/postgis` should not be assumed to include pgvector. On first database initialization, `infra/docker/db/init-extensions.sql` runs:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
```

For an existing Postgres volume created before this image, run the extension creation manually or recreate the local volume after confirming no local data is needed.

## Backups and restores

Create a local timestamped backup:

```powershell
.\scripts\backup-infra.ps1
```

Restore from a backup directory:

```powershell
.\scripts\restore-infra.ps1 -BackupDir .\.backups\YYYYMMDD-HHMMSS
```

Restore is destructive for the target local DB and MinIO buckets, so the script requires typing `RESTORE` unless `-Force` is supplied. These helpers are practical local/ops scaffolding only; production still needs encrypted offsite storage, scheduled execution, restore timing, and operational signoff before any submission-ready claim.

After a successful run, the scripts execute `scripts/record_infra_event.py` inside the API container:

- Backup records `infra.backup.completed` with the backup directory, DB dump, MinIO mirror, manifest hash, and duration.
- Restore records `infra.restore.completed` with the restored backup directory, checksum-validation flag, manifest hash, and duration.

The ops dashboard shows the latest backup/restore events, but release readiness requires production-grade evidence:

- Backup: `environment=production`, `offsite=true`, `encrypted=true`, `schedule=daily` or `scheduled=true`, database artifact, object-storage artifact, `manifest_sha256`, and `duration_seconds`.
- Restore: `environment=production`, `clean_machine_restore=true`, `checksum_validated=true`, `manifest_sha256`, and `duration_seconds`.

The local helper scripts default to `environment=local`, `offsite=false`, `encrypted=false`, and manual scheduling. Those events prove the scripts completed locally, but they intentionally do not clear the production backup/restore verification issues. A production backup run may pass `-Environment production -Offsite -Encrypted -ScheduledDaily`; a clean-machine restore test may pass `-Environment production -CleanMachineRestore`.

## VPS shape

The live VPS is `srv1625369` (`76.13.209.160`) and is reachable from the operator machine as
`ssh draftcheck`.

The active production checkout is `/srv/draftcheck/app`. Caddy terminates HTTP/TLS and routes:

- `api.cuz.fail` to the backend API mounted at `/api/v1`.
- `lotfile.app` to `/srv/draftcheck/app/web/dist`.

For UI-only releases, rebuild `web/dist` on the VPS after resetting the checkout to `origin/main`.
No Vercel deploy and no container restart are required for static frontend changes.

Do not put paid Australian Standards full text into MinIO or backups. Store only allowed public metadata and access notes for those sources.

## Production bootstrap (VPS-only)

Vercel is retired. The only production target is the VPS at `76.13.209.160` serving `lotfile.app`.

To deploy or redeploy the UI:

```bash
ssh draftcheck ‘cd /srv/draftcheck/app && git fetch origin && git reset --hard origin/main && cd web && npm ci && npm run build’
```

If the Caddyfile changed, reload Caddy:

```bash
ssh draftcheck ‘cd /srv/draftcheck/app/infra/v3 && sudo docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile’
```

Source library and eval tooling:

For local or durable databases where chat returns unsupported despite many stored chunks, run
`python scripts/bootstrap_source_library.py` and then `python scripts/audit_source_library.py`. The
audit distinguishes stored chunks from source versions that pass the runtime citable retrieval gate;
chunks without accepted source review, approved licence/storage/AI-processing, no blocking review
items, approved rule rows, and no-orphan audit clearance are intentionally not used for regulatory
answers.

Semantic retrieval remains opt-in. The default `EMBEDDING_PROVIDER=mock` keeps tests and offline
development deterministic. To use OpenAI-compatible embeddings, set `EMBEDDING_PROVIDER=openai`,
`OPENAI_API_KEY`, and optionally `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, `OPENAI_BASE_URL`, and
`EMBEDDING_TIMEOUT_SECONDS`, then run `python scripts/rebuild_source_embeddings.py` against the
durable database. Retrieval filters vector candidates by provider and model, so old mock embeddings
will not be mixed into OpenAI-backed searches.

To prepare accepted sources for rule review, run `python scripts/extract_source_rules.py` with a
source filter. The command dry-runs by default and requires `--commit` before it writes deterministic
rule candidates or clause dispositions. It never approves rule rows; reviewers still need to promote
and approve quote-anchored candidates before a source version can support citable retrieval.
Use `python scripts/rule_review_worklist.py --source-version-id <id>` to render the source-specific
gate checks, coverage/no-orphan summaries, rule rows, rule candidate IDs, and open review queue items
that must be cleared before that source can support chat or other regulatory answers.
Use `python scripts/promote_rule_candidate.py --candidate-id <candidate-id> --reconcile-source` to
dry-run promotion into a pending `RuleRow`, then add `--commit` only after the output is correct.
Promotion never approves a rule row and does not make a source citable; it creates the pending rule
review artifact that a human reviewer must approve, reject, or revise.
After reviewers promote/approve/reject rule work, run
`python scripts/reconcile_source_review_queue.py --source-version-id <id>` to resolve stale queue
items that are no longer present in the current acceptance-gate audits. Current blockers remain open.
