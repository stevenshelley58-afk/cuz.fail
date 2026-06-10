# LotFile / DraftCheck WA — Launch Readiness Handoff Plan

Date: 2026-06-10
Audience: a code agent executing work packages (WPs) in order. Each WP is one PR with acceptance criteria.
Authority: complements `docs/MASTER_REBUILD_PLAN.md` (does not change locked decisions). Follows CLAUDE.md operator standing approval — act, don't ask.

## Verdict

The architecture is right and the schema is nearly complete, but the build is at roughly Phase 2–3 of 8. Three things block customers today:

1. **Security**: leaked API keys, an unguarded dev-login with default credentials on the production surface, CSRF-exposed mutation endpoints, no rate limiting.
2. **Product loop is broken**: the primary CTA does nothing, project cards aren't clickable, two API field mismatches blank out compliance results and break fact confirmation, the engine can never find an approved rule (always `unsupported`), and embeddings/search/LLM are all mocks.
3. **Ads readiness is zero**: no landing page, no privacy/terms, no analytics, no SEO meta, no pricing.

Do the WPs in order. WP-0 today. WP-1..3 before any customer touches the site. WP-4..6 before spending a dollar on ads.

---

## WP-0 — Credential rotation + repo hygiene (TODAY, manual + agent)

1. **Rotate the OpenAI key and Anthropic key now.** Live keys are in `.env:77` and `.env:87`. `.env` is gitignored but treat as compromised; verify with `git log --all -- .env` and `git ls-files .env` that it was never tracked.
2. Inspect `backups/stray-jenny-root-20260608T203212.bundle` (`git bundle verify`, then grep extracted history for `sk-proj`/`sk-ant`). Delete the bundle after inspection.
3. Confirm `git ls-files draftcheck.db` is empty; if tracked, untrack it. Archive `draftcheck.db` and `.storage/backups/*.db` out of the working tree after the label harvest (WP-7.3).
4. Add `gitleaks` to CI (`.github/workflows`) so a leaked secret fails the build.

Accept: new keys deployed via VPS `.env` only; gitleaks green; bundle gone.

---

## WP-1 — Auth lockdown (P0 security)

Files: `src/draftcheck/api/auth.py`, `src/draftcheck/config.py`, `infra/v3/compose.yml`, VPS `.env`.

1. `auth.py:217 dev_login` — add as the FIRST statement:
   `if settings.app_env.strip().lower() not in ("local", "development"): raise HTTPException(status_code=404)`.
   There is currently NO environment guard — only an Origin check (verified 2026-06-10).
2. Remove the credential fallbacks at `auth.py:226-227` (`jemma`/`jemma123`). Require `DEV_LOGIN_USERNAME`/`DEV_LOGIN_PASSWORD` env vars; 404 if unset. Note the docs say `jemma6969` but code defaults to `jemma123` — kill both.
3. `infra/v3/compose.yml:46` defaults `DRAFTCHECK_ENV` to `staging`. Set `DRAFTCHECK_ENV: production` explicitly in the VPS `.env`, and add a startup assertion in `config.py`: refuse to boot with `app_env != production` when `DATABASE_URL` host is non-local.
4. `compose.yml:37` runs `scripts/dev_approve_sources.py` whenever env != production. Change guard to `== "local"`.
5. Token pepper: `domain/identity/tokens.py:38` falls back to unsalted SHA-256 when `AUTH_TOKEN_HASH_PEPPER` is empty. Raise at startup if empty in production; set `AUTH_PEPPER` on the VPS.
6. Implement magic-link auth for real (`auth.py:195-213` currently 404s both endpoints — production has NO working login once dev-login is disabled). Wire `EmailSender` per MASTER_REBUILD_PLAN §5.1; use any SMTP provider (e.g. Postmark/SES) via env; keep `cli login-link` as bootstrap.
7. Add absolute session age ceiling (90 d) in `domain/identity/sqlalchemy_store.py:263` (sliding expiry currently extends forever).

Accept: `POST /api/v1/auth/dev-login` returns 404 on lotfile.app; magic-link round-trip works in staging; boot fails loudly on missing pepper/env.

## WP-2 — API hardening (P0 security)

