# Open-Vocab Rule DB Rebuild — Agent Dispatch Plan

Date: 2026-06-14. Authority: operator decision (Steven, 2026-06-14) to abandon the closed 50-key vocabulary that was constraining the LLM extractors to a pre-decided list of rule shapes. New architecture: **LLM extracts freely, deterministic validators catch errors, post-hoc clustering canonicalises rule_keys, adversarial review polishes, CheckDefinitions are derived from the resulting clusters rather than declared up-front.**

Subordinate to `docs/MASTER_REBUILD_PLAN.md`. Supersedes the closed-vocab references in `docs/DB_BUILDOUT_AGENT_PLAN.md` WP6 (kept for history; the new pipeline replaces it).

Audience: an autonomous agent picking up the next session. Each WP has exact files, exact commands, machine-checkable gates, and an escalation rule. Operator standing approval applies (see CLAUDE.md): act, log, do not ask permission. The plan is sized for one Opus-driven sprint (~5 hours wall, ~$80–200 LLM spend depending on corpus depth).

---

## IMPLEMENTATION STATUS UPDATE — Rich rule DECODE model (2026-06-15)

Operator reframe (Steven, 2026-06-14): **"not every rule will have a number — that's why we use an LLM to decode it. There is a rule; then we need to know what it IS, what it MEANS, and how we will QUERY it."** The pipeline below was numeric-atom-centric (only `numeric_threshold` rules survived). It is now generalised to decode **every** kind of planning rule.

**New decode schema (migration `0019_rule_decode_logic`, applied to prod).** `rules` and `rule_candidates` gain:
- `check_type` — `numeric_threshold | categorical | boolean_presence | qualitative_performance | conditional` (+ `not_a_rule`, which is filtered, not stored).
- `evaluable` — `auto_numeric | auto_presence | ai_judgement | needs_more_info`.
- `rule_logic_json` (JSONB) — `{what_it_is, what_it_means, requirement, applies_when, how_to_query, modality, relevance}`.

**New pipeline (replaces WP-C/E for non-numeric rules; WP-D/F still apply to numerics):**
1. `scripts/wp6_decode.py` — concurrent OpenAI (`gpt-4o-mini`, JSON mode) decoder. One clause → N rule objects, each with a **verbatim quote anchor** (cite-or-refuse) and a `relevance` class. **Keeps only `relevance='development'`** (drops administration / enforcement / definition noise — Local Government Act audit/fee/delegation provisions a draftsperson never checks against). Idempotent per `(clause_id, extractor_model)`.
2. `scripts/wp6_promote_decode.py --apply` — promotes development decode candidates → approved, cited, advisory `rules`, carrying `check_type/evaluable/rule_logic_json`. Idempotent (`rule.id == candidate.id`).
3. `src/draftcheck/checks/engine.py` step 7 — `_get_advisory_rules()` surfaces applicable non-numeric rules (filtered by `council_scope`/`r_codes`, capped 80) as advisory `CheckResultItem`s carrying `what_it_means` + `how_to_query` + citation. **Never a false pass/fail:** `ai_judgement` → `needs_assessment`, presence/categorical/conditional unconfirmed → `needs_more_info`.

**Verified end-to-end (Beeliar, partial corpus).** A single compliance run returns the 31 numeric checks **plus** ~80 non-numeric advisory rules (`boolean_presence`, `qualitative_performance`, `conditional`, `categorical`), each decoded and cited. Contract pinned in `tests/test_beeliar_canary.py::test_advisory_rules_are_decoded_and_cited`.

**Known gate (operator/legal, not a rebuild bug):** numeric checks can only evaluate against real facts when the restricted Landgate/DPLH spatial datasets (`lgate-*`, `dplh-*`) are moved from `pending_review` → `approved`. Until then address resolution correctly refuses zoning/R-code facts (cite-or-refuse). Approving restricted-licence data is Steven's legal call.

---

## What changed in mental model

| | Before (closed vocab) | After (open vocab) |
|---|---|---|
| LLM input schema | `rule_key: enum[50]` | `rule_key: snake_case string + description` |
| Failure mode | Anything outside the 50 silently dropped at extraction | LLM emits whatever it sees; structural validators catch garbage |
| Canonicalisation | Pre-declared in `vocabulary.py` | Learned by clustering after extraction |
| Check registry | 11 hand-written CheckDefinitions | Derived from clusters with ≥N rules |
| Corpus coverage | ~1.5 atoms / 100 clauses (we built ~750 rules from 28k clauses) | Projected 5–10 atoms / 100 clauses (the LLM stops dropping noise/signage/bushfire/heritage/etc. rules) |

