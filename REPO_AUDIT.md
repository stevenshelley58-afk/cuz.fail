# 2026-06-07 V3 Refresh

Authority: `docs/MASTER_REBUILD_PLAN.md` is now the active implementation source. This refresh
records the PR0/PR1 ground truth for the V3 multi-agent build. Older audit detail below remains useful
background where it does not conflict with this section or the V3 rebuild plan.

## Current Source-Control State

```text
git ls-files                         1 tracked file (`README.md`) before PR0 materialisation
git status                           most source/config/docs are untracked local workspace files
.gitignore                           updated before staging to exclude runtime/private artifacts
```

Do not stage `draftcheck.db`, `.storage/`, `.venv/`, `.vercel/`, `build/`, caches, backups, or
`data/corpus/`.

## PR0 Safety Gates Added

```text
scripts/precommit_guard.py           rejects forbidden paths, files >5 MB, and obvious secrets
scripts/check_sqlite_integrity.py    read-only SQLite integrity and harvest-count checker
DATA_INVENTORY.md                    data/corpus, .storage, SQLite count baseline
```

Local verification:

```text
draftcheck.db PRAGMA integrity_check  ok
data/corpus                          1,422 files / 1,867,624,576 bytes
.storage                             2,233 files / 18,175,942 bytes
```

## V3 Conflict Resolution

The previous backend-only rule is superseded. V3 builds a first-class frontend under `web/`, exposes
new-app traffic only under `/api/v1`, moves target code into `src/draftcheck/`, uses PostgreSQL with
PostGIS and pgvector, Procrastinate, local content-addressed storage, and a governed Hermes runtime.

Legacy `apps/`, `packages/`, `api/`, `ui/`, `landing/`, and `mockups/` have been removed from the
tree; V3 code lives in `src/draftcheck/` with the frontend under `web/` (recoverable from git history).

## Verification Baseline To Re-run In CI

The PR0 implementation intentionally avoids fixing frozen legacy type errors. CI must record current
baseline numbers and then enforce zero `mypy` errors only for new V3 code under `src/draftcheck/` and
`web/`.

Observed after PR0 hygiene edits:

```text
ruff check .                         pass
pytest -q                            286 passed, 1 Starlette/httpx warning
mypy V3 src + V3 tests               pass
lint-imports --config pyproject.toml pass
web build                            pass
mypy apps packages                   19 legacy errors in 8 files
precommit_guard safe-doc/config set  pass
precommit_guard dangerous fixtures   blocks draftcheck.db, data/corpus, .storage, .vercel, >5 MB files
```

# DraftCheck WA Core Repo Audit

Date: 2026-06-06

Purpose: repo-truth audit before implementing the master plan corrections. This file maps the current
codebase as it exists today and identifies the schema, endpoint, migration, and sequencing risks that
must be resolved before agents start coding from the master plan.

## Executive Summary

- The repository is a Python/FastAPI backend monorepo with packages for core models, ingestion,
  retrieval, compliance, document parsing, export, scraping, shared schemas, API, and a worker
  placeholder.
- The active persistence model is SQLAlchemy over SQLite by default. Docker development compose uses
  plain `postgres:16`, not PostGIS, and no DB image currently proves pgvector support.
- The core evidence tables exist: `SourceDocument`, `SourceVersion`, `Clause`, `SourceChunk`,
  `SourceCitation`, `CheckDefinition`, `CheckResult`, `AuditEvent`, `BackgroundJob`, `JobTrace`, and
  `ExportValidation`.
- The spatial/legal spine in the master plan is not implemented yet. Missing tables include
  `SourceArtifact`, `SourceLicenceReview`, `ClauseReference`, `RuleExtractionCandidate`, `RuleRow`,
  `SpatialDataset`, `Parcel`, `AddressPoint`, `PlanningLayerFeature`, `AddressProfile`,
  row-per-fact `AddressFact`, `ProjectProposal`, `ResolvedRule`, and `DecisionTrace`.
- Current compliance can emit `likely_pass` or `likely_fail` from seed `DEFAULT_CHECKS` and
  measurements without the future `ResolvedRule` and `DecisionTrace` preconditions. Treat this as a
  known transitional risk.
- Current tests are green: `23 passed` across 8 test files, with one Starlette/httpx deprecation
  warning.

