# Production Deployment

Date: 2026-06-10 (updated — Vercel retired, VPS is sole production target)

This is the operator guide for the live VPS deployment at `lotfile.app`. It is
written for Codex/PowerShell on Steven's Windows machine and the
VPS `srv1625369`. Vercel is retired — do not deploy there.

## Authority

- Follow `AGENTS.md` and `docs/CODEX_DEPLOY_SYNC_RUNBOOK.md`.
- Steven has granted standing approval for deploy, build, commit, push, VPS, DNS, CI, and
  infra work that follows those docs.
- Do not pause for permission. Preserve unpushed work, apply sensible fallbacks, and
  report the result.

## Where Commands Run

- PowerShell/Codex is the local operator shell.
- `ssh draftcheck '...'` runs the quoted command on the VPS.
- An interactive VPS shell starts with:

```powershell
ssh draftcheck
```

- The production checkout on the VPS is:

```text
/srv/draftcheck/app
```

- Caddy serves the web UI from:

```text
/srv/draftcheck/app/web/dist
```

The most common mistake is running VPS build commands in Windows PowerShell without SSH.
If a command changes `/srv/draftcheck/app`, run it through `ssh draftcheck` or after
opening `ssh draftcheck`.

## SSH Target

The local SSH config should contain:

```sshconfig
Host draftcheck
  HostName 76.13.209.160
  User root
  IdentityFile C:\Users\steve\.ssh\id_ed25519
  IdentitiesOnly yes
  ServerAliveInterval 30
  ServerAliveCountMax 4
```

Check it with:

```powershell
ssh -o BatchMode=yes draftcheck hostname
```

Expected output:

```text
srv1625369
```

## Current Production Shape

- Web URL: `https://lotfile.app/`
- API URL: `https://lotfile.app/api/v1`
- VPS host: `srv1625369`
- VPS IP: `76.13.209.160`
- Repo checkout: `/srv/draftcheck/app`
- Live static root: `/srv/draftcheck/app/web/dist`
- UI deploy: `infra/v3/deploy-web-only.sh`; no Vercel, no container restart.
- API health check: `https://lotfile.app/api/v1/health`
- Document upload/parser cap: 100 MB by default; Caddy allows 250 MB. Override with
  `DRAFTCHECK_MAX_DOCUMENT_BYTES` or `DRAFTCHECK_MAX_DOCUMENT_MB` only after checking
  worker memory headroom.
- Vercel: RETIRED

## UI-Only Deploy From Main

Use this when `origin/main` already contains the desired frontend and the live site is
serving an old compiled `web/dist`. The script refuses to deploy unless
`VITE_CHECKOUT_URL` is set to a real Stripe Payment Link in the VPS env.

```powershell
ssh draftcheck 'bash /srv/draftcheck/app/infra/v3/deploy-web-only.sh'
```

## Required Verification

Run these from local PowerShell/Codex after the deploy:

```powershell
cd web
npm run verify:launch:live
cd ..

curl.exe -s https://lotfile.app/ |
  Select-String -Pattern '<title>[^<]*</title>' -AllMatches |
  ForEach-Object { $_.Matches.Value }

curl.exe -s -w "`nHTTP_STATUS=%{http_code}`n" https://lotfile.app/api/v1/health
curl.exe -s -w "`nHTTP_STATUS=%{http_code}`n" https://lotfile.app/api/v1/ready
```

Expected:

```text
Live launch verification passed for https://lotfile.app.
<title>LotFile - WA R-Code & Planning Compliance Checker</title>
{"status":"ok","db":"ok"}
HTTP_STATUS=200
{"status":"ok","service":"draftcheck-api",...}
HTTP_STATUS=200
```

Also load `https://lotfile.app/` at desktop width. The current LotFile UI should show:

- Left sidebar.
- Full-width content area across the remaining viewport.
- One address/question box on the home screen.
- Bottom status pills for `api` and `ready`.

For launch-page UI releases, also load `https://lotfile.app/` and verify the public
landing page no longer shows the orange advisory badge, the orange advisory disclaimer
callout, or obvious advisory/no-finality marketing copy.

## Troubleshooting

### Dubious Ownership

Root may see `/srv/draftcheck/app` as unsafe because the checkout is owned by another
user. Fix it once:

```powershell
ssh draftcheck 'git config --global --add safe.directory /srv/draftcheck/app'
```

### Site Still Shows The Old UI

The code may be current but `web/dist` may be stale. Re-run the UI-only deploy and verify
the local file on the VPS:

```powershell
ssh draftcheck "grep -o '<title>[^<]*</title>' /srv/draftcheck/app/web/dist/index.html"
```

Expected:

```text
<title>LotFile - WA R-Code & Planning Compliance Checker</title>
```

### Build Fails

Do not leave a half-built `dist`. The deploy script above backs up the old static files and
restores them on failure. Report the full `npm run build` error and the deployed SHA that
was attempted.

### API Health Fails

Check the VPS compose state:

```powershell
ssh draftcheck 'cd /srv/draftcheck/app/infra/v3 && docker compose ps'
```

Do not add `/v1` shims, Vercel routes, or production-reachable password/dev-login routes to
work around API issues. Fix the `/api/v1` service. (The dev-only `/api/v1/auth/dev-login`
added 2026-06-08 is exempt: it returns 404 whenever `app_env=production`.)

## Never Do During Deploy

- Do not touch Vercel for the VPS app.
- Do not commit `*.db`, `*.sqlite*`, `.env*` except `.env.example`, `.storage/`,
  `node_modules/`, `web/dist/`, or local agent state.
- Do not force-push, rewrite history, or run `git clean` unless Steven explicitly says so
  in the current session.
- Do not discard unpushed VPS work silently. Stash it or branch and push it, then report it.
- Do not add password/dev-login routes that are reachable in production. (The dev-only
  login added 2026-06-08 is hard-disabled — 404 — when `app_env=production`.)

## Guest Org Hygiene (cron)

Guest sessions each create a throwaway org (slug `guest-*`). Purge stale ones nightly on
the VPS so guest data does not accumulate:

```
0 3 * * * cd /srv/draftcheck/app && DATABASE_URL=postgresql+psycopg://... .venv/bin/python scripts/purge_guest_orgs.py >> /var/log/draftcheck/purge_guest_orgs.log 2>&1
```

Retention defaults to 14 days (`GUEST_ORG_RETENTION_DAYS`). Deleting the org cascades to
its users, sessions, projects, and `guest_usage` rows.
