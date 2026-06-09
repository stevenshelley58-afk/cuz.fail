# DraftCheck WA — Stage 3 Build Spec: Rule Extraction (All-AI)

Date: 2026-06-09  
Authority: `docs/MASTER_REBUILD_PLAN.md` §5.4/§7/§9 Phase 3 · `docs/RULES_EXTRACTION_PIPELINE.md`  
Format model: `docs/MULTI_AGENT_BUILD_PLAN.md`  
Status: **implementation authority for Stage 3**

Supersedes as implementation authority for Stage 3 only: earlier Codex/PR6 descriptions of the
legal/extraction wave. The main MASTER_REBUILD_PLAN.md invariants (§12) are unchanged.

---

## 0. Why this stage bites hardest

Every other stage has a human backstop. Stage 3 has none. The pipeline turns approved regulatory
text into `resolved_rules` that drive compliance verdicts — and it does so without a human
promoting each rule. Automated validators and an eval-case gate are the complete quality bar.

That means the gate must be **exhaustive**, not advisory. A candidate that passes every validator
and every eval case becomes `auto_accepted` and enters the engine. A candidate that fails any check
stays in `pending_review` and surfaces a `review_item`. There is no middle path.

The risk the gate must block:
- A hallucinated value that happens to pass string-match quote anchoring.
- A normative "must" quietly re-classified as informational.
- An orphan number in the source that was never extracted.
- An exception clause that becomes a blob instead of a linkable `rule_type=exception` row.
- A rule extracted from a superseded source version.
- Any candidate produced by an LLM call that was not traced and spend-capped.

---

## 1. Baseline — what already exists

The build session **must not reinvent** any of the following. It extends or implements them.

### 1.1 Tables (already migrated in `0002_v3_complete_target_schema`)

| Table | State | Notes |
|---|---|---|
| `clauses` | Populated from Phase 1 | `disposition` column exists; `clause_key`, `text`, `quote` columns present |
| `source_versions` | Populated from Phase 1 | currency audit from Session A available; `licence_status`, `review_status` |
| `rule_candidates` | Empty | All structural columns present: `quote`, `clause_id`, `source_version_id`, `skill_version_id`, `prompt_hash`, `rule_type`, `pathway`, `review_status`, `confidence` |
| `rules` | Empty | `lifecycle_status ∈ {candidate, pending_review, auto_accepted, approved, rejected, stale, superseded}` |
| `rule_clause_links` | Empty | `link_type`, `quote`, `confidence` present |
| `legal_edges` | Empty | `from_type/from_ref/to_type/to_ref/relation/evidence_quote/review_status` present |
| `skill_versions` | Empty | `skill_name`, `version`, `content_hash`, `status`, `manifest_json` |
| `eval_cases` | Empty | `suite_name`, `case_key`, `skill_name`, `input_json`, `expected_json` |
| `eval_runs` | Empty | `eval_case_id`, `skill_version_id`, `score`, `output_json`, `metrics_json` |
| `job_traces` | Populated from Phase 1 `/ask` | Spend-cap infrastructure already active |
| `spend_events` | Populated from Phase 1 | Daily budget already tracked |
| `review_items` | Populated | Surface for gate failures |
| `audit_events` | Populated | Every state transition must write one |

### 1.2 Substrate (`src/draftcheck/ai/substrate.py`)

Fully implemented. `LocalDeterministicModelAdapter` with `SpendCaps`, `CircuitBreaker`,
`InMemoryJobTraceStore`. The real provider adapter wires `job_traces` DB rows; Stage 3 calls
**must** use it. No LLM call outside the adapter. No exceptions.

### 1.3 Skills scaffold (to be created in Wave 1)

`skills/extract_rules/` and `skills/classify_clauses/` do not yet exist. The Fixtures Owner
creates the directory + SKILL.md + schema.json + `examples/` stubs in Wave 1. The
Legal/Extraction agent fills the examples.

### 1.4 Extraction module (to be created by Validators/Eval Gate agent)

`src/draftcheck/extraction/` does not yet exist. Target files after Stage 3:

```text
src/draftcheck/extraction/
    validators.py     quote-anchor + normative-lang + no-orphan + unit-norm + carve-out checks
    vocabulary.py     closed rule_key vocab, closed conditions vocab (§6 of RULES_EXTRACTION_PIPELINE.md)
    normalize.py      unit normalization (mm→m, etc.) with original preserved
```

### 1.5 Session B eval seeds

The `tests/fixtures/golden/` tree already has the M1 canary golden fixture (address resolution,
property facts, proposals, document facts, expected compliance). The Fixtures Owner **adopts**
these as the cross-check corpus: if a Stage 3 rule extraction contradicts a canary expectation,
that is a gate failure.

