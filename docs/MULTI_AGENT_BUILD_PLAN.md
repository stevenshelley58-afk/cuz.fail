# DraftCheck WA — Multi-Agent Build Plan (Codex plan, reviewed and corrected)

Date: 2026-06-07
Authority: `docs/MASTER_REBUILD_PLAN.md` (V3). This document is the execution layer on top of it: who builds what, in which order, with which isolation. Where the Codex draft conflicted with V3, V3 wins and the conflict is listed in §2.

## 1. Verdict

The Codex plan is accepted as the PR ladder (PR0–PR11) with the corrections below. Its biggest real contribution is PR0: **git currently tracks exactly one file (`README.md`)** — verified — so source-control hygiene is the hard first gate. Its biggest defect is that it reintroduces the exact sequencing bug V3 fixed: LLM governance lands in PR11 while LLM calls start in PR5/PR6. Second defect, relevant to the instruction "use multiple agents": it permits parallelism but never defines the dependency graph, waves, or write scopes that make parallelism safe. Both fixed here.

### Verified baseline (2026-06-07, this workspace)

```text
git ls-files            -> 1 file (README.md)            Codex claim TRUE
.gitignore              -> covers .env*, *.db, .storage, caches
                           MISSING: .venv/, .vercel/, build/, backups/,
                           *.db-wal, *.db-shm, data/corpus policy      <- fix before any git add
.env files              -> none found (only .env.example)             good
docs/MASTER_REBUILD_PLAN.md -> present (V3 authority)
tests/                  -> 184 test functions, zero parametrize
                           (Codex's "pytest 269" not reproduced here; re-baseline in PR0 CI)
draftcheck.db (127 MB)  -> PRAGMA integrity_check FAILS from this workspace:
                           "database disk image is malformed"          <- NEW RISK, see fix 5
```

## 2. Required corrections to the Codex plan

| # | Defect | Correction | Severity |
|---|---|---|---|
| 1 | **Agent substrate regression.** PR11 holds job_traces, skill_versions, spend caps — but PR5 ships `/search/ask` and PR6 ships LLM rule extraction. This is the bug V3 §7 / fix #1 exists to prevent. | Substrate v0 (single model adapter + `job_traces` + per-job/daily spend caps + breaker) moves into **PR5**. `skill_versions` + eval-case seeding move into **PR6**. PR11 keeps only autonomy, agent memory curation, and the console. | High |
| 2 | **Endpoint contract regression.** Codex's "core endpoints" list (`/address/resolve`, `/projects/{id}/property/resolve`, `/projects/{id}/resolved-rules`) is the voided addendum set, not V3 §6.1. | API surface = V3 §6.1, frozen as an OpenAPI stub in PR2 (`/projects/{id}/resolve-address`, `/compliance/run`, `/compliance/matrix`, …). Any deviation requires a V3 amendment PR first. A pre-project address probe, if wanted, is a deliberate addition — not a silent one. | High |
| 3 | **No dependency graph.** "Parallel for disjoint scopes" with no statement of what runs when. | Waves + graph in §4. Max 3 concurrent backend writers + 1 frontend track. | High |
| 4 | **Schema contention unaddressed.** PR4–PR9 all add tables; `models.py` and `alembic/versions/` are a serial resource (revision IDs collide across branches). | New single-writer role: **Schema Integrator**. Domain agents submit table specs (DDL-as-markdown in their PR description); the integrator lands migrations *ahead of* the dependent service PR in the same wave. No domain agent ever edits models.py or creates a migration. | High |
| 5 | **Harvest source integrity.** PR5 assumes `draftcheck.db` is readable; it fails integrity check from this workspace. Cause may be host-side corruption or mount artifact — unknown. | PR0 adds a host-side step (human or host agent): run `PRAGMA integrity_check` on the user's machine; if bad, `sqlite3 .recover` into a fresh file; archive a verified-good copy to storage **before** any cleanup. PR5 acceptance: harvest ran against an integrity-checked copy, with row counts recorded in `DATA_INVENTORY.md`. The "19 eval cases" figure is unverified until then. | High |
| 6 | **PR0 will stage garbage.** `git add` with today's `.gitignore` stages `.venv/`, `.vercel/`, `build/`, and 1,422 corpus files. | PR0 order: extend `.gitignore` first (add `.venv/`, `.vercel/`, `build/`, `backups/`, `*.db-wal`, `*.db-shm`, `data/corpus/` — corpus is evidence input, not source; tracked seed manifests live in `data/fixtures/`) → secret scan → size guard (pre-commit reject >5 MB) → then stage. `landing/` and `mockups/` are tracked as design references until M1, then archived. | High |
| 7 | **mypy zero-error gate over-scoped.** Legacy code has 19 errors and is frozen; "mypy is zero-error" would send an agent fixing dead code. | Gate: zero errors for `src/draftcheck/` + `web/` only. Legacy stays at its recorded baseline and is never "improved". | Med |
| 8 | **Vercel/DNS cutover missing.** PR3 builds the VPS but never cuts over (V3 Phase 0 step 12). | PR3 acceptance adds: DNS TTL drop → switch → 48 h dual-run → rollback path → disconnect Vercel integration → archive `vercel.json`, `api/index.py`, root `index.py`, `.vercel/`. DNS and Vercel dashboard actions are **human-in-the-loop** (coordinator escalates to Steven). | Med |
| 9 | **Frontend serialized.** PR10 queued after PR9 wastes the one track that parallelizes perfectly. | Frontend is a **continuous track** from Wave 1: shell + design tokens against the PR2 OpenAPI stub, then screens land per wave as their APIs merge (§4). PR10 becomes the track's M1 acceptance, not its start. | Med |
| 10 | **Embeddings unpinned.** PR5 says nothing about model/dimension; V3 §8.1 pins them. | PR5 acceptance adds: pinned provider/model/dim via env, `embedding_model` recorded per chunk, HNSW index, re-embed runbook. | Med |
| 11 | **Golden fixture unowned.** PR7/8/9 all consume one council + address + drawing fixture. | Fixtures Owner (single writer for `tests/fixtures/golden/`) creates it in Wave 3; it becomes the M1 demo and the permanent canary. | Med |
| 12 | **Reviewer mechanics vague.** "Two review agents" without isolation or checklists. | §6: reviewers are fresh-context, read-only, run in pairs — Spec (diffs the PR against named V3 sections + acceptance list) then Quality (runs gates; greps forbidden patterns: `create_all`, `dev-login`, verdict writes outside the engine, uncited regulatory strings). Red-team agent attacks `/search/ask` at PR5 and the engine at PR9. | Low |

