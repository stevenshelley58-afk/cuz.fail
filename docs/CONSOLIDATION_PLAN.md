# Consolidation & Pre-Prod Cleanup Plan

Date: 2026-06-09
Status: **execution plan for handoff to Claude Code.** Authority for product shape stays with
`docs/MASTER_REBUILD_PLAN.md`; this plan supersedes it only on the two points decided 2026-06-09:
(1) collapse the two stacks/DBs into one, (2) the pipeline is **fully AI** — no human reviewer or
signoff gate.

This doc is written so an executing agent can follow it top-to-bottom. Do the phases in order.
Each phase ends with an acceptance gate that must pass before the next phase starts.

---

## 0. Why this exists (what's wrong today)

The repo currently carries **two complete, parallel stacks**:

| | Legacy stack (dead) | V3 stack (live in prod) |
|---|---|---|
| App code | `apps/api`, `apps/worker`, `packages/*` (8 roots) | `src/draftcheck/*` |
| DB | SQLite `draftcheck.db` (153 MB) | PostgreSQL 16 + PostGIS + pgvector (VPS) |
| Migrations | `infra/alembic` (0001–0009), `alembic-legacy.ini` | `src/draftcheck/db/alembic` (0001–0002), `alembic.ini` |
| Entry | `index.py` / `api/index.py` (Vercel serverless, copies SQLite to `/tmp`) | `uvicorn draftcheck.api.main:app` via `infra/v3/compose.yml` |
| Hosting | Vercel + Supabase (decommissioned, files still present) | VPS `cuz.fail`, Docker Compose, Caddy |
| UI | `ui/*.html` (design refs) | `web/` SPA (LotFile) |

`api.cuz.fail/api/v1/health` is served by the **V3 stack**. The legacy stack is dead weight that
still pollutes `pyproject.toml`, the test suite, and CI, and `index.py` still wires a SQLite
runtime that must never run in prod.

**Target end state:** one stack (`src/draftcheck` on Postgres), one alembic chain, no Vercel /
Supabase / SQLite, no legacy `apps/` `packages/`, and a fully-AI pipeline with the human reviewer/
signoff gate removed.

### Known data fact (decided 2026-06-09)
Nothing in `draftcheck.db` is human-labelled. Provenance check shows every "approved/reviewed" row
was written by `system-bootstrap`, `deterministic_rule_extractor`, `dev-user`, `system-backfill`,
or a test fixture (`rules@example.test`). It is all reproducible (source library from
`data/corpus`; derived tables by re-running the extractor). See `data/harvest/README.md`. So the
DB is **archive-then-delete**, not migrate.

---

## 1. Pre-flight (do before changing anything)

1. **Branch.** `git checkout -b consolidation-prod-cleanup`. All work lands here; PR to `main`.
2. **Capture green baseline.** Run the current suite and record the result so regressions are
   visible later: `python -m pytest -q | tee /tmp/baseline_tests.txt`. Expect the documented
   "23 passed" (some target legacy code that will be deleted — note which).
3. **Confirm the live prod alembic head** (drives the migration strategy in Phase 2):
   ```
   ssh draftcheck "cd /srv/draftcheck/app && docker compose -f infra/v3/compose.yml exec -T db \
     psql -U draftcheck -d draftcheck -c 'select version_num from alembic_version' \
     -c \"select extname from pg_extension where extname in ('postgis','vector')\""
   ```
   Record the head (expected `0002_v3_complete_target_schema`) and that both extensions exist.
4. **Back up prod DB** before any later migration: `pg_dump` per `docs/PRODUCTION_DEPLOYMENT.md` /
   `infra/v3/backup`. Confirm the dump is fresh (<1 h) and restorable into a scratch container.
5. **Archive the legacy SQLite** once, to object storage, before deleting it from the tree:
   copy `draftcheck.db` → `.storage/archive/draftcheck-legacy-YYYYMMDD.db`. It is already
   `.gitignore`d. Confirm `data/corpus` is intact (file census matches `DATA_INVENTORY.md`:
   1,422 files) so the source library is reproducible.

**Gate 1:** branch created; baseline test result saved; prod alembic head + extensions recorded;
fresh restorable DB backup; SQLite archived; corpus census matches inventory.

---

## 2. Phase A — One database, one migration chain