The legacy DB harvest (JSONL files from `draftcheck.db`) provides additional eval seeds. Session
A's currency audit identifies which `source_versions` are current — only those may seed `eval_cases`.
The "5 fixture rules" referenced in the roster are the five Tier-1 check keys
(`site_cover`, `primary_street_setback`, `open_space`, `garage_dominance`,
`boundary_wall_length`) extracted from the demo R-Codes extract source version
(`sv_artificial_demo_rcodes_extract_2026_v1`). These must be present as `eval_cases` before any
live extraction run executes.

---

## 2. The all-AI promotion gate (core contract)

### 2.1 Lifecycle transitions

```text
clause (rule_bearing disposition)
  → rule_candidates (review_status = pending_review)  [extractor writes]
       │
       ├─ any validator FAIL → review_status = validator_failed
       │                        + review_items row created
       │                        STOP — never promotes
       │
       ├─ all validators PASS → validator_results_json updated, review_status = validators_passed
       │
       └─ eval gate RUN
              │
              ├─ any eval_case FAIL → review_status = eval_failed
              │                        + review_items row created
              │                        STOP — never promotes
              │
              └─ all eval_cases PASS → rules INSERT (lifecycle_status = auto_accepted)
                                        review_status = auto_promoted
                                        auto_promoted_at = now()
```

### 2.2 What "auto_accepted" means (V3 §7 preserved)

`auto_accepted` is a legitimate engine-consumable status. The engine reads rules with
`lifecycle_status IN ('auto_accepted', 'approved')` and `source_version_id` not superseded.
It does NOT require `approved`. `approved` remains a human-only status that can only be set
by a `reviewer`-role user via the review API. Stage 3 never touches `approved`.

The invariant from V3 §7 — "Hermes may never write `rules.lifecycle_status = approved`" — is
preserved. The automated pipeline writes `auto_accepted`. Human reviewers may later elevate to
`approved` or demote to `rejected`; both changes write `audit_events` rows.

### 2.3 Candidate grouping

Three independent extraction passes over the same clause write three `rule_candidates` rows.
They are grouped by `extraction_group_id` (new column, §3). The adjudication logic runs after
all three passes for a group are `validators_passed`:

| Agreement | Action |
|---|---|
| 3/3 exact `(rule_key, operator, value_json, unit, condition_json)` | Auto-promote the first (confidence = 0.95) |
| 2/3 agree | Challenge round: dissenting candidate gets a new extraction pass with its peers visible; concede OR hold-with-quote; concede → auto-promote at 0.85; hold → `pending_review` (human) |
| No 2-way agreement | All three marked `pending_review`; single `review_items` row |

"Exact" means normalized value equality after unit normalization. Quote may differ; the promoted
candidate's quote is used.

### 2.4 What the gate cannot be bypassed by

- A `rule` row may not be inserted directly. The only insertion path is auto-promotion from a
  `rule_candidate` that has passed all validators and the eval gate.
- The API route `POST /rules` does not exist. Candidate promotion is a job, not an API endpoint.
  The only human-write routes for rules are `POST /rules/candidates/{id}/review` (set to
  `pending_review` or `rejected`) and `POST /rules/{id}/review` (set to `approved` or
  `rejected`).
- A `rule_candidate` with `validator_results_json` showing any failure may not be promoted by
  any code path. This is enforced in the promotion service function, not just the job.

---

## 3. Schema delta

Migration: `0003_v3_stage3_extraction_schema`  
Owner: Schema Integrator only.

### 3.1 `rule_candidates` — new columns

| Column | Type | Default | Purpose |
|---|---|---|---|
| `extraction_group_id` | `UUID` nullable | NULL | Groups 3 independent passes for the same clause + job |
| `extraction_pass` | `smallint` nullable | NULL | Ordinal: 1, 2, or 3 |
| `quote_char_start` | `integer` nullable | NULL | Char offset into `clauses.text` (whitespace-normalised) |
| `quote_char_end` | `integer` nullable | NULL | Char offset end |
| `validator_results_json` | `JSONB` not null | `{}` | Per-validator name → `{pass: bool, detail: str}` |
| `auto_promoted_at` | `timestamptz` nullable | NULL | Set when this candidate becomes a rule |

Index: `ix_rule_candidates_group` on `(extraction_group_id, extraction_pass)`.

### 3.2 `clauses` — new column

| Column | Type | Default | Purpose |
|---|---|---|---|
| `classification_skill_version_id` | `string(160)` nullable, FK `skill_versions.id` | NULL | Records which skill version classified the disposition |

Index: `ix_clauses_classification_skill` on `(classification_skill_version_id)`.

### 3.3 No other table changes