## 1. Current Repository Shape

Primary backend paths:

```text
apps/api/draftcheck_api/          FastAPI app and router
apps/worker/draftcheck_worker/    worker entrypoint placeholder
packages/core/draftcheck_core/    SQLAlchemy models, DB config, audit, object storage, Hermes jobs
packages/ingestion/               source manifest and Hermes corpus ingestion
packages/retrieval/               source-library retrieval and cited answer service
packages/compliance/              deterministic seed compliance checks
packages/document_ai/             document parsing, fact extraction, RFI services
packages/export/                  export generation
packages/scraper/                 lawful fetch and source discovery helpers
packages/shared_schemas/          Pydantic request/response schemas
infra/alembic/                    Alembic env and initial metadata migration
tests/                            API/service tests
```

Non-backend folders exist (`ui/`, `landing/`), but the active repo rules say this repository must
remain backend-only. Do not add or modify frontend/browser UI as part of the master plan work.

## 2. Current Instructions

Active instruction file: `AGENTS.md`.

Current constraints:

- Build backend, ingestion, retrieval, compliance, RFI, export, job, audit, and documentation layers
  only.
- Do not create a frontend app or browser UI.
- Do not claim final legal, planning, building, or certification compliance.
- Regulatory outputs must cite approved source versions or explicitly state that the approved source
  library cannot support the answer.
- Do not scrape or store paid Australian Standards full text.
- Respect robots.txt, rate limits, paywalls, login gates, captchas, copyright, and licence
  restrictions.
- Prefer deterministic calculations for measurements.
- Automated validation gate is required before any export is treated as submission-ready.

## 3. Current SQLAlchemy Models

All requested current models are present.

```text
SourceDocument -> source_documents
  id, title, jurisdiction, authority, local_government, source_type, canonical_url,
  licence_notes, access_type, scrape_allowed, is_active, created_at, updated_at

SourceVersion -> source_versions
  id, source_document_id, version_label, effective_date, published_date, retrieved_at,
  content_sha256, raw_object_key, parsed_object_key, superseded_by_id, is_superseded,
  parse_status, raw_text, created_at, updated_at

Clause -> clauses
  id, source_version_id, clause_id, heading, parent_clause_id, page_number, text,
  normalized_text, start_anchor, end_anchor, text_sha256, created_at, updated_at

SourceChunk -> source_chunks
  id, source_version_id, clause_id, heading, page_number, text, embedding_ref,
  token_count, created_at, updated_at

SourceCitation -> source_citations
  id, source_chunk_id, source_version_id, clause_id, citation_json, created_at, updated_at

Property -> properties
  id, project_id, address, zoning, lot_area_m2, overlays_json, planning_scheme,
  created_at, updated_at

PlanningOverlay -> planning_overlays
  id, project_id, overlay_type, label, source_url, detected_by, created_at, updated_at

ProjectDocument -> project_documents
  id, project_id, document_type, title, filename, content_type, raw_object_key,
  text_content, content_sha256, parse_status, analysis_status, metadata_json,
  created_at, updated_at

CheckResult -> check_results
  id, check_run_id, project_id, check_key, label, category, status, requirement,
  proposed, evidence_refs_json, citations_json, assumptions_json,
  missing_information_json, confidence, requires_human_review, created_by_model,
  prompt_version, created_at, updated_at

AuditEvent -> audit_events
  id, actor_id, project_id, action, target_type, target_id, metadata_json,
  created_at, updated_at

BackgroundJob -> background_jobs
  id, job_type, status, correlation_id, project_id, source_version_id, provider,
  model, payload_json, remote_job_id, error, created_at, updated_at

JobTrace -> job_traces
  id, job_id, correlation_id, project_id, source_version_id, prompt, model,
  provider, input_tokens, output_tokens, cost, status, started_at, finished_at,
  error, artifacts_json, created_at, updated_at

ExportValidation -> export_validations
  id, project_id, target_type, target_id, status, validated_by, notes, created_at, updated_at
```

Additional current models:

```text
User, Organisation, Project, LocalGovernment, DocumentPage, DocumentChunk,
ExtractedDocumentFact, DocumentAsset, SourceFetchLog, SourceUpdateEvent,
CheckDefinition, CheckRun, ExtractedMeasurement, Assumption, RfiItem, Task,
ResponseDraft, Export
```

