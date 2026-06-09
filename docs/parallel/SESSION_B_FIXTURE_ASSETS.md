# Session B — Pre-stage M1 Fixture Assets (multi-agent)

Authority: `docs/M1_GOLDEN_FIXTURE.md` (§1–5), `docs/ROAD_TO_PROD.md` Stage 1.
Conventions: `docs/MULTI_AGENT_BUILD_PLAN.md` §5–6.
**Sole output:** `data/fixtures/m1/`. Do **not** write to `tests/fixtures/golden/` (that is the
Stage 2 Fixtures Owner's scope — they adopt from `data/fixtures/m1/`). Touch no code.

## Why
The M1 vertical slice needs concrete input assets: a site-plan drawing, fixture spatial data, and
eval cases. Pre-staging them lets the Stage 2 Fixtures Owner and the Stage 3 eval gate adopt
ready-made inputs instead of inventing them late.

## Goal
Produce, in `data/fixtures/m1/`: (1) a site-plan PDF with the dimensions from `M1_GOLDEN_FIXTURE`
§2 including the two designed-in non-passes, (2) the five eval-case JSON stubs from §5, (3) the
fixture spatial records (parcel geometry + address point + zoning + LGA) as GeoJSON, (4) a
`MANIFEST.md` mapping each asset to the check/expected-outcome it supports.

## Agents
| Agent | Scope | Task |
|---|---|---|
| **Drawing** (worker) | `data/fixtures/m1/site_plan.pdf` (+ source) | Generate a single-house site plan: lot outline, building footprint, front setback (pass), one side-boundary setback **under DtC min** (→ `likely_fail`), open space (pass), garage width/setback (pass), and a boundary wall with an **ambiguous/uncalibrated** dimension (→ `needs_more_info`). Use the `pdf` or `canvas-design` skill. Label all values "illustrative test data". |
| **Eval Stubs** (worker, parallel) | `data/fixtures/m1/eval/*.json` | The five cases from §5 (quote-anchoring, unit-normalization, no-orphan, refuse-not-guess, cite-or-refuse) as JSON matching the `eval_cases` shape (`track`, `name`, `input_json`, `expected_json`, `notes`). Values illustrative; mark `source_version` as a placeholder to be bound at Stage 3. |
| **Fixture Data** (worker, parallel) | `data/fixtures/m1/spatial/*.geojson` | Parcel polygon, address point, zoning/R-code feature, LGA boundary for the City of Vincent test parcel (GDA2020). Synthetic-but-plausible if Session C's real pull isn't ready; clearly tag `synthetic: true` if so. |
| **Reviewer** (fresh, read-only) | read `data/fixtures/m1/` | Confirm each asset matches the §2 expected outcomes (3 pass / 1 fail / 1 needs-info), CRS is GDA2020, and **no value is presented as authoritative** — all illustrative. |

## Hard constraints
- The two designed-in non-passes must be unambiguous in the drawing (one measurably under-min; one
  genuinely uncalibrated/ambiguous).
- No asset may assert a real deemed-to-comply number as truth; all are illustrative test targets to
  be confirmed against the approved R-Codes source at Stage 3/5.
- Everything deterministic/re-generatable; commit the generator (script) alongside the PDF.

## Acceptance gate
`data/fixtures/m1/` contains the PDF, 5 eval JSONs, the GeoJSON set, and `MANIFEST.md`; Reviewer
confirms outcome alignment + GDA2020 + illustrative-only; a Stage 2/3 agent could adopt them with no
rework.