All other needed tables (`rules`, `legal_edges`, `skill_versions`, `eval_cases`, `eval_runs`)
are complete as of migration `0002`. If a build agent believes it needs additional columns,
it must raise a schema change request to the Schema Integrator — never edit `models.py` directly.

---

## 4. Agent roster

| Agent | Write scope | Responsibility | Wave |
|---|---|---|---|
| **Schema Integrator** | `src/draftcheck/db/models.py`, `db/alembic/versions/0003_*` | Adds §3 delta columns; forward migration only (downgrade stubs acceptable) | 1 |
| **Fixtures Owner** | `skills/extract_rules/`, `skills/classify_clauses/`, `data/fixtures/stage3/`, `tests/fixtures/stage3/` | Skill scaffold (SKILL.md + schema.json + examples/); seeds `eval_cases` from legacy harvest JSONL + 5 Tier-1 fixture rules; ensures canary consistency with `tests/fixtures/golden/` | 1 |
| **Legal/Extraction** | `src/draftcheck/domain/rules/`, `src/draftcheck/jobs/extraction.py`, `src/draftcheck/api/rules.py`, `skills/extract_rules/examples/`, `skills/classify_clauses/examples/` | Clause parser → classify_clauses skill; 3-pass extraction orchestration; multi-pass Procrastinate jobs; adjudication logic; carve-out detection → `rule_type=exception` rows + `legal_edges`; all calls through substrate | 2 |
| **Validators/Eval Gate** | `src/draftcheck/extraction/validators.py`, `src/draftcheck/extraction/vocabulary.py`, `src/draftcheck/extraction/normalize.py`, `src/draftcheck/domain/rules/gate.py` | Quote-anchor validator; normative-language validator; no-orphan-numbers sweep; unit-normalisation validator; carve-out validator; eval-case gate runner; `review_items` creation on failure; auto-promotion path | 2 |
| **Frontend** | `web/src/` (rules inspection screens only) | Rules inspection view: rule + quote + clause + source version + validator status. No approve button. Read-only. Routes: `/sources/:id/rules`, `/rules/:id`, `/rules/candidates/:id` | 3 |
| **Reviewers ×2** | read-only | Spec Reviewer: diffs PR against §2/§7/§9 of MASTER_REBUILD_PLAN.md + acceptance list (§10 below). Quality Reviewer: runs gates; adversarial greps; confirms no approve button, no direct rule INSERT, every call traced. Per-PR, both must pass before merge. | per merge |
| **Red-team** | read-only + test harness | Attempts (a) promoting a rule_candidate that fails quote-anchoring, (b) extracting a rule from a superseded source version, (c) eliciting a `auto_accepted` rule whose quote does not appear verbatim in the clause text, (d) bypassing the eval gate. Reports findings; any successful bypass is a blocker. | Wave 3 |

**Substrate is reuse, not an agent.** `ai/substrate.py` is already built. Every extraction call
goes through it. No agent touches `src/draftcheck/ai/`.

---

## 5. Waves and dependency graph

```text
W1  Schema Integrator (migration 0003)
    ||  Fixtures Owner (skill scaffolds + eval seeds)
    [BARRIER — W2 cannot start until both W1 agents merge]

W2  Legal/Extraction agent
    ||  Validators/Eval Gate agent
    [Both develop concurrently against W1 outputs.
     Interface contract: see §5.1 below.
     Both reviewed before W3 starts.]

W3  Frontend (inspection screens)
    ||  Red-team (attacks the W2 merged gate)
    [Frontend needs rule/candidate read endpoints from W2.
     Red-team needs the full promotion path from W2.]

W4  Final integration: run golden-fixture eval suite end-to-end.
    Phase 3 exit acceptance list (§10) verified.
```

### 5.1 Interface contract between W2 agents

The Legal/Extraction and Validators/Eval Gate agents share one interface and must agree on it
before either writes implementation. The contract:

```python
# src/draftcheck/domain/rules/gate.py (written by Validators/Eval Gate)

def run_validators(candidate: RuleCandidate, clause: Clause) -> ValidatorResults:
    """Returns dict of validator_name -> {pass: bool, detail: str}.
    Does NOT write to DB. Caller (extraction job) writes the results.
    Raises nothing — failures are expressed as result entries."""
    ...

def eval_gate_pass(candidate_id: UUID, skill_version_id: str, session: Session) -> bool:
    """Runs all active eval_cases for the candidate's skill_name against candidate's output.
    Writes eval_runs rows. Returns True iff all cases pass (score >= threshold).
    Called by extraction job only after all validators pass."""
    ...

def auto_promote(candidate_id: UUID, session: Session) -> Rule:
    """Inserts a rules row with lifecycle_status=auto_accepted and sets candidate
    auto_promoted_at. Writes audit_events. Called only when both gates green.
    Raises PromotionBlockedError if any validator failed or eval gate not yet run."""
    ...
```

