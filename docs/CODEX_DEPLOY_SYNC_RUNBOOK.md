# Codex Runbook — Sync Local → Git → GitHub → VPS (Autonomous)

Date: 2026-06-08
Goal: get the V3 workspace committed, pushed, CI-green, deployed to the VPS, and verified in
sync end to end — with zero human approvals. Authority: `docs/MASTER_REBUILD_PLAN.md` and
`AGENTS.md`. Read both first.

## STANDING APPROVAL — do not ask, do not wait

The operator (Steven) pre-approves every step in this runbook, recorded 2026-06-08. There are
no human checkpoints. Never pause for confirmation, never end a session with "shall I
proceed?". If a step needs missing information or credentials, apply its fallback, continue
with everything else, and list what remains in the final report. Decisions you make along the
way are logged in commit/PR descriptions, not asked about.

Credentials are discovered, never requested interactively:

```text
VPS        $DRAFTCHECK_VPS_HOST or `Host draftcheck` in ~/.ssh/config (root@76.13.209.160)
DNS        $CLOUDFLARE_API_TOKEN (or provider equivalent) if present → automate; else report records
Restic     $RESTIC_REPOSITORY + $RESTIC_PASSWORD + B2/R2 keys if present → configure; else local-only
Vercel     RETIRED — no token needed; no Vercel deploys.
GitHub     gh auth status (already authenticated on this machine)
```

## Command execution model

- Local PowerShell/Codex is the operator shell. Use it for public checks such as
  `curl https://app.cuz.fail/` and for launching SSH commands.
- VPS deploy commands run on the server via `ssh draftcheck '...'`. Anything inside the
  quoted command executes on `srv1625369` (`root@76.13.209.160`), not on Windows.
- The production app checkout is `/srv/draftcheck/app`. Caddy serves the web UI directly
  from `/srv/draftcheck/app/web/dist`, so a UI-only deploy is a repo reset plus
  `cd web && npm ci && npm run build`; no Vercel action and no container restart are needed.
- Do not paste deploy code into Vercel. If a command mutates `/srv/draftcheck/app`, run it
  through `ssh draftcheck` or from an interactive shell after `ssh draftcheck`.
- For the current production runbook and troubleshooting checklist, also read
  `docs/PRODUCTION_DEPLOYMENT.md`.

Current ground truth (verified 2026-06-08):

```text
Local repo      C:\Dev\Cuz, branch main. The active V3 workspace is now on origin/main;
                local dirty/untracked work may exist and must be preserved.
Remote          origin = https://github.com/stevenshelley58-afk/cuz.fail.git (main exists)
CI              .github/workflows/ci.yml exists on origin/main.
VPS             srv1625369 is reachable as `ssh draftcheck`; app.cuz.fail serves
                `/srv/draftcheck/app/web/dist` from the VPS.
Web UI          web/index.html title is `LotFile`; live deploy requires rebuilding web/dist
                on the VPS because Caddy serves compiled files.
Vercel          RETIRED. Only deploy target is the VPS. UI deploy = `cd web && npm ci && npm run build`
                into `/srv/draftcheck/app/web/dist`. Reload Caddy after if Caddyfile changed.
V3 app          Phases 0–2: auth, sources, address/spatial. Product routes are 501 stubs.
```

## Automated tripwires (not approvals — enforced by tooling, cost zero time)

- Never stage/commit: `*.db`/`*.sqlite*` (incl. `draftcheck.db`), `.storage/`, `data/corpus/`,
  `.vercel/`, `.env`/`.env.*` (except `.env.example`), `node_modules/`, `web/dist/`, `.codex/`.
  `.gitignore` + `scripts/precommit_guard.py` enforce this; GitHub would reject the 153 MB DB
  anyway. Do not weaken either.
- Never: force-push, rewrite history, `git clean`, delete legacy `apps/ packages/ api/ ui/`
  (M1 work), add `create_all` to V3, mount anything besides `/api/v1` in the new app.
  (Exception, operator decision 2026-06-08: a dev-only `/api/v1/auth/dev-login` is allowed;
  it is hard-disabled — 404 — when `app_env=production`.)
- Secrets are generated on the VPS, live only in `infra/v3/.env` there, never committed.

Anything not on those two lists is yours to do without asking.

---

## Phase A — Local → GitHub

### A0. (Vercel guard — RETIRED)

Vercel is retired. No guard steps needed. The only deploy target is the VPS.
UI deploy: `cd web && npm ci && npm run build` into `/srv/draftcheck/app/web/dist`.

### A1. Preflight

```bash
git config user.name && git config user.email     # set sensible values if empty
git fetch origin && git status --short | head
```

### A2. Stage everything legitimate, prove nothing forbidden is staged

