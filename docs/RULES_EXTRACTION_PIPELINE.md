# Rules Extraction Pipeline — Accuracy Specification

Goal: convert every ingested source document into a structured, queryable rules
database with the highest achievable accuracy, using LLM agents for extraction
and humans only for adjudication. This spec is the build contract for that
pipeline. It extends — does not replace — SOURCE_GOVERNANCE.md and the existing
ingestion/clause/citation layers.

The product promise this protects: **every value in the rules DB is traceable
to a verbatim quote in a versioned source document, and was either agreed by
independent extractors or approved by a human.** No exceptions.

---

## 1. Data model additions

### rule_rows
| field | notes |
|---|---|
| id | `rule_` prefix |
| rule_key | closed vocabulary (see §6), e.g. `front_setback_min_m` |
| jurisdiction / local_government | scope |
| applies_to_json | structured applicability: density codes, zones, dwelling types, lot types |
| operator | `min` / `max` / `eq` / `range` / `boolean` / `trigger` |
| value / value_high / unit | numeric, normalised units (m, m2, %, count, hours) |
| conditions_json | structured conditions, closed vocabulary (§6); `[]` if unconditional |
| carveout_refs_json | clause ids of exceptions that modify this rule |
| quote | **verbatim** source text the value came from |
| quote_start / quote_end | char offsets into the clause's normalized_text |
| clause_pk / source_version_id | provenance (FK to existing Clause / SourceVersion) |
| extraction_method | `consensus_3of3` / `consensus_2of3_challenge` / `human` |
| extractor_models_json | which models produced/agreed |
| confidence | computed per §8, not model-self-reported |
| status | `auto_accepted` / `pending_review` / `approved` / `rejected` / `stale` |
| approved_by / approved_at | nullable until human touch |

### clause_dispositions
Every clause of every source version gets exactly one row:
`rule_bearing` / `informational` / `definitions` / `procedural` / `fluff`,
plus `disposition_by` (model ids) and `audited` flag. This is the coverage
guarantee: a clause with no disposition is a pipeline bug, detectable by query.

### address_profiles
| field | notes |
|---|---|
| id, address, lot_plan, local_government | identity |
| facts_json | zone, r_code, overlays, lot geometry, fetched links |
| resolved_rule_ids_json | rule_rows applicable after precedence |
| triggers_json | tripped exception regimes (bushfire, heritage, corner lot…) |
| sources_checked_json | source_version_ids consulted — the declared scope |
| open_questions_json | challenge-agent findings not yet resolved |
| built_at / stale | invalidated when any source in sources_checked updates |

### precedence_rules
Per local government, human-confirmed once: ordered list of which source
documents override which (scheme amendment > scheme > LPP > R-Codes default),
and which R-Codes clauses each LPP varies. Resolver walks this order; it is
data, not code.

---

## 2. Stage 1 — ingest pipeline (per source version)

Run as Hermes/BackgroundJob chain. Every step writes JobTrace rows.

### 2.1 Structure pass
- Parse with layout awareness. Tables are first-class: extract cell-by-cell
  with row/column headers preserved, store as structured table JSON attached
  to the clause. (Table 1 / 2a / 2b of the R-Codes are the crown jewels —
  naive text extraction of tables is the single biggest known failure mode.)
- For PDFs: run BOTH text-layer extraction AND a page-image vision pass on
  pages containing tables; cross-check cell values; mismatch → human queue.
- Output: Clause rows (existing model) + table JSON assets.

### 2.2 Extraction ensemble — 3 independent passes
- Three structured-output extraction runs over each rule-bearing clause.
- Independence is the point — decorrelate errors:
  - different model families where available (not three temperatures of one model);
  - different chunking for one pass (whole-section context vs clause-only);
  - no pass sees another pass's output.
- Temperature 0, strict JSON schema, invalid output → automatic retry once,
  then counted as a null vote.
- **Quote anchoring (hard requirement):** every extracted row must include the
  verbatim quote. A deterministic validator confirms the quote appears in the
  clause text (after whitespace normalisation). No match → the row is discarded
  as hallucination, automatically, before any human sees it.
- **Abstention is a valid output.** Schema includes
  `{"cannot_structure": true, "reason": …}`. Forced extraction is worse than
  a flagged gap.

### 2.3 Deterministic validators (free accuracy, run on every candidate row)
- Unit normalisation (mm→m etc.) with original preserved in quote.
- Range sanity priors per rule_key (e.g. setbacks 0–15 m, open space 25–80 %,
  wall height 2–12 m, parking 0–6 bays). Out of range → human queue, never auto-accept.
- Applicability sanity: density codes must be real codes; LGA must match the
  source document's local_government.
- Cross-reference resolution: "subject to clause X" in the quote must resolve
  to an existing clause id → stored in carveout_refs; unresolved → flag.

### 2.4 Adjudication
- Consensus key: (rule_key, applies_to, operator, value, unit, conditions).
- **3/3 exact agreement** → `auto_accepted`, confidence 0.95.
- **2/3** → challenge round: dissenting agent is shown the two matching rows,
  its own row, and the clause text; it must either concede (state what it
  misread) or hold with a quoted justification. Concede → accepted at 0.85.
  Hold → `pending_review` (human).
- **No 2-way agreement** → `pending_review` with all three candidates attached.
- Human review UI shows: clause text, highlighted quotes, the candidate rows
  side by side. One click approve/edit/reject. Target: minutes per document.

### 2.5 Coverage audit (the "did we miss anything" answer)
- Audit agent (different model from extractors) walks EVERY clause and assigns
  a disposition. A second audit pass by another model; disposition disagreement
  → human queue.