Neither agent may change this interface after W1 review; if a change is needed,
both agents must coordinate through the Coordinator.

### 5.2 Hard edges

```text
W2 Legal/Extraction ← W1 Schema Integrator (migration 0003 must be merged first)
W2 Legal/Extraction ← W1 Fixtures Owner (skill_versions rows must exist for extraction jobs)
W2 Validators/Eval Gate ← W1 Fixtures Owner (eval_cases must be seeded before gate can run)
W3 Frontend ← W2 merged (read endpoints must exist)
W3 Red-team ← W2 merged (full promotion path must be live)
W4 ← W3 (all agents merged)
```

---

## 6. Worker invariants (every Stage 3 agent, verbatim)

```text
Authority: docs/MASTER_REBUILD_PLAN.md (V3) + docs/STAGE_3_BUILD.md.
Write scope: only the paths listed in your §4 row. Schema changes → Schema Integrator spec,
  never edit models.py yourself.
Single-writer files you must NOT touch: pyproject.toml, uv.lock, models.py (except Schema
  Integrator), alembic/ (except Schema Integrator), infra/compose.yml, Caddyfile, CI
  workflows, AGENTS.md, src/draftcheck/ai/substrate.py, tests/fixtures/golden/ (canary).

All-AI invariants (§2):
  - A rule_candidate becomes a rule ONLY via auto_promote(), ONLY after all validators pass AND
    eval gate returns True. No other promotion path exists or may be created.
  - lifecycle_status=approved is set only by a reviewer-role human via the review API. Stage 3
    code never touches it.
  - No approve button, no manual-promote route, no bypass flag, no fallback silent promotion.
  - The frontend inspection view is read-only. It shows validator status. There is no action
    button that changes lifecycle state.

Extraction invariants:
  - Every extraction call uses src/draftcheck/ai/substrate.py. No direct SDK/HTTP calls.
  - Every extraction call provides skill_version_id and job_id. No untraceable calls.
  - quote must appear verbatim in clauses.text after whitespace normalisation. Candidates that
    fail quote-anchor are discarded before any DB write of validator_results_json.
  - Carve-outs/exceptions are rows (rule_type=exception) with their own quote + clause_id +
    legal_edges rows. They are never stored as JSON blobs on a requirement rule.
  - Extractors must use the closed rule_key vocabulary from extraction/vocabulary.py.
    Unrecognised patterns must produce {"cannot_structure": true, "reason": "..."} — never a
    made-up rule_key.
  - A normative clause (contains "must", "shall", "is not to exceed", "minimum", "maximum",
    "required", "prohibited") may not have disposition=informational. Any such classification
    is a validator failure and creates a review_item.
  - No orphan number: every numeric token in a rule-bearing clause must appear in at least one
    candidate's quote, or be explicitly classified as non-normative (date, clause reference,
    page number, worked example, document ID). Unclaimed numbers → validator failure.
  - No rule may reference a source_version with licence_status != 'approved' or
    review_status != 'approved'. Session A's currency audit is the authority.
  - unit normalization: mm→m, cm→m, m²→m2, %→pct, count→count. Original preserved in quote.
    Out-of-range values for a rule_key (vocabulary.py has priors) → review_item, never discard.

Safety invariants (V3 §12 — reproduced for completeness):
  - Never claim final legal/planning/building/certification compliance.
  - LLMs extract and classify — never decide compliance verdicts.
  - No likely_pass/likely_fail without approved rule + promoted measurement + citation + trace.
  - Alembic is the only schema authority; create_all never ships.
  - All legal values in examples are illustrative. Hardcoding a real regulatory value is a defect.

Done = code + tests (extraction job, each validator, gate runner, frontend routes) + handoff note
(what changed, contracts touched, V3 sections satisfied, any deferred items).
Tests failing or scope exceeded = not done; say so plainly.
```

---

## 7. Automated gate specification (full detail)

### 7.1 Quote-anchor validator (HARD — discard before DB write)

This validator runs *before* any DB write. A candidate whose quote fails quote-anchor is
discarded entirely — no `rule_candidates` row, no trace in `validator_results_json`.

Algorithm:
1. Normalise both the quote and `clauses.text`: collapse runs of whitespace to single space,
   strip leading/trailing whitespace from each.
2. Check `normalized_quote in normalized_clause_text`.
3. If found: record `quote_char_start` and `quote_char_end` as the char offsets in the
   **normalised** text.
4. If not found: discard. The extraction job emits a `DEBUG` log entry:
   `quote_anchor_failed clause_id={} pass={} job_id={}`. No DB write.

The LLM's self-confidence is not consulted. The check is deterministic.