Files: `src/draftcheck/api/main.py`, `v1.py`, `rules.py`, `compliance.py`, `projects.py`, `documents.py`, `sources.py`, `domain/sources/fetching.py`, `infra/v3/Caddyfile`.

1. **CSRF**: cookie is `SameSite=None` (`compose.yml:50`) and many mutating endpoints lack the Origin check. Since we are same-origin now (one host, lotfile.app), change `SESSION_COOKIE_SAMESITE` to `lax` AND add `Depends(require_allowed_origin)` to every state-mutating endpoint: `compliance.py:178` run, all of `projects.py` writes, `documents.py:408-484` fact update/promote, `rules.py:231` and `rules.py:327` reviews.
2. **Auth on leaky endpoints**: add `get_current_session` to `GET /ops/dashboard` and `GET /ready` detail (`v1.py:141-200`, strip DB error detail from ready) and to `POST /assistant` (`sources.py:973` — currently unauthenticated LLM spend).
3. **Rate limiting**: mount slowapi in `main.py` — 10/min auth, 20/min upload, 30/min assistant+search, 120/min default, keyed by IP.
4. **SSRF**: `fetching.py:592 _assert_lawful_public_url` — block RFC-1918 (10/8, 172.16/12, 192.168/16), 169.254.169.254, fd00::/8; resolve DNS first and validate the resolved IP.
5. **Caddy**: merge the duplicate `http://lotfile.app` blocks (`infra/v3/Caddyfile:49-63`); add `Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'"` to the security_headers snippet; drop upload `max_size` from 250MB to 25MB to match the app (or raise the app cap per WP-8.1 and align both).
6. **Container**: add non-root `USER` to `infra/v3/app.Dockerfile`. Root legacy `docker-compose.yml` exposes 5432/6379/9000 on 0.0.0.0 — prefix with `127.0.0.1:` or delete the file (legacy stack is retired).
7. CORS middleware (`main.py:30`): same-origin means it can be removed entirely per CLAUDE.md; if kept for local dev, restrict methods/headers explicitly.
8. Sanitize markdown rendering: `web/src/main.tsx:1577` injects `marked.parse()` via dangerouslySetInnerHTML — add DOMPurify.

Accept: OWASP-style smoke test passes: no mutation without session+origin; metadata endpoints need auth; curl from container cannot reach 169.254.169.254 via source import.

## WP-3 — Make the product loop actually work (P0 product)

Files: `web/src/main.tsx`, `web/src/api.ts`, `src/draftcheck/domain/rules/service.py`, `src/draftcheck/checks/engine.py`, `api/documents.py`.

Frontend bugs (each verified):
1. `main.tsx:35` `const DEV_LOGIN = true` → false; show magic-link form (request → "check your email" → verify). Remove pre-filled username "jemma" (`main.tsx:1782`). Add a "Create account" path (magic-link request doubles as signup).
2. `main.tsx:1302` "Start checking" CTA is an empty stub → trigger `runCheck()` / reveal CompliancePanel.
3. Project cards (`main.tsx:1641`, `1705`) have no onClick → add a project detail view that reopens the wizard at the project's current step.
4. `api.ts:289 confirmFact` sends `{}` but server requires `{review_status: "confirmed"}` → 422 on every confirm, silently masked. Fix the body.
5. `api.ts:172` expects `check_name`; server sends `display_name` (`compliance.py:77`) → every compliance row title renders blank. Align fields (also `created_at` vs `as_of_date`).
6. Render `advisory_disclaimer` from the compliance response as a banner (currently discarded) — legal posture requires it visible.
7. Auth-guard `RulesView` (`main.tsx:2346`) — internal rule pipeline data is visible to guests.
8. Add DB-backed `GET /documents/{doc_id}/facts` (missing — the review UI has no way to list facts after upload) and a per-project uploaded-documents list in the UI.