## 4. Current Endpoint Routes

The API mounts the same router under both `/v1` and `/api`. The canonical surface should be `/v1`.

Project and property:

```text
POST   /v1/projects
GET    /v1/projects
GET    /v1/projects/{project_id}
PATCH  /v1/projects/{project_id}
DELETE /v1/projects/{project_id}
PUT    /v1/projects/{project_id}/property
GET    /v1/projects/{project_id}/property
```

Document upload and project-document parsing:

```text
POST /v1/projects/{project_id}/documents
POST /v1/projects/{project_id}/documents/upload
GET  /v1/projects/{project_id}/documents
GET  /v1/projects/{project_id}/documents/{document_id}
POST /v1/projects/{project_id}/documents/{document_id}/analyze
GET  /v1/projects/{project_id}/documents/{document_id}/pages
GET  /v1/projects/{project_id}/documents/{document_id}/facts
GET  /v1/projects/{project_id}/document-search
```

Source ingestion/import:

```text
POST /v1/sources/manifest/import
POST /v1/sources/hermes-corpus/import
POST /v1/sources/seed
POST /v1/sources/ingest
GET  /v1/sources
GET  /v1/sources/fetch-logs
GET  /v1/sources/{source_id}
GET  /v1/sources/{source_id}/versions
POST /v1/sources/{source_id}/refresh
```

Retrieval and ask/chat:

```text
GET  /v1/source-chunks/search
POST /v1/ask-source-library
POST /v1/projects/{project_id}/ask-source
```

Compliance:

```text
POST /v1/checks/definitions/import
POST /v1/projects/{project_id}/checks/run
POST /v1/projects/{project_id}/compliance/run
GET  /v1/projects/{project_id}/checks
GET  /v1/projects/{project_id}/compliance
PATCH /v1/projects/{project_id}/checks/{check_result_id}
GET  /v1/projects/{project_id}/compliance-matrix
POST /v1/projects/{project_id}/measurements
GET  /v1/projects/{project_id}/measurements
```

RFI, responses, exports, validation gate, jobs, audit:

```text
POST /v1/projects/{project_id}/rfi/parse
POST /v1/projects/{project_id}/rfi/analyse
GET  /v1/projects/{project_id}/rfi/items
GET  /v1/projects/{project_id}/rfi
PATCH /v1/projects/{project_id}/rfi/items/{rfi_item_id}
POST /v1/projects/{project_id}/rfi/draft-response
POST /v1/projects/{project_id}/responses/generate
GET  /v1/projects/{project_id}/responses
POST /v1/projects/{project_id}/exports
POST /v1/projects/{project_id}/exports/response-pack
GET  /v1/projects/{project_id}/exports
GET  /v1/projects/{project_id}/exports/{export_id}
GET  /v1/projects/{project_id}/exports/{export_id}/download
POST /v1/projects/{project_id}/validations
GET  /v1/projects/{project_id}/validations
GET  /v1/jobs/{job_id}
POST /v1/jobs/{job_id}/retry
POST /v1/jobs/{job_id}/cancel
GET  /v1/jobs/{job_id}/traces
GET  /v1/audit
```

Endpoint drift against the requested final surface:

```text
Missing:
  POST /v1/address/resolve
  POST /v1/projects/{id}/property/resolve
  GET  /v1/projects/{id}/property/profile
  POST /v1/projects/{id}/resolved-rules
  GET  /v1/projects/{id}/compliance/matrix

Current aliases/drift:
  GET /v1/projects/{id}/compliance-matrix should become /v1/projects/{id}/compliance/matrix.
  POST /v1/projects/{id}/checks/run remains an alias for compliance/run.
  GET /v1/projects/{id}/checks and /compliance return result lists, not the requested matrix route.
  /api duplicates every /v1 route and should remain secondary compatibility surface only.
```

## 5. Tests

Current test files:

```text
tests/conftest.py
tests/test_compliance_rfi_export.py
tests/test_documents_hermes.py
tests/test_fetch_and_check_definitions.py
tests/test_hermes_corpus_import.py
tests/test_source_discovery.py
tests/test_sources_retrieval.py
tests/__init__.py
```

Command run:

```text
.venv/Scripts/python.exe -m pytest -q
```

Result:

