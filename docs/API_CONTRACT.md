# API Contract

The API is exposed under `/v1`. Compatibility aliases are also mounted under `/api` for the earlier endpoint names.

## Core Endpoints

- `POST /v1/auth/dev-login` (development only; disabled when durable deployment flags are enabled)
- `GET /v1/me`
- `POST /v1/address/resolve`
- `GET /v1/address/autocomplete?q=...`
- `POST /v1/projects`
- `GET /v1/projects`
- `GET /v1/projects/{project_id}`
- `PATCH /v1/projects/{project_id}`
- `DELETE /v1/projects/{project_id}`
- `PUT /v1/projects/{project_id}/property`
- `GET /v1/projects/{project_id}/property`
- `POST /v1/projects/{project_id}/property/resolve`
- `GET /v1/projects/{project_id}/property/profile`
- `PUT /v1/projects/{project_id}/proposal`
- `GET /v1/projects/{project_id}/proposal`
- `POST /v1/projects/{project_id}/documents`
- `POST /v1/projects/{project_id}/documents/upload`
- `GET /v1/projects/{project_id}/documents`
- `GET /v1/projects/{project_id}/documents/{document_id}`
- `POST /v1/projects/{project_id}/documents/{document_id}/analyze`
- `GET /v1/projects/{project_id}/documents/{document_id}/pages`
- `GET /v1/projects/{project_id}/documents/{document_id}/facts`
- `GET /v1/projects/{project_id}/document-search?q=...`
- `POST /v1/sources/manifest/import`
- `POST /v1/sources/hermes-corpus/import`
- `POST /v1/sources/seed`
- `POST /v1/sources/ingest`
- `GET /v1/sources`
- `GET /v1/sources/{source_id}`
- `GET /v1/sources/{source_id}/versions`
- `POST /v1/sources/{source_id}/refresh`
- `GET /v1/source-chunks/search?q=...`
- `POST /v1/ask-source-library`
- `POST /v1/projects/{project_id}/ask-source`
- `POST /v1/projects/{project_id}/resolved-rules`
- `POST /v1/projects/{project_id}/compliance/run`
- `GET /v1/projects/{project_id}/compliance/matrix`
- `GET /v1/projects/{project_id}/checks`
- `PATCH /v1/projects/{project_id}/checks/{check_result_id}`
- `GET /v1/projects/{project_id}/checks/{check_result_id}/decision-trace`
- `POST /v1/projects/{project_id}/measurements`
- `GET /v1/projects/{project_id}/measurements`
- `POST /v1/projects/{project_id}/rfi/parse`
- `GET /v1/projects/{project_id}/rfi/items`
- `PATCH /v1/projects/{project_id}/rfi/items/{rfi_item_id}`
- `POST /v1/projects/{project_id}/rfi/draft-response`
- `GET /v1/projects/{project_id}/responses`
- `POST /v1/projects/{project_id}/exports`
- `GET /v1/projects/{project_id}/exports`
- `GET /v1/projects/{project_id}/exports/{export_id}/download`
- `POST /v1/projects/{project_id}/validations`
- `GET /v1/projects/{project_id}/validations`
- `GET /v1/jobs/{job_id}`
- `POST /v1/jobs/{job_id}/retry`
- `POST /v1/jobs/{job_id}/cancel`
- `GET /v1/jobs/{job_id}/traces`
- `GET /v1/audit?project_id=...`

Deprecated compatibility aliases remain available where practical, including
`POST /v1/projects/{project_id}/checks/run` and
`GET /v1/projects/{project_id}/compliance-matrix`. New clients should use the
canonical `/compliance/run` and `/compliance/matrix` routes.

## Safety Schema Rules

Regulatory answers include:

- `answer`
- `citations`
- `source_version_ids`
- `assumptions`
- `missing_information`
- `confidence`
- `human_review_required`
- `risk_level`
- `status`

Statuses are deliberately non-final: `likely_pass`, `likely_fail`, `missing_info`, `needs_human_review`, `not_applicable`, or `unsupported`.

## Source Import Contracts

`POST /v1/sources/hermes-corpus/import` imports a Hermes `source_inventory.jsonl` corpus, matching the same behavior as `scripts/import_hermes_corpus.py`. Public/open rows with parsed PDF/text content become versioned source text and chunks, but default to `pending_review` and cannot support citable chat/retrieval until accepted through source governance. Pass `request_acceptance: true` only when the operator wants the import to request acceptance through the governance gate. Blocked, paid, login-gated, captcha-gated, robots-denied, unknown-access, restricted-licence, and otherwise non-public rows are skipped. Standards Australia rows are metadata-only and must not store paid Australian Standards full text.

When `inventory_path` is used, `corpus_root` defaults to the inventory file's parent folder. Parsed/raw file paths in rows are resolved under `corpus_root`; paths outside that root are rejected. The import response reports `imported`, `skipped`, `metadata_only`, `duplicates`, `error_count`, `errors`, and row-level `items`.

## Project Document Extraction

`POST /v1/projects/{project_id}/documents/upload` accepts project PDFs, DOCX, HTML, text files, and DXF files. Uploaded documents produce stored document pages, chunks for project-local search, extracted facts, extracted measurements, and `/v1/projects/{project_id}/document-search?q=...` results. CAD/DXF geometry is treated conservatively: extraction may summarize layers, entity types, drawing text, coordinates, and measurement-like values, but ambiguous geometry remains missing information or human-review evidence rather than an invented measurement.