Backend loop-breakers:
9. **`approve_rule()` does not exist.** `gate.py auto_promote` sets `lifecycle_status='auto_accepted'`; the engine filters `== 'approved'` (`engine.py:129`) → every check returns `unsupported` forever. Add operator-gated `approve_rule()` in `domain/rules/service.py` + API endpoint + button in RulesView, writing an `audit_events` row.
10. **Engine safety invariant (CRITICAL)**: `engine.py:145` loads ALL PropertyFacts. Add `.filter(PropertyFact.promoted_to_measurement == True, PropertyFact.review_status == "confirmed")` and reject `method="assumption"` from producing likely_pass/likely_fail. Add index `(project_id, review_status)`. This is the exact failure mode MASTER_REBUILD_PLAN §12 bans.
11. **Promotion guards**: `api/documents.py:437-484` promotes any fact unconditionally. Port `_measurement_readiness()` from `build/lib/draftcheck_document_ai/service.py:253` — block promotion without numeric value, unit, check_key, evidence ref, confidence ≥ threshold (env-configurable); block `drawing_dimension` facts without calibration.
12. Reconcile `checks/registry.py` (9 keys) vs `checks/tier1.py` (7 keys) — make registry.py the single source the engine consumes; delete the divergent set.
13. Fix disposition vocabulary mismatch: `service.py` uses `definitional`/`not_applicable`; `clause_parser.py` emits `definition`; plan says `definition`/`manual_review`. Standardize on the plan vocabulary, grep all call sites.

Accept: golden-fixture E2E (one address → project → upload DXF fixture → confirm fact → approve rule → run → matrix shows titled, cited results with disclaimer) passes in CI.

---

## WP-4 — Landing page + legal pages (P0 for ads)

1. Static landing at `/` (SPA moves to `/app`, or landing renders for unauthenticated `/`): headline ("Check WA residential drawings against the R-Codes in minutes — advisory, cited, deterministic"), 3-step how-it-works, screenshot, CTA "Check an address free", trust section (advisory-not-certification, cite-or-refuse), footer links. Keep it a single static HTML for speed; reuse the SPA design tokens from `styles.css`.
2. `/privacy` and `/terms` static pages (required by Google Ads and the Australian Privacy Act; terms must state advisory-only, no liability for planning decisions, data handling for uploaded drawings). Link from landing footer, sign-in modal, and StatusBar.
3. Caddy: serve landing + legal pages; SPA stays same-origin at `/app` with `/api/v1` proxy unchanged (do NOT reintroduce Vercel).

Accept: lotfile.app shows marketing page to a logged-out visitor; /privacy and /terms return 200; SPA still works.

## WP-5 — SEO, analytics, conversion plumbing (P0 for ads)

Files: `web/index.html`, `web/public/*`, landing page.

1. `<title>LotFile — WA R-Code & Planning Compliance Checker</title>` + meta description; OG + Twitter card tags with a 1200×630 image; favicon; canonical URL.
2. `robots.txt` (allow landing/legal, disallow `/app`) + `sitemap.xml`.
3. Analytics: Plausible (no consent banner needed) or GA4; fire conversion events: `signup_requested`, `project_created`, `compliance_run`, `checkout_clicked`. Without this, ad spend is unmeasurable.
4. Pricing: put real prices on the Paywall modal (`main.tsx:1880`) and set `VITE_CHECKOUT_URL` (Stripe Payment Link is the fastest path). A paywall with no price converts nobody.
5. Mobile fixes: tabbar `styles.css:204` is `repeat(4,1fr)` with 5 tabs → `repeat(5,1fr)`; verify wizard on 375px width; `aria-label="Send"` on the go button; darken `--ink-faint` to ≥4.5:1 contrast; labels on login inputs; focus-trap in modals; keyboard handlers on rules table rows.

Accept: Lighthouse SEO ≥ 90 on landing; events visible in analytics; paywall has a working checkout link.

## WP-6 — Ops guardrails before traffic

1. Spend persistence: `ai/substrate.py` keeps job traces and daily spend in memory — persist to `job_traces` + `spend_events` tables (they exist, unused) so caps survive restarts. Without this, a restart resets the LLM budget breaker.
2. Backups: implement nightly `pg_dump -Fc` + restic per MASTER_REBUILD_PLAN §3.3 (`infra/v3/backup/` has only a README). Run one restore drill and document it.
3. Uptime monitor on `https://lotfile.app` and `/api/v1/ready` (after WP-2 auth fix, expose a minimal unauthenticated `/api/v1/health` for the monitor instead).
4. Sentry (or GlitchTip) on api + worker.