```text
23 passed, 1 warning in 4.12s
```

Warning:

```text
StarletteDeprecationWarning from fastapi.testclient importing Starlette TestClient.
```

## 6. Worker and Queue Placeholders

Current worker path:

```text
apps/worker/draftcheck_worker/main.py
```

Current state:

- Worker is a placeholder that prints a configuration message.
- `packages/core/draftcheck_core/queue.py` has `queue_handle()` and `enqueue_local_placeholder()`.
- Queue backend is reported as `redis-rq` only when `HERMES_ENABLED=true`; otherwise it is
  `local-disabled`.
- `packages/core/draftcheck_core/hermes.py` persists `BackgroundJob` and `JobTrace` rows and can
  enqueue disabled/queued Hermes-style jobs.
- Job APIs exist under `/v1/jobs/{job_id}`, `/retry`, `/cancel`, and `/traces`.

Missing for PR 2:

- Real Redis/RQ worker loop.
- Job retry policy, per-job timeout, concurrency limits, and failure handling.
- Health/readiness endpoint that checks DB, Redis, object storage, and worker readiness.

## 7. Docker Compose and Database Config

Current local config:

```text
packages/core/draftcheck_core/config.py
  DATABASE_URL defaults to sqlite:///./draftcheck.db
  OBJECT_STORAGE_ROOT defaults to .storage
  HERMES_ENABLED defaults to false
  EMBEDDING_PROVIDER defaults to mock
```

Current root `docker-compose.yml`:

```text
postgres: image postgres:16
redis: image redis:7
minio: image minio/minio:latest
api: python:3.12-slim, pip install -e .[dev], DATABASE_URL points at postgres
worker: python:3.12-slim, placeholder worker
```

Current production/VPS compose:

```text
infra/docker/docker-compose.production.yml
  API and worker only, local object_storage volume, no DB/Redis/MinIO/Caddy.

deploy/docker-compose.vps.yml
  API only, local storage volume, no DB/Redis/MinIO/Caddy.
```

Current migrations:

```text
infra/alembic/versions/0001_initial_metadata.py
  Uses Base.metadata.create_all() and drop_all().
```

Risks:

- Plain `postgres:16` lacks PostGIS and does not prove pgvector extension availability.
- The production compose files do not yet represent the target stack.
- Alembic revision is metadata-wide, not explicit DDL. Future schema work should use explicit
  revisions for safe upgrades.
- SQLite remains acceptable for non-spatial tests only.

## 8. Property and PlanningOverlay Write Paths

Current `Property` writes:

```text
packages/core/draftcheck_core/project_service.py
  ProjectService.upsert_property()
    creates Property(project_id=..., address=...)
    writes address, zoning, lot_area_m2, overlays_json, planning_scheme
    records property.upserted audit event
```

Current `Property` routes:

```text
PUT /v1/projects/{project_id}/property
GET /v1/projects/{project_id}/property
```

Current `PlanningOverlay` writes:

```text
No active code write path found.
```

Current `PlanningOverlay` references:

```text
packages/core/draftcheck_core/models.py defines the table.
Older docs propose future spatial writes.
supabase/migrations/20260605093000_draftcheck_initial_schema.sql creates the table.
```

Migration instruction:

- Do not convert `Property` to a DB view in Phase 1.
- First add `address_profile_id` and keep current fields backward-compatible.
- Refactor readers after `AddressProfile`/`AddressFact` exists.
- Consider a DB view only after another write-path audit proves no code writes to `Property`.

## 9. DEFAULT_CHECKS and Current Compliance Calculators

Current default check source:

```text
packages/compliance/draftcheck_compliance/service.py
```

Current `DEFAULT_CHECKS` count:

```text
25
```

Categories:

```text
planning
building
drawing_qa
```

Current methods:

```text
max_percentage
min_percentage
min_value
max_value
all_min_values
garage_ratio
boundary_wall_ratio
boolean_required
trigger_flag
human_review
```

Current calculators:

```text
packages/compliance/draftcheck_compliance/calculators.py
  area_percentage()
  compare_minimum()
  compare_maximum()
  garage_width_ratio()
  boundary_wall_length_percentage()
```

Important transitional behavior:

