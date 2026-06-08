# DraftCheck WA — Master Rebuild Plan (v3)

Date: 2026-06-07
Status: **single implementation authority** for the greenfield rebuild.

Supersedes as implementation authority (files stay, marked superseded):

```text
docs/REBUILD_SPEC.md                  (absorbed as the base)
docs/MASTER_IMPLEMENTATION_PLAN.md
MASTER_PLAN_ADDENDUM.md
docs/PLAN_LOCK_NOTICE.md              (lock rules re-issued in §12)
the 2026-06-07 review pair: "Merged Rebuild Plan" + "brain" notes (folded in)
```

The old lock rule "do not add frontend/browser UI in this repository" is dead. On merge of PR 1: update `AGENTS.md` to point here and add a `SUPERSEDED — see docs/MASTER_REBUILD_PLAN.md` banner to the docs above.

---

## 0. Review verdict

Both reviewed plans hold up. The merged rebuild plan is the right backbone: one repo, one VPS, one `/api/v1` mount, one Postgres, Procrastinate, content-addressed storage, governed Hermes, deterministic compliance. The "brain" note is the right architecture rationale: the LLM is a governed worker, never the judge; four memory layers; hybrid search; deterministic engine. Both are kept.

But both were written partly against an imagined repo. The 2026-06-07 audit (§11) shows: the router is mounted at **both `/v1` and `/api`** (not a lone `/v1` alias), the frontend already lives in this repo as static HTML under `ui/`, `create_all` and Alembic both claim schema authority, a **127 MB SQLite file sits in the git tree** as the Vercel seed, there is **no CI at all**, and the legacy DB holds human-labelled data (approved rules, clause dispositions, golden evals) that a naive greenfield would discard.

### Fixes applied in v3

| # | Problem in the reviewed plans | Fix | Severity |
|---|---|---|---|
| 1 | LLM governance (traces, skill versions, spend caps) scheduled for Phase 6, but LLM calls start in Phase 1 (`/ask`) and Phase 3 (extraction) | Agent substrate lands with the first LLM call; Phase 6 is autonomy + console only (§7, §9) | High |
| 2 | Plans assumed wrong repo state (single `/v1` alias, frontend separate, CI exists) | Cutover steps rewritten against audit ground truth (§6.3, §11) | High |
| 3 | Carve-out modeling conflict: `carveout_json`/`override_json` on rules (plan A) vs separate `Carveout` table (plan B) vs legacy `rule_overrides` + `rule_carveouts` | One mechanism: `rules.rule_type` + `legal_edges`; no carve-out JSON blobs on rules (§5.4) | High |
| 4 | Drawing-fact → measurement promotion underspecified | Explicit promotion contract; engine consumes only promoted, confirmed facts (§5.6, §8.3) | High |
| 5 | G-NAF address points missing from greenfield spatial schema, in an address-first product | `address_points` added to spatial group (§5.3) | High |
| 6 | Deemed-to-comply vs design-principle pathway (core WA R-Codes structure) not modeled | `rules.pathway`, `performance_alternative_to` edge, result annotation (§5.4, §8.4) | High |
| 7 | Legacy human labels (approved RuleRows, dispositions, golden evals) lost in greenfield | Label harvest from legacy DB before decommission → eval seed corpus (§9 PR 5) | High |
| 8 | No Postgres backup plan (restic covered files only) | Nightly `pg_dump` → restic + restore drill as Phase 0 exit criterion (§3.3) | High |
| 9 | SLIP public cadastre is a personal-use-licensed subset; plans assumed free commercial use | Per-dataset licence verification gate; risk register item (§8.2, Appendix B) | High |
| 10 | Magic-link auth from day one, with no email provider or bootstrap path | EmailSender abstraction + operator CLI login link; dev mode logs the link (§5.1) | Med |
| 11 | Embedding model/dimensions unpinned (vector columns are dimension-locked) | Pinned provider/model/dim, recorded per chunk, re-embed procedure (§8.1) | Med |
| 12 | No VPS hardening, upload limits, or observability until Phase 8 | Phase 0 hardening + minimal observability checklist (§3.4) | Med |
| 13 | No LLM spend controls until the ops dashboard | Daily budget + per-job caps + circuit breaker from first call (§7) | Med |
| 14 | First end-to-end demo implicit and late | Golden fixture project from Phase 2; M1 vertical-slice gate at Phase 5 (§9) | Med |
| 15 | Drawing revisions (Rev A/B/C) unmodeled, though every real project iterates | `documents.supersedes_document_id` revision chain (§5.6) | Med |
| 16 | No datum decision | GDA2020 (EPSG:7844) everywhere; transform at import (§8.2) | Med |
| 17 | `orgs` table absent and no roles, despite org_id-everywhere and human approval gates | `orgs` table; `users.role ∈ {owner, reviewer}`; approvals require reviewer (§5.1) | Med |
| 18 | Height checks treated like setbacks (they need natural ground level / survey data) | Check difficulty tiers; v1 = Tier 1; heights default `needs_human_review` (§8.4) | Med |
| 19 | `check_definitions` as DB seed rows let fallback defaults masquerade as rules (25 DEFAULT_CHECKS do this today) | Check registry moves to code (typed, versioned); DB seeds removed (§5.7) | Med |
| 20 | Table-count fetish (36 vs 33 stated; 57 exist today) | Target ≈ 42; count descriptive, provenance wins; full legacy mapping (Appendix A) | Low |
| 21 | No API conventions (errors, pagination, idempotency) | §6.2 | Low |
| 22 | Procrastinate schema step unstated; legacy RQ queue names unmapped | §3.2 | Low |
| 23 | Worked examples (R40, 4.5 m) risk being hardcoded by agents | All legal values in examples are illustrative; hardcoding one is a defect (§12) | Low |
| 24 | No DNS rollback plan for the Vercel cutover | TTL drop + 48 h dual-run + rollback (§9 Phase 0) | Low |

---

## 1. Locked decisions

Rows marked **(new)** amend the reviewed plans. Everything overrides older docs where they conflict.

