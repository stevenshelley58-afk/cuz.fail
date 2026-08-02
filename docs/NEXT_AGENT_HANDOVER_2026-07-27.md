# Next-agent handover — verified state and remaining work

Date: 2026-07-27 (Australia/Perth)  
Repository: `C:\Dev\Cuz` / `stevenshelley58-afk/cuz.fail`

## Why this handover exists

The operator asked for a current audit of the latest work and then stopped the audit
to hand it to the next agent. This file records only evidence verified during that
audit. No product, database, GitHub, or VPS mutations were made.

Primary authority remains:

- `docs/MASTER_REBUILD_PLAN.md`
- `AGENTS.md`
- `docs/CODEX_DEPLOY_SYNC_RUNBOOK.md`
- `docs/PRODUCTION_DEPLOYMENT.md`

## Source-control and delivery state

- `origin/main`: `121ff524f082d08609aa67451d1a692fac324e0b`
  (`fix: exclude road polygons from property zones (#157)`).
- Local branch: `codex/planwa-zone-facts` at
  `2188f576ad35c57d1492981a29ed21cd49fe8c9a`.
- The local HEAD and `origin/main` have identical Git tree hashes
  (`73e21887cfab4223da77640b0ac71fa40eb77d0c`); only commit ancestry differs
  because PR #157 was squash-merged.
- Preserve the existing untracked local paths:
  `.ops/`, `.superpowers/`, `.worktrees/`, `reports_tmp_register_fix.py`,
  and `tunnel.log`. They were not inspected as operator-owned disposable data
  and must not be deleted.
- The VPS checkout is on `121ff524...` and tracks `origin/main`.
- The VPS contains untracked operational reports under `/srv/draftcheck/app/reports/`.
  Preserve them.

Latest merged PRs:

1. #154 — rule-coverage phases and governance hardening.
2. #155 — parcel-scoped rule selection plus versioned PlanWA validation.
3. #156 — ignore road/reserve boundary artefacts in PlanWA comparison.
4. #157 — omit road/reserve polygons from user-facing development-zone facts.

Latest GitHub state:

- Main CI run `30237063561`: success.
- Latest deploy run `30237132394`: success.
- Two immediately preceding deploys failed:
  - `30236402325`: concurrent Docker Compose recreation caused a container-name
    conflict.
  - `30236852432`: all four GitHub-hosted-runner SSH attempts timed out.
- Production ultimately converged to the correct SHA and is currently healthy.

## Verification completed

Tracked product paths passed:

- Ruff: pass (`src`, `scripts`, `tests`).
- mypy: pass, 124 source files.
- Import-linter: pass, 1 contract kept.
- pytest: **551 passed, 29 skipped**, 2 deprecation warnings.
- Web TypeScript/Vite production build: pass.

Running Ruff across the entire dirty workspace fails only in the untracked
`.ops/extract_rcodes_v3.py` copy (two E741 ambiguous `l` variable findings).
Do not confuse that with a tracked-code or CI failure.

Production:

- `https://lotfile.app/api/v1/health`: HTTP 200, DB OK.
- `https://lotfile.app/api/v1/ready`: HTTP 200, all reported checks OK.
- Site title and compiled frontend are current.
- Compose services are up: API healthy, DB healthy, worker, Hermes, and internal
  Caddy running.
- Alembic is at `0020_add_rule_coverage_columns` (head).

## Critical finding 1 — production development login is exposed

This is the first task for the next agent.

Verified production environment state:

- `DRAFTCHECK_ENV=staging` (not production).
- `DEV_LOGIN_USERNAME` unset.
- `DEV_LOGIN_PASSWORD` unset.
- `AUTH_TOKEN_HASH_PEPPER` set.
- `SMTP_HOST` unset.
- `SENTRY_DSN` unset.

Verified HTTP behavior using deliberately invalid credentials:

- `/api/v1/auth/dev-login` returns **401**, proving that the route is mounted and
  processing credentials in production.
- `/api/v1/auth/magic-link/request` returns **404**, so real durable sign-in
  remains disabled.

The current handler in `src/draftcheck/api/auth.py` uses hard-coded fallback
credentials when the two development-login variables are absent and does not
check `app_env` before authenticating. Therefore the deployed configuration is
unsafe even though the invalid audit credentials did not authenticate.

Required fix:

1. Make `/auth/dev-login` return 404 unless `app_env` is explicitly local or
   development.
2. Remove all fallback credentials; require explicit development-only variables.
3. Add production regression tests.
4. Set VPS `DRAFTCHECK_ENV=production`.
5. Redeploy and verify that the endpoint returns 404 with a correctly formed
   request.
6. Do not enable magic-link login until SMTP and the end-to-end flow are ready.

## Critical finding 2 — PR #154's approved-rule total is not the live truth

PR #154 reported 17,929 approved rules after loading 1,372 new rules. The current
production database has:

- Rules total: 32,426.
- Approved: **16,596**.
- Rejected: 14,497.
- Pending review: **1,333**.

The discrepancy is explained by the governance revalidation:

- All 1,372 new rows still carry approval timestamps and approval metadata.
- `scripts/revalidate_bulk_approved_rules.py` subsequently quarantined **1,333**
  of them to `pending_review`.
