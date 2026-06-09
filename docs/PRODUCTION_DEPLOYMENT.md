# Production Deployment

Date: 2026-06-10 (updated — Vercel retired, VPS is sole production target)

This is the operator guide for the live VPS deployment at `lotfile.app` and
`api.cuz.fail`. It is written for Codex/PowerShell on Steven's Windows machine and the
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
- API URL: `https://api.cuz.fail/api/v1`
- VPS host: `srv1625369`
- VPS IP: `76.13.209.160`
- Repo checkout: `/srv/draftcheck/app`
- Live static root: `/srv/draftcheck/app/web/dist`
- UI deploy: rebuild `web/dist` on VPS; no Vercel, no container restart.
- API health check: `https://api.cuz.fail/api/v1/health`
- Vercel: RETIRED

## UI-Only Deploy From Main

Use this when `origin/main` already contains the desired frontend and the live site is
serving an old compiled `web/dist`.

```powershell
@'
set -euo pipefail
git config --global --add safe.directory /srv/draftcheck/app
cd /srv/draftcheck/app

echo "== preflight =="
git status --porcelain
git branch -a
git stash list

if [ -n "$(git status --porcelain -- web)" ]; then
  git stash push -m "pre-deploy web changes $(date -Is)" -- web
fi

backup_dir=""
if [ -d web/dist ]; then
  backup_dir="$(mktemp -d /tmp/draftcheck-web-dist.XXXXXX)"
  cp -a web/dist/. "$backup_dir"/
fi

echo "== deploy =="
git fetch origin
git reset --hard origin/main
deploy_sha="$(git rev-parse HEAD)"

cd web
npm ci
if npm run build; then
  [ -n "$backup_dir" ] && rm -rf "$backup_dir"
else
  status=$?
  if [ -n "$backup_dir" ] && [ -d "$backup_dir" ]; then
    rm -rf dist
    mkdir -p dist
    cp -a "$backup_dir"/. dist/
    rm -rf "$backup_dir"
  fi
  exit "$status"
fi

echo "deployed $deploy_sha"
'@ | ssh draftcheck "tr -d '\r' | bash -s"
```

## Required Verification

Run these from local PowerShell/Codex after the deploy:

```powershell
curl.exe -s https://lotfile.app/ |
  Select-String -Pattern '<title>[^<]*</title>' -AllMatches |
  ForEach-Object { $_.Matches.Value }

curl.exe -s -w "`nHTTP_STATUS=%{http_code}`n" https://api.cuz.fail/api/v1/health
```

Expected:

```text
<title>LotFile</title>
{"status":"ok","service":"draftcheck-api","version":"0.1.0"}
HTTP_STATUS=200
```

Also load `https://lotfile.app/` at desktop width. The current LotFile UI should show:

- Left sidebar.
- Full-width content area across the remaining viewport.
- One address/question box on the home screen.
- Bottom status pills for `api` and `ready`.

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
<title>LotFile</title>
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
