# Council Rollout Plan — scale the rule DB one council at a time

Date: 2026-06-15. Audience: the next agent. Authority: subordinate to
`docs/MASTER_REBUILD_PLAN.md`; this is the repeatable recipe for adding councils now that the
**Cockburn** pipeline is proven (1,723 faithful rules, independently audited faithfulness 1.00).
Operator standing approval applies (CLAUDE.md): act, log, do not pause to ask.

---

## 0. Where things stand (read first)

- **Cockburn is prod-grade.** 1,723 faithful, in-scope, cited development rules; engine surfaces
  numeric checks + ranked non-numeric advisory rules; live resolution works
  (`1 BLACK SWAN RISE BEELIAR` → parcel → R20 → 6 facts).
- **The proven content pipeline is `decode → correct → filter → noise-sweep → audit`** (NOT a strict
  re-decode — that lost ~67% recall; NOT a reject-only gate — that lost good rules). See §4.
- **What is SHARED across all councils (already done, do NOT redo per council):**
  - WA **state** planning docs: Planning & Development Act, LPS Regulations, the SPPs, MRS, R-Codes,
    DC policies (173 `source_documents` with `local_government IS NULL`). These rules stay **global**
    (`council_scope = NULL`) and apply to every council.
  - **Spatial datasets** (all `approved`, statewide): `gnaf_wa` (1.67M address points),
    `lgate-233` (LGA boundaries), `dplh-070/071` (R-Codes / Zones & Reserves), `dplh-006/008/090`
    (heritage). `lgate-001` (cadastre) and `planning_features` (zoning) are currently ~Cockburn-area
    subsets — **verify coverage per council** (§3.2).
  - The **engine** (`src/draftcheck/checks/engine.py`) — already council-scoped: numeric
    `_get_applicable_rules` and advisory `_get_advisory_rules` filter `(council_scope IS NULL OR =
    resolved scope)` and rank advisory by proposal relevance. No per-council code needed.
  - The **scripts** (`scripts/wp6_*.py`) — reusable, parameterised by source/disposition.
- **What is PER-COUNCIL:** the council's local planning documents, the `council_scope` tag on its
  local rules, its spatial parcel/zoning coverage, and a verification canary address.

### ⚠️ WP-0 — PREREQUISITE before adding any second council
All 1,723 Cockburn rules are `council_scope = NULL` (global). The moment a second council's rules
exist, a Cockburn proposal would surface the other council's local rules and vice-versa. Fix first:

1. **Normalise the LGA value.** The engine resolves council scope from the `local_government` fact,
   which is currently `"City of Cockburn (bbox extent)"` (a bbox match against `lgate-233`). Decide
   the canonical council string (recommend `"City of Cockburn"`) and make BOTH the resolver
   (`postgis_store` LGA lookup → polygon containment, dropping the `(bbox extent)` suffix) and the
   rule `council_scope` use it. **Setting `council_scope` to a value that does not exactly match what
   the engine resolves will silently stop those rules surfacing** — verify against `verify_beeliar.py`
   after.
2. **Scope only LOCAL rules.** Set `council_scope = '<canonical council>'` on rules whose
   `source_documents.local_government` = that council (scheme text, LPPs, structure plans, strategy).
   Leave state-doc rules `council_scope = NULL` (global). SQL pattern:
   ```sql
   UPDATE rules r SET council_scope = 'City of Cockburn'
   FROM source_versions sv, source_documents sd
   WHERE r.source_version_id = sv.id AND sv.source_id = sd.id
     AND r.extractor_model LIKE 'openai%decode' AND r.lifecycle_status = 'approved'
     AND sd.local_government ILIKE '%cockburn%';
   ```
3. **Gate:** re-run `verify_beeliar.py` — must still resolve R20 + surface the Cockburn advisory set.
   Add a canary assertion that a *different* council's address does NOT surface Cockburn local rules.

---

## 1. Per-council recipe (repeat for each council)

Each council is one WP. Target ≈ a day of agent time per council once WP-0 is done. The recipe is
deterministic; only step 2 (ingest) varies by what's available for that council.

### 1.1 Choose & confirm the council
Pick the next council (§2 order). Confirm it has: digital local planning scheme text, G-NAF address
coverage (it will — statewide), and an LGA boundary in `lgate-233`.

