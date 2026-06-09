# DraftCheck WA — Greenfield Rebuild Spec

Date: 2026-06-07. Status: proposed. Supersedes nothing yet — this is the target architecture if rebuilt from scratch, written against the as-built audit (`docs/ARCHITECTURE_AS_BUILT.md`).

**SUPERSEDED:** See `docs/MASTER_REBUILD_PLAN.md`. This file is background context only
for the V3 rebuild where it conflicts with the rebuild plan.

## 0. Locked decisions

- **Deploy**: single VPS (cuz.fail), Docker Compose, Caddy for TLS. No Vercel, no Supabase, no second proxy.
- **Frontend**: in this repo, first-class. The "backend-only" rule is dead.
- **AI**: LLM-assisted but gated — models extract, classify, embed, and draft; they never decide compliance verdicts. Every regulatory claim cites stored source text or refuses.
- **Users**: single-tenant (your practice). Schema carries `org_id` everywhere so multi-tenant is a migration, not a rewrite.
- **Hermes**: promoted from dead config to the system's agent runtime — with persistent memory, a versioned skills library, and an eval-gated self-improvement loop. Detail in §8.

## 1. Principles (what survives, what changes)

Keep from the current design — these are right:

- Content-addressed source versions (SHA-256), supersession chains, licence gates.
- Cite-or-refuse: every regulatory answer carries source_version/chunk citations or an explicit unsupported status.
- Deterministic compliance verdicts (calculators + resolved rules); `missing_info` / `needs_human_review` as honest outcomes.
- Append-only audit events; automated validation gate for exports.
- Lawful scraping constraints (robots, licence notes, Standards Australia metadata-only).
- Job traces with model/tokens/cost per LLM call.

Change — these caused the mess:

- One app package, not eight micro-packages. ~7k lines does not need 10 importable roots.
- One queue (Postgres-backed), not three job paths. Redis is deleted from the stack.
- One schema authority (Alembic), not create_all + Alembic + Supabase SQL.
- One API mount (`/api/v1`), no alias routes.
- One deploy target, one compose file, one proxy.
- Real auth from day one; CORS locked.
- 36 tables, not 57 — JSONB and status columns replace a dozen satellite tables.
- Build tables when a feature ships, not when a plan mentions them.

## 2. System topology

```
                    ┌────────────────────────── VPS (cuz.fail) ──────────────────────────┐
                    │                                                                     │
 Browser ── TLS ──► │  Caddy ──► /            static  web/dist  (React SPA)              │
                    │        ──► /api/v1/*    api container (FastAPI, uvicorn)            │
                    │                              │                                      │
                    │                              ▼                                      │
                    │        Postgres 16 + PostGIS + pgvector  (single instance)          │
                    │           ▲            ▲              ▲                             │
                    │           │            │              │                             │
                    │        worker       hermes         procrastinate queue              │
                    │   (mechanical jobs) (agent jobs)   (tables in same Postgres)        │
                    │           │            │                                            │
                    │           ▼            ▼                                            │
                    │        /srv/draftcheck/storage   (uploads, exports, corpus)         │
                    └─────────────────────────────────────────────────────────────────────┘
                                   │ nightly restic
                                   ▼
                          Backblaze B2 / Cloudflare R2  (db dump + storage + corpus)
```

Five containers: `db`, `api`, `worker`, `hermes`, `caddy`. Nothing else. MinIO, Redis, nginx, Vercel functions: gone.

## 3. Repo layout

```
draftcheck/
├── src/draftcheck/            # ONE installable package
│   ├── api/                   #   FastAPI app, routers, deps (thin: parse → service → respond)
│   ├── domain/                #   modules: projects, sources, rules, documents,
│   │                          #   compliance, rfi, exports, address
│   ├── ai/                    #   provider clients, prompts, gating, traces, embeddings
│   ├── agent/                 #   Hermes runtime: loop, memory, skills loader, evals
│   ├── jobs/                  #   procrastinate app + task definitions
│   ├── db/                    #   models.py, session, alembic/
│   └── config.py              #   pydantic-settings, one Settings class
├── skills/                    # Hermes skills library (versioned markdown+schema, see §8)
├── web/                       # Vite + React + TS SPA → builds to web/dist
├── infra/                     #   compose.yml, Caddyfile, db/Dockerfile (PostGIS+pgvector), deploy.sh
├── tests/                     #   pytest: unit, api, golden evals
├── data/                      #   gitignored: corpus, seeds stay out of git
└── pyproject.toml             # single project, src layout
```