```bash
git add -A
git status --porcelain | grep -Ei "\.db|\.sqlite|\.storage/|data/corpus/|\.vercel/|^\?\? \.env|node_modules" && echo "FORBIDDEN PATH STAGED - FIX" || echo "clean"
python scripts/precommit_guard.py $(git diff --cached --name-only)
git diff --cached --stat | tail -5
```

If the guard flags anything: unstage, extend `.gitignore` if appropriate, re-run. Decide
yourself; note it in the commit body.

### A3. Full local gate (same as CI)

```bash
pip install -e ".[dev]"
python -m ruff check .
python -m mypy src
lint-imports --config pyproject.toml
python -m pytest -q                               # expect ~342+ passing
( ! grep -R "create_all" src web )   # dev-login is intentionally present (off in prod); see ci.yml
cd web && npm ci && npm run build && cd ..
git diff --check
```

Failures: fix them yourself if the fix is unambiguous and in-plan; otherwise quarantine the
failing path from this commit, file the issue in the final report, and keep moving.

### A4. Commit, push, PR with auto-merge (no waiting on a human)

```bash
git checkout -b v3/materialise-workspace
git commit -m "V3 materialisation: phases 0-2 (skeleton, CI, infra, auth, sources, address/spatial) + plan docs + Vercel git-deploy guard"
git push -u origin v3/materialise-workspace
gh pr create --title "V3 materialisation + sync" --body "Full V3 workspace into version control. No legacy deletions. Authority: docs/MASTER_REBUILD_PLAN.md. Standing approval: docs/CODEX_DEPLOY_SYNC_RUNBOOK.md."
gh pr merge --auto --squash --delete-branch       # merges the moment CI is green
gh pr checks --watch                              # observe; fix-forward if CI fails
git checkout main && git pull
git tag v3-sync-2026-06-08 && git push origin v3-sync-2026-06-08
```

Small follow-up commits (deploy.sh, CLI, doc fixes) may go straight to main; CI runs on push.

Exit criteria A: `git status` clean; `main == origin/main`; CI green; full tree on GitHub.

---

## Phase B — VPS deploy

Resolve the target from `$DRAFTCHECK_VPS_HOST` or `~/.ssh/config` (`Host draftcheck`).
**Fallback if no VPS is reachable:** complete Phases A and the deploy.sh/CLI work, generate
`infra/v3/.env.production.template`, and put exact provisioning commands in the final report.
Do not block anything else on this.

### B0. UI-only redeploy from current main

Use this when the API/container stack is already live and only `app.cuz.fail` is serving an old
compiled frontend. Preserve unpushed VPS work first.

```bash
ssh draftcheck 'set -euo pipefail
git config --global --add safe.directory /srv/draftcheck/app
cd /srv/draftcheck/app
git status --porcelain
git branch -a
git stash list
if [ -n "$(git status --porcelain -- web)" ]; then
  git stash push -m "pre-deploy web changes $(date -Is)" -- web
fi
git fetch origin
git reset --hard origin/main
cd web
npm ci
npm run build'
```

Verification:

```bash
curl -s https://app.cuz.fail/ | grep -o '<title>[^<]*</title>'     # <title>LotFile</title>
curl -s https://api.cuz.fail/api/v1/health                         # 200 / status ok
```

### B1. Harden + install (once, idempotent)

```bash
ssh draftcheck 'sudo apt-get update && sudo apt-get install -y ufw fail2ban unattended-upgrades git curl
sudo ufw allow OpenSSH && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw --force enable
curl -fsSL https://get.docker.com | sudo sh
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash - && sudo apt-get install -y nodejs
sudo mkdir -p /srv/draftcheck/storage /srv/draftcheck/backups'
```

Also disable SSH password auth in `/etc/ssh/sshd_config` and restart ssh.

### B2. Clone + configure

```bash
ssh draftcheck 'sudo mkdir -p /srv/draftcheck && sudo chown $USER /srv/draftcheck
git clone https://github.com/stevenshelley58-afk/cuz.fail.git /srv/draftcheck/app
cd /srv/draftcheck/app && git checkout main
printf "POSTGRES_PASSWORD=%s\nAUTH_TOKEN_HASH_PEPPER=%s\nHERMES_SPEND_CAP_CENTS=500\n" "$(openssl rand -hex 32)" "$(openssl rand -hex 32)" > infra/v3/.env
chmod 600 infra/v3/.env'
```

Defaults already target `api.cuz.fail`/`app.cuz.fail`, storage `/srv/draftcheck/storage`,
CORS `https://app.cuz.fail` (`infra/v3/compose.yml`).

### B3. Build + start

```bash
ssh draftcheck 'cd /srv/draftcheck/app/web && npm ci && npm run build
cd ../infra/v3 && sudo docker compose build && sudo docker compose up -d --wait && sudo docker compose ps'
```

Caddy cert errors before DNS exists are expected; ignore until Phase C.

### B4. Prove the database and migrations (closes the plan's open risk #1)