The closed vocab was a bootstrap shortcut; it served its purpose proving the pipeline. The corpus is now well-understood enough that the vocab can come *from* the corpus, not be imposed *on* it.

---

## Work-package dependency graph

```text
WP-A strip closed-vocab gates           ─┐
WP-B extend universal validators        ─┴── WP-C open-vocab extraction sweep
                                                          │
                                              WP-D clustering / canonical-key map
                                                          │
                                              WP-E adversarial review at scale
                                                          │
                                              WP-F CheckDefinition derivation
                                                          │
WP-G spatial enrichment   ──────────────────────────────┐ │
WP-H UX polish (mostly done 2026-06-13)                 │ │
                                                        └─┴── WP-I Beeliar verification gate
```

---

## WP-A — Strip the closed-vocab gates (≈30 min code)

**Goal:** the extractor and validator no longer treat the 50 RULE_KEYS as a hard wall. The set is renamed to a hint and used only as a soft signal.

**Status (2026-06-14):** scaffolding LANDED on main — `RULE_KEYS` is renamed to `RULE_KEY_HINTS` with `is_hinted_key()` in `src/draftcheck/extraction/vocabulary.py`, and `validate_rule_key` now accepts new snake_case keys as a soft signal.

**Files:**
- `src/draftcheck/extraction/vocabulary.py`
  - Rename `RULE_KEYS` → `RULE_KEY_HINTS` (keep the existing 50 keys verbatim — they remain the most likely categories).
  - Add a new module-level helper `is_hinted_key(key: str) -> bool` that returns `True` for the 50 hints, snake_case-normalised.
  - Keep `OPERATORS`, `NORMATIVE_WORDS`, `RULE_TYPES`.
- `src/draftcheck/extraction/validators.py`
  - Remove `validate_rule_key`'s hard fail. Replace with:
    ```python
    def validate_rule_key(rule_key: str) -> ValidatorResult:
        if not rule_key or not re.fullmatch(r"[a-z][a-z0-9_]{2,60}", rule_key):
            return ValidatorResult(passed=False, detail="rule_key must be snake_case 3-60 chars")
        return ValidatorResult(passed=True, detail=f"rule_key {rule_key!r}; hinted={is_hinted_key(rule_key)}")
    ```
  - Keep `validate_quote_anchor`, `validate_normative_language`, `validate_no_orphan_numbers`, `validate_unit_normalization` exactly as they are — they were already universal.
- `scripts/wp6_extract.py`
  - Rewrite `JSON_SCHEMA_TEXT` so `rule_key` is described, not enumerated:
    ```text
    "rule_key": "snake_case noun phrase naming the regulated thing
                 (examples: primary_street_setback, parking_bays_per_dwelling,
                  noise_attenuation_distance, slope_threshold_for_retaining,
                  driveway_gradient_max). New keys allowed — pick the most
                  specific accurate name."
    ```
  - `RANGE_PRIORS` stays for the 50 hinted keys (used as soft sanity); for unknown keys, fall back to unit-category bounds (see WP-B).
  - `vocab_gap_only` helper: keep, but treat it as "hint-gap only" (still useful for telemetry).
- `tests/test_v3_stage3_validators.py`, `tests/test_wp6_*` — update assertions that expected hard rule_key rejection.

**Gate:** `pytest tests/test_v3_stage3_validators.py tests/test_wp6_*.py -q` green; `ruff check` green.

---

## WP-B — Universal structural validators (≈45 min code)

**Goal:** validators no longer need to know about the rule_key at all. Every promotable atom must clear quote anchor, no-orphan-numbers, normative language, operator/unit canonical, value finite, and unit-category sanity.

**Status (2026-06-14):** scaffolding LANDED on main — `validate_value_finite` and `validate_unit_category_sanity` are implemented in `src/draftcheck/extraction/validators.py`.

**Files:**
- `src/draftcheck/extraction/normalize.py`
  - Extend `_UNIT_ALIASES` with: `mm`, `cm`, `km`, `ha`, `m²` → `m2`, `sq m`, `sq.m`, `metres squared`, `°`, `degrees`, `db`, `dB`, `decibels`, `lx`, `lux`, `count`, `bays`, `dwellings`, `ratio`, `per dwelling`.
  - Add a unit→category map: `{m, mm, cm, km}→length`, `{m2, ha}→area`, `{%}→percent`, `{storeys}→count_storeys`, `{}→count`, etc.
- `src/draftcheck/extraction/validators.py`
  - Add `validate_value_finite(value) -> ValidatorResult`: reject NaN, inf, value > 1e6.
  - Add `validate_unit_category_sanity(value, unit_category) -> ValidatorResult` with hard bounds: length ≤ 1000m, percent 0–100, count_storeys 1–60, count ≤ 1000, area ≤ 1e6.
  - `run_all_validators` now returns the new pair plus the existing five.
