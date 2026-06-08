# DraftCheck WA — As-Built Architecture

Date: 2026-06-07. This maps what is actually in the repo today, verified against the code — not what the planning docs say should exist. Companion to `REPO_AUDIT.md` (2026-06-06).

## What the app is

A FastAPI backend (`draftcheck-wa-core`) for a WA residential drafting compliance assistant, plus a thin static frontend. Core promise: every regulatory answer either cites approved, versioned source text or refuses. Compliance checks are deterministic (calculators + rules), never LLM-asserted.

## Runtime shape

```
ui/app.html (static, hardcoded → https://api.cuz.fail/v1)
        │
        ▼
FastAPI app  apps/api/draftcheck_api/main.py
  - lifespan: init_database() → create_all + alembic upgrade head
  - same router mounted TWICE: /v1/* and /api/*
  - CORS: local/test wildcard with a durable-deployment allowlist readiness gate; auth: API key in production
        │
        ▼
router.py (~1,270 lines, ~90 routes incl. aliases)
        │
        ├─ packages/core        models (57 tables), config, audit, object storage,
        │                       queue, HermesAdapter (job orchestration), providers,
        │                       embeddings, project/address/review/eval services
        ├─ packages/ingestion   manifest + Hermes-corpus import, versioning, chunking
        ├─ packages/retrieval   FTS keyword + mock-vector ranking, cited answers, refusal
        ├─ packages/compliance  calculators, rule resolution, matrix, audits (~2,100 lines)
        ├─ packages/document_ai PDF/DOCX/HTML/DXF parsing, facts, RFI parsing
        ├─ packages/export      JSON/DOCX/XLSX/HTML/CSV response packs
        ├─ packages/scraper     lawful fetcher (robots/licence checks), discovery
        └─ packages/shared_schemas  Pydantic contracts
        │
        ▼
SQLAlchemy → SQLite ./draftcheck.db (default) | Postgres+PostGIS+pgvector (compose)
Object storage → local disk .storage/ (S3-shaped adapter, no real S3 client)
Background jobs → RQ on Redis (RQ_ENABLED) | remote Hermes (HERMES_ENABLED, off) | disabled
```

## API surface (grouped)

- Auth/identity: `dev-login`, `me` — dev-grade only.
- Address: resolve, autocomplete, profile (spatial spine tables behind it).
- Projects: CRUD, property, proposal.
- Project documents: upload/parse (PDF, DOCX, HTML, text, DXF), pages, facts, search, analyze.
- Sources: manifest import, Hermes-corpus import, seed, ingest, versions, acceptance review, refresh job, fetch logs, chunk search.
- Rules/clauses: rule rows, candidates, promote/review, dispositions, coverage + no-orphan audits.
- Ask/chat: `ask`, `chat`, `ask-source-library` + project-scoped variants — cited answers or refusal.
- Compliance: resolved-rules, run, results, matrix (+ deprecated alias), measurements.
- RFI: parse/analyse, items, draft-response, responses.
- Exports: response packs + download; signoffs; review-queues; ops dashboard; golden evals; jobs (status/retry/cancel/traces); audit log.

Most workflows write `audit_events`; exports gate on `human_signoffs`.

## Data model (57 tables, 7 domains)

1. Identity/projects: users, organisations, projects, properties, project_proposals.
2. Spatial spine: spatial_datasets, parcels, address_points, planning_layer_features, local_government_boundaries, address_profiles, address_facts, local_government_facts, planning_overlays.
3. Source library: source_documents, source_versions (SHA-256 content-addressed), source_artifacts, source_licence_reviews, source_supersessions, source_references, source_chunks, source_chunk_embeddings, source_citations, source_fetch_logs, source_update_events.
4. Rules: clauses, clause_references, clause_dispositions, rule_extraction_candidates, rule_rows, rule_to_clauses, rule_overrides, rule_carveouts.
5. Project documents: project_documents, document_pages, document_chunks, extracted_document_facts, document_assets, extracted_measurements.
6. Compliance/RFI/output: check_definitions, check_runs, resolved_rules, check_results, decision_traces, assumptions, rfi_items, tasks, response_drafts, exports, human_signoffs.
7. Governance/ops: review_queue_items, golden_eval_cases, golden_eval_runs, audit_events, background_jobs, job_traces.

## Background jobs

`HermesAdapter` (packages/core) fronts ALL job enqueueing despite the name. Provider selection: `hermes` (remote HTTP, requires HERMES_ENABLED + base URL — off everywhere) → `local-rq` (RQ on Redis, used in compose) → `local-disabled` (bare local dev). The worker (`apps/worker`) is a real RQ worker with handlers for all four queues: source_ingestion, council_pack, rfi_analysis, source_freshness_audit. `docs/ARCHITECTURE.md` still calls it a placeholder — stale.

## AI layer — currently all mock