Import rule (enforced by import-linter in CI): `api → domain → db`; `domain → ai/jobs`; `agent → domain, ai`; nothing imports `api`. No `build/` ever committed; `pip install -e .` only.

## 4. Stack

| Concern | Choice | Why / what it replaces |
|---|---|---|
| Language/runtime | Python 3.12, uv | uv replaces pip+venv drift; lockfile committed |
| API | FastAPI + Pydantic v2 | unchanged — it was fine |
| ORM/migrations | SQLAlchemy 2 + Alembic | Alembic is the only schema authority; `create_all` allowed in tests only |
| Database | Postgres 16 + PostGIS + pgvector | keep the existing custom image — it was one of the good parts. SQLite is gone; dev runs the same compose db |
| Queue | procrastinate (Postgres-backed) | deletes Redis+RQ; one less stateful service; jobs visible in SQL; LISTEN/NOTIFY latency is fine at this scale |
| LLM | Anthropic API (Sonnet for extraction/drafting, Haiku for classification/triage) behind a provider protocol | replaces MockLlmProvider as default; mock stays for tests |
| Embeddings | voyage-3-large or text-embedding-3-small → `vector` column on source_chunks | replaces hash-mock; pgvector HNSW index |
| Frontend | Vite + React + TS, TanStack Query | replaces hand-rolled app.html; static build, no SSR needed |
| Auth | magic-link email + signed session cookies (itsdangerous) | replaces dev-login |
| Proxy/TLS | Caddy only | deletes nginx config |
| Observability | structlog JSON → docker logs, Sentry free tier, /health + /ready | replaces print + .codex logs |
| Backups | restic nightly → B2/R2 | replaces the ps1 scripts; tested restore in CI quarterly |
| CI/CD | GitHub Actions: ruff + mypy + pytest + alembic-check → build → ssh deploy | replaces nothing — there is currently no CI |

## 5. Data model — 36 tables in 9 groups