| Area | Final decision |
|---|---|
| Production | Single VPS on `cuz.fail`, Docker Compose, Caddy. No Vercel, no Supabase. |
| Repo | `C:\Dev\Cuz` is the repo. Frontend is first-class under `web/`. Legacy `ui/`, `landing/`, `mockups/` become design references, then archived. |
| API mount | One mount: `/api/v1`. The new app never exposes `/v1` or `/api`. Legacy app keeps serving `/v1` until M1 cutover (§6.3). |
| App shape | One installable package: `src/draftcheck/`. The ten legacy package roots are frozen (bugfix only) and deleted at M1 parity. |
| DB | PostgreSQL 16 + PostGIS + pgvector. Alembic is the only schema authority; `create_all`/`init_database()` never ships in the new app. |
| Queue | Procrastinate on Postgres. Redis/RQ and the `background_jobs` table are deleted from the target. |
| Storage | Local content-addressed tree at `/srv/draftcheck/storage` (`sha256[:2]/sha256`), restic to B2/R2. No MinIO/S3/boto in v1. |
| Proxy | Caddy only. `deploy/nginx-cuz.conf` is dead and removed. |
| Auth | Magic-link email + signed session cookies. **(new)** Email goes through an `EmailSender` port (SMTP creds via env, provider chosen at deploy); dev mode logs the link; `cli login-link` issues a one-time bootstrap URL. No dev-login in production. **Amended 2026-06-08 (operator):** a dev-only username/password login (`POST /api/v1/auth/dev-login`, default `jemma`/`jemma6969`, creds overridable via `DEV_LOGIN_USERNAME`/`DEV_LOGIN_PASSWORD`) is allowed while building; it is hard-disabled (404) whenever `app_env=production`, so the shipped surface stays magic-link only. |
| Roles **(new)** | `users.role ∈ {owner, reviewer}`. Rule approval, source approval, overrides, and signoffs require `reviewer`+. Single human may hold both; the audit trail still records who. |
| AI | Hermes is the governed agent runtime. LLMs extract, classify, embed, draft — never decide compliance verdicts. Governance substrate exists from the first LLM call (§7). |
| Spend **(new)** | Per-job token caps + daily budget env + breaker that pauses agent queues. From Phase 1, not Phase 8. |
| Compliance | Deterministic calculators over resolved rules and promoted measurements. `likely_pass`/`likely_fail` require proof (§8.4). Check registry lives in code, not DB seeds. |
| Check scope **(new)** | v1 ships Tier 1 checks only: setbacks, site cover, open space, garage width/dominance, boundary wall length. Heights are Tier 2 → `needs_human_review` unless calibrated levels exist. |
| Embeddings **(new)** | One pinned provider/model/dimension via env (default: API provider, 1536-dim, cosine, HNSW). `embedding_model` recorded per chunk; changing models = documented re-embed migration. |
| Spatial datum **(new)** | GDA2020 (EPSG:7844) for everything; transform at import; record source CRS in `spatial_datasets`. |
| Backups **(new)** | Nightly `pg_dump` + `/srv/draftcheck/storage` via restic; weekly `restic check`; monthly restore drill into a scratch container. Phase 0 exit criterion. |
| UX | Address-first wizard. Chat secondary. Issue card is the core object. |
| Tenancy | Single-tenant operationally; `orgs` table exists and `org_id` is on every tenant-owned row. |
| Examples **(new)** | Every numeric/legal value in this plan's examples is illustrative. Real values come only from approved, cited rules. |
| Autonomy **(new 2026-06-08)** | Operator standing approval: agents execute git/CI/deploy/DNS/infra work without per-step human approval (see `AGENTS.md`). Dual-run/monitoring windows are discretionary, not mandated. Product-level legal gates (rule approval, signoffs) are unchanged. |

Caddy provides automatic HTTPS for the configured hostnames. Procrastinate gives retries, periodic jobs, locks, and workers on plain Postgres. pgvector supports exact search plus HNSW/IVFFlat. uv manages Python deps with a lockfile. (References: Caddy docs, Procrastinate docs, pgvector README, uv docs.)

---

## 2. Architecture — the brain

The brain is not a model. It is eight components; the LLM is a worker inside them.

```text
1. Source archive        official docs, versions, hashes, licence status
2. Legal parser          clauses, definitions, tables, exceptions, cross-references
3. Rule graph            approved rule atoms + exceptions + precedence (rules + legal_edges)
4. Spatial resolver      address -> parcel -> council -> zone -> overlays -> hazards
5. Drawing fact extractor CAD/PDF/IFC -> facts -> promoted measurements with evidence
6. Deterministic engine  resolved rules vs promoted measurements -> traced results
7. Retrieval layer       finds and explains evidence; never decides compliance
8. Agent memory          scraper quirks, council quirks, parser fixes, failure notes
```

Four memories, never mixed:

```text
Legal memory    source_versions, clauses, rules, legal_edges, source_reviews
Spatial memory  parcels, address_points, planning_features, property_facts, spatial_datasets
Drawing memory  documents, document_pages, document_facts
Agent memory    agent_memory, skill_versions, job_traces, eval_cases/runs, review_items
```

```text
Retrieval memory finds evidence.
Agent memory improves workflow.
Rule memory decides applicability.
The deterministic engine decides results.
```

End-to-end:

```text
Official docs -> source_versions -> clauses -> rule_candidates -> rules/legal_edges
Address -> parcel -> council -> zone/R-code/overlays -> property_facts
Proposal -> applicability + precedence -> resolved_rules
Drawings -> document_facts -> promoted measurements
Engine -> check_results + decision_trace_json -> issue cards -> signoff -> export
```

---

## 3. Topology and infrastructure

### 3.1 Final shape

```text
Browser -> https://app.cuz.fail  -> Caddy -> web/dist (SPA)
SPA     -> https://api.cuz.fail/api/v1/* -> Caddy -> api container
api / worker / hermes -> Postgres 16 (PostGIS + pgvector)
                      -> Procrastinate queue tables (same Postgres)
                      -> /srv/draftcheck/storage
restic  -> B2/R2 (DB dumps + storage tree)
```

