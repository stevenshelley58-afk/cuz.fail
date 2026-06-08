# Infrastructure Foundation

This repository remains backend-only. The Caddy `app` route is a proxy/file-serving shape for a separately built frontend artifact and does not add frontend source code here.

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

Use `deploy/docker-compose.vps.yml` with a private `deploy/.env` derived from `deploy/env.production.example`. Caddy terminates HTTP/TLS and routes:

- `CADDY_API_HOST` to the backend API container.
- `CADDY_APP_HOST` to `${STATIC_FRONTEND_ROOT}`, expected to be a separately deployed static frontend artifact.

Do not put paid Australian Standards full text into MinIO or backups. Store only allowed public metadata and access notes for those sources.

## Vercel production bootstrap

Vercel deployments must not run with the serverless SQLite fallback for production use. `/ready`
will fail until the runtime has a durable PostgreSQL/PostGIS `DATABASE_URL` and API-key auth is
enabled.

To install the public-safe production defaults before secrets are available, run:

```powershell
.\scripts\configure-vercel-production.ps1 -PublicDefaultsOnly -Deploy
```

This sets the durable deployment flags, explicit CORS origin, rate limits, bucket names, and
`BOOTSTRAP_DEMO_SOURCE_LIBRARY=false`. It does not set `DATABASE_URL`, `API_AUTH_KEYS`,
`S3_ENDPOINT_URL`, or S3 credentials, so protected routes remain fail-closed until the full
secret-backed bootstrap below is completed.

Supply secrets from the operator shell or CI secret store, then run:

```powershell
$env:DRAFTCHECK_DATABASE_URL = "postgresql+psycopg://..."
$env:DRAFTCHECK_API_AUTH_KEYS = "tenant-a:REPLACE_WITH_LONG_RANDOM_KEY"
$env:CORS_ALLOWED_ORIGINS = "https://app.cuz.fail"
$env:RATE_LIMIT_CHAT_REQUESTS = "120"
$env:RATE_LIMIT_UPLOAD_REQUESTS = "20"
.\scripts\configure-vercel-production.ps1 -SeedGoldenEvals -RunGoldenEvals -Deploy
```

`DRAFTCHECK_DATABASE_URL` must point at the durable database. For the linked Supabase project, use
the project database connection string from Supabase’s secret source or dashboard; do not commit it
and do not paste it into docs. The API key format is `tenant-id:key`, which scopes project ownership
and project-linked reads to that tenant when `API_AUTH_ENABLED=true`.

Do not use the 64-character value returned by `supabase secrets list` for `SUPABASE_DB_URL`; that is
a secret digest, not the PostgreSQL connection string. The production setup script rejects that shape
explicitly. Use the actual database password/connection string from the Supabase dashboard, an
operator password vault, or a CI secret store. Resetting the Supabase database password through the
Management API is possible, but it invalidates the existing password and must be treated as an
operator-approved credential rotation.

For the linked Supabase project, the script can also derive `DATABASE_URL` from
`supabase/.temp/pooler-url` or `SUPABASE_POOLER_URL` when `SUPABASE_DB_PASSWORD` is set. Supabase
secret values are write-only and cannot be recovered from CLI digests, so use the dashboard, password
vault, or CI secret store as the source of truth. If `DRAFTCHECK_API_AUTH_KEYS` is omitted, the script
generates a `default-tenant:<random-key>` value and prints it once for the operator to store securely.
Production readiness requires tenant-scoped keys in `tenant-id:key` format, and each key value must
be at least 32 characters long.
The development login endpoint is disabled whenever durable deployment flags are enabled; production
traffic must authenticate with the configured API key or future real-auth mechanism.
`CORS_ALLOWED_ORIGINS` must be an explicit comma-separated origin list for durable deployments. The
bootstrap script defaults it to `https://app.cuz.fail` if the operator shell does not provide a value;
wildcard CORS is allowed only for local/test deployments.
Upload and chat endpoints are rate-limited by default. Authenticated requests are bucketed by tenant
API key; unauthenticated or invalid-key traffic falls back to the client IP bucket.
Durable deployments fail `/ready` and protected-route admission if rate limiting is disabled or if
the chat/upload limits are non-positive.

The script applies database migrations by default with the same `init_database()` path used by the
API runtime. Use `-SkipMigrations` only when a separate controlled migration step has already brought
the durable database to the current Alembic head; otherwise `/ready` and protected routes remain
fail-closed on the migration-head check.

The script upserts these Vercel production env vars as sensitive values:

- `DATABASE_URL`
- `REQUIRE_DURABLE_DATABASE=true`
- `REQUIRE_DURABLE_OBJECT_STORAGE=true`
- `API_AUTH_ENABLED=true`
- `API_AUTH_KEYS`
- `CORS_ALLOWED_ORIGINS`
- `RATE_LIMIT_ENABLED=true`
- `RATE_LIMIT_WINDOW_SECONDS`
- `RATE_LIMIT_CHAT_REQUESTS`
- `RATE_LIMIT_UPLOAD_REQUESTS`
- `BOOTSTRAP_DEMO_SOURCE_LIBRARY=false`

Production runtime startup must not automatically seed the demo/bootstrap source library. Seed the
bootstrap excerpts only as an explicit operator action, such as `-SeedGoldenEvals -RunGoldenEvals`
or `python scripts/bootstrap_source_library.py`, then audit the resulting citable source gate before
using it for regulatory answers.

S3-compatible object storage values are required for a production-ready deployment:
`S3_ENDPOINT_URL`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, optional
`S3_SESSION_TOKEN`, and bucket names. If they are present in the shell, the script upserts those too.
Supabase Storage S3 endpoints include a path such as
`https://<project-ref>.storage.supabase.co/storage/v1/s3`; copy the endpoint, region, and generated
server-side S3 access key pair from the Supabase Storage S3 settings. Supabase session-token auth is
also supported by setting `S3_ACCESS_KEY_ID` to the project ref, `S3_SECRET_ACCESS_KEY` to the anon
key, and `S3_SESSION_TOKEN` to a valid Supabase JWT. Without durable storage credentials, `/ready`
remains red and protected routes remain fail-closed because uploads and exports would otherwise be
stored on ephemeral serverless disk.
Protected routes use the same live S3 bucket probe as `/ready`, so configured credentials alone do
not unblock API traffic if any required bucket is missing or not writable.
Document uploads are type-checked, size-limited, filename-sanitized, and stored with content-addressed
object keys so repeated client filenames cannot overwrite earlier raw evidence. Local and S3 storage
adapters reject traversal-style object keys.
They also reuse the database connectivity/schema, Alembic migration head, and PostgreSQL extension
checks, so a deployed API does not serve protected traffic until migrations and required extensions
are in place.
When `RQ_ENABLED=true`, protected routes also require the Redis/RQ ping check to pass before traffic
is admitted.

After env setup it optionally deploys and checks `https://api.cuz.fail/ready`. A passing `/ready`
only proves the API dependency gate. `scripts/run_golden_evals.py` upserts the checked-in manifest
from `tests/gold` before running by default, so the release gate measures current repo expectations
instead of stale database rows; pass `--skip-seed-manifest` only for diagnostics against already-stored
cases. `-SeedGoldenEvals -RunGoldenEvals` seeds `tests/gold` into the durable database, explicitly
ensures the bootstrap source library is present for that eval run, and records a retrieval eval run.
Backup/restore blockers still require a real backup run and a tested restore with audit events
recorded by the backup/restore scripts.

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