Accept: kill the api container → restart → daily spend counter unchanged; restore drill log committed.

---

## WP-7 — The brain: make DB + retrieval real (HIGH, after launch blockers)

Files: `domain/sources/library.py`, `sqlalchemy_store.py`, `ai/substrate.py`, `cli.py`, new migration 0007.

1. **Real embeddings (CRITICAL)**: `_hash_embedding()` (`library.py:61`, used by `sqlalchemy_store.py:2294`) writes sha256-derived junk vectors — the HNSW index is meaningless. Implement OpenAI `text-embedding-3-small` (1536-dim, already pinned in models.py) behind the ModelAdapter with batching + retry; refuse mock embeddings when `app_env=production`. Re-embed existing chunks via a CLI command.
2. **Real hybrid search (CRITICAL)**: there is no Postgres-backed search — `/search/chunks` and `/search/ask` run in-memory Jaccard. Build `SqlAlchemySourceSearchService`: FTS (`websearch_to_tsquery` + `ts_rank_cd` on the existing GIN index) + pgvector cosine (`<=>` on HNSW) + RRF fusion (k=60) + legal_edges expansion + rerank (approved/current/jurisdiction first). Keep cite-or-refuse: no hits or restricted licence → `unsupported`.
3. **Real LLM adapter**: add `anthropic`/`openai` modes to `substrate.py` (currently only `disabled`/`local` stub). Wire `classify_clause()` (currently discards the adapter response — labelled stub) and `enqueue_extraction_group()` (currently creates empty candidates) to actually call the model, populate `value_json/condition_json/quote/quote_char_start/end`, and run the 5 validators in `gate.py`. Every call → persisted job_trace + spend cap.
4. **Migration 0007**: GIN trigram index on `address_points.address_text` (`gin_trgm_ops` — resolver does pg_trgm similarity over ~2M rows with no index today) + `pg_trgm` extension; CHECK constraints on `rules.lifecycle_status`, `rule_candidates.review_status`, `check_results.status`, `document_facts.review_status`; `org_id` on `property_facts`/`clauses`/`rules`; queryable `projects.council_scope` column (currently buried in metadata_json); index `property_facts(project_id, review_status)`.
5. **Clause-aligned chunking**: pipe `ClauseParser` output into chunk boundaries instead of paragraph splits (`library.py:74`); CLI `parse-source-clauses`; populate `legal_edges` from "see clause X.Y" references and supersession metadata (table exists, zero rows today).
6. **CLI gaps**: `import-corpus` (walk `data/corpus` 1,422 files → `import_source()`, sha256 dedup) and `label-harvest` (legacy SQLite approved rule_rows/clause_dispositions/golden evals → eval seeds + `rules` with provenance) — then archive `draftcheck.db` per WP-0.4.
7. **Engine applicability**: add `applicable_zones`/`applicable_r_codes` (JSONB) to rules; filter by the project's resolved zone/R-code before evaluation (today every approved rule applies to every project). Add precedence per §8.2 and pathway preference; expand `decision_trace_json` to plan shape (measurement_ids, snapshot hashes, applicability/precedence traces).
8. **Spatial fixes**: resolver `_upsert_facts()` — include `spatial_dataset_id` in the INSERT (provenance chain currently broken); guard the DELETE so confirmed/promoted facts survive re-resolve; add R-code layer query (`layer_type IN ('r_code','residential_density')`) — R-code is the single most important fact for R-Codes checks and is never extracted today; post-import parcel linkage UPDATE for G-NAF points.
9. Paginate `citable_chunks()` (full-table load into memory today).

Accept: `/search/ask` answers from Postgres with citations or refuses; EXPLAIN shows index use on address lookup and search; a real extraction run produces a validated, quote-anchored candidate; engine only evaluates rules matching the project's zone/R-code.

## WP-8 — CAD/drawing intake that gets good results (HIGH)

Order matters; each is one PR. Today the only real extractor is regex over prose — the "DXF parser" greps raw text for literals like `DIMENSION:` that never appear in real CAD exports.