Containers: `db`, `api`, `worker`, `hermes`, `caddy`. Nothing else. Only `caddy` publishes 80/443; `db`/`api`/`worker`/`hermes` stay on the internal network. Removed from target: redis, minio, minio-init, nginx, vercel, supabase, SQLite production path.

DB image: build on PostGIS base + install `postgresql-16-pgvector`; an init script runs `CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS vector;` (extension creation needs superuser — do it in image init, not Alembic).

VPS minimum: 4 vCPU / 16 GB RAM / 200 GB NVMe (Docling + OCR + spatial imports are memory-hungry; parse jobs run in `worker` with concurrency 1–2, never in `api`).

### 3.2 Queue

Procrastinate, pinned version. Deploy runs `procrastinate schema --apply` alongside `alembic upgrade head`. Queue names carry over from the legacy RQ set:

```text
default | source_ingestion | council_pack | rfi_analysis | source_freshness_audit | hermes
```

`source_freshness_audit` becomes a Procrastinate periodic task. The spend breaker (§7) pauses `hermes` and extraction queues only; deterministic jobs keep running.

### 3.3 Backups

```text
Nightly: pg_dump -Fc -> /srv/draftcheck/backups -> restic backup (DB + storage tree)
Weekly:  restic check
Monthly: restore drill -> scratch postgres container -> alembic current + row-count sanity
```

A failed or stale backup (>26 h) raises an alert (§3.4). Restore drill is a Phase 0/1 exit criterion, not an aspiration.

### 3.4 Hardening and observability (Phase 0)

```text
SSH keys only; ufw allow 22/80/443; fail2ban; unattended-upgrades
Docker: no socket mounts into app containers; non-root users; internal-only db
Caddy: security headers; request body limit (250 MB on /api/v1 upload routes only)
API: rate-limit middleware (carried over from legacy), request IDs, JSON logs
Uptime: external monitor on /api/v1/ready and https://app.cuz.fail
Alerts: backup freshness, disk usage on /srv and Postgres volume, worker heartbeat
Errors: Sentry (or equivalent) on api + worker; optional but recommended
```

---

## 4. Repo layout and migration

### 4.1 Target

```text
draftcheck/
├── src/draftcheck/
│   ├── api/                 routers, auth, middleware
│   ├── domain/              projects/ sources/ rules/ documents/ compliance/ rfi/ exports/ address/
│   ├── ai/                  model adapters, embeddings, validators
│   ├── agent/               hermes runtime, memory, skills loader
│   ├── jobs/                procrastinate tasks
│   ├── checks/              code-owned check registry + calculators (§5.7)
│   ├── db/                  models.py, session.py, alembic/
│   ├── cli.py               login-link, corpus import, label harvest, ops
│   └── config.py
├── skills/                  extract_rules/ classify_clauses/ analyse_rfi/ draft_response/
│   └── <skill>/SKILL.md + schema.json + examples/
├── web/                     React SPA (src/, package.json, dist/)
├── infra/                   compose.yml, Caddyfile, db/Dockerfile, deploy.sh, backup/
├── tests/
├── data/                    corpus (1,422 files today) + fixtures
└── pyproject.toml + uv.lock
```

Tooling: uv, ruff, mypy, import-linter (layer rule: `api -> domain -> db`; `checks/` imports no `ai/`). Single `pyproject.toml`; the legacy root `requirements.txt` is deleted.

### 4.2 Migration of the ten legacy package roots

```text
apps/api/draftcheck_api            -> src/draftcheck/api
apps/worker/draftcheck_worker      -> src/draftcheck/jobs
packages/core/draftcheck_core      -> split: db/, config.py, domain/*
packages/ingestion/...             -> domain/sources + jobs
packages/retrieval/...             -> domain/sources/search
packages/compliance/...            -> checks/ + domain/compliance
packages/document_ai/...           -> domain/documents/parsers
packages/export/...                -> domain/exports
packages/scraper/...               -> domain/sources/fetcher
packages/shared_schemas/...        -> dissolved into domain modules
```

Rule during rebuild: legacy packages are frozen (bugfix only). New code never imports legacy packages and vice versa. At M1 parity, legacy `apps/`, `packages/`, `api/`, root `index.py` are deleted in one PR.

`draftcheck.db` (127 MB) leaves the git working tree in Phase 0: harvested (§9 PR 5), archived to storage, `.gitignore`d. History rewrite is optional later; stop tracking now.

---

## 5. Data model (~42 tables)

Count is descriptive. Provenance, auditability, and query correctness always beat table-count aesthetics. Full legacy→greenfield mapping in Appendix A.

### 5.1 Identity

```text
orgs        single row operationally; everything tenant-owned carries org_id
users       email, role ∈ {owner, reviewer}, status
sessions    token_hash (random 256-bit, stored hashed), created_at, expires_at, revoked_at
```

Auth flow: `POST /auth/magic-link/request` → EmailSender (SMTP env; dev logs URL; `cli login-link` for bootstrap) → 15-min single-use token → session cookie (HttpOnly, Secure, SameSite=Lax, sliding 30 d). Unsafe methods require an Origin check. In production this is the only auth path. **Amended 2026-06-08 (operator):** a dev-only `POST /auth/dev-login` (username/password, default `jemma`/`jemma6969`) exists for local building and is hard-disabled (404) when `app_env=production`.

### 5.2 Projects

```text
projects        lodgement_date, as_of_date, assessment_basis
properties      resolved address identity + resolution_cache (display only, never authority)
proposals       proposal_type, dwelling_type, building_class, work_type, new_or_existing,
                lot_type, primary/secondary_street_confirmed, source, confidence
property_facts  row-per-fact provenance (below)
```

`property_facts` (the queryable spatial spine — never bury legal facts in opaque JSON):

```text
fact_type   council | parcel | zone | r_code | overlay | bushfire | heritage |
            lot_area | frontage | corner_lot | primary_street | secondary_street |
            lot_topology | easement
value_json, confidence, method ∈ {parcel_intersection, point_intersection, manual_override,
            source_import, drawing_inferred, user_confirmed, assumption}
spatial_dataset_id, source_version_id, planning_feature_id, parcel_id
effective_from, effective_to, stale_at, review_status
```

