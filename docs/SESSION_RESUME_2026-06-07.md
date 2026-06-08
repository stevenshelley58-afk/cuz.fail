# DraftCheck WA V3 Restart Checkpoint

Date: 2026-06-07
Workspace: `C:\Dev\Cuz`

## Current State

No files are staged or committed. Subagents used in this pass have completed and the active explorer
was closed.

The workspace now includes PR0/PR1 hygiene and authority docs, PR2 API/web/CI shell, PR3 infra
skeleton, PR4 auth/base schema, Wave 3 source/substrate and address/spatial slices, V3 schema
metadata, golden fixtures, and a V3 Alembic scaffold.

Root `alembic.ini` is now V3-only and points at `src/draftcheck/db/alembic`. The legacy transition
runtime now uses `alembic-legacy.ini`, which still points at `infra/alembic`.

## Latest Fixes

- Source versions are no longer superseded by a pending replacement; supersession happens when a
  replacement version is approved.
- Content-identical source artifacts keep per-version provenance while sharing the same content hash
  storage path.
- Standards Australia detection now covers common code-title forms such as `AS 3959:2018 ...`.
- Source import rejects blank/whitespace titles and caller-controlled review/lawful fields.
- Public magic-link requests require a pre-provisioned `owner` or `reviewer`; unknown users do not
  receive login tokens.
- The V3 role set remains locked to `owner` and `reviewer`; DB role defaults were removed so future
  persisted identity paths must assign roles explicitly.
- Unsafe source and address mutations require an allowed `Origin`.
- Source search POST endpoints require an authenticated session and allowed `Origin` before retrieval
  or model tracing.
- Source review records org scope in the in-memory value object and API path.
- Manual address overrides require reviewer authority.
- The V3 FastAPI app installs CORS middleware for configured frontend origins.
- Supported `/search/ask` responses require a recorded governed model trace, not just a nonblank ID.
- Address/property profiles are scoped by `(org_id, project_id)`.
- Rejected spatial dataset metadata cannot overwrite an already accepted authoritative dataset.
- V3 metadata now includes `projects`, `properties`, `proposals`, and `lg_areas`.
- `create_app()` gets a fresh source router/library per app instance.
- Root Alembic now has an explicit V3 foundation migration; legacy Alembic remains frozen separately.

## Verified Gates

These passed after the latest changes:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\lint-imports.exe --config pyproject.toml
npm.cmd run build
git diff --check
rg -n "create_all|dev-login|likely_pass|likely_fail" src/draftcheck src/draftcheck/db/alembic web
```

Results: ruff pass, mypy pass, pytest `342 passed` with one existing Starlette/TestClient warning,
import-linter contract kept, web build pass, diff check pass, V3 Alembic offline SQL generation pass,
narrowed forbidden-pattern grep clean.

## Open Risks / Next Work

- A real PostgreSQL 16 database with PostGIS and pgvector has not run `alembic upgrade head` and
  `alembic downgrade base`; current migration coverage uses offline PostgreSQL SQL generation.
- `draftcheck.db` still needs the host-side integrity/recovery/archive step before any harvest.
- Full source-control staging has not happened; many files are still untracked by design at this
  checkpoint.
- Legacy code still contains transition-only `create_all`, `/v1`, and `dev-login` references; V3
  code/web grep is clean.

## Resume Commands

```powershell
git status --short --ignored
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\lint-imports.exe --config pyproject.toml
npm.cmd run build
```

Next implementation target: run/prove V3 Alembic against a real Postgres/PostGIS/pgvector service,
then continue PR6 legal skills/evals or PR8 documents depending on the coordinator wave.
