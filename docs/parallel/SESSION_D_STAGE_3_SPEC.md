# Session D — Author the Stage 3 Build Spec (rule extraction, all-AI)

Authority: `docs/MASTER_REBUILD_PLAN.md` §5.4/§7/§9 Phase 3, `docs/ROAD_TO_PROD.md` Stage 3,
`docs/RULES_EXTRACTION_PIPELINE.md`. Format model: `docs/STAGE_2_BUILD.md`.
**Sole output:** `docs/STAGE_3_BUILD.md`. Touch no code. (This session writes the *spec*; a later
build session executes it.)

## Why
Stage 3 turns approved regulatory text into `resolved_rules` the engine can apply. It's the stage
where the all-AI decision bites hardest: there is **no human promotion** — automated validators + an
eval-case gate are the only thing between an LLM extraction and a rule that drives a verdict. The
spec must make that gate airtight.

## Goal
Produce `docs/STAGE_3_BUILD.md` in the same multi-agent shape as Stage 2: roster + write scopes,
waves, invariants, merge protocol, acceptance gates — for the all-AI rule-extraction pipeline,
grounded in what already exists.

## What already exists (the spec must extend, not reinvent)
- `src/draftcheck/extraction/{validators.py (242), vocabulary.py (137), normalize.py (54)}` — real
  extraction scaffolding.
- `src/draftcheck/ai/substrate.py` — the traced, spend-capped model adapter (Stage 1).
- Empty target tables: `rules`, `rule_candidates`, `rule_clause_links`, `resolved_rules`,
  `legal_edges`, `skill_versions`, `eval_cases`, `eval_runs`. `clauses` is already populated.

## The spec must cover (agent roster to define inside STAGE_3_BUILD.md)
| Agent | Likely scope | Responsibility |
|---|---|---|
| **Schema Integrator** | `models.py`, `db/alembic/` | Any rule/skill/eval table deltas; forward migration |
| **Legal/Extraction** | `domain/rules/`, `extraction/`, `skills/extract_rules`, `skills/classify_clauses` | Clause parsing, multi-pass extraction, quote anchoring, unit normalization, carve-outs as `rule_type=exception` rows linked by `legal_edges` |
| **Validators/Eval gate** | `extraction/validators.py`, `skills/`, eval harness | The automated gate that **replaces human promotion**: quote-anchoring, normative-language, no-orphan (numbers/tables/exceptions), unit checks; `eval_cases` must pass before a candidate becomes a rule |
| **Substrate (reuse)** | — | Every extraction call traced (model, prompt_hash, skill_version) + spend-capped; no call outside the adapter |
| **Frontend** | `web/` | Rules **inspection** view (not approval): show rule + quote + clause + source version + validator status. No human approve button (all-AI). |
| **Fixtures Owner** | `tests/fixtures/golden/` | Seed `eval_cases` (adopt `data/fixtures/m1/eval/` from Session B); the 5 fixture rules |
| **Reviewers ×2 + Red-team** | read-only | Spec/Quality per merge; Red-team tries to get a rule promoted that fails a validator, or a verdict from an un-anchored quote |

## Invariants the spec must embed (all-AI)
- Promotion is automated: a candidate becomes a `rule` only when validators pass **and** the eval
  gate is green. No human approval step; no reviewer role.
- Every rule has quote + clause + source version; an invalid/mutated quote is rejected.
- A normative clause cannot be silently downgraded to informational; no orphan numbers/tables/
  exceptions at source approval.
- Carve-outs/exceptions are rows (`rule_type=exception`, own quote + citation), linked by
  `legal_edges` — never blobs.
- Every extraction traced + spend-capped; the engine consumes only rules that passed the gate.
- No superseded source supports a rule (consume Session A's currency audit).

## Acceptance gate (for the Stage 3 spec)
`docs/STAGE_3_BUILD.md` defines: roster + isolated write scopes, waves with hard edges (Stage 3 ←
Stage 1 sources/clauses; eval seeds ← Session B), the automated promotion gate in full, the
invariants above, the merge/red-team protocol, and a Phase-3-exit acceptance list. It must be
executable by a build session with no further design decisions.