`dwelling_type` is a proposal fact, never an address fact. Address resolution responses use `resolution_status ∈ {resolved, missing_info, needs_human_review, unsupported}` with separate `confidence` (carried over from the addendum — that correction stands).

### 5.3 Spatial

```text
parcels            cadastral polygons (GDA2020)
address_points     G-NAF points (the resolver's first hop — was missing from the greenfield spec)
planning_features  layer_type ∈ {zone, overlay, bushfire, heritage, airport, noise, region_scheme}
lg_areas           local government areas (merged legacy boundaries + registry)
spatial_datasets   dataset_id, licence, licence_status, source_crs, version, fetched_at, refresh_due
```

### 5.4 Sources and legal structure

```text
source_documents, source_versions, source_chunks, source_citations,
source_fetch_log, source_reviews, artifacts
clauses, rule_candidates, rules, rule_clause_links, legal_edges
```

`artifacts` — one generic evidence vault (replaces SourceArtifact + DocumentAsset):

```text
subject_type ∈ {source_version, document, document_page, export, skill_version}
kind ∈ {raw_pdf, raw_html, raw_docx, parsed_text, ocr_text, table_json, page_image,
        extraction_output, canonical_text, export_file, skill_bundle}
storage_path, sha256, media_type, size_bytes, parser_name, parser_version, metadata_json
```

Storage is deduped by sha256 path; multiple artifact rows may point at one blob.

`source_versions`: sha256, storage_manifest_json, effective_from/to, published_at, fetched_at, superseded_by_version_id, licence_status, review_status. Changed source text always creates a new version; approved rules are never silently updated.

`rules` — approved, quote-anchored rule atoms:

```text
rule_key, operator, value_json, unit, condition_json, quote, clause_id, source_version_id
rule_type  ∈ {requirement, exception, definition, procedural_gate}
pathway    ∈ {deemed_to_comply, design_principle, none}
lifecycle_status ∈ {candidate, pending_review, auto_accepted, approved, rejected, stale, superseded}
extractor_model, skill_version_id, prompt_hash
```

**Carve-outs and overrides are rows, not blobs.** An exception is a `rules` row with `rule_type = exception` (own quote, own citation, own review status), linked by `legal_edges`. The reviewed plans' `override_json`/`carveout_json` fields and the legacy `rule_overrides`/`rule_carveouts` tables are all replaced by this one mechanism.

`legal_edges` — the legal graph:

```text
from/to ∈ {clause, rule, source_version, external_reference}
relation ∈ {cites, modifies, defines, overrides, repeals, supersedes, depends_on,
            exception_to, applies_with, performance_alternative_to}
evidence_quote, confidence, review_status
unique (from_type, from_id, to_type, to_id, relation); indexed both directions
```

`performance_alternative_to` links each deemed-to-comply rule to its design-principle clause — the R-Codes are structured this way, and the engine reports "fails DTC, design-principle pathway available" instead of a bare fail.

Clause dispositions (column on `clauses`): `rule_bearing | definition | procedural | informational | manual_review`. The deprecated `fluff`/`definitions`/`needs_review` values stay banned.

### 5.5 Compliance

```text
check_runs       pins as_of_date + source_version set; immutable
resolved_rules   output of applicability + precedence, with assumptions_json
check_results    status, requirement_json, proposed_json, why_this_applies, citations_json,
                 drawing_evidence_json, decision_trace_json, pathway_note,
                 human_review_reason, human_override_json
```

`decision_trace_json` stays inline (no separate table in v1 — the legacy `decision_traces` table folds in). Minimum shape:

```json
{
  "inputs": {}, "formula": "proposed >= required", "comparison": "3.8 >= 4.5",
  "unit_conversions": [], "rounding_policy": "no_rounding_before_comparison",
  "tolerance": "0.001 m", "result": "likely_fail",
  "resolved_rule_ids": [], "measurement_ids": [], "citation_ids": [],
  "applicability_trace": {}, "precedence_trace": {},
  "engine_version": "", "rule_snapshot_hash": "sha256", "measurement_snapshot_hash": "sha256"
}
```

### 5.6 Project documents

```text
documents        + supersedes_document_id, revision_label  (Rev A/B/C chains; re-run on new
                   revision; matrix can diff runs later)
document_pages, document_chunks
document_facts   fact_kind ∈ {measurement, drawing_entity, drawing_label, area, height,
                 setback, boundary, note, table_value}
                 value_json {value, unit, basis}, check_key, confidence, page_id, artifact_id,
                 evidence_ref_json, promoted_to_measurement, review_status
```

**Promotion contract** (replaces the vague flag): a fact may be promoted to a measurement only when unit is known, the label is explicit, the evidence link (entity/page/region + parser run) exists, the value parses, confidence clears threshold, and a `check_key` mapping is recorded. The engine reads only `promoted_to_measurement = true AND review_status = confirmed`. Everything else is display/review material. Legacy `extracted_measurements` + `extracted_document_facts` fold into this one table.

### 5.7 Check registry lives in code

The legacy `check_definitions` table (25 seeded DEFAULT_CHECKS) let fallback defaults emit pass/fail without resolved rules — exactly the failure mode this system exists to prevent. In the rebuild:

```text
src/draftcheck/checks/registry.py   typed check_keys + calculator bindings + required inputs
```

versioned with the code (`engine_version`), tested with property-based tests. Fallback defaults may exist only as clearly-labelled `assumption` provenance and can never produce `likely_pass`/`likely_fail` on their own.

### 5.8 RFI, outputs, agent

```text
rfi_items, response_drafts, exports, signoffs            (exports blocked without signoff)
job_traces, agent_memory, skill_versions, eval_cases, eval_runs, audit_events, review_items
```

`review_items` absorbs the legacy `tasks` + `review_queue_items` pair. Every approve/override/signoff writes an `audit_events` row — enforced in service code, asserted in tests. Procrastinate owns its own queue tables on top of these 42.

---

## 6. API

### 6.1 Surface — `/api/v1` only