Consolidation rules: satellite tables become JSONB or status columns; provenance stays relational (it's queried); nothing ships before its feature.

**identity (2)** — `users`, `sessions`. `org_id` column on every tenant-owned table, default the single practice org; no orgs table until multi-tenant.

**projects (3)** — `projects` (incl. `lodgement_date`, `as_of_date`, `assessment_basis`), `properties` (PostGIS geometry, resolved address JSONB + provenance), `proposals`.

**spatial (3)** — `parcels`, `planning_features` (one table, `layer_type` discriminator: zones, overlays, bushfire, heritage…), `lg_areas`. Address resolution hits WA SLIP/Landgate APIs with a `resolution_cache` JSONB on properties; the current 9-table spine collapses into these 3 + columns. `address_facts` rows only where independent provenance is genuinely needed (overlay hits) — folded into `planning_features` links.

**sources (6)** — `source_documents` (licence/access state as columns), `source_versions` (sha256, storage path, effective dates), `source_chunks` (text + fts tsvector + `embedding vector(1024)` inline — no separate embeddings table), `source_citations`, `source_fetch_log`, `source_reviews` (acceptance gate history).

**rules (4)** — `clauses` (disposition as a column: rule_bearing | definition | procedural | informational | manual_review), `rule_candidates` (extraction output awaiting promotion; includes extractor model + skill version), `rules` (lifecycle column; overrides/carveouts as validated JSONB), `rule_clause_links`.

**project documents (4)** — `documents`, `document_pages`, `document_chunks` (fts + vector, same shape as source_chunks), `document_facts` (typed facts + measurements merged: `fact_kind` discriminator, value JSONB, confidence, page ref).

**compliance (3)** — `check_runs` (as_of_date, basis, status), `resolved_rules` (rule snapshot chosen for a run, with selection trace), `check_results` (verdict, decision trace JSONB inline, citations, human override fields). Decision traces don't need their own table until something queries them independently.

**rfi & output (4)** — `rfi_items`, `response_drafts` (drafting model + skill version + human-edited flag), `exports` (manifest JSONB, storage path), `validations`.

**agent & governance (7 + queue)** — `job_traces` (every LLM/agent call: model, tokens, cost, prompt hash, artifacts), `agent_memory` (§8), `skill_versions` (§8), `eval_cases` + `eval_runs` count as one concern (two tables; ship with the first skill, not before), `audit_events` (append-only), `review_items` (one generic operator-review queue: subject_type + subject_id + reason + status). Procrastinate owns its own queue tables.

That folds: users/organisations dupes, 6 spatial tables, separate embeddings table, clause_references/dispositions, rule_overrides/carveouts, decision_traces, extracted_measurements, assumptions, tasks, background_jobs, document_assets, source_artifacts/supersessions/references/update_events (supersession becomes `superseded_by_version_id` on source_versions; references become JSONB) — from 57 to 36 with no provenance loss.

## 6. API design

Single mount: `/api/v1`. No aliases — one canonical path per operation; old names die in the rewrite. Conventions: cursor pagination (`?after=`), RFC 7807 problem JSON errors, every mutating route writes an audit event, every list route filterable by project.

```
/auth          magic-link request/verify, session, logout
/projects      CRUD · property · proposal · resolve-address
/documents     upload (pdf/docx/html/txt/dxf) · pages · facts · search · per-project
/sources       import (manifest | hermes-corpus) · list/detail · versions · review · refresh → job
/search        /chunks (hybrid FTS+vector over approved sources) · /ask (cited answer or refusal)
/rules         clauses · candidates (promote/reject) · rules (review) · coverage-audit
/compliance    run → check_run · results · matrix · result override (human)
/rfi           parse → items · item status · draft-response → job · drafts
/exports       create (json|docx|xlsx|html|csv) · list · download   [blocked until automated validation]
/validations   create · list
/reviews       generic review queue (subject_type filter)
/agent         jobs (status/retry/cancel) · traces · memory (browse/edit) ·
               skills (versions, activate, diff) · evals (cases, runs, scores)
/ops           dashboard (job health, spend, source freshness, eval trend)
```

~55 routes. The current repo's ~90 collapse mostly by deleting aliases and the doubled mount.

## 7. Background jobs — one queue, two consumers

Procrastinate tasks in Postgres; every task idempotent and keyed (`job_key = hash(type, payload)`) so retries never duplicate work. Two consumer processes:

**worker** (mechanical, no LLM): `parse_document`, `chunk_and_embed` (embeddings via ai/ but deterministic pipeline), `import_corpus_row`, `build_export`, `refresh_source` (fetch + diff + new version), `backup_verify`.

**hermes** (agentic, LLM in the loop — §8): `discover_sources`, `triage_source_change`, `extract_rules` (3-pass over a source version), `classify_clauses`, `analyse_rfi`, `draft_response`, `consolidate_memory`, `run_evals`.

Job rows carry `skill_version_id` (for agent jobs), correlation id, and write `job_traces` per LLM call. Failure policy: 2 retries with backoff, then a `review_items` row — failures surface to a human, never silently.

## 8. The Hermes agent layer — memory, skills, self-learning

Hermes stops being a dead HTTP config and becomes the agent runtime that does the heavy cognitive lifting, under governance. It is a long-running container in the same compose stack, consuming agent-queue jobs. Implementation: Claude Agent SDK (or a thin loop over the Anthropic API) with tool access limited to: read approved source/document text, call domain services, write candidates/drafts/memory — never write verdicts, rules, or exports directly.

**Hard gate (unchanged from current philosophy):** Hermes produces *candidates and drafts with citations*; deterministic code produces *verdicts*; humans produce *approvals*. Anything Hermes writes lands in a reviewable state.

### 8.1 Memory

`agent_memory` table: `(scope_type, scope_key, kind, content JSONB, confidence, source_job_id, updated_at)`.

- scope_type ∈ {domain, council, source, document_kind, skill} — e.g. (`council`, `stirling`): "LDP PDFs publish under /planning/documents; table extraction needs lattice mode", or (`domain`, `dfes`): "robots disallows /api, use sitemap".
- Written by Hermes during jobs (tool call), read at job start: the skills loader injects the relevant memory slice into context.
- Human-editable in the agent console (`/agent/memory`) — memory is data, not magic; you can correct it.
- `consolidate_memory` job runs weekly: dedupes, merges, expires stale entries, flags contradictions into `review_items`. (Same idea as the corpus provenance ledger — Hermes keeps a tidy head.)

### 8.2 Skills

`skills/` directory in the repo — one folder per agent job type:

```
skills/extract_rules/
├── SKILL.md          # procedure, constraints, output contract (the prompt spine)
├── schema.json       # required structured output (validated before anything persists)
└── examples/         # curated few-shot examples (see self-learning)
```

`skill_versions` table mirrors each content hash: `(skill_name, version, content_hash, status: draft|candidate|active|retired, eval_run_id, activated_by)`. Hermes always loads the **active** version; the version id is stamped onto every job, candidate, and draft it produces — full provenance from any rule candidate back to the exact instructions and examples that generated it.

### 8.3 Self-learning loop

Learning happens through artifacts and gates, not silent weight-drift:

1. **Capture** — every human disposition is a labeled example: promoted/rejected rule candidates, edited RFI drafts (diff of Hermes draft vs final), corrected clause classifications, fetch failures and their fixes.
2. **Distill** — weekly `improve_skill` job: Hermes reviews its own recent failures + the label bank for one skill, proposes a new skill version (updated SKILL.md, rotated examples/) as a **draft** — visible as a diff in the agent console.
3. **Gate** — proposed version runs the golden eval suite (`eval_cases`: frozen inputs with expected outputs — extraction F1, citation accuracy, refusal correctness). Score must beat or match active. Results in `eval_runs`.
4. **Approve** — you activate it with one click (audit-logged). No skill self-activates. Rollback = re-activate previous version.

Memory handles *facts about the world* (cheap, continuous, reversible); skill versions handle *behaviour* (gated, evaluated, human-approved). That split is what makes "self-learning" safe in a compliance product.

## 9. Source pipeline (ingest → citable)

```
discover_sources (hermes, manifest-anchored, lawful fetcher: robots, per-domain delay, licence notes)
  → source_inventory rows → import: licence gate (blocked/paid/robots-denied → metadata-only, never stored text)
  → source_versions (sha256, effective dates; supersession by content diff)
  → chunk (structure-aware: clause/table boundaries, not fixed windows)
  → embed (worker) + fts
  → extract_rules / classify_clauses (hermes, skill-versioned) → rule_candidates → human promote
  → triage_source_change (hermes) on refresh diffs → review_items when material
```

Standards Australia: metadata-only, enforced at import (as today). Retrieval (`/search/ask`): hybrid candidate set (FTS + pgvector cosine, reciprocal-rank fusion) → optional Haiku rerank → answer composer that only quotes retrieved chunks, returns citations or a typed refusal. The stitched threshold-table logic from the current retrieval service survives as a composer strategy.

## 10. Compliance engine

Unchanged in philosophy, simplified in plumbing: `resolve_rules(project, as_of_date)` snapshots applicable rules (zone, overlays, proposal type, date) → calculators run against `document_facts` measurements → verdict ∈ {likely_pass, likely_fail, missing_info, needs_operator_review, not_applicable} with decision trace JSONB (inputs, rule snapshot, arithmetic) and citations. LLMs never touch this path. `likely_fail`/`likely_pass` require both a resolved rule and sufficient measurements — else honest `missing_info`. Matrix endpoint renders the latest run; automated validation gate required before export, as today.

## 11. Frontend (web/)

React SPA, ~8 screens: Dashboard (projects + job/ops health) · Project workspace (property, proposal, documents) · Evidence viewer (PDF page + extracted facts side-by-side, click-through citations) · Ask (cited Q&A with refusals shown honestly) · Compliance matrix (verdicts + traces + override) · RFI workspace (items → draft → edit → export) · Sources admin (library, versions, reviews, freshness) · Agent console (jobs, traces, memory editor, skill diffs + eval scores + activate button).

State: TanStack Query against `/api/v1`, no client state library. Auth: session cookie, 401 → login screen. The agent console is what makes Hermes governable — skills and memory visible, diffable, and one click to roll back.

## 12. Security

Magic-link auth (email via Resend/Postmark), itsdangerous-signed cookies, SameSite=Lax, secure. CORS: app origin only. Rate limits (slowapi): auth 5/min/IP, ask 30/min/user. Caddy: TLS, HSTS, security headers (current Caddyfile is good — keep it). Secrets: `.env` on VPS only, never in git; `ANTHROPIC_API_KEY` only in `hermes` + `worker` env, not `api`. LLM spend: per-job-type token budgets + daily cap; breach → jobs pause + review item. Uploads: size caps, content-type sniffing, stored outside webroot. DB: no public port; containers on an internal network; Postgres password auth even locally.

## 13. Storage & backups

Local disk `/srv/draftcheck/storage/{uploads,exports,corpus,raw}` — content-addressed paths (`sha256[:2]/sha256`). No S3 abstraction until there's a second machine. Nightly restic: `pg_dump` + storage + skills → B2/R2, 30 daily/12 monthly retention; restore drill quarterly (scripted, run in CI against a scratch container).

## 14. Observability

structlog JSON with correlation ids (request id ↔ job id ↔ trace id). Sentry for exceptions (api + worker + hermes). `/health` (liveness) and `/ready` (db, queue, storage, migrations-current) — keep the current pattern. `/ops/dashboard` aggregates: queue depth, failure rate, LLM spend by skill, source freshness, eval trend. Uptime: healthchecks.io ping from a cron in the api container.

## 15. Testing & CI

- Unit: domain logic (calculators, resolvers, chunkers) — fast, no DB.
- API: pytest + httpx against a real Postgres (testcontainers) — kills the SQLite/Postgres behaviour split.
- Golden evals: frozen corpus fixtures → extraction/citation/refusal scoring; run on every skill change (gate) and weekly (drift).
- Contract: OpenAPI schema snapshot — breaking change fails CI.
- CI (GitHub Actions): ruff → mypy → import-linter → pytest → alembic upgrade+downgrade check → build images → on main: ssh deploy (compose pull + up, migrations run by api entrypoint with advisory lock).

## 16. Migration from the current repo

| Disposition | What |
|---|---|
| **Keep as-is** | corpus data (1.8 GB — it's the moat), db Dockerfile (PostGIS+pgvector), Caddyfile, lawful-fetcher rules, docs/HERMES_SCRAPE_JOB.md constraints |
| **Port with tests** | compliance calculators + rule resolution, ingestion content-addressing + licence gate, retrieval composer (incl. threshold-table stitching), document parsers (pdf/docx/html/dxf), RFI parsing, export builders, audit helper |
| **Rewrite** | router (thin, single mount), models (33-table schema, fresh Alembic base), config, job system, auth, frontend |
| **Drop** | build/, mockups/, ui/ (superseded by web/), landing (move to its own tiny repo or Caddy static), Vercel files, Supabase dir, nginx conf, MinIO, Redis/RQ, HermesAdapter (replaced by agent layer), 24 satellite tables, SQLite path |

Data migration: none needed — current DB is dev/test junk (300+ throwaway projects). Re-import the corpus through the new pipeline; it re-versions identically by SHA-256. That's the payoff of content addressing.

## 17. Build order

1. **Skeleton** (repo, CI, compose, db, auth, /health, deploy pipeline green end-to-end first).
2. **Source library**: import corpus → versions → chunks → hybrid search → `/search/ask` with citations/refusal. *(First user-visible value.)*
3. **Projects + documents**: upload, parse, facts, evidence viewer.
4. **Compliance**: resolve rules (seeded manually at first) → runs → matrix UI.
5. **Hermes v1**: agent runtime + `extract_rules` + `classify_clauses` skills, memory, agent console. Rule candidates start flowing.
6. **RFI + exports + validations**.
7. **Self-learning loop**: label capture → improve_skill → eval gate → activation UI. *(Last, because it needs accumulated human dispositions to learn from.)*

Each milestone deploys to the VPS. Nothing merges without its tests; nothing ships tables for future milestones.
# SUPERSEDED - see docs/MASTER_REBUILD_PLAN.md

This file is background context only for the V3 rebuild. Do not use it as implementation
authority where it conflicts with `docs/MASTER_REBUILD_PLAN.md`.