1. **Parser protocol + plumbing**: `domain/documents/parsers/__init__.py` with `can_parse()/parse() → ParsedDocument(pages, artifacts, parser_name, parser_version)`; registry-ordered dispatch in upload; write `artifacts` rows and populate `document_facts.artifact_id` (always NULL today — evidence chain broken); raise upload cap to 100–250MB (align Caddy); accept `.ifc`, images, `.dwg` (metadata-only).
2. **ezdxf DXF parser** (`parsers/dxf.py`, add `ezdxf>=1.3`): `$INSUNITS` unit handling (unitless → confidence ≤0.4, never convert); DIMENSION group 42 actual measurement vs group 1 text override — flag disagreement (override ≠ measured is the classic drafting trap), `<>`/empty are safe; recurse BLOCK/INSERT with scale factors; separate paper/model space; entity handle in `evidence_ref_json`. Use legacy `build/lib/draftcheck_document_ai/extraction.py` only as a coverage reference.
3. **PyMuPDF vector-PDF parser** (`parsers/pdf_vector.py`, dep already present): text spans with bboxes → regex facts with real `{page, bbox}` evidence; `page.get_drawings()` line segments stored as unpromoted `drawing_entity` facts for calibration — never measured at assumed scale.
4. **Pattern + guard port**: bring over legacy patterns (outdoor living area/min dimension, retaining height, boundary wall length, FFL/NGL/RL, `1:NNN` scale) and unify units through `extraction/normalize.py` (`sqm` vs `m2` divergence today); promotion guard from WP-3.11 if not already landed.
5. **Scale calibration**: `documents.scale_calibration_json` migration; `POST /documents/{id}/calibrate` (two points + known distance → units_per_pixel) and `apply-calibration` (recompute drawing_entity facts, raise confidence); minimal click-two-points canvas UI. This unlocks raster + vector-PDF measurement legitimately.
6. **Title-block parser**: scan DXF blocks named TITLE/TB/A0-A4 for scale `1:NNN`, revision `Rev X`, drawing number → `documents.metadata_json.title_block`; pre-fill calibration when unambiguous.
7. **IfcOpenShell parser**: IfcSpace areas, IfcSite plot area/RefElevation, wall lengths — model-derived, confidence 0.9.
8. **LLM vision proposer (last)**: page images → vision model proposes labeled dimensions as `pending_review` facts (≤0.7 confidence) through the substrate (traced, capped); confidence rises only on agreement with a deterministic extractor; disagreement keeps both in review. The LLM proposes; geometry + humans confirm; the engine decides.

Accept: a real DXF site plan from a CAD export yields entity-linked dimension facts with correct units; a 1:200 vector PDF yields facts only after calibration; nothing raster-derived can be promoted uncalibrated.

---

## Suggested PR sequence

| # | WP | Size | Gate |
|---|----|------|------|
| 1 | WP-0 + WP-1 | S/M | nothing ships before this |
| 2 | WP-2 | M | before any external user |
| 3 | WP-3 | L (split FE/BE) | golden-fixture E2E green |
| 4 | WP-4 + WP-5 | M | before first ad dollar |
| 5 | WP-6 | S | before traffic |
| 6 | WP-7.1–7.4 | L | brain becomes real |
| 7 | WP-7.5–7.9 | M | |
| 8 | WP-8.1–8.4 | L | DXF results become real |
| 9 | WP-8.5–8.8 | M | calibration + IFC + vision |

## Standing verification for every PR

- CI: ruff, mypy, pytest, `alembic upgrade head && downgrade -1 && upgrade head`, `web` build, gitleaks.
- The golden fixture project (MASTER_REBUILD_PLAN Phase 2) runs E2E in CI from WP-3 onward.
- Invariant tests (add in WP-3): no `likely_pass/likely_fail` without approved rule + promoted confirmed measurement + citation + trace; dev-login 404 when `app_env=production`; no LLM call without a persisted job_trace.

## Detailed findings reference

Full per-file findings (28 security items C-1…L-8; 28 frontend items P0-A…P2-K; 29 brain items; 14 extraction gaps) are preserved in the review transcripts of 2026-06-10. The highest-severity items are all embedded in the WPs above with file:line targets.