The two DBs are not "merged" — there is no data worth merging. We **retire SQLite + the legacy
chain** and keep Postgres + the V3 chain as the single authority.

1. **Migrate the one live cross-dependency first.** `src/draftcheck/api/sources.py:19` imports
   `from draftcheck_core.providers import get_chat_provider` — the only place V3 still reaches into
   legacy `packages/core`. Move the needed provider code into `src/draftcheck/ai/` (or
   `src/draftcheck/providers.py`), update the import, and confirm nothing else in `src/` imports
   `draftcheck_core`, `apps.*`, or `packages.*` (`grep -rn -E "draftcheck_core|apps\.|packages\." src/`).
2. **Decide migration strategy from the Gate 1 head:**
   - If prod is at `0002` (expected) and not yet serving external users: add a **forward
     migration** `0003_drop_human_review.py` (see Phase B) — do not rewrite history on a live DB.
   - Only squash the V3 chain to a single baseline if prod DB can be rebuilt from scratch; if you
     squash, re-stamp prod (`alembic stamp head`) and verify schema parity against a fresh build.
   Default: **forward migration**.
3. **Delete the legacy chain:** remove `infra/alembic/`, `alembic-legacy.ini`. Keep `alembic.ini`
   (points at `src/draftcheck/db/alembic`).
4. **Kill the SQLite runtime path:** delete `index.py`, `api/index.py`, and any `seed_db` / `/tmp/
   draftcheck.db` logic. Ensure no shipped module imports `sqlite3` or references `draftcheck.db`
   (`grep -rn -iE "sqlite|draftcheck\.db" src/`). SQLite may remain only in dev/test fixtures if
   clearly isolated — prefer Postgres testcontainers per `REBUILD_SPEC.md`.
5. **Remove `draftcheck.db`** from the working tree (archived in Gate 1).

**Gate A:** `grep -rn -iE "sqlite|draftcheck\.db|draftcheck_core|infra/alembic" src/ apps/ 2>/dev/null`
returns nothing in shipped code; `alembic upgrade head` runs clean on a scratch Postgres; only one
alembic chain remains.

---

## 3. Phase B — Remove human review (code + schema)

The pipeline becomes: **LLM/extractor proposes → automated validators → eval gate → deterministic
engine decides → cited, advisory output.** No reviewer role, no human approval step, no signoff.

### Code targets (exact)
- `src/draftcheck/domain/identity/` — remove the `reviewer` role and `require_reviewer`. Reduce
  `IdentityRole` to a single role (e.g. `OWNER`) or drop role gating entirely.
- `src/draftcheck/api/auth.py` — delete `require_reviewer`, `require_reviewer_session` and their
  use as dependencies.
- `src/draftcheck/api/address.py:199`, `documents.py:149`, `sources.py` — remove
  `require_reviewer*` dependencies so writes no longer require a reviewer.
- `src/draftcheck/api/sources.py:94` — reword the hardcoded string
  *"...have a human reviewer sign off before relying on it"* (see Disclaimer note below).
- `src/draftcheck/cli.py` — drop `IdentityRole.REVIEWER` provisioning; use the single role.
- Keep `review_status` columns as an **automated** lifecycle field (set by validators/evals, not a
  person). Remove only the human gating, not the status machine.
- **Residual human-review semantics scrub (added 2026-06-09 — verification found these survive the
  role removal):** the auth/role gate is not the whole gate. Also fix:
  - `src/draftcheck/domain/address/spatial.py` — rename `ResolutionStatus.NEEDS_HUMAN_REVIEW` →
    `NEEDS_MORE_INFO` (or `UNSUPPORTED`) and the `manual_override_requires_human_review` issue
    string. This status is in the V3 resolution set and **Stage 2 builds on it**, so rename it now,
    not later. Update `ROAD_TO_PROD.md`/`STAGE_2_BUILD.md` already use `needs_more_info`.
  - `src/draftcheck/domain/documents/parsing.py` — `"needs_human_review"` parse status + the copy
    *"pending review until promoted by a human reviewer"* → automated promotion-contract language.
  - `src/draftcheck/domain/sources/fetching.py` — *"...require human review"* → automated
    licence-gate language.
  - `src/draftcheck/domain/sources/library.py` — `human_review_required=True` → an automated-gate
    flag (e.g. `gate_blocked` / `needs_more_info`).
  - `src/draftcheck/api/documents.py` — the `"human review promotion workflow"` string.