```text
/auth        POST magic-link/request | POST magic-link/verify | GET session | POST logout
/projects    CRUD | POST {id}/resolve-address | GET {id}/property | PUT {id}/proposal
/documents   POST projects/{project_id}/upload | GET {id} | GET {id}/pages | GET {id}/facts
             POST {id}/facts/{fact_id}/review
/sources     POST import | GET / | GET {id} | GET {id}/versions | POST {id}/review
             POST {id}/refresh | GET freshness
/rules       GET clauses | GET clauses/{id} | GET candidates | POST candidates/{id}/promote
             POST candidates/{id}/reject | GET / | POST {id}/review | GET coverage-audit
/search      POST chunks | POST ask        (cite-or-refuse)
/compliance  POST projects/{project_id}/run | GET projects/{project_id}/matrix
             POST results/{id}/override
/rfi         POST projects/{project_id}/parse | GET projects/{project_id}/items
             POST items/{id}/draft-response | GET drafts/{id}
/exports     POST / | GET / | GET {id}/download
/signoffs    POST / | GET projects/{project_id}
/reviews     GET / | POST {id}/resolve
/agent       GET jobs | POST jobs/{id}/retry | POST jobs/{id}/cancel | GET traces
             GET memory | PUT memory/{id} | GET skills | GET skills/{id}/diff
             POST skills/{id}/activate | GET evals | POST evals/run
/ops         GET dashboard | GET health | GET ready
```

### 6.2 Conventions (new)

```text
Errors      RFC 9457 problem+json everywhere
Pagination  cursor-based (?cursor=&limit=), stable ordering
Uploads     streamed to storage; idempotent by sha256 (re-upload returns existing document)
Limits      body cap 250 MB on upload routes; rate limiting carried from legacy middleware
Versioning  path only (/api/v1); breaking change = /api/v2, no header tricks
```

### 6.3 Mount migration (ground truth, not the imagined state)

Today `apps/api/draftcheck_api/main.py` mounts the router at **both `/v1` and `/api`**, and `ui/app.html` hardcodes `https://api.cuz.fail/v1`. Plan:

```text
1. New app mounts once at /api/v1. No aliases, ever.
2. Legacy app keeps /v1 (and its /api mount) untouched until M1.
3. Caddy routes by path: /api/v1/* -> new api; /v1/* -> legacy api (transition only).
4. web/ SPA talks to /api/v1 from its first commit.
5. At M1: legacy app + /v1 route deleted; the addendum's /v1 canonical-endpoint list is void.
```

---

## 7. AI governance — substrate before autonomy

The reviewed plans put job traces, skill versions, and evals in Phase 6 while spending LLM tokens from Phase 1 (`/search/ask`) and Phase 3 (rule extraction). Wrong order. The rule:

**No LLM call without substrate.** From the first call, every model invocation runs through one adapter that writes `job_traces` (model, prompt_hash, skill_version_id, input/output artifact ids, tokens, cost) and respects spend controls (per-job token cap, daily budget env, breaker that pauses agent queues). `skill_versions` + `eval_cases` exist from Phase 3, seeded by harvesting the legacy DB's human labels (approved RuleRows, clause dispositions, golden eval cases) before it is decommissioned. Phase 6 adds only the autonomous Hermes loop, memory curation, and the console — not the bookkeeping.

Hermes may write:

```text
rule_candidates | clause classifications | response_drafts | agent_memory
skill draft proposals | review_items | job_traces
```

Hermes may never write:

```text
rules.lifecycle_status = approved | resolved_rules (final) |
check_results likely_pass/likely_fail | exports/signoffs
```

Gate chain: `LLM proposes → validators check → evals gate → human approves → deterministic engine decides`. Skills live in `skills/<name>/` (SKILL.md + schema.json + examples/); every output records skill_version_id, model, prompt_hash, input/output artifacts, job_trace_id. Self-learning (Phase 8) starts only after human-labelled examples accumulate — and the legacy label harvest gives it a head start.

Note: the legacy `HermesAdapter` points at an external service via `HERMES_BASE_URL`. In the rebuild Hermes is the in-repo `hermes` container (an agent loop over the same Procrastinate queue), not an external dependency.

---

## 8. Pipelines

### 8.1 Sources

```text
discover -> lawful fetch (robots, licence, delay) -> source_documents -> source_versions (sha256)
-> artifacts (raw, parsed, OCR, tables, page images) -> chunk -> FTS + embeddings
-> clauses + legal_edges -> rule_candidates -> quote-anchor validation
-> no-orphan audit -> normative-language audit -> human promotion -> approved rules
```

Hard rules: changed text ⇒ new version; stale rules excluded from applicability; Standards Australia metadata-only unless lawfully supplied and licence-reviewed; no source supports an answer until licence/review status allows.

Search is hybrid, in Postgres: metadata filters → FTS (`tsvector`/`websearch_to_tsquery`) + pgvector cosine, fused with reciprocal-rank fusion → legal-graph expansion via `legal_edges` → rerank preferring approved/current/jurisdiction-matched → cite-or-refuse composer. Chunks align to clause boundaries, not fixed windows.

Embeddings: one pinned model + dimension (env-locked; default API provider at 1536-dim). `source_chunks.embedding` is an inline vector column with `embedding_model` recorded per row; the legacy separate `source_chunk_embeddings` table folds in. Model change = scripted re-embed migration + index rebuild, never silent drift.

### 8.2 Spatial spine (verified datasets — Appendix B)

```text
address (autocomplete: any geocoder, display only)
  -> G-NAF address point        (Geoscape G-NAF, data.gov.au, quarterly, GDA2020;
                                 EULA based on CC BY 4.0 with a mail-use restriction)
  -> parcel polygon             (Landgate cadastre via SLIP — public tier is a simplified,
                                 personal-use-licensed subset: commercial terms MUST be
                                 confirmed with Landgate before launch. Risk register item.)
  -> LGA by parcel intersection (Landgate admin boundaries)
  -> zone + R-code              (DPLH Local Planning Scheme Zones and Reserves, DPLH-071, WFS)
  -> bushfire / heritage / overlays (SPP 3.7 bushfire-prone mapping via SLIP; heritage registers;
                                 confirm current dataset IDs + licence at import)
```

