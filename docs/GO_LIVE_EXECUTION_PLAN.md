# LotFile — Go-Live Execution Plan (worker-agent dispatch sheet)

Date: 2026-06-12. Audience: an execution agent working through tasks in order, one PR per
task. Authorities: `docs/MASTER_REBUILD_PLAN.md` (locked decisions),
`docs/LAUNCH_HANDOFF_PLAN.md` (2026-06-10 security/product review — partially superseded;
this file states what is still open), `docs/DB_BUILDOUT_AGENT_PLAN.md` (DB work packages).
CLAUDE.md operator standing approval applies: act, log, don't ask.

Every task here has exact commands and a machine-checkable gate. If a step is ambiguous:
write a `review_items` row (or append `reports/escalations.jsonl` if the DB is unreachable),
note it in the PR description, and move to the next task. Never stall.

## How to run anything (read once, applies everywhere)

- Production = the VPS only (`lotfile.app`, same-origin, Caddy → FastAPI). Never Vercel,
  never `VITE_API_BASE_URL`, never CORS workarounds.
- Run things on prod inside the api container:
  `ssh draftcheck 'cd /srv/draftcheck/app/infra/v3 && sudo docker compose exec -T api <cmd>'`
- **Every push to main auto-deploys and RESTARTS the api container, killing any running
  job inside it.** While a detached job runs: iterate via
  `scp <file> draftcheck:/tmp/f && ssh draftcheck 'cd /srv/draftcheck/app/infra/v3 && sudo docker compose cp /tmp/f api:/app/<path>'`,
  and push only when the container is idle. (The deploy workflow is
  `.github/workflows/deploy.yml`, triggered by CI success on main. It can also fail with a
  transient SSH timeout — if prod lags main, deploy manually:
  `ssh draftcheck 'cd /srv/draftcheck/app && git fetch origin && git reset --hard origin/main && cd infra/v3 && sudo docker compose up -d --build api worker hermes'`.)
- Long jobs: launch detached
  (`sudo docker compose exec -dT api sh -c "python /app/scripts/<s>.py ... > /app/reports/<s>.log 2>&1"`),
  poll the log, copy the report out, commit it under `reports/`.
- Local tests before any PR: `.venv/Scripts/python.exe -m pytest -q` (283+ passing today),
  `ruff check`, and the migration roundtrip runs in CI.

## Verified state (2026-06-12 — do not re-derive)

- Prod healthy and on latest main; `/api/v1/ready` all ok. Chat works live (MiniMax),
  retrieval-backed; `<think>`-leak fixed; legacy `licence_status='approved'` crash fixed
  (`_coerce_licence_status` in `domain/sources/library.py`).
- Local dev works: vite proxy for `/api/v1` added (`web/vite.config.ts`); a stale compiled
  `web/vite.config.js` was deleted — if local API calls 404 again, delete it again.
- DB: migrations at head (0015). `target_manifest` fully drained: 203 acquired /
  14 metadata_only / 17 out_of_scope / 2 blocked / 0 pending (`reports/wp4_acquisition.json`).
  Approved rules: **111** (`reports/wp9_adjudication.json`: 30 promoted, 177 rejected).
  `rule_candidates`: 1070 validators_passed (506 single-model-family), 289 pending_review,
  490 rejected, 1930 validator_failed (dead), 301 auto_promoted. 19 golden eval cases.
- Retrieval gate: chunks are searchable only when `source_versions.review_status='approved'`
  AND licence in {open, verified_open} AND not metadata_only/superseded
  (`library.py` search SQL + `can_support_citable_retrieval`). All 286 versions currently
  approved. Hybrid scoring = 0.4 FTS + 0.6 cosine.
- Much of LAUNCH_HANDOFF_PLAN WP-3/WP-7 is ALREADY DONE (verified in code 2026-06-12):
  `approve_rule` endpoint exists (`api/rules.py:374`), engine filters confirmed promoted
  facts and rejects assumptions (`checks/engine.py:262,371`), promotion gates exist
  (`api/documents.py:408`), document fact list endpoints exist (`documents.py:521,561`),
  compliance API fields align with the SPA, project cards/wizard CTA are wired,
  `DEV_LOGIN=false` (`web/src/config.ts:1`), `/assistant` is session-guarded, real
  Postgres hybrid search exists. Do NOT redo these; spot-check and move on.

