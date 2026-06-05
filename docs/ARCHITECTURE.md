# Architecture

DraftCheck WA Core uses a Python/FastAPI monorepo layout:

- `apps/api`: FastAPI app and route wiring.
- `apps/worker`: worker entrypoint placeholder for RQ/Celery integration.
- `packages/core`: SQLAlchemy models, database setup, project service, audit, Hermes adapter.
- `packages/core/object_storage.py`: S3/MinIO-shaped local object storage adapter.
- `packages/core/providers.py`: LLM/embedding/rerank provider protocol with a mock provider for tests.
- `infra/alembic`: Alembic migration environment for PostgreSQL/SQLite deployments.
- `packages/ingestion`: source manifest/Hermes corpus import, source versioning, clause extraction, chunking, citations.
- `packages/retrieval`: approved-source keyword retrieval and unsupported-answer refusal.
- `packages/compliance`: deterministic calculators and compliance matrix generation.
- `packages/document_ai`: document upload analysis and RFI parsing/response drafting.
- `packages/export`: JSON, CSV, DOCX, XLSX, and HTML export artifacts.
- `packages/scraper`: lawful public-source URL guardrails.
- `packages/shared_schemas`: Pydantic API schemas.

## Data Flow

1. Source manifests, Hermes corpus imports, or source seed payloads create `source_documents`.
2. Each new source body creates a `source_version` keyed by content SHA-256.
3. Older current versions are marked superseded only after the new version is stored.
4. Clause extraction creates `clauses`, `source_chunks`, and `source_citations`.
5. Retrieval searches only active, non-superseded source versions.
6. Project document uploads store raw bytes through the object-storage adapter, extract text/pages, persist `document_pages` and `document_chunks`, and extract structured facts into `extracted_document_facts`.
7. Compliance checks combine manual/extracted measurements with source citations.
8. RFI parsing creates `rfi_items` and tasks, then response drafting creates `response_drafts`.
9. Exports compile response packs and persist `exports`.
10. Every workflow creates `audit_events`; Hermes delegation creates `background_jobs` and `job_traces`.

Hermes corpus output is imported from `source_inventory.jsonl` through `POST /v1/sources/hermes-corpus/import` or `scripts/import_hermes_corpus.py`. Public/open rows with parsed PDF/text content become versioned, chunked, citable source text. Blocked, paid, login-gated, captcha-gated, robots-denied, unknown-access, restricted-licence, or otherwise non-public rows are skipped. Standards Australia rows remain metadata-only, with public metadata and access/licence notes stored but no paid Australian Standards full text and no retrieval chunks.

## Compliance Coverage

The default check pack covers front/side/rear setbacks, site cover, open space, deep soil/tree planting, garage dominance, street surveillance, outdoor living area, solar access, privacy, overshadowing, vehicle access, bin storage, ancillary dwelling triggers, retaining/fill, BAL/bushfire, heritage/planning overlays, boundary walls, and drawing QA completeness for title block, revision, north point, scale, and dimensions.

Checks remain conservative: missing measurements return `missing_info`; trigger flags return `needs_human_review`; source gaps are listed as missing information and prevent uncited likely pass/fail claims.

## Document Intelligence

Uploaded PDFs, DOCX, HTML, text files, and DXF files are converted into document pages and chunks for project-local search. DOCX paragraph and table text is indexed. The analyzer extracts common drafting facts such as sheet references, scales, revisions, north/title/dimension markers, levels, areas, setbacks, garage/frontage widths, outdoor living dimensions, retaining/fill heights, generic numeric values, and PDF-style values with comma separators or square-metre glyphs. Measurement-like facts are also inserted into `extracted_measurements` with document/page/fact evidence refs so compliance checks can use them without inventing values.

CAD/DXF extraction is intentionally conservative: it summarizes entity types, declared units, layers, drawing text, coordinate ranges, line lengths, polyline lengths, and DIMENSION entity measurements for search and evidence. Lengths are unit-labeled only when DXF declared units are present; otherwise they stay as drawing units. Ambiguous geometry remains missing information or human-review evidence, and proprietary DWG geometry extraction is not claimed.

## Deployment Shape

Local tests use SQLite. `docker-compose.yml` includes PostgreSQL, Redis, MinIO, API, and worker services for the intended deployment shape. Production should run Alembic migrations against PostgreSQL and wire Redis/RQ or Celery for background work.
