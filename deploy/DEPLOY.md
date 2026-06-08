# Deploying cuz.fail

Three pieces: frontend on Vercel, Postgres on Supabase, FastAPI backend on the VPS.

## 1. Frontend — Vercel (done by repo)

The Vercel project `cuz.fail` serves the static `ui/` folder. Its project
Root Directory is `ui`, and every push to `main` deploys production
automatically. Keep `.vercelignore` from excluding `ui`; Vercel still reads
the repository-level ignore file before the frontend build.

If the project must be reconnected: Vercel project -> Settings -> Git ->
connect `stevenshelley58-afk/cuz.fail`, set Root Directory to `ui`, and leave
Git deployments enabled for the frontend project.

Later, to let the frontend call the API without CORS pain, add to vercel.json:

    "rewrites": [{ "source": "/api/:path*", "destination": "https://api.cuz.fail/v1/:path*" }]

## 2. Database — Supabase (already done)

Schema is applied (alembic `0001_initial_metadata`, 31 tables). The backend's
startup `create_all` is a no-op against it. You only need the **database
password** for the connection string (Dashboard -> Settings -> Database ->
Reset password if unknown).

Security note: RLS is currently disabled on all tables. The FastAPI backend
connects directly to Postgres and is unaffected by RLS, so enabling it is the
safe default to lock the tables away from the Supabase anon-key data API.
Run in the SQL editor when ready (one line per table):

    ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;

## 3. Backend — VPS (alongside blockwise)

The API container binds 127.0.0.1:8088 (chosen to stay clear of blockwise —
change in `deploy/docker-compose.vps.yml` if taken).

### Get the code onto the VPS

Option A — once the backend source is pushed to this repo:

    git clone https://github.com/stevenshelley58-afk/cuz.fail.git /opt/cuz

Option B — straight from the dev machine (works today, before any push):

    # PowerShell on the dev PC
    scp -r C:\Dev\Cuz user@YOUR_VPS:/opt/cuz

### Run it

    cd /opt/cuz
    cp deploy/env.production.example deploy/.env
    nano deploy/.env        # paste the real DATABASE_URL (see Supabase section)
    docker compose -f deploy/docker-compose.vps.yml --project-name cuz up -d --build

### Verify

    curl http://127.0.0.1:8088/v1/me          # {"id":"dev-user",...}
    curl http://127.0.0.1:8088/openapi.json | head -c 200

Swagger UI at http://127.0.0.1:8088/docs (via SSH tunnel) or through the
reverse proxy once `deploy/nginx-cuz.conf` (or the Caddy one-liner) is in
place pointing api.cuz.fail at 127.0.0.1:8088.

### Notes

- The worker entrypoint is still a placeholder; no worker container is
  defined yet. Add one mirroring the api service (command:
  `python -m draftcheck_worker.main`) when Hermes/queues go live.
- Database password lives only in `deploy/.env` on the VPS (gitignored).
- Container persists uploads/exports in the `cuz_storage` volume.