### 1.2 Ingest local planning documents  (the only bespoke step)
Fetch and ingest the council's **local** instruments into `source_documents` (tag
`local_government = '<canonical council>'`, appropriate `source_type`) + `clauses`:
- Local Planning Scheme text (the TPS / LPS).
- Local Planning Policies (LPPs).
- Adopted Structure Plans / Local Development Plans.
- Local Planning Strategy.
Reuse the existing ingestion path (see `docs/DATA_INVENTORY.md` / the WP that loaded Cockburn's 107
docs). Do NOT ingest other regions or non-planning statutes (they are denylisted downstream anyway).

### 1.3 Verify spatial coverage for the council
- Parcels: `SELECT count(*) FROM parcels p JOIN ... WHERE <in council LGA>` — must be non-trivial.
- Zoning/R-codes: `planning_features` intersecting the LGA must exist (so resolution yields an
  R-code). If `lgate-001`/`planning_features` don't cover the LGA, extend them (same import path used
  for Cockburn). **Gate:** a known address in the council resolves to a parcel + R-code.

### 1.4 Decode → correct → filter → noise-sweep (run in a STANDALONE container)
Run jobs in a `docker run` container on `draftcheck-wa-v3_default` (survives deploys — see §4.4),
scoped to THIS council's sources. Use gpt-4o for correction.
1. **Decode** (high recall): `wp6_decode.py --dispositions rule_bearing procedural` over the
   council's clauses. (Writes `rule_candidates`; idempotent.) Then `wp6_promote_decode.py --apply`.
2. **Correct-don't-delete:** `wp6_correct.py --apply --model gpt-4o` — rewrites each rule's
   `what_it_means` to match its quote, rejects non-obligations, recovers false-rejects.
3. **Real-rule filter:** `wp6_correct.py --apply --scope approved --redo --model gpt-4o` — drops
   faithful-but-not-checkable admin/process/objective/report-prep, KEEPS design principles +
   measurable standards. (The reject criteria are already calibrated in the script.)
4. **Noise sweep (SQL):** reject broken quotes (`btrim(quote) LIKE '%:'` or `length < 25`),
   out-of-scope sector acts (Main Roads / Water Services / Fish Resources / MRA / mining / strata /
   liquor), and Commonwealth/EPBC cross-references. (See the denylist in `wp6_review.py` /
   `wp6_redecode.py`.)
**Always pilot each LLM pass with `--limit 25 --debug` and eyeball before the full `--apply`.**

### 1.5 Scope the new rules to the council
`UPDATE rules SET council_scope = '<canonical council>'` for the council's newly-approved local
rules (same join as WP-0). State-doc rules stay global.