- **No-orphan-numbers sweep (deterministic):** regex every numeric token in the
  document. Every number must be either (a) inside the quote of some rule_row,
  or (b) classified by the audit as non-normative (date, clause number, page
  ref, worked example, document id). Unclaimed numbers → human queue.
  This single check catches most "missed rule" failures.
- Audit also tags clauses containing exception language
  (`notwithstanding`, `despite`, `except where`, `unless`, `does not apply`)
  — these clauses MUST end up either as conditions/carveout_refs on some rule
  or in the human queue. Exception language is never allowed to be `fluff`.

### 2.6 Acceptance gate (per document)
A source version is `active` for resolution only when:
- 100 % of clauses have dispositions;
- 0 unclaimed numbers;
- 0 unresolved exception-language clauses;
- pending_review queue for the doc is empty;
- golden evals (§5) pass.
Until then the doc serves Q&A (retrieval with citations) but NOT the rules DB.

---

## 3. Stage 2 — address profile build (per address, cached)

1. **Facts agents:** PlanWA / Landgate / DFES / Water Corp lookups → zone,
   R-Code, MRS, overlays, lot geometry, links. Deterministic API/scrape where
   possible; agent-assisted where not; every fact carries its source URL.
2. **Resolver (plain code, no LLM):** select rule_rows matching LGA + density
   + applicability; apply precedence_rules; evaluate structured conditions
   against facts; emit applicable set + tripped triggers.
3. **Challenge agent (recall net):** searches the FULL clause library — not the
   rules DB — for: suburb/precinct/street mentions, structure plans, DCPs,
   heritage areas, exception language touching this zone or density. Anything
   found that is not represented in the resolved set → `open_questions`.
4. **Adversarial pass:** a second agent is prompted to *break* the profile:
   "find a reason any resolved rule does not apply, or an applicable rule that
   is missing." Cheap, surprisingly effective, runs against clause library.
5. Profile cached with `sources_checked`; any source update marks it stale.

Target: 2–4 minutes first build per address; instant thereafter.

---

## 4. Version drift protection

- Re-scrape schedule per source (existing SourceVersion machinery).
- New version → clause-level diff (text_sha256 already exists). Only changed
  clauses re-run the ensemble. Rule rows linked to changed clauses → `stale`,
  excluded from resolution until re-approved. Profiles referencing them → stale.
- Weekly canary job: sample 20 random approved rule rows, re-derive each from
  its clause with a fresh extractor; mismatch → alert + row to review queue.
  This detects silent regressions in prompts/models.

---

## 5. Golden evals (non-negotiable, build first)

A YAML file of human-verified facts, seeded by the designer (the in-house
expert), grown every time she corrects anything:

```yaml
- q: front_setback_min_m, R25, City of Stirling, single house
  expect: 6.0
  source: "Stirling LPP 6.1"
- q: open_space_min_pct, R25, WA default
  expect: 45        # verify against current R-Codes Table 1 — do not trust this example
  source: "R-Codes Vol 1 Table 1"
```

- Run after every ingest, every prompt change, every model swap. Any
  regression blocks the doc's acceptance gate.
- Every human correction in the review UI auto-appends a golden row. The eval
  set is the accuracy ratchet: it only gets stricter.
- Track per-extractor precision against human decisions; drop or re-prompt
  underperforming models.

---

## 6. Closed vocabularies (extend by PR, never by extractor)

- `rule_key`: ~40 keys covering R-Codes Vol 1 deemed-to-comply + drawing QA
  (start from the 25 in DEFAULT_CHECKS; add per council as encountered).
- `conditions`: `corner_lot`, `battleaxe_lot`, `heritage_listed`,
  `heritage_area`, `bushfire_prone`, `boundary_wall_proposed`, `two_storey`,
  `ancillary_dwelling`, `r_code_in {…}`, `lot_area_lt/gt {n}`,
  `adjoining_setbacks_lower`, `laneway_lot`, `sloping_site_gt {n}` …
- Extractors must map to these or abstain (`conditional_unstructured`).
  Unstructured conditionals surface in the checklist as "read the clause"
  rows — visible, never silently dropped.

---

## 7. What stays out of scope (accuracy by refusal)

- Australian Standards full text: metadata only (LEGAL_AND_LICENSING_NOTES.md).
- Design-principles judgement calls: never extracted as rules; the checklist
  shows "deemed-to-comply not met → design principles pathway" and stops.
- Anything the ensemble cannot quote-anchor: does not enter the DB. Period.

---

## 8. Confidence model (computed, not vibes)

`confidence = base(extraction_method) × validator_score × source_freshness`
- base: 3/3 = 0.95, 2/3-conceded = 0.85, human = 1.0
- validator_score: 1.0 if all deterministic checks pass (they must, to enter DB)
- freshness: 1.0 current version; 0 if stale (excluded anyway)
Models' self-reported confidence is ignored — it is not calibrated.

---

## 9. Build order

1. `rule_rows` + `clause_dispositions` tables, quote-anchor validator, golden
   eval harness (empty set runs green).
2. Single-extractor pipeline end-to-end on ONE document (R-Codes Vol 1) with
   table-aware parsing. Get the review UI loop working.
3. Add ensemble + adjudication + coverage audit + no-orphan-numbers.
4. Precedence table + resolver + one council's LPP set (her main council).
5. Address profile build with challenge + adversarial passes; caching + staleness.
6. Canary job, calibration tracking, second council.

Each step ships something she can use; accuracy machinery compounds.