### 7.2 Normative-language validator

Runs after quote-anchor passes (candidate now has a DB row).

Normative trigger words:
```python
NORMATIVE_TRIGGERS = {
    "must", "shall", "is not to exceed", "is not to be less than",
    "minimum", "maximum", "required", "prohibited", "not permitted",
    "is to be", "are to be", "must not", "shall not",
}
```

Algorithm:
1. Check if any trigger word appears in `clause.text` (case-insensitive).
2. If a trigger is present AND `clause.disposition == 'informational'`: FAIL.
3. If a trigger is present AND the candidate's `rule_key` is absent (abstained): WARN only
   (candidate remains `validators_passed` but the warning is recorded in
   `validator_results_json["normative_language"]["detail"]`).
4. If a trigger is present AND `rule_key` is set AND `rule_type` is set appropriately: PASS.

A normative clause classified as informational is a gate blocker. It creates a `review_items`
row with `reason="normative_language_classified_informational"` and `subject_type="clause"`.

### 7.3 No-orphan-numbers sweep

Runs once per source document (not per candidate), as a prerequisite for the source document
reaching `auto_accepted` status. Runs after all extraction passes for the document complete.

Algorithm:
1. Regex-extract every numeric token from each `rule_bearing` clause's text:
   `pattern = r'\b\d+(?:\.\d+)?(?:\s*m²?|%|mm|cm|m2|ha|hrs?)?\b'`
2. For each numeric token: check if it appears inside any `rule_candidate.quote` for this
   clause (using the already-normalised quote).
3. If a number is not claimed by any candidate AND has not been manually classified as
   non-normative (date: `\b(19|20)\d{2}\b`, clause ref: `\bclause\s+\d`, page ref,
   worked-example tag): create a `review_items` row with
   `reason="unclaimed_numeric_in_rule_bearing_clause"`, `subject_type="clause"`,
   `subject_id=clause.id`.
4. The source document's `source_versions.review_status` cannot reach `approved` while any
   such review item remains open.

### 7.4 Unit-normalization validator

Runs in-flight during extraction (before DB write), verifies after write.

Algorithm:
1. Parse `rule_candidate.unit` against the normalised unit table in `normalize.py`.
2. If unit is recognised and normalisable: write the normalised value to `value_json.value`
   and `value_json.original_value` (the pre-normalisation version).
3. If unit is unrecognised: FAIL. candidate stays in `pending_review`.
4. If value is out of range for the rule_key (see `vocabulary.py` sanity priors): do NOT
   discard — write a `review_items` row with `reason="value_out_of_range_prior"` AND continue
   to the eval gate. The out-of-range warning does not block promotion, but the review item
   is created so a human can inspect. (This policy preserves unusual-but-valid rules.)

### 7.5 Carve-out / exception language validator

Runs per clause, triggered by exception language detection.

Trigger phrases:
```python
EXCEPTION_TRIGGERS = {
    "notwithstanding", "despite", "except where", "unless",
    "does not apply", "subject to", "other than", "in lieu of",
}
```

Algorithm:
1. If any trigger appears in `clause.text`:
   a. The clause MUST produce at least one `rule_candidate` with `rule_type="exception"`, OR
   b. Each candidate for this clause must have `carve_out_clause_ids_json` non-empty (referencing
      the exception clause), OR
   c. A `legal_edges` row with `relation="exception_to"` must link this clause to a requirement rule.
2. If none of (a/b/c) is satisfied after all extraction passes complete: create a `review_items` row
   with `reason="exception_language_unhandled"`, `subject_type="clause"`.
3. Exception-type candidates require their own quote (anchored to the exception clause), their
   own `clause_id`, and a `legal_edges` row of the form:
   `(from_type="rule", from_ref=exception_rule.id, to_type="rule", to_ref=requirement_rule.id,
   relation="exception_to", evidence_quote=<verbatim quote>)`.

Exception candidates undergo the same validator pipeline. They are never exempt.

### 7.6 Eval-case gate

Runs after ALL validators pass for a candidate in a group (not before).

Algorithm:
1. Look up `eval_cases` where `skill_name = "extract_rules"` AND `status = "active"`.
2. For each case: run the skill against `case.input_json`, compare output to `case.expected_json`
   using the metric defined in the skill's `schema.json` (`exact_match`, `value_within_tolerance`,
   or `contains_rule_key`).
3. Write one `eval_runs` row per case: `eval_case_id`, `skill_version_id`, `score`,
   `output_json`, `metrics_json`, `status ∈ {pass, fail, error}`.
4. If any `eval_runs.status = fail`: mark the candidate `review_status = eval_failed` and create
   a `review_items` row with `reason="eval_gate_fail"`. Do NOT promote.