---

# PART A — Security before customers (1–2 days)

These are the still-open items from LAUNCH_HANDOFF_PLAN WP-0/1/2 (each re-verified open
on 2026-06-12).

## A1. Magic-link auth is a stub — production has NO real sign-in
`src/draftcheck/api/auth.py` lines ~195–215: both magic-link endpoints raise 404.
1. Implement request + verify per MASTER_REBUILD_PLAN §5.1 (token issue → email → verify →
   session cookie). The identity store and session machinery already exist.
2. SMTP: `infra/v3/compose.yml:54-62` passes empty SMTP vars. Provision Postmark or SES,
   set `SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD/SMTP_FROM` in the VPS `/srv/draftcheck/app/infra/v3/.env`.
   In production an empty SMTP_HOST raises EmailConfigurationError on send (`auth.py:97-112`) — correct, keep.
3. Token pepper: `config.py:102` defaults `auth_token_hash_pepper` to "" and
   `domain/identity/tokens.py:38` silently falls back to unsalted SHA-256. Add a startup
   assertion: refuse boot when pepper empty and app_env=production. Set `AUTH_TOKEN_HASH_PEPPER`
   on the VPS (generate on the VPS, never commit).
4. Dev-login (`auth.py:218-230`): add env guard as FIRST line —
   404 unless `app_env in {local, development}`. Remove the `jemma`/`jemma123` fallbacks;
   require env vars.
5. `compose.yml:46` defaults `DRAFTCHECK_ENV=staging` → set `production` in VPS .env.

Gate: magic-link round trip works on lotfile.app (request → email → verify → session);
`POST /api/v1/auth/dev-login` returns 404 on prod; boot fails loudly without pepper.

## A2. Request hardening
1. Rate limiting: none exists (`api/main.py`). Mount slowapi: 10/min auth, 20/min upload,
   30/min assistant+search, 120/min default, by IP.
2. CSRF: `SESSION_COOKIE_SAMESITE=none` (`compose.yml:50`) → `lax` (we are same-origin).
   Add `Depends(require_allowed_origin)` to mutating endpoints that lack it
   (`compliance.py` run, `projects.py` writes, `documents.py` fact update/promote, `rules.py` reviews).
3. SSRF: verify `fetching.py _assert_lawful_public_url` blocks RFC-1918 + 169.254.169.254 +
   fd00::/8 with DNS resolution first; add if missing.
4. Caddy CSP header per LAUNCH_HANDOFF WP-2.5; align upload max body with the app cap.
5. `web`: DOMPurify around `marked.parse()` output (XSS), wherever dangerouslySetInnerHTML is used.
6. Add `gitleaks` to CI; rotate any key found in `.env` history per WP-0 (treat `.env` as compromised).

Gate: no mutation without session+origin; curl from the container cannot fetch
169.254.169.254 via source import; gitleaks green in CI.

# PART B — Finish the data brain (the DB work, 2–4 days + LLM spend)

## B0. Collect + verify (15 min)
`reports/wp9_adjudication.json` and `reports/wp4_acquisition.json` are committed. Confirm
counts still match the Verified State above; if they drifted, re-print and update this file.

## B1. Unblock the 2 blocked manifest rows (30 min)
`SELECT id, instrument_name, notes FROM target_manifest WHERE status='blocked'` —
both are landing pages (Planning and Development Act 2005; Greater Bunbury Region Scheme).
Find the real consolidated PDF on legislation.wa.gov.au, then:
`UPDATE target_manifest SET canonical_url='<pdf>', status='pending', notes=NULL WHERE id='<id>'`
and run `python /app/scripts/wp4_acquire.py --limit 5 --report /app/reports/wp4_unblock.json`.
Gate: 0 blocked rows (or escalated with the failing URL recorded).

## B2. Real embeddings audit (2 h, then possibly a re-embed run)
Embeddings default to OpenAI text-embedding-3-small via OPENAI_API_KEY, but legacy chunks
may carry hash-based junk vectors (the dev fallback).
1. Check: `SELECT embedding_provider, embedding_model, count(*) FROM source_chunks GROUP BY 1,2`.
2. Any chunks with provider 'stub'/'hash' (or NULL embedding): re-embed via the import
   path's `_embed()` with OPENAI_API_KEY set (write `scripts/reembed_chunks.py`, idempotent,
   batch 100, detached run). Refuse mock embeddings when app_env=production (add assertion).
