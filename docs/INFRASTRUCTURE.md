# Infrastructure Foundation

The V3 repository includes the backend core and the LotFile web UI under `web/`. Caddy serves the
production web UI from the compiled static artifact at `/srv/draftcheck/app/web/dist` on the VPS.
See `docs/PRODUCTION_DEPLOYMENT.md` for the current `lotfile.app` deploy procedure.

## Local stack

Start the local services from the repository root:

```powershell
docker compose up -d --build
```

The local stack mirrors the V3 production shape (`infra/v3/compose.yml`):

- `db`: custom `postgis/postgis:16-3.5` image (`infra/v3/db/Dockerfile`) with pgvector built in.
- `api`: FastAPI app (`infra/v3/app.Dockerfile`); runs `alembic upgrade head`, applies the
  Procrastinate schema, then serves `draftcheck.api.main:app` on port 8000.
- `worker`: Procrastinate worker consuming all queues (the production split between `worker`
  and `hermes` queue groups is collapsed into one local worker).

There is no redis, minio, or local caddy — the V3 stack uses PostgreSQL for queues
(Procrastinate) and a local content-addressed storage tree (`OBJECT_STORAGE_ROOT`).

`GET /api/v1/ready` is the dependency gate: database connectivity/schema, Alembic migration
head, required PostgreSQL extensions (`postgis`, `vector`), and content-storage read/write.
Compose health checks use it.

Alternatively, run the API on the host against the compose database:

```powershell
docker compose up -d db
make migrate
make dev
```

## Database extensions

The DB image is custom because `postgis/postgis` does not include pgvector. On first database
initialization, `infra/v3/db/init-extensions.sql` runs:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
```

For an existing Postgres volume created before this image, run the extension creation manually or
recreate the local volume after confirming no local data is needed.

## Backups and restores

Production backups are owned by `infra/v3/backup/` (systemd timer + `pg_dump` + restic, with a
documented restore drill). See `infra/v3/backup/README.md` and `docs/ops/restore-drill-template.md`.
Local volumes are disposable; recreate them rather than building local backup tooling.

## VPS shape

The live VPS is `srv1625369` (`76.13.209.160`) and is reachable from the operator machine as
`ssh draftcheck`.

The active production checkout is `/srv/draftcheck/app`. Caddy terminates HTTP/TLS, proxies
`/api/v1` to the backend, and serves `lotfile.app` from `/srv/draftcheck/app/web/dist`
(`infra/v3/Caddyfile` is the source of truth; the global reverse proxy is tracked at
`infra/blockwise-caddy/Caddyfile`).

For UI-only releases, rebuild `web/dist` on the VPS after resetting the checkout to `origin/main`.
No container restart is required for static frontend changes.

## Production bootstrap (VPS-only)

Vercel is retired. The only production target is the VPS at `76.13.209.160` serving `lotfile.app`.
Deploys run `deploy/vps_deploy.sh`, which delegates to `infra/v3/deploy.sh` (see
`.github/workflows/deploy.yml` and `docs/PRODUCTION_DEPLOYMENT.md`).

To deploy or redeploy the UI manually:

```bash
ssh draftcheck 'cd /srv/draftcheck/app && git fetch origin && git reset --hard origin/main && cd web && npm ci && npm run build'
```

If the Caddyfile changed, reload Caddy:

```bash
ssh draftcheck 'cd /srv/draftcheck/app/infra/v3 && sudo docker compose exec internal_caddy caddy reload --config /etc/caddy/Caddyfile'
```

## Embeddings

Semantic retrieval is opt-in. The default `EMBEDDING_PROVIDER=mock` keeps tests and offline
development deterministic. To use OpenAI-compatible embeddings, set `EMBEDDING_PROVIDER=openai`,
`OPENAI_API_KEY`, and optionally `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, `OPENAI_BASE_URL`, and
`EMBEDDING_TIMEOUT_SECONDS`, then re-embed sources against the durable database. Retrieval filters
vector candidates by provider and model, so old mock embeddings are never mixed into
OpenAI-backed searches.

Do not store paid Australian Standards full text in content storage or backups. Store only allowed
public metadata and access notes for those sources.