### Schema targets (in the new `0003_drop_human_review` migration)
- Drop the `signoffs` table (`0002_v3_complete_target_schema.py:593`) — the human signoff gate.
- Drop `source_reviews.reviewer_user_id` FK / human-reviewer columns
  (`0001_v3_foundation_metadata.py:279,289`) or repoint to an automated actor.
- Drop `rules.approved_by_user_id` human-approver FK (`0002:240,254`); rule acceptance is set by
  the automated gate, not a person.
- Collapse the `users.role ∈ {owner, reviewer}` enum to a single role
  (`0001:69`). Leave `review_status` defaults intact (now AI-driven).

### `CLAUDE.md` governance update
Rewrite the governance section so it no longer asserts a human signoff in the product. Keep the
two hard rules that are about **output honesty, not human review**:
- *Never claim final legal, planning, building, or certification compliance.*
- *All regulatory outputs cite approved source versions or state the library can't support the
  answer.*

### FLAGGED — single retained item (override if you disagree)
The product keeps an **output disclaimer**: results are advisory, cited, and explicitly **not a
final certification**, with statuses like `likely_pass / likely_fail / needs_more_info /
unsupported`. This is **not** a human-in-the-loop gate — it is the product not overclaiming, and
`CLAUDE.md` makes it a hard rule. Everything requiring a *person* is removed. If you want this gone
too, delete the disclaimer copy and the two hard rules above — but that means a WA building/
planning tool issuing determinations it labels as final, which is a real liability call. Left in by
default.

**Gate B:** `grep -rn -iE "reviewer|require_reviewer|human.?signoff|sign.?off|approved_by_user" src/`
returns only automated-lifecycle references (no human gate); new migration applies clean; tests
that asserted the reviewer gate are updated to the AI-only flow.

---

## 4. Phase C — Delete legacy code & fix the build

1. **Delete legacy roots** (after Phase A step 1 migration):
   `apps/`, `packages/`, `ui/`, `supabase/`, `.vercel/`, `vercel.json`, `.vercelignore`, `build/`,
   `scripts/configure-vercel-production.ps1`, and any other Vercel/Supabase artifacts.
2. **`pyproject.toml`** — `[tool.setuptools.packages.find].where` and
   `[tool.pytest.ini_options].pythonpath` currently list `src` + `apps/*` + `packages/*`. Reduce
   both to `["src"]`.
3. **Test triage.** 26 test files import the legacy stack and 14 import `src/draftcheck`
   (`tests/conftest.py` is shared — rewrite it for the V3/Postgres fixture). For each legacy test:
   delete if it only covers deleted code; port to `src/draftcheck` if it covers behaviour that
   still ships (e.g. `test_health`, `test_rule_governance`, `test_source_acceptance_gate`,
   `test_spatial_resolution`). End state: every test imports only `draftcheck.*`.
4. **CI (`.github/workflows/ci.yml`)** — update `mypy`/`lint-imports`/`precommit_guard` targets to
   `src` + the V3 tests; remove legacy paths. **`deploy.yml`** — confirm it deploys the VPS via the
   runbook and never triggers a Vercel deploy.
5. **`.gitignore` / `.vercelignore`** — drop Vercel entries; keep `draftcheck.db`, `*.sqlite*`,
   `.storage/`, `.env*` (except `.env.example`) ignored.

**Gate C:** repo contains no `apps/ packages/ ui/ supabase/ .vercel/ vercel.json index.py`;
`pip install -e ".[dev]"` succeeds; `lint-imports` passes; no test imports legacy modules.

---

## 5. Phase D — Sanity check everything

Run the full gate locally on the branch:

1. **Static:** `ruff check .`, `mypy src tests`, `lint-imports`, `python scripts/precommit_guard.py`.
2. **Tests:** `pytest -q` green; compare against `/tmp/baseline_tests.txt` and account for every
   removed/changed test.
3. **Schema:** spin a scratch Postgres (`infra/v3/compose.yml` db service or testcontainer),
   `alembic upgrade head`, then assert:
   - extensions: `select extname from pg_extension` shows `postgis` + `vector`.
   - removed objects: no `signoffs` table, no reviewer role, no `approved_by_user_id`.