- `ComplianceService.run_checks()` creates `CheckRun` and `CheckResult` rows.
- It retrieves citations with `RetrievalService.citation_for_check()`.
- It can set `likely_pass` or `likely_fail` when measurements satisfy/fail seed thresholds, without
  `ResolvedRule`, `DecisionTrace`, explicit assessment date, or rule precedence.
- It sets `requires_human_review=True` for all results.

## 10. Current Parsing Paths

Project document parser:

```text
packages/document_ai/draftcheck_document_ai/extraction.py
```

Current parsers:

```text
PDF:  pypdf.PdfReader page.extract_text()
DOCX: python-docx paragraphs and tables
HTML: BeautifulSoup get_text()
Text: UTF-8 decode with form-feed page split
DXF:  handwritten group-code parser that summarizes units, entities, layers, text, line/polyline
      lengths, and DIMENSION group 42 values
```

Current source parsing:

```text
packages/ingestion/draftcheck_ingestion/service.py
  SourceIngestionService._extract_clauses()
  Regex clause splitter over normalized source text.
```

Missing against master plan:

- No `packages/parsing/` shared parser interface.
- No Docling adapter.
- No Unstructured adapter.
- No OCR adapter.
- No parser consensus table (`DocumentArtifact`/`SourceArtifact`).
- No ezdxf or IfcOpenShell implementation.

Ownership risk:

- Source parsing and project-document parsing are separate code paths today.
- Future parser services should return parse outputs only. Agent B should persist source artifacts;
  Agent E should persist project document/drawing artifacts.

## 11. Current Retrieval Implementation

Current retrieval service:

```text
packages/retrieval/draftcheck_retrieval/service.py
```

Current behavior:

- Searches active, non-superseded `SourceChunk` rows joined to `SourceCitation`, `SourceVersion`, and
  `SourceDocument`.
- On SQLite, optionally uses `source_chunk_fts` with `bm25(source_chunk_fts)` if that virtual table
  exists.
- Otherwise uses `ILIKE` prefiltering and a local lexical scoring function.
- `RetrievalService.ask()` returns cited source-library summaries or `unsupported`.
- Paid/proprietary Australian Standards full-text questions are refused as `unsupported`.

Mock/unused vector state:

```text
packages/core/draftcheck_core/config.py has EMBEDDING_PROVIDER=mock.
packages/core/draftcheck_core/providers.py defines mock embed/rerank provider methods.
SourceChunk.embedding_ref exists but no vector column is present.
pgvector is a Python dependency but the database schema does not enable/store vectors.
```

## 12. Migrations Needed

First migration set should be explicit Alembic revisions, not a broad `create_all()` delta.

High-priority additions:

```text
SourceArtifact
SourceLicenceReview
SourceSupersession
SourceReference
ClauseReference
ClauseDisposition
RuleExtractionCandidate
RuleRow with lifecycle_status
RuleToClause
RuleOverride
RuleCarveout
SpatialDataset
Parcel
AddressPoint
PlanningLayerFeature
LocalGovernmentBoundary
AddressProfile
AddressFact row-per-fact
ProjectProposal
Project.as_of_date
Project.lodgement_date
Project.assessment_basis
Property.address_profile_id
ResolvedRule
DecisionTrace
DocumentArtifact
DrawingEntity
DrawingMeasurement
GoldenEvalCase
GoldenEvalRun
ReviewQueueItem
```

Infrastructure migration/config:

```text
PostGIS extension
pgvector extension
spatial indexes for geometry tables
vector column and ANN indexes only after DB image proves pgvector availability
```

## 13. Breaking-Change Risks

- `Property` is currently writable. Converting it to a view now would break `PUT
  /v1/projects/{project_id}/property` and `ProjectService.upsert_property()`.
- `ProjectCreate` currently requires `address` and `local_government`. Adding address resolution
  should be backward-compatible until project creation is refactored.
- `CheckStatus` currently excludes `unsupported` except for `StandardAnswer`. Regulatory result
  schemas must be updated carefully if `unsupported` becomes broader.
- Current compliance pass/fail semantics conflict with the stricter `ResolvedRule`/`DecisionTrace`
  precondition. Do not harden the reliability contract without updating tests and existing seed-check
  behavior.
- `/v1/projects/{id}/compliance-matrix` exists but requested final route is
  `/v1/projects/{id}/compliance/matrix`.