- `providers.py` contains only `MockLlmProvider`. `LLM_PROVIDER` / `EMBEDDING_PROVIDER` default to `mock`; no OpenAI/Anthropic/etc. client exists anywhere in the code.
- Embeddings are deterministic hash vectors (`mock-hash-v1`). Vector search is cosine over those (pgvector literals on Postgres, JSON on SQLite).
- Retrieval = FTS/keyword candidates + mock-vector blend + hand-built stitching for threshold tables; answers carry citations or refuse.
- Net effect: the product's "intelligence" today is deterministic parsing, rules, and keyword retrieval. That is consistent with the safety posture, but chat/ask quality is bounded until a real provider lands behind the existing protocol.

## Persistence & migrations — three competing stories

1. `init_database()` runs `Base.metadata.create_all()` **and then** `alembic upgrade head` on every app start.
2. Alembic migrations 0001–0009 (0008 requires PostGIS+pgvector; default dev DB is SQLite).
3. `supabase/migrations/` holds a 526-line initial-schema SQL that nothing in the code references.

Pick one (alembic), make `create_all` test-only, delete or regenerate the Supabase SQL.

## Deployment — four competing stories

| Target | Files | State |
|---|---|---|
| Local dev | Makefile → uvicorn + SQLite + `.storage/` | works, default |
| Docker dev | `docker-compose.yml`: custom PostGIS+pgvector db, Redis, MinIO (+init), api, worker, Caddy | plausible, but MinIO is **dead weight** — S3_* env vars are read by nothing; object storage is local-disk only |
| VPS (cuz.fail) | `deploy/docker-compose.vps.yml`, `deploy/Caddyfile`, `deploy/nginx-cuz.conf`, `infra/docker/docker-compose.production.yml`, ps1 scripts | two reverse-proxy configs and two "production" compose files for the same target |
| Vercel serverless | `vercel.json`, `index.py`, `api/index.py` | demo hack: copies the 127 MB `draftcheck.db` seed to `/tmp` on cold start; **all writes are ephemeral**; 60 s function cap |

Frontends: `ui/app.html` (live SPA → api.cuz.fail), `ui/0-3*.html` + `mockups/` (near-duplicate static mockups), `landing/`. README and AGENTS.md still say "this repo intentionally contains no frontend."

## The actual mess, ranked

1. **Version control: one commit, one tracked file.** `git ls-files` returns only README.md. ~7,000 lines of backend, all infra, all docs — untracked. Any bad edit or disk fault is unrecoverable. This dwarfs everything else.
2. **`build/` is a stale code snapshot** (setuptools artifact) containing an older router/core that shows up in every search and invites editing the wrong file. Delete + gitignore.
3. **Dual router mount (`/v1` and `/api`)** doubles the OpenAPI surface; plus intentional alias paths (ask/chat, checks/compliance, rfi parse/analyse) multiply it further. Keep `/v1`, redirect `/api`.
4. **Hermes naming**: every job flows through `HermesAdapter` while Hermes itself is disabled; the team already lost track of whether Hermes is used (it isn't). Rename to `JobService`; keep the remote provider behind it if the VPS agent ever materialises.
5. **Dead/duplicated infra**: MinIO with no S3 client; nginx + Caddy; vps + production compose; Supabase SQL; Vercel-with-SQLite. Choose VPS compose + Caddy (already named for cuz.fail), delete the rest or move to an `attic/`.
6. **Security**: production CORS allowlist and API-key auth are enforced before durable public traffic; keep real auth on the roadmap for a public API that drafts council responses.
7. **Repo hygiene**: 127 MB `draftcheck.db` at root doubling as Vercel seed; 1.8 GB `data/corpus/`; ~330 junk project dirs in `.storage/`; `mockups/` vs `ui/` near-dupes; egg-info at root; docs drift (ARCHITECTURE.md, README "no frontend", REPO_AUDIT's "worker placeholder").

## What is NOT a mess

The core is sound: clean one-direction package dependencies, a disciplined 57-table provenance model (content-addressed source versions, licence gates, citations, decision traces, signoffs, golden evals), deterministic compliance with refusal semantics, a real RQ worker, alembic chain, and 27 test files (REPO_AUDIT reported green on 2026-06-06). The mess is concentrated in deployment sprawl, dead infrastructure, naming, and the absence of version control — all fixable without touching the domain core.

## Suggested order of operations

1. Commit everything now (code, docs, infra; exclude corpus/db via .gitignore — already covered). Then commit in small slices from here on.
2. Delete `build/`, root egg-info, `.storage/` junk, `mockups/`; archive unused deploy configs.
3. Pick the deployment story (VPS compose + Caddy) and delete Vercel/Supabase remnants, or explicitly mark them experimental.
4. Collapse to a single `/v1` mount; rename HermesAdapter; update README/AGENTS to admit the frontend exists.
5. Unify migrations on alembic.
6. Real auth + CORS allowlist before anything public writes data.
7. Only then: wire a real LLM/embedding provider behind the existing protocol.