## 3. Agent roster

| Agent | Type | Write scope | Lifetime |
|---|---|---|---|
| **Coordinator** | orchestrator | merges, branch strategy, contracts, human escalations (DNS, Landgate licence, host DB check) | whole build |
| **Schema Integrator** | worker | `src/draftcheck/db/models.py`, `db/alembic/`, procrastinate schema | whole build |
| **Infra** | worker | `infra/`, CI workflows, deploy/backup scripts | PR3 (+fixes) |
| **Auth** | worker | `src/draftcheck/api/auth*`, `domain/identity` | PR4 |
| **Sources** | worker | `domain/sources`, `ai/` substrate v0 | PR5 |
| **Legal** | worker | `domain/rules`, `skills/extract_rules`, `skills/classify_clauses` | PR6 |
| **Spatial** | worker | `domain/address`, dataset importers | PR7 |
| **Documents** | worker | `domain/documents`, parser interface | PR8 |
| **Compliance** | worker | `checks/`, `domain/compliance` | PR9 |
| **Hermes** | worker | `agent/`, `skills/analyse_rfi`, `skills/draft_response` | PR11a |
| **RFI/Export** | worker | `domain/rfi`, `domain/exports` | PR11b |
| **Frontend** | track worker | `web/` only | Waves 1→6 |
| **Fixtures Owner** | worker | `tests/fixtures/` | Wave 3→ |
| **Spec Reviewer / Quality Reviewer** | reviewers ×2 per merge | read-only | per PR |
| **Red-team** | reviewer | read-only + eval harness | PR5, PR9 |

Workers are fresh subagents per PR, each in an isolated git worktree, each receiving the invariants block (§5). A worker never edits outside its write scope; schema needs go to the Schema Integrator as specs.

## 4. Waves and dependency graph

```text
W0  PR0 repo hygiene  ->  PR1 authority lock                      (serial, coordinator)
W1  PR2 skeleton+CI   ||  PR3 infra                || FE: shell + tokens vs OpenAPI stub
W2  PR4 auth + base schema (Schema Integrator + Auth)
        || harvest-dev vs integrity-checked DB copy || corpus inventory
W3  PR5 sources + SUBSTRATE v0   ||  PR7 spatial    || FE: login, dashboard, resolver
        (Fixtures Owner creates golden fixture)
W4  PR6 legal + skills/evals     ||  PR8 documents  || FE: sources admin, upload, facts review
W5  PR9 compliance -> M1 GATE (golden fixture e2e; legacy deletion; /v1 removed)
        || FE: matrix, evidence drawer, ask         -> PR10 acceptance = FE M1
W6  PR11a hermes autonomy        ||  PR11b RFI/exports/signoffs   || FE: RFI, agent/ops
```

