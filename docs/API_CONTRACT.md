# API Contract

The API is exposed under `/api/v1` (see `src/draftcheck/api/main.py`,
`app.include_router(create_v1_router(), prefix="/api/v1")`). All paths below are
relative to that prefix unless stated otherwise.

## Authentication & access

Production auth is passwordless magic-link only:

- `POST /auth/magic-link/request` — body `{ email, org_slug? }`. Emails a link to
  `{FRONTEND_URL}/auth/magic-link/verify?token=…`. Requires an allowed `Origin`
  header. In production with no SMTP configured this returns `503`.
- `POST /auth/magic-link/verify` — body `{ token }`. Consumes the token and sets
  an httponly session cookie (`draftcheck_session`, 30-day TTL; `secure` defaults
  on in production, `samesite=lax`).
- `GET /auth/session` — returns the active session for the cookie, else `401`.
- `POST /auth/logout` — revokes the session and clears the cookie.
- `POST /auth/dev-login` — dev-only username/password convenience login, hidden
  from the schema. Reachable only when **both** `app_env != production` **and**
  `DEV_LOGIN_ENABLED` is explicitly truthy; otherwise `404`. Credentials default
  to `jemma`/`jemma6969` (override via `DEV_LOGIN_USERNAME`/`DEV_LOGIN_PASSWORD`).

Route access tiers:

- **Public (no session):** `GET /health`, `GET /ready`, `GET /ops/dashboard`,
  `GET /sources`, `GET /sources/freshness`, `GET /sources/ingestion-status`,
  `GET /sources/{id}`, `GET /sources/{id}/versions`.
- **Session required (`401` without cookie):** `/search/chunks`, `/search/ask`,
  `/assistant`, address resolve, project document endpoints, and all writes.
- **Reviewer role required (`403` otherwise):** source import/review/refresh,
  fact review, and other mutating governance actions.

Guest ("no login") mode is a **client-only** concept implemented in
`web/src/main.tsx`; the backend grants unauthenticated users nothing beyond the
public reads above. Guest usage counters live in `localStorage` and guest
"answers" are non-grounded preview text rendered locally, clearly labelled as
previews — they are not source-backed API responses.

## Core Endpoints

- `POST /address/resolve`
- `GET /address/autocomplete?q=...`
- `POST /projects`
- `GET /projects`
- `GET /projects/{project_id}`
- `PATCH /projects/{project_id}`
- `DELETE /projects/{project_id}`
- `PUT /projects/{project_id}/property`
- `GET /projects/{project_id}/property`
- `POST /projects/{project_id}/property/resolve`
- `GET /projects/{project_id}/property/profile`
- `PUT /projects/{project_id}/proposal`
- `GET /projects/{project_id}/proposal`
- `POST /projects/{project_id}/documents`
- `POST /projects/{project_id}/documents/upload`
- `GET /projects/{project_id}/documents`
- `GET /projects/{project_id}/documents/{document_id}`
- `POST /projects/{project_id}/documents/{document_id}/analyze`
- `GET /projects/{project_id}/documents/{document_id}/pages`
- `GET /projects/{project_id}/documents/{document_id}/facts`
- `GET /projects/{project_id}/document-search?q=...`
- `POST /sources/manifest/import`
- `POST /sources/hermes-corpus/import`
- `POST /sources/seed`
- `POST /sources/ingest`
- `GET /sources`
- `GET /sources/{source_id}`
- `GET /sources/{source_id}/versions`
- `POST /sources/{source_id}/refresh`
- `GET /source-chunks/search?q=...`
- `POST /ask-source-library`
- `POST /projects/{project_id}/ask-source`
- `POST /projects/{project_id}/resolved-rules`
- `POST /projects/{project_id}/compliance/run`
- `GET /projects/{project_id}/compliance/matrix`
- `GET /projects/{project_id}/checks`
- `PATCH /projects/{project_id}/checks/{check_result_id}`
- `GET /projects/{project_id}/checks/{check_result_id}/decision-trace`
- `POST /projects/{project_id}/measurements`
- `GET /projects/{project_id}/measurements`
- `POST /projects/{project_id}/rfi/parse`
- `GET /projects/{project_id}/rfi/items`
- `PATCH /projects/{project_id}/rfi/items/{rfi_item_id}`
- `POST /projects/{project_id}/rfi/draft-response`
- `GET /projects/{project_id}/responses`
- `POST /projects/{project_id}/exports`
- `GET /projects/{project_id}/exports`
- `GET /projects/{project_id}/exports/{export_id}/download`
- `POST /projects/{project_id}/validations`
- `GET /projects/{project_id}/validations`
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/retry`
- `POST /jobs/{job_id}/cancel`
- `GET /jobs/{job_id}/traces`
- `GET /audit?project_id=...`

Deprecated compatibility aliases remain available where practical, including
`POST /projects/{project_id}/checks/run` and
`GET /projects/{project_id}/compliance-matrix`. New clients should use the
canonical `/compliance/run` and `/compliance/matrix` routes.

## Safety Schema Rules

Regulatory answers include:

- `answer`
- `citati