Everything transforms to GDA2020 (EPSG:7844) at import; `spatial_datasets` records dataset id, licence, source CRS, version, fetched_at, refresh cadence. Parcel intersection is primary; point-in-polygon is a flagged lower-confidence fallback. A Google/other geocoder result is never legal proof — resolution must land on a G-NAF point + parcel, both with provenance. Dataset refresh diffs mark dependent `property_facts` stale → `review_items`.

Precedence (explicit, recorded in `precedence_trace`):

```text
1 scheme amendment > 2 local planning scheme > 3 structure plan / LDP
> 4 local planning policy > 5 R-Codes / state policy > 6 guidance material
```

Overridden rules are recorded as overridden, never deleted — the evidence drawer shows "state default exists but local rule X overrides it here."

### 8.3 Drawings

| Input | Reliability | Treatment |
|---|---|---|
| DXF | High | ezdxf; dimensions/text/layers → facts. Primary v1 target. |
| IFC | High when supplied | IfcOpenShell; spaces/walls/storeys → facts. |
| DWG | Medium/low | Only via recorded conversion to DXF/IFC; else metadata-only. |
| Vector PDF | Medium | Docling primary, Unstructured second-opinion; text/tables yes, geometry cautious. |
| Raster/scan | Low | OCR only. No measurement unless explicitly calibrated. |

Today only pypdf + python-docx + a handwritten DXF parser exist — Docling, Unstructured, ezdxf, IfcOpenShell are all Phase 4 additions behind one parser interface, outputs stored as `artifacts` with parser name/version. Facts → promotion contract (§5.6) → measurements. A PDF line length at an assumed scale stays `needs_human_review`, always.

### 8.4 Compliance

```text
project + property_facts + proposal
  -> applicable source versions (as_of_date)
  -> rule selection (jurisdiction, zone, R-code, overlays, proposal type)
  -> precedence + exceptions (rule_type=exception edges)
  -> resolved_rules -> promoted measurements -> code-registry calculators
  -> check_results + decision_trace_json -> issue cards -> signoff -> export
```

Statuses: `likely_pass | likely_fail | missing_info | needs_human_review | not_applicable | unsupported`.

`likely_pass`/`likely_fail` require all of: approved resolved rule, promoted measurement, official citation, decision trace, not excluded by precedence. Otherwise: missing source/spatial fact/measurement → `missing_info`; legal conflict or discretion → `needs_human_review`; no citable support → `unsupported`. When a DTC rule fails and a `performance_alternative_to` edge exists, the result carries a `pathway_note`: design-principle assessment available — that is WA reality, not a softener.

Check tiers (new): **Tier 1 (v1):** setbacks, site cover, open space, garage width/dominance, boundary wall length — matches the calculators already proven in `packages/compliance`. **Tier 2:** heights, levels — require calibrated FFL/NGL facts; default `needs_human_review`. **Tier 3:** overshadowing, visual privacy cones — post-v1. Shipping a tier above its evidence quality is a defect.

### 8.5 Frontend

Wizard-first, chat secondary. Screens: login; dashboard; address/property resolver; proposal confirmation; matched sources; upload drawings; extracted-facts review; compliance matrix; evidence drawer; ask-with-citations; RFI workspace; sources admin; agent console; ops dashboard. The issue card (status, rule, requirement, proposed, result, why-this-applies, citation, drawing evidence, calculation, review reason) is the core object. No wall of model prose; no uncited regulatory claim. The legacy `ui/*.html` pages are design references only — the SPA in `web/` is a fresh build (there is no JS toolchain in the repo today; `web/` gets Vite + React + package.json in PR 2).

---

## 9. Build order

### Phase 0 — Skeleton, VPS, safety rails

```text
1.  Refresh REPO_AUDIT.md (exists, 2026-06-06) + add DATA_INVENTORY.md (corpus, .storage,
    SQLite contents, label counts) + VERCEL_AUDIT.md
2.  src/draftcheck skeleton; uv + pyproject + lockfile; ruff/mypy/import-linter
3.  web/ skeleton (Vite + React) building to web/dist
4.  infra/compose.yml (db, api, worker, hermes, caddy); custom PostGIS+pgvector image
5.  Caddyfile: SPA + /api/v1 -> new api, /v1 -> legacy api (transition)
6.  FastAPI shell: /api/v1/health, /api/v1/ready; JSON logs; request IDs
7.  Alembic base migration; create_all banned in new app (import-linter rule + test)
8.  Auth skeleton (§5.1) incl. cli login-link
9.  CI from scratch (none exists): lint, typecheck, tests, alembic upgrade+downgrade,
    web build — on every PR
10. deploy.sh over SSH; backups + hardening + uptime (§3.3–3.4)
11. draftcheck.db out of git tree (harvest first — PR 5); archive ui/ as design reference
12. Vercel cutover, safely: audit -> VPS verified green -> DNS TTL dropped -> switch
    api.cuz.fail/app.cuz.fail -> dual-run with rollback (window discretionary; default
    proceed once checks are green) -> disconnect Vercel
    integration -> archive vercel.json, api/index.py, root index.py, .vercelignore, .vercel/
```

Exit: VPS deploy green; TLS green; `SELECT extname FROM pg_extension` shows postgis + vector; auth works; CI green on PRs; backup restore drill passed; no Vercel deploy fires on push.

### Phase 1 — Source library + search

Sources/artifacts tables; corpus import (1,422 files in `data/corpus` + `.storage` blobs → content-addressed storage); clause-aligned chunking; FTS; pinned embeddings + HNSW; `/search/chunks`; `/search/ask` (cite-or-refuse). **Agent substrate v0 ships here**: model adapter + `job_traces` + spend caps, because `/ask` is the first LLM call.
Exit: corpus imported with hash/licence/review status + artifacts; ask cites or refuses; metadata-only sources cannot support answers; every model call traced and budget-capped.

### Phase 2 — Projects, address, spatial