5. If all cases pass: proceed to `auto_promote()`.

The eval gate is a **recall gate**, not a quality gate. It verifies that the skill can reproduce
known-correct extractions from the eval corpus. A new skill version that degrades on existing
cases cannot promote candidates.

---

## 8. Extraction pipeline sequence

### 8.1 Clause classification (classify_clauses skill)

Runs once per source document, produces `clauses.disposition` assignments.

Job: `classify_clauses_for_source_version(source_version_id: UUID)`

1. For each `clause` in the source version (ordered by `clause_path`):
   a. Call `classify_clauses` skill via the substrate adapter (traced, spend-capped).
   b. Skill output: `disposition ∈ {rule_bearing, definition, procedural, informational,
      manual_review}` + `classification_reasoning` (for debug only, never stored).
   c. Write `clause.disposition` and `clause.classification_skill_version_id`.
2. A second independent pass with a different model configuration re-classifies each clause.
   Disagreement on any `rule_bearing` → `manual_review` disposition → `review_items` row.
3. No clause may have `disposition = NULL` after this job. Any NULL is a pipeline bug,
   surfaced by the nightly canary query:
   ```sql
   SELECT id FROM clauses WHERE source_version_id = :sv AND disposition IS NULL;
   ```

### 8.2 Multi-pass extraction (extract_rules skill)

Job: `extract_rules_for_clause(clause_id: UUID, group_id: UUID, pass_ordinal: int)`

Runs three times per `rule_bearing` clause (pass_ordinal 1, 2, 3). The three job invocations
share `group_id`; they are enqueued together but run independently. No pass sees another's output.

Per pass:
1. Call `extract_rules` skill via the substrate adapter.
2. Skill output schema (per SKILL.md):
   ```json
   {
     "rules": [
       {
         "rule_key": "...",
         "rule_type": "requirement|exception|definition|procedural_gate",
         "pathway": "deemed_to_comply|design_principle|none",
         "operator": "min|max|eq|range|boolean|trigger",
         "value": <number|bool|null>,
         "value_high": <number|null>,
         "unit": "...",
         "conditions": [{"key": "...", "op": "...", "value": "..."}],
         "quote": "...",
         "exception_language_present": true|false,
         "carve_out_clause_keys": ["..."]
       }
     ],
     "cannot_structure": false,
     "reason": null
   }
   ```
3. If `cannot_structure = true`: write a single `rule_candidate` row with
   `review_status = cannot_structure`. Do not run validators. Create `review_items`.
4. For each extracted rule: run quote-anchor validator. Discard if fails.
5. Write `rule_candidate` row with `extraction_pass`, `extraction_group_id`, `skill_version_id`,
   `prompt_hash` (from substrate trace), `extractor_model`.

### 8.3 Adjudication

Job: `adjudicate_extraction_group(group_id: UUID)` — runs after all 3 passes complete.

1. Load all candidates for the group.
2. Group by `(rule_key, operator, normalised_value, unit, normalised_conditions)`.
3. Apply consensus logic from §2.3.
4. Run remaining validators (§7.2–7.5) on each surviving candidate.
5. Run eval gate (§7.6) on each candidate that passes all validators.
6. Auto-promote or create review_items.

### 8.4 Exception and legal-edge wiring

Runs after adjudication for the whole clause set of a source document.

1. For each `auto_accepted` rule with `rule_type = exception`:
   a. Identify the requirement rule(s) it modifies (from `carve_out_clause_keys` mapped to
      `clause_id` → `rule.id`).
   b. Write `legal_edges` row:
      `(from_type="rule", from_ref=exception_rule.id, to_type="rule",
       to_ref=requirement_rule.id, relation="exception_to", evidence_quote=exception_rule.quote,
       review_status="pending_review")`.
2. Legal-edge `review_status` starts at `pending_review` — a reviewer confirms the linkage is
   correct. This is the ONE point where a human reviewer acts in Stage 3: confirming legal
   graph edges. It does NOT block the engine from consuming the rules — it refines the graph.
3. For each `performance_alternative_to` edge (DTC rule → design-principle clause):
   write `legal_edges` with `relation="performance_alternative_to"`.

---

## 9. Merge protocol and red-team