- Only **39** from that load remain approved.
- Audit events record 1,333 `quarantine -> pending_review` actions.

Common failures include:

- Non-verbatim quote anchors.
- Rule keys outside the current snake-case/length contract.
- Non-canonical units such as aliases that should have been normalized.
- Unit-category failures.

Do **not** mass-reapprove these rows. The next rule-coverage effort must repair
the extraction reports/clauses/normalization, rerun the universal validators,
and promote only genuinely valid rows. The PR description and any dashboard
claiming 17,929 approved rules should be corrected to current truth.

## Live data state

Source/corpus:

- Source documents: 875.
- Source versions: 1,044; all currently report `approved`.
- Target manifest:
  - acquired: 874
  - pending: 127
  - blocked: 44
  - metadata-only: 54
  - out-of-scope: 3,848
- Source chunks: 81,786.
- Proper API embeddings: 68,898.
- Deferred embeddings still needing backfill: **12,888**.
- Legal edges: 53,429 total; 53,222 `cites`.
- Golden eval cases: 19.
- Job traces: 7.

Open review work:

- `review_items` open: **1,390**.
- 865 concern clause extraction/adjudication.
- 525 are approved exception rules lacking an `exception_to` edge with a
  deterministic single base rule.
- These 1,390 review items are separate from the 1,333 quarantined rule rows.

Spatial:

- Address points: 1,673,144.
- Parcels: 469,528.
- Planning features: 219,436.
- LGAs: 139.
- Four new weekly PlanWA/DPLH versions are approved and current:
  DPLH-024, DPLH-068, DPLH-070, and DPLH-071.
- The `draftcheck-planwa-refresh.timer` is enabled and active.
- Current cadastre records are regional/subset imports. The latest LGATE-001
  metadata explicitly says commercial-use terms remain unconfirmed. Do not
  treat the current parcel collection as complete statewide licensed cadastre.

## Council rollout truth

`docs/COUNCIL_ROLLOUT_PLAN.md` records six completed, audited councils:

- Cockburn
- Melville
- Fremantle
- East Fremantle
- Kwinana
- Rockingham

PR #154 added some Canning, Armadale, Stirling, Joondalup, Vincent, and other
local-policy rule batches, but those councils have not completed the rollout
definition (corpus closure, spatial verification, scoping, three-judge audit,
and passing canary). Most of the new batch was also quarantined. Do not mark
those council rows done from PR #154 alone.

## Operations state

- UFW: active.
- fail2ban: inactive.
- SSH: root login permitted and password authentication enabled.
- Off-site backup configuration `/etc/draftcheck/backup.env`: absent.
- `draftcheck-backup.timer`: not installed/enabled.
- A recent local backup file exists, but there is no verified off-site backup
  or restore-drill evidence from this audit.
- Disk: 43% used, about 223 GB free.
- Sentry DSN: unset.
- PlanWA refresh timer: enabled and active.

The deploy workflow should be serialized with a GitHub Actions concurrency
group. Rapid successive merges currently allow overlapping VPS deployments,
which produced the observed Compose container-name conflict.

## Ordered next-agent work

### P0 — before further public use

1. Close the production development-login vulnerability and set the real
   production environment mode.
2. Verify no other development-only route or fallback is reachable in the
   deployed configuration.

### P0 — restore truthful rule coverage

3. Produce a deterministic breakdown of the 1,333 quarantined rows by validator,
   batch, and repairability.
4. Fix extraction/normalization at the source; never bulk-flip lifecycle status.
5. Revalidate, promote only passing rows, rerun live rule-coverage tests, and
   publish corrected approved totals.

### P1 — corpus and legal closure

6. Drain or explicitly disposition 127 pending and 44 blocked manifest entries.
7. Backfill 12,888 deferred embeddings with the pinned provider/model.
8. Resolve the 525 missing exception edges and the 865 extraction review items.
9. Expand the golden eval set beyond the current 19 cases.

### P1 — delivery and operations

10. Add deploy concurrency/serialization and verify two rapid main updates cannot
    overlap on the VPS.
11. Configure off-site backups, enable the backup timer, and run/document a
    restore drill.
12. Enable fail2ban and disable SSH password authentication using the runbook's
    active-session safety procedure.
13. Configure monitoring/Sentry and verify alert delivery.

### P2 — product depth and scale

14. Complete the next councils through the full rollout gate rather than merely
    importing isolated policy rules.
15. Deepen drawing/proposal extraction and operator review UX.
16. Complete RFI/export validation and the later Hermes/self-learning phases only
    after the P0/P1 gates are green.

## Safe commands to resume verification

```powershell
git fetch --prune origin
git status --short --branch
gh run list --repo stevenshelley58-afk/cuz.fail --branch main --limit 10
uv run ruff check src scripts tests
uv run mypy src
uv run lint-imports --config pyproject.toml
uv run pytest -q
cd web
npm run build
cd ..
curl.exe -s https://lotfile.app/api/v1/health
curl.exe -s https://lotfile.app/api/v1/ready
ssh draftcheck 'git -C /srv/draftcheck/app rev-parse HEAD'
ssh draftcheck 'cd /srv/draftcheck/app/infra/v3 && docker compose ps'
```

Do not run destructive Git cleanup or remove the untracked local/VPS reports.