```bash
ssh draftcheck 'cd /srv/draftcheck/app/infra/v3
sudo docker compose exec db psql -U draftcheck -c "SELECT extname FROM pg_extension;"   # postgis, vector
sudo docker compose exec api alembic current
sudo docker compose exec api alembic downgrade base
sudo docker compose exec api alembic upgrade head
sudo docker compose exec api python -c "import urllib.request; print(urllib.request.urlopen(\"http://127.0.0.1:8000/api/v1/ready\", timeout=5).read())"'
```

Record the result in a dated note under `docs/` (commit it).

### B5. Backups

```bash
ssh draftcheck "cat | sudo tee /etc/cron.d/draftcheck-backup <<'EOF'
15 2 * * * root cd /srv/draftcheck/app/infra/v3 && docker compose exec -T db pg_dump -U draftcheck -Fc draftcheck > /srv/draftcheck/backups/draftcheck-\$(date +\%F).dump
EOF"
```

If `$RESTIC_REPOSITORY`/`$RESTIC_PASSWORD` (+ B2/R2 keys) are present: configure nightly
`restic backup /srv/draftcheck/backups /srv/draftcheck/storage`, weekly `restic check`, run
one restore drill into a scratch container, and record it. If absent: local dumps only;
list "offsite backups pending credentials" in the report and continue.

### B6. Create `infra/v3/deploy.sh`, commit to main

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /srv/draftcheck/app
git fetch origin && git reset --hard origin/main
(cd web && npm ci && npm run build)
cd infra/v3
docker compose build api
docker compose up -d --wait
docker compose exec api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/ready', timeout=5)"
echo "deployed $(git -C /srv/draftcheck/app rev-parse --short HEAD)"
```

### B7. Auth bootstrap — implement, don't defer

The deployed shell is unusable without a login path: magic-link requires a pre-provisioned
`owner`/`operator` and the planned `cli login-link` (plan §5.1) doesn't exist yet. You are
authorized to implement it now, per plan: `src/draftcheck/cli.py` with `login-link` issuing a
one-time bootstrap URL for a provisioned owner (email from `$DRAFTCHECK_OWNER_EMAIL`, default
`stevenshelley58@gmail.com`), wired to the existing identity store and token machinery, with
tests, merged through CI like everything else. Then run it on the VPS and verify a session
cookie round-trip against `https://api.cuz.fail` once DNS is live.

Exit criteria B: compose healthy; postgis+vector present; alembic round-trip proven;
`/api/v1/ready` 200; backup cron live; deploy.sh + cli login-link merged.

---

## Phase C — DNS cutover (autonomous; rollback is two A records)

1. If a DNS provider token is available (`$CLOUDFLARE_API_TOKEN` or equivalent): drop TTL on
   `api.cuz.fail` + `app.cuz.fail` to 300, wait out the old TTL, then point both A records at
   the VPS IP — via API, no human. If no token: put the exact records (host → IP, TTL 300) in
   the final report as the single remaining manual action, and continue with everything else.
2. Verify once DNS resolves (Caddy fetches certs automatically):

```bash
curl -fsS https://api.cuz.fail/api/v1/ready
curl -fsS https://app.cuz.fail/ | head -5
curl -s -o /dev/null -w "%{http_code}" https://api.cuz.fail/api/v1/projects   # 401/501, not 404
```

3. VPS is the only production target. Rollback = revert the two A records. Legacy `ui/` pages
   call `api.cuz.fail/v1` and will break at cutover — accepted; they are design references,
   pre-M1, with no real users. Do not build a `/v1` proxy overlay unless the operator asks.
4. Vercel is retired. No disconnect step needed; no Vercel deploys fire.
5. Legacy Vercel files (`vercel.json`, `api/index.py`, root `index.py`, `.vercelignore`,
   `scripts/configure-vercel-production.ps1`) remain archived under `deploy/legacy-vercel/`
   for reference. (`.vercel/` stays local-only; gitignored.)

---

## Phase D — Final sync assertion (end the run with this table)

```bash
git status --porcelain                      # empty
git rev-parse main origin/main              # identical
gh run list --branch main --limit 1         # CI: success
ssh draftcheck 'git -C /srv/draftcheck/app rev-parse HEAD'           # == origin/main
ssh draftcheck 'cd /srv/draftcheck/app/infra/v3 && sudo docker compose ps'
curl -fsS https://api.cuz.fail/api/v1/ready
```

In sync = local main == origin/main == VPS HEAD, CI green, compose healthy, ready endpoint
200, no Vercel auto-deploys.

## Final report (instead of asking questions along the way)

End with: what was deployed (commit, tag), gate results, decisions taken autonomously, and
the short list of items blocked on missing credentials (VPS host, DNS token, restic creds —
whichever applied), each with the exact command Steven runs once to unblock it.