Gate: 100% of chunks carry the pinned provider/model/dimension; report committed.

## B3. WP5 — citation closure (1 day, deterministic-first)
Write `scripts/wp5_citations.py` (claim-loop pattern copied from `wp4_acquire.py`):
1. Queue: source_versions with chunks and no `legal_edges` row with `relation='cites'`
   + `metadata_json->>'wp5'='true'`.
2. Deterministic regex pass per chunk for instrument references:
   `State Planning Policy [0-9.]+`, `Development Control Policy [0-9.]+`,
   `Local Planning Scheme No\.? ?\d+`, `R-Codes|Residential Design Codes`,
   `[A-Z][a-z]+ (Act|Regulations) \d{4}`, `AS/NZS [0-9.]+`, `NCC|Building Code of Australia`.
3. Resolve against `target_manifest.instrument_name` (ci-exact, then `instrument_aliases`).
   Resolved → `legal_edges` row (relation='cites', verbatim sentence as quote, uuid5
   idempotent id). Unresolved → idempotent new `target_manifest` pending row + alias row.
4. Fixpoint loop: pool drains → new pending rows? → run `wp4_acquire.py`, re-run wp5 over
   the new versions only. Stop when a full pass adds zero rows.
Gate: `reports/citation_closure.json` committed — fixpoint reached, 0 unresolved
references (each either resolved or escalated). LLM use only if the deterministic pass
leaves unresolved matches (one pass per doc max, strict JSON, quote anchors).

## B4. WP6 — extraction over the new corpus (the big LLM item, ~$20–60)
~80 newly acquired sources have chunks but no clause/rule extraction.
1. Queue: rule-bearing versions (source_type in state_planning_policy, dc_policy,
   local_planning_policy, local_planning_scheme, region_scheme, act) with no clauses rows.
2. One at a time, detached:
   `python /app/scripts/wp6_extract.py --source-version <uuid> --report /app/reports/wp6/<uuid>.json`
3. Spend check every 10 docs against `spend_events` (stop + escalate at $50/day).
4. After the queue drains: `python /app/scripts/wp6_adjudicate.py --apply --report /app/reports/wp6_adjudication.json`
   (idempotent; runs on every deploy anyway).
Gate: every queued version has clauses; `rules` count increased; per-doc reports committed.
A doc that crashes extraction twice → skip + escalate, continue.

## B5. WP6 challenge round — the 506 single-family groups (~$10–20)
They sit at `review_status='validators_passed'` with
`metadata_json->>'pending_reason'='single_model_family'`.
1. Precondition: a second model family key on the VPS (OPENAI_API_KEY is present and was
   used by wp9; OPENROUTER_API_KEY is missing — escalation already recorded in
   `reports/wp9_adjudication.json`).
2. Write `scripts/wp6_challenge.py` — clone `wp9_pending_adjudicate.py`, change the
   candidate query to the filter above, and force the fresh passes to a DIFFERENT family
   from the stored votes (`family_of()` in `draftcheck/extraction/adjudication.py`).
   2 fresh reproductions → promote at 0.85; 1 → keep; 0 → reject. Mark every processed
   candidate `metadata_json.challenge_done=true`.
Gate: 0 unprocessed single_model_family candidates; report committed.

## B6. WP7 — legal graph + conflict sweep (1 day, deterministic)
1. Every `rules.rule_type='exception'` row must have an `exception_to` edge; missing →
   create from clause context if the quote names the base rule, else `review_items`.
2. Write `scripts/wp7_conflict_sweep.py`: for every (rule_key, density_code, pathway)
   with >1 approved rule from different instruments → row in `reports/conflict_sweep.json`.
   Same instrument + same applicability + different values = extraction bug → `review_items`.
3. Precedence lives in code (`src/draftcheck/checks/`), never AI-decided. If absent, escalate.
Gate: 0 quoteless legal_edges; `reports/conflict_sweep.json` committed.