### 1.6 Faithfulness audit (the gate)
Pull a stratified ~75-rule sample of the council's approved rules and run the **3-independent-judge
faithfulness audit** (the `Workflow` pattern used for Cockburn — see the run scripts under the
session's `workflows/`). **Gate: faithfulness ≥ 0.90** on the sample, judging "does the quote support
`what_it_means`" (NOT "is it a hard numeric standard" — see §4.3). If below, re-run the correct/filter
passes; if a recurring failure mode appears, sharpen `wp6_correct.py` reject criteria and re-pilot.

### 1.7 Verify end-to-end + record canary
- Add a canary address in the council (clone `scripts/verify_beeliar.py` → `verify_<council>.py`,
  pick a real G-NAF address). Confirm: resolves to parcel + R-code + facts; engine returns numeric
  checks + ranked advisory rules; every result cited; the council's rules surface and **other
  councils' local rules do NOT**.
- Record the run into `evals/seeds/<council>_canary.json` (mirror `beeliar_canary.json`), with the
  faithfulness number. Add/extend the canary test.

### 1.8 Ship
Commit scripts/canary/docs; PR; merge once CI green. Rule-data changes apply to prod DB directly
(data-only) and are verified live. Deploy only if engine/registry code changed.

**Definition of "council done":** local docs ingested; spatial resolves to R-code; rules decoded →
corrected → filtered → noise-swept → `council_scope` set; faithfulness ≥ 0.90 (3-judge audit);
canary recorded + passing; no cross-council leakage.

---

## 2. Recommended council order

Start with metro councils adjacent to Cockburn (highest G-NAF density, most similar scheme
structure, likely already partly covered by `lgate`/`dplh`):
1. **Melville**, **Fremantle**, **Kwinana**, **Rockingham** (immediate neighbours).
2. **Canning**, **Gosnells**, **Armadale**, **Belmont**, **Stirling** (broader metro).
3. Then outward / regional as data allows.
Sequence by **availability of digital scheme text** first — pick whichever of the above has the
cleanest machine-readable LPS. Do ONE fully (through §1.8) before starting the next.

---

## 3. Reusable assets & where things live

- **Scripts** (`scripts/`): `wp6_decode.py` (decode), `wp6_promote_decode.py` (promote),
  `wp6_correct.py` (correct-don't-delete + real-rule filter, `--scope`), `wp6_review.py`
  (faithfulness+relevance gate + source denylist), `wp6_redecode.py` (strict re-decode — kept as a
  tool, NOT the main path), `verify_beeliar.py` (end-to-end canary harness).
- **Engine**: `src/draftcheck/checks/engine.py` — council/zone/r-code scoped; advisory relevance
  ranking in `_advisory_relevance_score`; manual-override facts consumed.
- **DB access pattern** (no psql in api container): `ssh draftcheck "docker exec
  draftcheck-wa-v3-api-1 python -c '...psycopg...'"`, DB host is `db`, URL from the api container's
  env. See `[[project-vps-db-access]]` and `[[project-deploy-jobs-gotcha]]`.
- **Standalone durable job pattern** (deploy-proof): `[[project-deploy-jobs-gotcha]]` — `docker run`
  on `draftcheck-wa-v3_default` with DB/OPENAI env from the api container/.env; mount the script via
  `-v /tmp/<script>.py:/app/scripts/<script>.py:ro`.

---

## 4. Hard-won lessons (do not relearn these)

1. **Correct-don't-delete beats both alternatives.** A strict faithfulness-first re-decode had great
   precision but ~33% recall (refused real rules). A reject-only gate threw away ~10% good rules.
   The winner: an LLM that REWRITES each rule's meaning to match its cited quote (fixing should/may-
   vs-must modality, invented thresholds, reversals) and rejects only non-obligations — preserving
   recall AND fixing faithfulness.
2. **Calibrate every LLM pass on a `--limit 25 --debug` pilot before `--apply`.** Both the gate and
   the filter over-rejected on the first prompt and had to be dialled back. A pass that rejects ≫ its
   target rate is mis-calibrated — stop and fix the prompt.
3. **Separate FAITHFULNESS from "checkable standard".** Faithfulness (does the rule misrepresent its
   source?) is the correctness bar — chase it to ~1.0. "Is it a hard numeric standard?" is product
   curation — an advisory tool legitimately holds principles/conditions/objectives, surfaced with
   citations. Chasing "100% checkable" just shrinks the DB; don't.
4. **Run long jobs in standalone containers**, not `docker exec -d` in the api container — deploys
   recreate the api container and `git reset --hard` reverts cp'd files, killing in-container jobs.
5. **Idempotent + resumable.** Every pass skips already-processed rows; safe to re-run after an
   interruption. Watch completion via the job container exiting.
6. **Scope discipline.** A source denylist removes wrong-region (Peel/Bunbury/Leeuwin) and non-
   planning law (strata/mining/liquor/transfer-of-land/public-works/health/fish-resources). State
   PLANNING docs (SPPs incl. "Perth and Peel" metro policies, P&D Act, MRS, R-Codes) stay in.

---

## 5. Open cross-council enhancements (not blockers)

- **Proposal-drawing flow:** numeric pass/fail beyond lot-derived (area/frontage) needs a user to
  upload a drawing / enter proposed values. The manual-override path now works (engine consumes
  `method='manual_override'` facts); the drawing→extraction→facts loop exists. Surfacing/UX could be
  deepened.
- **R-Codes Vol 2 + residential LPPs** (medium-density) — ingest once, benefits all councils.
- **LGA precision:** replace the `lgate-233` bbox-extent match with polygon containment (also fixes
  the council_scope string — see WP-0).
- **Advisory cap (80) + relevance ranking** could be tuned per proposal type.
- **Durable accounts:** magic-link signup is 404 on prod; guests are quota-limited (raised for
  testing). Real auth is a separate workstream before wide public launch.