Projects/properties/proposals/property_facts; parcels/address_points/planning_features/lg_areas/spatial_datasets; dataset import with licence verification gate (cadastre licence confirmed — §8.2); resolver; manual override with provenance; wizard steps 1–3; **golden fixture project created** (one council, one address) and used by tests from here on.
Exit: address → parcel/council/zone/overlays or `missing_info`; geocoder results never legal proof; every fact has provenance; wizard creates a project and shows matched sources.

### Phase 3 — Legal structure + rule extraction

Clauses, legal_edges, rule_candidates, rules, rule_clause_links; clause parser; 3-pass extraction; quote anchoring; unit normalization; no-orphan + normative-language audits; review UI. **skill_versions + eval_cases ship here**, seeded from the legacy label harvest.
Exit: every candidate has quote + clause + source version; invalid quotes rejected; normative clauses can't be silently informational; no orphan numbers/tables/exceptions at source approval; humans promote; every extraction traced with skill version + prompt hash.

### Phase 4 — Documents + drawing facts

Documents (with revision chain), pages, chunks, document_facts; parser interface (Docling, Unstructured, OCR, ezdxf, IfcOpenShell; DWG metadata-only without recorded conversion); parser outputs as artifacts; facts review UI; promotion contract enforced.
Exit: PDF/DOCX/HTML/TXT parse; DXF dimensions become evidence-linked facts; raster scale never inferred without calibration; ambiguous facts stay in review.

### Phase 5 — Compliance engine → **M1 gate**

check_runs/resolved_rules/check_results; applicability + precedence resolvers; code-registry calculators; decision traces; matrix UI; issue cards + evidence drawer.
**M1 vertical slice (demo gate):** one council, one address, one source set, one drawing, five Tier-1 checks — perfect end-to-end with citations and traces. Then: legacy apps/packages/api deleted; `/v1` route removed; the golden fixture becomes the permanent canary.
Exit: pass/fail impossible without rule+measurement+citation+trace; conflicts → human review; assumptions labelled; M1 demo runs clean.

### Phase 6 — Hermes autonomy

hermes container (in-repo runtime, not external HERMES_BASE_URL); agent_memory; skills (extract_rules, classify_clauses, analyse_rfi, draft_response); agent console; eval-gated activation.
Exit: Hermes creates candidates/drafts only; cannot approve or emit verdicts; every output fully attributed.

### Phase 7 — RFI, exports, signoffs

RFI parser; drafts; export builders with manifest (source/rule/address coverage, decision traces, citations, assumptions + limitations section); signoff gate.
Exit: export blocked without signoff; drafts editable and traceable.

### Phase 8 — Self-learning + scale

Human dispositions → labelled examples; improve_skill job; skill diff UI; golden evals gate activation; weekly canaries on the golden fixture; source refresh/diff → review items; ops dashboard (freshness, failures, spend, backups, eval trend).
Exit: no skill self-activates; rollback works; canaries protect the demo; drift surfaces as review items.

---

## 10. First 5 PRs

**PR 1 — Audit refresh + plan lock.** Refresh REPO_AUDIT.md; add DATA_INVENTORY.md (corpus file census, `.storage` blobs, SQLite table row counts, harvestable label counts) + VERCEL_AUDIT.md; update AGENTS.md to point at this doc; banner superseded docs (Appendix C). Accept: every current code path mapped; no deletions yet.

**PR 2 — New skeleton.** `src/draftcheck` package; `web/` Vite+React skeleton; uv lock; ruff/mypy/import-linter; FastAPI shell with `/api/v1/health` + `/api/v1/ready`; **CI workflows (first in repo)**. Accept: `uv sync` works; pytest green in CI; api boots; `web/dist` builds.

**PR 3 — VPS compose + Caddy + safety rails.** infra/compose.yml; Caddyfile (incl. transition routing §6.3); db image PostGIS+pgvector; deploy.sh; backups (§3.3); hardening + uptime (§3.4). Accept: `docker compose up --wait` green; `/api/v1/ready` via Caddy; postgis+vector present; first restore drill documented.

**PR 4 — Auth + schema base.** orgs/users/sessions + roles; magic-link skeleton + EmailSender + cli login-link; CSRF/Origin checks; CORS locked; Alembic base; org_id convention. Accept: no dev-login path exists in production (the dev-only login added 2026-06-08 returns 404 when `app_env=production`); mutating routes require auth; alembic upgrade+downgrade in CI.

**PR 5 — Source foundation + label harvest.** Source tables + artifacts; corpus import from `data/corpus` + `.storage`; licence/review gate; **harvest legacy SQLite** (approved rule_rows, clause_dispositions, golden_eval_cases → JSONL eval seeds) then archive `draftcheck.db` out of the tree. Accept: corpus imported content-addressed; every source has hash + licence/review status; restricted sources can't support answers; ≥1 eval seed file committed.

---

## 11. Ground truth — repo audit snapshot (2026-06-07)

```text
Packages   10 roots (apps/api, apps/worker, packages/{core,ingestion,retrieval,compliance,
           document_ai,export,scraper,shared_schemas})
API        router mounted at /v1 AND /api (main.py:147-148); 50+ routes; dev-login + API keys
Models     57 tables in packages/core/draftcheck_core/models.py
Schema     Alembic (7 migrations, infra/alembic) AND create_all via init_database()  ← conflict
Vercel     ACTIVE: vercel.json, api/index.py, root index.py, .vercel/, .vercelignore;
           seeds /tmp from draftcheck.db (127 MB, tracked in git)
Supabase   dormant (empty dir, no code refs)
Redis/RQ   active, feature-gated (RQ_ENABLED); 5 queues; compose services in 3 files
MinIO/S3   active in all compose files; boto3 dep; .storage/ local adapter
Frontend   ui/ static HTML (6 files), hardcodes https://api.cuz.fail/v1; landing/, mockups/;
           no package.json anywhere → SPA is a fresh build
Hermes     HermesAdapter → external HERMES_BASE_URL, feature-gated
Parsers    pypdf, python-docx, openpyxl, BeautifulSoup, handwritten DXF; no docling/
           unstructured/ezdxf/ifcopenshell
Compliance calculators for setbacks/site cover/garage ratio/boundary wall (Tier 1 set);
           25 seeded DEFAULT_CHECKS can emit pass/fail without resolved rules  ← must die
Search     pgvector dep + embeddings provider abstraction (mock/openai) partially wired
Corpus     data/corpus: 1,422 files (council batches + discovery runs)
Tests      ~35 files / ~184 test functions; NO CI (.github/workflows absent)
Docs       18+ planning docs; REPO_AUDIT.md exists (2026-06-06)
```

