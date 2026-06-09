# DraftCheck WA Core Claude Rules

## Deployment architecture — LOCKED (2026-06-09). Do not relitigate.

- **One host: the VPS (Caddy, `76.13.209.160`). Same-origin. Vercel is RETIRED.**
- The SPA (`web/src/api.ts`) calls **same-origin `/api/v1`**. The host serving the SPA MUST
  proxy `/api/v1` to the FastAPI backend. `infra/v3/Caddyfile` is the source of truth and does
  this for `app.cuz.fail` (canonical product URL). `cuz.fail` / `www.cuz.fail` redirect there.
- **Never** set `VITE_API_BASE_URL`, add CORS, or use cross-origin cookies. Same-origin removes
  the need. Reintroducing a split frontend/backend (Vercel + api.cuz.fail) is what repeatedly
  broke the app — do not do it.
- Do not deploy to Vercel. If a domain serves the blank "LotFile" shell, its DNS is pointing at
  Vercel instead of the VPS — fix DNS, do not touch the build. See `docs/FIX_ONE_HOST_VPS.md`.

- Active implementation source: `docs/MASTER_REBUILD_PLAN.md` (single authority for the V3
  rebuild) plus refreshed `REPO_AUDIT.md`, `DATA_INVENTORY.md`, and `VERCEL_AUDIT.md`.
  (`docs/MASTER_IMPLEMENTATION_PLAN.md`, `MASTER_PLAN_ADDENDUM.md`, and
  `docs/PLAN_LOCK_NOTICE.md` are superseded background context.)
- Older planning docs are background context only where they conflict with the active implementation
  source.

## Operator Standing Approval (2026-06-09)

- The operator (Steven) pre-approves all operational and implementation work that follows the
  active implementation source: git commits/pushes, PRs and merges once CI is green, CI changes,
  VPS provisioning and deploys, DNS changes, backups, and infra scripts.
- Do not pause to ask permission or wait for confirmation; decide, act, and log the decision in
  the commit/PR description. Missing credentials → documented fallback, continue, and list the
  one-command unblock in the final report (see `docs/CODEX_DEPLOY_SYNC_RUNBOOK.md`).

## Pipeline and output governance (2026-06-09)

The pipeline is **fully AI**: LLM/extractor proposes → automated validators → eval gate →
deterministic engine decides → cited, advisory output. There is no human reviewer or signoff
gate in the product.

- Never claim final legal, planning, building, or certification compliance.
- All regulatory outputs must cite approved source versions or explicitly state that the approved source library cannot support the answer.
- Outputs are advisory with statuses like `likely_pass / likely_fail / needs_more_info / unsupported`. They are not final certifications.

- Prefer deterministic calculations for measurements. If measurements are absent or ambiguous, return missing information.

## External Agent Resources

- Agent and workflow references:
  - [affaan-m/ECC](https://github.com/affaan-m/ECC)
  - [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)
- Use these supporting tools or patterns for applicable graph, workflow, QA, or agent-output review tasks, provided they do not conflict with the active implementation source:
  - [safishamsi/graphify](https://github.com/safishamsi/graphify)
  - [pbakaus/impeccable](https://github.com/pbakaus/impeccable)