- Source and project parsing paths are not shared. Introducing shared parser adapters must not let a
  parser write directly to both source and project tables.
- Root `docker-compose.yml` and production compose files differ substantially. PR 2 should choose the
  target stack explicitly and test it.
- Existing docs include older endpoint/model names. Agents must use `docs/MASTER_IMPLEMENTATION_PLAN.md`
  plus `MASTER_PLAN_ADDENDUM.md` when documents disagree.

## 14. Recommended First 5 PRs

### PR 1: Repo audit and plan lock

Output:

```text
REPO_AUDIT.md
MASTER_PLAN_ADDENDUM.md
docs/PLAN_LOCK_NOTICE.md
README.md and AGENTS.md plan-lock updates
Superseded notices on older planning docs
```

Acceptance:

```text
Master plan plus addendum is the only active implementation source.
Older docs are marked superseded where they conflict.
Current models, endpoints, tests, workers, config, parsers, retrieval, and write paths are mapped.
```

### PR 2: Infrastructure foundation

Scope:

```text
PostGIS + pgvector-capable DB image
Redis/RQ worker loop
MinIO private buckets
Caddy config
health/ready endpoints
Alembic extension migration
backup/restore scripts
```

Acceptance:

```text
docker compose up brings all services healthy.
Alembic migrates cleanly from empty DB.
postgis and vector extensions are present.
MinIO buckets are private.
Restore is tested and documented.
```

### PR 3: Source artifact and licence gate

Scope:

```text
SourceArtifact
SourceLicenceReview
SourceSupersession
SourceReference
source import from existing corpus
object storage keys and hashes
source review status
```

Acceptance:

```text
Every source has official URL, jurisdiction, hash, raw/parsed artifact records, licence status,
and review status.
Restricted or metadata-only sources cannot support answers.
Changed source text creates a new SourceVersion.
```

### PR 4: Clause and rule foundation

Scope:

```text
Clause hierarchy extensions
ClauseReference
ClauseDisposition
RuleExtractionCandidate
RuleRow
RuleToClause
RuleOverride
RuleCarveout
quote-anchor validator
unit normalizer
closed vocabularies
```

> Superseded 2026-06-14 — the closed-vocab `rule_key` enum was retired; see
> `docs/OPEN_VOCAB_REBUILD_PLAN.md` (subordinate to `docs/MASTER_REBUILD_PLAN.md`).
> The former closed set `RULE_KEYS` is renamed to `RULE_KEY_HINTS` in
> `src/draftcheck/extraction/vocabulary.py` and is now a soft signal only
> (`is_hinted_key()`), not a hard gate: the extractor proposes any snake_case
> `rule_key` and `validators.validate_rule_key` accepts new keys. Garbage is caught
> by universal structural validators (quote-anchor, no-orphan-numbers,
> normative-language, operator/unit canonical, `validate_value_finite`,
> `validate_unit_category_sanity`), not by an enum. Raw keys are canonicalised
> post-hoc into the `canonical_rule_key` column (`String(160)`, nullable, indexed)
> added by migration `0018_rule_canonical_keys` on both the `rules` and
> `rule_candidates` tables (`scripts/wp6_cluster_keys.py` →
> `scripts/wp6_apply_clustering.py`).

Acceptance:

```text
RuleRow cannot be approved without quote anchor.
Invalid rule key is rejected.
Numeric units are normalized.
Normative-language audit cannot classify must/shall/required clauses as informational.
```

> Superseded 2026-06-14 — "Invalid rule key is rejected" now means only that
> `validate_rule_key` rejects strings outside `[a-z][a-z0-9_]{2,60}`; a key is no
> longer rejected merely for being outside the former closed vocabulary. Approval is
> driven by the universal structural validators above, not enum membership.

### PR 5: Spatial data skeleton and resolver contract

Scope:

```text
SpatialDataset
Parcel
AddressPoint
PlanningLayerFeature
LocalGovernmentBoundary
AddressProfile
row-per-fact AddressFact
LocalGovernmentFact or AddressFact fact_type=local_government
POST /v1/address/resolve
```

Acceptance:

```text
Exact fixture address resolves to parcel.
Ambiguous address returns needs_human_review.
Missing geometry returns missing_info.
No Google Places-derived council/zone/overlay is accepted as proof.
Every fact has dataset/source provenance.
```