---

## 12. Invariants (re-issued lock rules)

```text
One repo. One VPS. One /api/v1 mount. One Postgres. One Postgres-backed queue.
One content-addressed storage tree. One governed Hermes runtime.
One deterministic compliance engine. One address-first frontend.

Never claim final legal/planning/building/certification compliance.
Every regulatory claim cites approved source versions or is refused.
LLMs extract, classify, embed, draft — never decide compliance verdicts.
No LLM call without trace + skill version + spend cap.
No likely_pass/likely_fail without approved rule + promoted measurement + citation + trace.
No raster/PDF-derived measurement without explicit calibration.
Approved rules never silently change; changed sources create new versions.
Nothing authoritative is deleted; supersession and overrides are recorded.
No paid Standards Australia full text stored — metadata-only unless lawfully supplied.
No export without human signoff.
Every numeric in this plan's examples is illustrative; hardcoding one is a defect.
Alembic is the only schema authority; create_all never ships.
Table count never overrides provenance, auditability, or query correctness.
```

---

## Appendix A — Legacy → greenfield table map (57 → ~42)

| Legacy | Greenfield | Note |
|---|---|---|
| organisations | orgs | rename |
| users | users | + role |
| — | sessions | new (cookie sessions) |
| projects | projects | + lodgement_date, as_of_date, assessment_basis |
| properties | properties | facts move to property_facts |
| project_proposals | proposals | rename |
| address_profiles, address_facts, local_government_facts | property_facts | row-per-fact |
| local_governments, local_government_boundaries | lg_areas | merged |
| planning_overlays, planning_layer_features | planning_features | layer_type |
| parcels / address_points / spatial_datasets | same | spatial_datasets + licence fields |
| project_documents | documents | + revision chain |
| document_pages, document_chunks | same | — |
| extracted_document_facts, extracted_measurements, document_assets | document_facts (+ artifacts) | promotion contract |
| source_documents, source_citations | same | — |
| source_versions, source_supersessions | source_versions | + superseded_by; edges for graph |
| source_artifacts | artifacts | generic subject_type/kind |
| source_licence_reviews | source_reviews | rename |
| source_chunks, source_chunk_embeddings | source_chunks | embedding inline, model recorded |
| source_fetch_logs, source_update_events | source_fetch_log | drift → review_items |
| source_references, clause_references | legal_edges | generic graph |
| clauses, clause_dispositions | clauses | disposition column |
| rule_extraction_candidates | rule_candidates | rename |
| rule_rows | rules | + rule_type, pathway |
| rule_to_clauses | rule_clause_links | rename |
| rule_overrides, rule_carveouts | rules(rule_type=exception) + legal_edges | unified |
| check_definitions | code registry (§5.7) | not a table |
| check_runs, resolved_rules | same | — |
| check_results, decision_traces | check_results | trace inline JSONB |
| assumptions | resolved_rules.assumptions_json | folded |
| tasks, review_queue_items | review_items | merged |
| rfi_items, response_drafts, exports | same | — |
| human_signoffs | signoffs | rename |
| golden_eval_cases, golden_eval_runs | eval_cases, eval_runs | rename; seeded by harvest |
| audit_events, job_traces | same | job_traces from day one |
| background_jobs | Procrastinate tables | queue owns its schema |
| — | agent_memory, skill_versions | new |

## Appendix B — Spatial dataset register (verified 2026-06-07)

| Dataset | Publisher / access | Licence note | Cadence |
|---|---|---|---|
| G-NAF (address points) | Geoscape via data.gov.au | EULA based on CC BY 4.0; mail-use restriction; GDA2020 builds available | Quarterly |
| Cadastre (parcels), LGATE-218 | Landgate via SLIP / data.wa.gov.au | Public tier = simplified subset under **personal-use terms** — confirm commercial licence with Landgate before launch (**risk register**) | Ongoing |
| Local Planning Scheme Zones and Reserves, DPLH-071 | DPLH via data.wa.gov.au (WFS) | Open access; verify attribution terms at import | Ongoing |
| Bushfire-prone area mapping (SPP 3.7) | Via SLIP / data.wa.gov.au | Confirm current dataset ID at import (older buffers retired) | Periodic |
| LGA boundaries | Landgate admin boundaries via SLIP | Verify at import | Periodic |
| Heritage (state register + local surveys) | inHerit / councils | Register per-dataset with licence check | Periodic |

Every import records dataset id, licence, source CRS, version, fetched_at in `spatial_datasets`; all geometry transformed to GDA2020 (EPSG:7844).

## Appendix C — Document supersession

Authority now: **this file** + refreshed `REPO_AUDIT.md`. Superseded for implementation (banner each): `docs/REBUILD_SPEC.md`, `docs/MASTER_IMPLEMENTATION_PLAN.md`, `MASTER_PLAN_ADDENDUM.md`, `docs/PLAN_LOCK_NOTICE.md`. Background only (unchanged status): GAP_ANALYSIS, SPATIAL_ENGINE_DESIGN, ARCHITECTURE*, API_CONTRACT, RULES_EXTRACTION_PIPELINE, SOURCE_GOVERNANCE, DATA_SOURCES, HERMES_SCRAPE_JOB, LEGAL_AND_LICENSING_NOTES, FRONTEND_*. Carried forward from the addendum and still binding: `resolution_status` payload shape, rule/candidate lifecycle values, clause disposition values, row-per-fact provenance, `as_of_date` on every run, decision-trace completeness fields.

External references: Caddy automatic HTTPS docs · Procrastinate docs · pgvector README · uv docs · ezdxf · IfcOpenShell · Docling · Unstructured · data.gov.au G-NAF dataset + EULA · data.wa.gov.au LGATE-218, DPLH-071, SLIP.
