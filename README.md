# DraftCheck WA Core

Backend core for a WA residential drafting assistant. It manages projects, source ingestion, citation-backed retrieval, deterministic compliance checks, RFI parsing, draft response packs, Hermes job delegation, exports, signoffs, and audit events.

This repo intentionally contains no frontend.

## Local Setup

Use Python 3.12.

```bash
python -m pip install -e ".[dev]"
python -m uvicorn draftcheck_api.main:app --reload --host 127.0.0.1 --port 8000
python -m pytest
```

In this Codex workspace the bundled runtime was used:

```powershell
& 'C:\Users\steve\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest
```

OpenAPI is available at `/openapi.json` and Swagger UI at `/docs`.

## Environment

Copy `.env.example` to `.env` for local overrides.

Key variables:

- `DATABASE_URL`: defaults to SQLite for local dev.
- `OBJECT_STORAGE_ROOT`: local export/object output folder.
- `HERMES_ENABLED`: defaults to `false`.
- `HERMES_BASE_URL`, `HERMES_API_KEY`: required only when delegating to Hermes.
- `HERMES_MAX_CONCURRENCY`, `HERMES_DEFAULT_MODEL`, `HERMES_REVIEW_MODEL`: Hermes scheduling/model hints.

## Safety Boundaries

DraftCheck WA Core is assistive only. It must not claim final compliance, approval, certification, legal advice, or building-surveyor signoff.

Every regulatory answer must either cite approved source versions and chunks or say the approved source library cannot support the answer. Australian Standards full text must not be scraped or stored; store public metadata and access notes only.

Hermes `source_inventory.jsonl` output can be imported through `POST /v1/sources/hermes-corpus/import` or `python scripts/import_hermes_corpus.py --inventory path/to/source_inventory.jsonl`. Public/open parsed PDF/text content becomes versioned, chunked, citable source text. Blocked, paid, login-gated, captcha-gated, robots-denied, unknown-access, restricted-licence, or otherwise non-public rows are skipped, and Standards Australia content remains metadata-only and non-citable.

## Useful Commands

```bash
make setup
make dev
make test
make seed
make worker
```

## First Shippable Workflow

1. Create a project.
2. Import a lawful source manifest or Hermes corpus inventory.
3. Upload/paste a council RFI or upload a PDF/text/DOCX/HTML/DXF document through `/v1/projects/{project_id}/documents/upload`.
4. Parse RFI items.
5. Generate a draft response.
6. Run checklist/compliance matrix.
7. Export JSON/DOCX/XLSX/HTML/CSV response pack.
8. Require human review/signoff before submission.

The default compliance matrix is broad but conservative. It creates findings for planning, building-trigger, and drawing-QA checks, but returns `missing_info` or `needs_human_review` unless enough measurements and source support exist.

Uploaded project files are split into pages and chunks for search, then scanned for structured drafting facts and extracted measurements. PDFs, DOCX, HTML, text files, and DXF files can support project-local search through `/v1/projects/{project_id}/document-search?q=...`; use `/v1/projects/{project_id}/documents/{document_id}/facts` for page-specific evidence instead of raw blobs. CAD/DXF geometry is handled conservatively and ambiguous measurements remain missing information or human-review evidence.

# cuz.fail