```text
1. Worker develops in its worktree; rebases on main before handoff.
2. CI must be green: ruff, mypy (src/draftcheck/ scope), pytest, alembic upgrade+downgrade,
   import-linter, web build, forbidden-pattern grep (below).
3. Forbidden-pattern grep (must be clean on every Stage 3 PR):
     rg -n "lifecycle_status.*approved" src/draftcheck/domain/rules/ src/draftcheck/jobs/
        (only allowed in gate.py where status = 'auto_accepted', not 'approved')
     rg -n "INSERT.*rules\b" src/ --glob "*.py"
        (only gate.py's auto_promote() may insert into rules)
     rg -n "create_all|dev-login|\.complete\(\)" src/draftcheck/
     rg -n "approve" web/src/
        (no approve button, no approve action in the frontend)
4. Spec Reviewer (fresh context, read-only): PR vs §2/§7/§9 MASTER_REBUILD_PLAN.md + §2/§7/§8
   of this spec. Checks: isolation of write scopes, no schema changes outside Schema Integrator,
   every extraction call traced, gate is the only promotion path, frontend is read-only.
5. Quality Reviewer (fresh context): runs gate locally against the 5 fixture eval cases,
   confirms validators reject known-bad candidates (see test fixtures in §9.1), reviews test
   coverage of each validator branch.
6. Red-team gate (Wave 3): executes the four attack scenarios in §9.2. Any success is a blocker.
   Reports pass/fail per scenario.
7. Coordinator merges in wave order: W1 (Schema Integrator first, then Fixtures Owner),
   W2 (either order after both are reviewed), W3 (Frontend after W2 merged, Red-team alongside),
   W4 integration.
```

### 9.1 Required test fixtures (Validators/Eval Gate agent provides)

`tests/fixtures/stage3/bad_candidates/` — a set of known-bad `rule_candidate` dicts that each
validator must reject:

| File | Validator targeted | Bad property |
|---|---|---|
| `bad_quote_not_in_clause.json` | quote-anchor | quote text absent from clause |
| `bad_quote_partial_overlap.json` | quote-anchor | quote is a substring of a different passage |
| `bad_normative_as_informational.json` | normative-language | clause contains "must"; disposition=informational |
| `bad_unit_unknown.json` | unit-normalization | unit="furlongs" |
| `bad_orphan_number.json` | no-orphan-numbers | clause has "6.5 m" not in any quote |
| `bad_exception_unhandled.json` | carve-out | clause has "notwithstanding"; no exception row |
| `bad_superseded_source.json` | source-currency | source_version has review_status=superseded |

Each `bad_*` fixture is used in a pytest parametrize test: `assert not validator_passes(candidate)`.

### 9.2 Red-team attack scenarios

| Scenario | Goal | How attacked | Pass condition |
|---|---|---|---|
| A | Promote a hallucinated quote | Submit candidate whose `quote` is a plausible-but-absent string | Gate rejects at quote-anchor |
| B | Extract from superseded source | Use `source_versions.licence_status='pending_review'` source | Extraction job refuses to enqueue |
| C | Bypass eval gate via direct DB insert | Attempt `rules` INSERT outside `auto_promote()` | No DB-level guard needed if code is the only path; test that API returns 404 for `POST /rules` |
| D | Get a verdict using an un-promoted rule | Construct a `check_run` referencing a `rule_candidate` id | Compliance engine only queries `rules` table, not `rule_candidates` |

---

## 10. Phase 3 exit acceptance list

All items must be verified (by the Coordinator, confirmed by a Quality Reviewer run) before
Stage 3 is declared complete. These map directly to the Phase 3 exit criteria in
MASTER_REBUILD_PLAN.md §9.

- [ ] `0003_v3_stage3_extraction_schema` migration runs up and down without error on a live
      PostgreSQL 16 + PostGIS + pgvector instance.
- [ ] `skills/extract_rules/` and `skills/classify_clauses/` directories exist with SKILL.md,
      schema.json, and at least 5 examples each.
- [ ] `eval_cases` table has ≥ 5 active rows for `skill_name="extract_rules"`, seeded from
      either the legacy harvest JSONL or the M1 canary fixture set, covering the five Tier-1
      check keys.
- [ ] `eval_cases` table has ≥ 2 active rows for `skill_name="classify_clauses"`.
- [ ] All 7 bad-candidate fixtures in `tests/fixtures/stage3/bad_candidates/` are tested and
      each corresponding validator returns `pass=False`.
- [ ] Red-team scenarios A, B, C, D all pass (gate holds).
- [ ] `pytest -q` green with extraction job, validator, gate, and inspection-view API tests
      present. Import-linter, ruff, mypy clean.
- [ ] A complete extraction run on the demo R-Codes extract source version
      (`sv_artificial_demo_rcodes_extract_2026_v1`) produces ≥ 5 `auto_accepted` rules covering
      the five Tier-1 check keys, each with a valid quote, clause_id, source_version_id,
      skill_version_id, and prompt_hash.
- [ ] Each of the 5 auto-accepted rules can be retrieved via the inspection API:
      `GET /api/v1/rules/{id}` returns `rule + quote + clause + source_version + validator_status`.
