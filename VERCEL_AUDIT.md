# DraftCheck WA Vercel Audit

Date: 2026-06-07

Authority: supporting cutover inventory for `docs/MASTER_REBUILD_PLAN.md`.

## Current Vercel Surface

Vercel is legacy transition infrastructure and must not be expanded for V3.

Live exception as of 2026-06-08: the public `cuz.fail` frontend remains a
Vercel static project during transition. Its Vercel Root Directory is `ui`,
Git deployments are enabled, and `.vercelignore` must not exclude `ui`.
`api.cuz.fail` remains a separate Vercel API project until the VPS cutover is
complete.

| Path | Status | Notes |
|---|---|---|
| `vercel.json` | Present | Static frontend config for the `cuz.fail` transition deployment. |
| `api/index.py` | Present | Adds legacy package roots to `sys.path`, copies `draftcheck.db` to `/tmp/draftcheck.db`, sets SQLite/object-storage env vars, imports `draftcheck_api.main:app`. |
| `index.py` | Present | Similar root-level Vercel entrypoint; copies `draftcheck.db` to `/tmp/draftcheck.db`. |
| `.vercelignore` | Present | Excludes many local folders plus docs/data/tests/deploy, but this is not a V3 deployment path. |
| `.vercel/` | Present locally | Contains project metadata, output diagnostics, local Python venv/cache, and `.env.production.local`; excluded from Git. |
| `scripts/configure-vercel-production.ps1` | Present | Legacy deployment configuration helper. |

## Risks

- Vercel entrypoints depend on the local SQLite seed database, which is explicitly not a V3
  production path.
- `.vercel/.env.production.local` is local environment material and must never be staged.
- The Vercel route surface hides `/api/v1` cutover mistakes because it rewrites all traffic.
- Keeping Vercel connected after VPS cutover can cause accidental deployments from old paths.

## Required Cutover Steps (autonomous — operator standing approval 2026-06-08)

Agents execute these without per-step human approval (see `AGENTS.md` Operator Standing
Approval and `docs/CODEX_DEPLOY_SYNC_RUNBOOK.md`). The older V3 freeze used
`vercel.json` `"git": {"deploymentEnabled": false}`; do not reapply that to
the public `cuz.fail` frontend while it is still serving production traffic.

```text
1. Verify VPS deploy and Caddy routes are green.
2. Drop DNS TTL, then switch app.cuz.fail and api.cuz.fail to the VPS (via DNS provider API
   when a token is available; otherwise report the exact records as the one manual action).
3. Dual-run window is discretionary: the Vercel deployment stays live purely as the rollback
   target (rollback = revert two A records). Default is to proceed as soon as checks are green.
4. Disconnect the Vercel integration (API when token available; the vercel.json guard already
   prevents git deploys otherwise).
5. Archive, do not silently delete, vercel.json, api/index.py, root index.py, .vercelignore,
   and scripts/configure-vercel-production.ps1 (move under deploy/legacy-vercel/), only after
   the VPS answers on both domains.
```

Acceptance: no Vercel deployment fires on push after cutover, and all public new-app traffic uses
`/api/v1` through Caddy on the VPS.