- `scripts/wp6_extract.py`
  - In `validate_atom`, after the existing structural checks, run the new unit-category sanity using the unit→category map; demote `range_prior` to a soft "score" (used for confidence weighting, not as a hard gate) when the rule_key is not in `RULE_KEY_HINTS`.

**Gate:** all unit tests green. Manually exercise on a known-good atom and a known-bad atom (orphan number) — pass and fail respectively. Add `tests/test_v3_stage3_validators.py::test_unit_category_sanity` and `::test_value_finite_rejects_infinity`.

---

## WP-C — Open-vocab extraction sweep (≈45 min run, $40–120 spend)

**Goal:** re-extract over the *full* clause corpus with the new schema. Two-family ensemble (Sonnet via Workflow subagents + OpenAI via existing `wp6_extract.py` on the VPS). MiniMax stays parked until its `402` clears.

**Inputs:**
- All clauses with `disposition='rule_bearing'` AND no candidate yet whose `metadata_json->>'open_vocab'='true'`. Estimate ~28k clauses on first run.

**Files:**
- `scripts/wp6_extract.py`: stays the canonical OpenAI extractor; the schema change in WP-A is enough.
- `.claude/.../workflows/scripts/wp6-open-build.py`: new script that takes a chunk of clauses and emits a Workflow JS that runs Sonnet with the open-vocab schema (no `enum`, just snake_case regex pattern and an example list in the prompt).
- `data/extraction/open_vocab/clauses_*.jsonl`: 14 chunks of ~2000 clauses each (size shape from today's sweeps).
- `scripts/wp6_sonnet_postprocess.py`: drop the `RANGE_PRIORS` hard gate; pass-through any unit-category-sane atom. Add `metadata_json.open_vocab=true` on every candidate it writes.

**Run plan:**
1. Dump corpus to JSONL.
2. Launch 14 Workflow chunks for Sonnet — pace 3 at a time to avoid Anthropic rate-limit walls.
3. In parallel, kick off `wp6_extract.py` (OpenAI ensemble) on the VPS over the same source_versions.
4. Postprocess and write rule_candidates with the open `rule_key` strings preserved.

**Gate:** `reports/wp6_open_extract.json` exists with `total_atoms >= 3 × prior_count` (we were at 1655 candidate rows in the closed run → expect ≥5000 in the open run). If less than 3× growth, investigate prompt/schema before clustering — likely an over-restrictive validator.

---

## WP-D — Clustering / canonical-key map (≈45 min)

**Goal:** every raw `rule_key` string in the candidate pool maps to a canonical key. Equivalent variants collapse. Long-tail one-offs survive as their own clusters until enough rules accumulate.

**Status (2026-06-14):** scaffolding LANDED on main — `scripts/wp6_cluster_keys.py` and `scripts/wp6_apply_clustering.py` exist, and migration `0018_rule_canonical_keys` adds the `canonical_rule_key` columns on both tables.

**Files:**
- `scripts/wp6_cluster_keys.py` (new).
  - Pull all distinct `rule_key` strings + their candidate counts + sample quotes.
  - Normalise: lowercase, snake_case, strip plural `s`, strip prefixes like `min_`/`max_`/`maximum_`/`minimum_`.
  - Embed normalised strings via `sentence-transformers/all-MiniLM-L6-v2` (already pinned in pyproject).
  - Cluster with HDBSCAN (`min_cluster_size=2`, `min_samples=1`). Unclustered points stay as their own canonical key (singleton cluster).
  - For each cluster, the canonical key is the most frequent raw variant (tiebreaker: shortest).
  - Write `reports/key_clusters.json`: `[{canonical, members, total_rules, sample_quotes}]`.
  - Write `data/extraction/key_canonical_map.csv`: `raw,canonical`.
- DB migration `0018_rule_canonical_keys`: add `rules.canonical_rule_key` and `rule_candidates.canonical_rule_key` columns (nullable for compatibility, fill via UPDATE).
- `scripts/wp6_apply_clustering.py` (new): bulk UPDATE both tables from the CSV.

**Gate:** every candidate has a non-null `canonical_rule_key`. Top-20 clusters reviewed (by hand or by spot-prompt) for "would a drafts person see this as one category?" — if any cluster mis-groups (e.g. `primary_street_setback` and `parking_bay_setback` merging), tighten the clustering threshold and re-run. Idempotent.

---

## WP-E — Adversarial review at scale (≈45 min run, $30–70 spend)

**Goal:** Sonnet adversarial pass over every newly-extracted candidate using the workflow + apply script we built 2026-06-13.

**Files:**
- `scripts/wp6_apply_adv_review.py` — unchanged from 2026-06-13.
- `.claude/.../workflows/scripts/wp6-adv-build.py` — point at the new open-vocab candidate dump instead of the closed-vocab rules dump.

**Run plan:**
1. Dump `rule_candidates` filtered to `metadata_json->>'open_vocab'='true'` AND `review_status='validators_passed'`. Batch 4 per agent, ~10 chunks.
2. Launch Sonnet workflow in 3-at-a-time waves.
3. Aggregate verdicts.
4. Apply (idempotent — rejects move to `lifecycle_status='rejected'`; condition_missed and correct_* update `condition_json`; missed_exceptions insert as `rule_type='exception'` with `legal_edges` `exception_to`).

**Gate:** `reports/wp6_apply_adv_review.json` shows considered ≥ 80% of validators_passed pool; rejected_rate between 30–60% (similar to today's 57%). Anything outside that range = investigate before promoting.

**WP-E follow-up — lot-area operator curation (DONE 2026-06-15).** The open-vocab
`site_area` cluster mixed R-Codes Table-1 minimum/average lot-size rows with the wrong
extracted operator (`eq`/`gt` where the table means "at least"), so `site_area` was held
at needs_more_info (its `lot_area_m2` override removed). Fixed by
`scripts/wp6_curate_lot_area_operators.py` (quote-driven, idempotent, audited): flips ONLY
minimum/table rows to `gte` (45 in prod: site_area 30 eq + 4 gt, min_lot_area_per_dwelling
5, average_lot_size 6), leaving maxima / applicability filters / ranges / noise untouched.
`("site_area", ("lot_area_m2",))` re-added to `FACT_KEY_OVERRIDES`; registry regenerated.
Verified with `scripts/verify_lot_area_synth.py` (parcel-inject harness): 708 m² @ R20 →
`likely_pass` 450; 300 m² @ R20 → `likely_fail` 450. Open follow-up: deterministic
clustering still orphans 76% of approved rules (3827 singletons) — embedding clustering
(below) is the next lever, but any re-cluster must re-run this curation on merged clusters.

---

## WP-F — CheckDefinition derivation (≈45 min)

**Goal:** the compliance engine's check registry is rebuilt from data, not from the original 2026-06-10 hand-list.

**Files:**
- `scripts/wp6_register_checks_from_clusters.py` (new).
  - For each cluster in `reports/key_clusters.json` with `total_approved_rules >= MIN_RULES_FOR_CHECK` (start at 5).
  - Generate a `CheckDefinition` dict with:
    - `key` = canonical_rule_key
    - `name` = human-readable (title-cased canonical, replace `_` with space)
    - `tier` = TIER1 if cluster size ≥ 20, else TIER2
    - `category` = derived from a small mapping (front/rear/side → SETBACK, height/storeys/wall → HEIGHT, cover/space/area → SITE, etc. — keep this table small and editable in `src/draftcheck/checks/category_map.py`)
    - `fact_keys` = tuple guessed from the cluster's most common unit category (e.g. `("proposed_{canonical}_m",)` for length, `("proposed_{canonical}_pct", "site_area_m2")` for percent)
    - `rule_key_pattern` = the canonical_rule_key (literal)
    - `unit` = the cluster's dominant unit
    - `description` = a short auto-template citing the most-cited source for that cluster
  - Write `src/draftcheck/checks/registry_generated.py` (one big literal).
  - Refactor `src/draftcheck/checks/registry.py` to `from .registry_generated import TIER1_CHECKS, TIER2_CHECKS, ALL_CHECKS, CHECK_BY_KEY` — keep the public surface.
- `src/draftcheck/checks/engine.py` — replace `for check_def in TIER1_CHECKS` with a loop driven by `canonical_rule_key` so the engine sees the new keys.
- A test that pins the generated registry to a known checksum so accidental drift is caught.

**Gate:** `len(TIER1_CHECKS) + len(TIER2_CHECKS) >= 25`. Engine smoke test against the existing golden fixture green. Spot-check 5 random new checks: do they have a sensible `fact_keys` triple? If not, manually fix the `category_map.py`.

---

## WP-G — Spatial enrichment (≈30 min SQL + 60 min code)

**Goal:** every G-NAF address resolves cleanly to parcel + zone + R-code without the user supplying anything.

**Steps:**
1. **Backfill parcel link:**
   ```sql
   UPDATE address_points ap
   SET parcel_id = p.id, updated_at = now()
   FROM parcels p
   WHERE ap.parcel_id IS NULL AND ST_Contains(p.geom, ap.geom);
   ```
   Run on VPS, report counts.
2. **R-code stamping** on `planning_features`:
   - `scripts/spatial_stamp_rcodes.py` (new): for every `planning_features` row with `layer_type='zone'`, parse `label`/`code` for an `R\d+` token (also `RR`, `R-AC*`); write `metadata_json.r_code` and `metadata_json.density_code`.
3. **Auto-synth PropertyFact on project create:**
   - `src/draftcheck/api/projects.py` create endpoint: after a project is bound to an address, call a new `domain/spatial/synth_facts.py` that writes `PropertyFact` rows for `lot_area_m2`, `lot_width_m`, `lot_depth_m`, `r_code`, `zone_name`, `lga_name`, `bushfire_overlay`, `heritage_overlay`, `bal_rating_if_known`. All marked `method='spatial_derived'`, `review_status='confirmed'`.

**Gate:** `1 BLACK SWAN RISE BEELIAR` (test address used 2026-06-13 — "3" not in G-NAF) shows non-null `parcel_id`, non-null `r_code` on its zone, and 6+ auto-synth'd PropertyFacts on a fresh project. Existing `test_golden_e2e.py` still green.

---

## WP-H — UX polish (≈30 min — mostly done 2026-06-13)

**Status:** the alarmist-disclaimer/upload-prompt redesign shipped this turn ([fdd2d4a](https://github.com/stevenshelley58-afk/cuz.fail/commit/fdd2d4a)). What remains:
- Show category groupings in the compliance panel (Boundary setbacks / Building envelope / Site & landscape / Garages & parking / Walls & fences / Lot shape) once the engine returns >11 categories — currently flat list.
- "Why this check applies" tooltip pulled from the cluster's sample quotes.
- Empty-state for a check category with no rule in the user's scope: "No Cockburn rule found for X; falling back to global." (Today silently absent.)

**Gate:** mobile-narrow viewport (375px) the panel reads cleanly. No "needs more info" banner unless no measurements are available.

---

## WP-I — Beeliar verification (end-to-end gate)

**Goal:** typing `3 Black Swan Rise Beeliar` (or the proxy `1 BLACK SWAN RISE BEELIAR` if "3" still missing from G-NAF) into the app returns a real result set, not warnings.

**Acceptance criteria:**
1. Address resolves to `COCKBURN, CITY OF` + `RR20`.
2. Project create writes ≥6 synth'd PropertyFacts.
3. Compliance run returns:
   - ≥25 check categories evaluated (was 11).
   - ≥10 with status `likely_pass` or `likely_fail` (driven by the auto-synth'd facts — lot area, frontage, etc.).
   - The rest grouped under one blue "Upload drawing to fill in the remaining N measurements" prompt — not as N yellow banners.
4. Every result carries a citation back to the source clause.
5. The advisory line is the small grey footnote, not a yellow alert.

**Gate:** an `evals/seeds/beeliar_canary.json` fixture is added with these counts pinned, and CI runs it on every push.

---

## Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Sonnet rate-limits during the big sweep | High | Already saw 65/188 batches throttled today. Stagger launches, smaller chunks (3-clause batches), backoff. |
| Clustering merges unrelated rule_keys | Medium | Top-20 clusters spot-checked before applying; threshold tunable; idempotent re-run. |
| Engine derivation guesses wrong `fact_keys` | Medium | Generated registry is reviewable; manually adjust `category_map.py` for outliers. |
| Spatial stamping introduces wrong R-codes | Low | The label parse is regex; if no match, leave `r_code` null. Tests cover the match patterns. |
| Adversarial review false-negatives | Medium | Same 30–60% rejection range we hit today is the smell test; outside the band = re-prompt. |

---

## Order of execution (recommended)

1. **WP-A + WP-B** (code only, ~75 min, green CI) — these are free; no downside.
2. **WP-G step 1 (parcel backfill SQL)** — runs in seconds, unlocks everything else.
3. **WP-C open-vocab sweep** — biggest item; budget $40–120. Run while spatial work continues.
4. **WP-D clustering** — depends on WP-C output.
5. **WP-E adversarial review** — depends on WP-D.
6. **WP-F engine derivation** — depends on WP-E.
7. **WP-G step 2 + 3 (R-code + synth facts)** — code changes that can land any time after WP-A.
8. **WP-H UX polish** — landing-pages-light; can ship any time.
9. **WP-I Beeliar verification** — the final gate.

Standing rules apply (Alembic only, idempotent jobs, reports under `reports/`, every approve/override to `audit_events`).