4. **Forbidden-pattern grep (must all be empty in shipped code):**
   `sqlite`, `draftcheck\.db`, `create_all`, `vercel`, `supabase`, `require_reviewer`,
   `human_signoff`, `human.?review`, `NEEDS_HUMAN_REVIEW`, `human_review_required`,
   `apps\.`, `packages\.`, `draftcheck_core`.
5. **Runtime smoke:** `docker compose -f infra/v3/compose.yml up -d`; hit `/api/v1/health` and
   `/api/v1/ready`; confirm `app_env=production` returns 404 for `/api/v1/auth/dev-login`.
6. **Reproducibility check:** dry-run the corpus import from `data/corpus` into the scratch DB and
   confirm the source library + derived tables regenerate without the SQLite file. This is what
   makes deleting `draftcheck.db` safe.

**Gate D:** every check above passes; forbidden-pattern grep clean; runtime smoke green.

---

## 6. Phase E — Cutover to prod

Follow `docs/PRODUCTION_DEPLOYMENT.md` and `docs/CODEX_DEPLOY_SYNC_RUNBOOK.md`.

1. Merge the PR once CI is green (standing approval covers this).
2. On the VPS: `alembic upgrade head` (applies `0003_drop_human_review`) against the backed-up prod
   DB. Verify the dropped objects are gone.
3. Rebuild + deploy app and `web/dist` per the runbook; verify `/api/v1/health` and the LotFile UI.
4. Confirm no Vercel deploy fires on push.
5. Archive + remove `draftcheck.db` from the server checkout if present.

**Gate E:** prod health green; schema has no human-review objects; no Vercel/Supabase activity;
SQLite gone from prod.

---

## 7. Rollback

- All work is on a branch / PR — `main` and prod are untouched until merge + deploy.
- DB: the Gate 1 `pg_dump` restores prod if `0003` misbehaves; the migration must have a working
  `downgrade()`.
- Code: revert the merge commit; redeploy previous `web/dist` (the runbook's deploy script backs up
  and restores `dist` on build failure).
- Data: the archived `draftcheck-legacy-YYYYMMDD.db` in `.storage/archive` is the safety net; do not
  delete it until prod has run clean for one full backup cycle.

---

## 8. File disposition quick reference

**Delete:** `apps/ packages/ ui/ supabase/ build/ .vercel/ vercel.json .vercelignore index.py
api/ infra/alembic/ alembic-legacy.ini draftcheck.db` (archive first)
**Edit:** `pyproject.toml` (src-only), `.github/workflows/*`, `CLAUDE.md` (governance),
`src/draftcheck/{domain/identity,api/auth.py,api/address.py,api/documents.py,api/sources.py,cli.py}`,
new migration `0003_drop_human_review.py`, `tests/*` (triage)
**Keep:** `src/draftcheck/`, `src/draftcheck/db/alembic` (+ new 0003), `web/`, `infra/v3/`,
`infra/docker`, `data/corpus`, `scripts/` (drop Vercel script), `docs/` (with human-review edits)
**Docs to scrub of human-review language (~56 lines):** `MASTER_REBUILD_PLAN.md` (17),
`MULTI_AGENT_BUILD_PLAN.md` (9), `REBUILD_SPEC.md` (6), `REPO_AUDIT.md` (6),
`LEGAL_AND_LICENSING_NOTES.md` (4), `ARCHITECTURE_AS_BUILT.md` (4), `CODEX_DEPLOY_SYNC_RUNBOOK.md`
(2), `API_CONTRACT.md` (2), `README.md` (2), `RULES_EXTRACTION_PIPELINE.md` (1), `DATA_SOURCES.md`
(1), `AGENTS.md` (1). Replace "human reviewer approves/signs off" with the automated gate; keep
only the advisory/not-a-certification disclaimer (Phase B flagged item).

---

## 9. Open decisions for the executor

1. **Migration strategy** (Phase A.2): forward `0003` (default, safe on live prod) vs squash to a
   single baseline (only if prod DB is rebuildable). Resolve from the Gate 1 head.
2. **Retained disclaimer** (Phase B flagged): keep advisory/not-final-certification copy (default)
   or strip it too (operator's liability call).
3. **`review_status` columns:** keep as AI-driven lifecycle (default) vs remove entirely. Keeping
   them preserves traceability without implying a human.
