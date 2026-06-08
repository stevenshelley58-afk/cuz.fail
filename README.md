# DraftCheck WA Core

Backend core and V3 rebuild workspace for a WA residential drafting assistant. It manages projects,
source ingestion, citation-backed retrieval, deterministic compliance checks, RFI parsing, draft
response packs, Hermes job delegation, exports, signoffs, audit events, and the new address-first
frontend under `web/`.

## Plan Lock

Implementation work must follow `docs/MASTER_REBUILD_PLAN.md` together with refreshed
`REPO_AUDIT.md`, `DATA_INVENTORY.md`, and `VERCEL_AUDIT.md`. Older planning docs are background
context only when they conflict with the V3 rebuild plan.

## Local Setup

Use Python 3.12.

```bash
python -m pip install -e ".[dev]"
python scripts/bootstrap_source_library.py
python scripts/audit_source_library.py
python scripts/extract_source_rules.py --source-title-contains "Residential Design Codes" --limit 1
python scripts/rule_review_worklist.py --source-title-contains "Residential Design Codes" --limit 1
python scripts/promote_rule_candidate.py --candidate-id <candidate-id> --reconcile-source --commit
python scripts/reconcile_source_review_queue.py --source-version-id <source-version-id>
python -m uvicorn draftcheck_api.main:app --reload --host 127.0.0.1 --port 8000
python -m pytest
```

In this Codex workspace the bundled runtime was used:

```powershell
& 'C:\Users\steve\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest
```

The legacy FastAPI app still exposes OpenAPI at `/openapi.json` and Swagger UI at `/docs`.
For the V3 rebuild, the new app will expose only `/api/v1/*`; legacy `/v1` and `/api` routes are
transition surfaces until M1.

## Production Deploy

The live VPS target is `srv1625369` at `76.13.209.160`, reachable from the operator machine as
`ssh draftcheck`. PowerShell/Codex is the local shell; commands that mutate production must run
through `ssh draftcheck '...'` or inside an interactive `ssh draftcheck` session.

`https://app.cuz.fail/` is served by Caddy from `/srv/draftcheck/app/web/dist`. For a UI-only
deploy, sync `/srv/draftcheck/app` to `origin/main` and rebuild `web/dist`; no Vercel action and
no container restart are needed. See `docs/PRODUCTION_DEPLOYMENT.md` for the exact command and
verification checklist.

## Environment

Copy `.env.example` to `.env` for local overrides.

Key variables:

- `DATABASE_URL`: defaults to SQLite for local dev.
- `OBJECT_STORAGE_ROOT`: local export/object output folder.
- `HERMES_ENABLED`: defaults to `false`.
- `HERMES_BASE_URL`, `HERMES_API_KEY`: required only when delegating to Hermes.
- `HERMES_MAX_CONCURRENCY`, `HERMES_DEFAULT_MODEL`, `HERMES_REVIEW_MODEL`: Hermes scheduling/model hints.
- `RQ_ENABLED`, `RQ_REDIS_URL`, `RQ_QUEUES`: legacy transition queue settings only. V3 target queue
  is Procrastinate on PostgreSQL.
- `BOOTSTRAP_DEMO_SOURCE_LIBRARY`: when `true`, startup ensures a small approved WA R-Codes
  bootstrap excerpt is present. For local setup without that env var, run
  `python scripts/bootstrap_source_library.py` once before judging chat quality.

## Safety Boundaries

DraftCheck WA Core is assistive only. It must not claim final compliance, approval, certification, legal advice, or building-surveyor signoff.

Every regulatory answer must either cite approved source versions and chunks or say the approved source library cannot support the answer. Australian Standards full text must not be scraped or stored; store public metadata and access notes only.

Hermes `source_inventory.jsonl` output can be imported through the legacy import script
`python scripts/import_hermes_corpus.py --inventory path/to/source_inventory.jsonl` during harvest.
The V3 source path is `/api/v1` only and must use the governed, traced, spend-capped adapter before
any LLM-backed source/search behavior ships. Blocked, paid, login-gated, captcha-gated,
robots-denied, unknown-access, restricted-licence, or otherwise non-public rows are skipped, and
Standards Australia content remains metadata-only and non-citable.

## Useful Commands

```bash
make setup
make dev
make test
make bootstrap-sources
make audit-sources
make extract-rules
make rule-worklist
make reconcile-source-reviews
make seed
make worker
```

## Legacy Local Workflow

The existing `apps/` and `packages/` implementation is frozen transition code. Use it for harvest,
compatibility checks, and baseline tests only. Do not expand it as the V3 product surface.

## V3 First Shippable Workflow

1. Resolve an address through `/api/v1` to parcel, council, zone, overlays, and property facts with provenance.
2. Confirm proposal facts separately from address facts.
3. Match approved source versions and cite-or-refuse source search answers.
4. Upload drawings, review extracted facts, and promote only confirmed measurements.
5. Run Tier 1 deterministic checks against approved rules and promoted measurements.
6. Show issue cards with citations, drawing evidence, and decision traces.
7. Block exports until human signoff.

# cuz.fail