## B7. WP8 — adversarial rounds (after B3–B6 green)
Per DB_BUILDOUT_AGENT_PLAN WP8. Minimum viable round: 20 re-extractions with the other
family + 20 prosecutor questions through `/api/v1/search/ask` checked against the rules
table; findings → `adversarial_findings`; defense fixes via the candidate path (never
direct UPDATE); each confirmed finding → golden eval case.
Gate: 2 consecutive clean rounds → `reports/adversarial_closure.json`.

# PART C — Close the product loop end-to-end (2–4 days)

Current non-DB status as of 2026-06-13:

1. **Golden-fixture E2E in CI**: VERIFIED. CI has a named Golden fixture E2E gate covering
   address -> project -> DXF upload -> fact promotion -> compliance run with cited advisory
   results. Keep this gate green before shipping product-loop changes.
2. **Async document parsing**: ADVANCED. Uploads persist `parse_pending`, enqueue the worker
   parser, and the SPA polls both `parse_pending` and `parsing` until facts are available.
   Remaining live check: worker-backed upload on the VPS after DB work is idle.
3. **Real CAD extraction**: ADVANCED. Parser adapters cover DXF units/entity evidence, PDF
   text/vector evidence, IFC fallback, title-block metadata, and parser capability/accuracy
   reporting. Artifact-row persistence remains DB-owned.
4. **DocumentChunk embeddings**: VERIFIED. Document chunks are written and project-scoped
   search marks them non-authoritative (`legal_authority=false`).
5. **Engine refinement visibility**: VERIFIED for the frontend loop. Compliance responses
   expose missing-info reasons, drawing evidence, cited advisory results, saved-matrix load
   states, and operator review notes. The SPA also preserves newer manual run results when
   an older saved matrix response resolves late.
6. **Proposal/document review UX**: ADVANCED. The proposal wizard now captures building
   class and street confirmations before checks, blocks incomplete proposal saves, and
   lets returning users review persisted facts from already-uploaded parsed documents.

Historical baseline from the Phase 4/5 scan, retained for traceability:

1. **Golden-fixture E2E in CI**: address → project → upload DXF fixture
   (`tests/fixtures/golden/document_facts.json`) → confirm fact → approved rule → run
   compliance → titled, cited results with advisory disclaimer. This is the M1 gate and
   the single most valuable missing test.
2. **Async document parsing**: parsing is inline in the upload endpoint; move to a
   Procrastinate job (worker queues already run) so big DXF/IFC files don't block the API.
3. **Real CAD extraction** (LAUNCH_HANDOFF WP-8 sequence, in order): parser protocol +
   artifacts rows → ezdxf DXF parser (units, DIMENSION group 42 vs text override,
   block/insert scaling) → PyMuPDF vector-PDF parser with bbox evidence → pattern/unit
   port → scale calibration endpoint + UI → title-block parser → IfcOpenShell → vision
   proposer LAST (propose-only, ≤0.7 confidence).
4. **DocumentChunk embeddings**: model + HNSW index exist; upload never writes chunks.
   Write them and include document chunks in retrieval where appropriate.
5. **Engine refinements**: read council facts from PropertyFact (fact_type='council') not
   just Project.council_scope; categorize missing-info (missing fact vs missing rule);
   populate `drawing_evidence_json`; human-override workflow columns are unused.

Gate: the golden E2E passes in CI; a real CAD export produces entity-linked facts with
correct units; nothing raster-derived promotes uncalibrated.

# PART D — Launch surface (before any ad dollar, 2–3 days)

LAUNCH_HANDOFF WP-4/WP-5 current status as of 2026-06-13:

1. Static landing at `/`, `/app` SPA routing, `/privacy`, and `/terms`: VERIFIED.
2. SEO assets and metadata (`robots.txt`, `sitemap.xml`, favicon, OG image, canonical
   checks): VERIFIED by local and live launch verifiers.
3. Analytics events (`signup_requested`, `project_created`, `compliance_run`,
   `checkout_clicked`): WIRED and covered by launch-action tests.
4. Mobile sweep: VERIFIED by `verify:launch:mobile` and launch-action coverage.
5. Pricing/checkout: CODE VERIFIED with strict Stripe-shaped fixtures; production remains
   blocked only until the real Stripe Payment Link is installed as `VITE_CHECKOUT_URL`.