Hard edges: PR6 ← PR5 (source_versions, clauses) · PR8 ← PR5 (artifacts) · PR7 ← PR4 only · PR9 ← PR6+PR7+PR8 · PR11 ← PR9. PR2 ∥ PR3 share only a contract (image names, `/api/v1/health|ready`), no files. Concurrency cap: 3 backend writers + frontend + fixtures.

## 5. Worker prompt invariants (every worker, verbatim)

```text
Authority: docs/MASTER_REBUILD_PLAN.md (V3). Your PR brief names the sections you implement.
Write scope: only the paths listed in your brief. Schema changes are specs sent to the
  Schema Integrator — never edit models.py or alembic/ yourself.
Single-writer files you must not touch: pyproject.toml, uv.lock, models.py, alembic/,
  infra/compose.yml, Caddyfile, CI workflows, AGENTS.md, the OpenAPI contract.
Safety invariants (V3 §12): no final compliance claims; cite approved source versions or
  refuse; LLMs never decide verdicts; no likely_pass/likely_fail without approved rule +
  promoted measurement + citation + trace; no uncalibrated raster/PDF measurement; no paid
  Standards Australia full text; no export without signoff; no LLM call outside the traced,
  spend-capped adapter; no create_all; no dev-login; legal values in examples are
  illustrative — hardcoding one is a defect.
Never stage: draftcheck.db, .storage/, .venv/, .vercel/, build/, caches, data/corpus/.
Done = code + tests + handoff note (what changed, contracts touched, follow-ups, V3
  sections satisfied). Tests failing or scope exceeded = not done, say so plainly.
```

## 6. Merge protocol

```text
1. Worker develops in its worktree; rebases on main before handoff.
2. CI must be green: ruff, mypy (new-code scope), pytest, alembic up+down, import-linter,
   web build, OpenAPI diff, forbidden-pattern grep (create_all | dev-login | verdict
   writes outside engine | uncited regulatory output paths).
3. Spec Reviewer (fresh context, read-only): PR vs named V3 sections + acceptance list.
4. Quality Reviewer (fresh context): runs gates locally, adversarial greps, test quality.
5. Coordinator merges in dependency order; integration runs daily at minimum.
6. Schema PRs always merge before the service PRs that need them (same wave).
7. Red-team gate at PR5 (try to elicit uncited answers) and PR9 (try to fake a verdict).
8. Human-in-the-loop merges: DNS cutover (PR3), Landgate licence confirmation (PR7 import
   blocked until cleared), host-side draftcheck.db integrity check (PR0/PR5).
```

## 7. PR ladder deltas (Codex text stands except these)

```text
PR0  + extend .gitignore BEFORE staging (.venv/, .vercel/, build/, backups/, *.db-wal,
       *.db-shm, data/corpus/) + secret scan + >5MB pre-commit guard
     + host-side draftcheck.db integrity check; archive verified copy
     + record canonical CI baseline (pytest/ruff/mypy numbers live in CI, not prose)
PR2  mypy zero-error applies to src/draftcheck + web only; OpenAPI stub frozen from V3 §6.1
PR3  + DNS TTL drop, 48h dual-run, rollback, Vercel disconnect + file archival (human loop)
PR5  + substrate v0 (model adapter, job_traces, spend caps, breaker)
     + pinned embeddings (model/dim per chunk, HNSW, re-embed runbook)
     + harvest only from integrity-checked copy; row counts into DATA_INVENTORY.md
PR6  + skill_versions + eval_cases seeded from harvest; every extraction traced
PR9  M1 gate also deletes legacy apps/, packages/, api/, root index.py and removes /v1
PR10 = frontend track M1 acceptance (track starts Wave 1, not after PR9)
PR11 split: 11a Hermes autonomy + memory + console; 11b RFI/exports/signoffs
     (substrate is NOT here — it shipped in PR5/PR6)
```

Everything else in the Codex plan — operating model, safety test list, integration tests, assumptions (V3 authority, corpus untracked, Landgate licence as launch blocker, harvest-then-greenfield) — is accepted as written.