- [ ] No `auto_accepted` rule's quote is absent from its clause's text (query:
      `SELECT id FROM rules WHERE lifecycle_status='auto_accepted' AND quote NOT IN (SELECT text FROM clauses WHERE id=clause_id)` — zero rows).
- [ ] No normative clause has `disposition='informational'` (query:
      `SELECT id FROM clauses WHERE text ~* '(must|shall|minimum|maximum|prohibited)' AND disposition='informational'` — zero rows).
- [ ] No orphan-number review items remain open for the demo source version.
- [ ] Every extraction `job_traces` row for Stage 3 calls has a non-NULL `skill_version_id` and
      `prompt_hash` (zero NULL rows in scope).
- [ ] Forbidden-pattern grep (`lifecycle_status.*approved`, `INSERT.*rules`, approve-button
      strings in `web/src/`) is clean.
- [ ] The `GET /api/v1/rules/{id}` and `GET /api/v1/rules/candidates/{id}` inspection endpoints
      return 403 for unauthenticated requests and correct data for authenticated reviewers.
- [ ] The `web/` inspection view renders rule + quote + clause + source version + validator
      status with no state-changing action for rules with `lifecycle_status=auto_accepted`.
- [ ] `MASTER_REBUILD_PLAN.md §9 Phase 3` exit criteria are satisfied verbatim: every candidate
      has quote + clause + source version; invalid quotes rejected; normative clauses cannot be
      silently informational; no orphan numbers/tables/exceptions at source approval; every
      extraction traced with skill version + prompt hash. (Note: "humans promote" in the V3 exit
      text is superseded by this spec — `auto_accepted` is the promoted state; `approved` remains
      a human-only elevation available but not required for Phase 3 exit.)

---

## Appendix A — Closed vocabularies (locked for Stage 3, extend only via PR)

### rule_key vocabulary (Tier 1 — must be present at Stage 3 exit)

```text
site_cover_max_pct
primary_street_setback_min_m
secondary_street_setback_min_m
side_setback_min_m
rear_setback_min_m
open_space_min_pct
garage_width_max_m
garage_width_max_pct_facade
boundary_wall_max_length_m
boundary_wall_max_height_m
lot_area_min_m2
lot_frontage_min_m
```

Extractors that encounter a rule they cannot map to a known key must use
`{"cannot_structure": true}`. A made-up rule_key is a defect.

### Conditions closed vocabulary (must be in vocabulary.py)

```text
corner_lot
battleaxe_lot
heritage_listed
heritage_area
bushfire_prone
boundary_wall_proposed
two_storey
single_storey
ancillary_dwelling
r_code_in
lot_area_lt
lot_area_gt
adjoining_setbacks_lower
laneway_lot
sloping_site_gt
```

Unrecognised conditions map to `conditional_unstructured` — visible in the checklist as
"read the clause" rows, never silently dropped.

### Normative operators

```text
min | max | eq | range | boolean | trigger
```

---

## Appendix B — Source currency constraint (from Session A)

Only `source_versions` with `licence_status='approved'` AND `review_status='approved'` AND
`superseded_by_version_id IS NULL` may be used as extraction sources. The extraction job must
enforce this check before enqueuing. This is not a soft warning — it is a hard refusal with a
logged error.

The Session A currency audit results are the authority on which versions satisfy these conditions.
If no such version exists for a required source document, the extraction job exits with
`status="no_approved_source"` and creates a `review_items` row.

---

## Appendix C — Worker scope summary (quick reference)

| Path | Owner |
|---|---|
| `src/draftcheck/db/models.py` | Schema Integrator only |
| `src/draftcheck/db/alembic/versions/0003_*` | Schema Integrator only |
| `src/draftcheck/domain/rules/` | Legal/Extraction only |
| `src/draftcheck/jobs/extraction.py` | Legal/Extraction only |
| `src/draftcheck/api/rules.py` | Legal/Extraction only |
| `src/draftcheck/extraction/validators.py` | Validators/Eval Gate only |
| `src/draftcheck/extraction/vocabulary.py` | Validators/Eval Gate only |
| `src/draftcheck/extraction/normalize.py` | Validators/Eval Gate only |
| `src/draftcheck/domain/rules/gate.py` | Validators/Eval Gate only |
| `skills/extract_rules/` (scaffold) | Fixtures Owner (scaffold), Legal/Extraction (examples) |
| `skills/classify_clauses/` (scaffold) | Fixtures Owner (scaffold), Legal/Extraction (examples) |
| `data/fixtures/stage3/` | Fixtures Owner only |
| `tests/fixtures/stage3/` | Fixtures Owner only |
| `web/src/` (rules inspection) | Frontend only |
| `src/draftcheck/ai/` | NO agent (reuse only) |
| `tests/fixtures/golden/` | NO agent (M1 canary, read-only) |