Historical LAUNCH_HANDOFF WP-4/WP-5 baseline, retained for traceability:
1. Static landing at `/` (SPA at `/app` or render-for-logged-out), advisory-not-certification
   trust copy, CTA "Check an address free".
2. `/privacy` + `/terms` (advisory-only, liability, uploaded-drawing data handling).
3. SEO: title/meta/OG/favicon/robots.txt/sitemap.xml.
4. Analytics: Plausible (no consent banner) — events: signup_requested, project_created,
   compliance_run, checkout_clicked.
5. Pricing: real prices on the Paywall modal + `VITE_CHECKOUT_URL` (Stripe Payment Link).
6. Mobile sweep: 5-tab grid fix, 375px wizard pass, contrast + aria labels.
Gate: Lighthouse SEO ≥ 90 on landing; events visible; checkout link works.

# PART E — Ops guardrails (1 day)

Confirmed-open from the infra scan (backup scripts + timers + Sentry code all EXIST):
1. **Arm backups**: create `/etc/draftcheck/backup.env` on the VPS with RESTIC_REPOSITORY
   (off-site: B2/R2) + RESTIC_PASSWORD_FILE; enable `draftcheck-backup.timer`; run
   `infra/v3/backup/restore-drill.sh` once and commit the drill log to `docs/ops/`.
2. **Uptime monitor**: follow `docs/ops/uptime-monitor.md` (UptimeRobot keyword
   monitors on `https://lotfile.app/api/v1/health` + `https://lotfile.app/api/v1/ready`).
3. **Alerts**: backup freshness >26 h, disk >80% on /srv + pg volume, worker heartbeat
   (cron + curl to a webhook is fine; keep it simple).
4. **Sentry**: provision a DSN, set SENTRY_DSN in VPS .env (code already initializes it).
5. **Log rotation**: journald SystemMaxUse or logrotate for Docker logs.
6. **Spend persistence**: verify daily LLM spend survives an api restart (kill + restart
   the container, check the spend counter) — if it resets, persist to `spend_events`
   (LAUNCH_HANDOFF WP-6.1).
7. **Deploy reliability**: DONE 2026-06-12 — deploy.yml retries SSH 4× with
   ConnectTimeout=20. If deploys still fail, deploy manually (command at top) and check
   the provider's network status.
8. **Host firewall (Phase 0 gap, verified 2026-06-12)**: UFW and fail2ban are BOTH
   inactive on the VPS; iptables INPUT policy is ACCEPT (only Tailscale chains present).
   Apply the runbook hardening (`docs/CODEX_DEPLOY_SYNC_RUNBOOK.md` §B1): ufw allow
   OpenSSH/80/443 + enable, enable fail2ban, disable SSH password auth. Do this in a
   maintenance window and KEEP AN ACTIVE SSH SESSION OPEN while testing so a bad rule
   can't lock you out.
Gate: restore-drill log committed; monitor live; kill-restart keeps the spend counter.

# PART F — Post-launch (Phases 6–8, weeks)

Hermes autonomy loop (the hermes container currently idles), RFI parsing + draft_response
skill, export builders with cite-or-refuse signoff manifests, skill self-learning +
weekly canaries, ops dashboard completeness. Sequence after PARTs A–E are green; follow
MASTER_REBUILD_PLAN §Phases 6–8.

---

## Order of execution

| # | Part | Why first |
|---|------|-----------|
| 1 | A1 + A2 | nothing public before auth + hardening |
| 2 | B1–B3 | cheap, unlocks grounded chat |
| 3 | C1 (golden E2E) | locks the loop against regressions |
| 4 | B4–B5 | fills the rule matrix (LLM spend) |
| 5 | D | launch surface |
| 6 | E | guardrails before traffic |
| 7 | B6–B7, C2–C5 | depth and trust |
| 8 | F | post-launch |

## Standing rules

- Alembic is the only schema authority. Idempotent jobs only. Every fetch →
  `source_fetch_log`; every approve/override → `audit_events`.
- Outputs advisory; cite or refuse; never claim final compliance.
- Blocked ≠ stalled: record blocker + one-command unblock, continue, list in the PR.
- Commit every report under `reports/`. Push only when the api container is idle.
