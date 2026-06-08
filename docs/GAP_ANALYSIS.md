# Gap Analysis: Research Target vs. DraftCheck WA Core

> Plan-lock notice (2026-06-06): this is now a historical/background planning document. For
> implementation, use `docs/MASTER_IMPLEMENTATION_PLAN.md`, `MASTER_PLAN_ADDENDUM.md`,
> `REPO_AUDIT.md`, and `docs/PLAN_LOCK_NOTICE.md`. Those files supersede this document where they
> differ.

**Status:** Engineering planning doc. Not a commitment; effort sizes are indicative.
**Date:** 2026-06-06
**Companion docs:** `ARCHITECTURE.md`, `RULES_EXTRACTION_PIPELINE.md`, `SOURCE_GOVERNANCE.md`

## Purpose

A research brief described a "regulatory intelligence platform" for address-and-CAD
compliance built from **four hard parts joined together**:

1. an authoritative legal archive,
2. a spatial applicability engine,
3. a rule-evaluation layer,
4. a CAD/BIM checking layer.

This document maps that target onto what DraftCheck WA Core actually is today, then proposes
a concrete, sequenced way to close the gaps. The current codebase is a backend-only
(FastAPI / Python 3.12 / SQLAlchemy 2.0) monorepo that is **project-and-document-centric**:
you create a project, hand-enter its planning context, import a vetted source library, upload an
RFI plus drawings, and it runs conservative deterministic checks with citations, refusing when no
approved source supports an answer.

The honest one-line summary: the app has built a strong version of part 1, conservative versions
of parts 3 and 4, and has **essentially not built part 2** — the spatial spine that turns "an
address" into "the rules that apply." Everything below is organized around closing that and seven
related gaps.

## Scorecard

| # | Gap | Research target | Current state | Severity |
|---|-----|-----------------|---------------|----------|
| G1 | Spatial applicability engine | address → G-NAF → parcel → zoning/overlay by geometry | Absent. `Property.address` is free text; zoning/overlays hand-entered (`detected_by="manual"`); map layers stored as documents, not geometry | **Critical** |
| G2 | Rule-evaluation engine | declarative, versioned, traceable policy (OPA/DMN-style) | ~29 hand-coded Python checks (`DEFAULT_CHECKS` + 5 calculators); right philosophy, light mechanism | High |
| G3 | Structured legal/instrument model | stable section IDs, hierarchy, cross-references, amendments | Flat `Clause → SourceChunk` keyed by SHA-256; strong provenance, no structure/graph | High |
| G4 | Semantic + graph retrieval | hybrid vector + cross-reference traversal | SQLite FTS + `ILIKE` only; `embed()`/`rerank()` are mock; `embedding_ref`/pgvector unused | High |
| G5 | Document & CAD/BIM intake | Docling/OCR + IFC + clean DXF | pypdf + BeautifulSoup + python-docx; hand-rolled DXF reader; no OCR, no IFC | Medium |
| G6 | Crawl scheduling, lineage & freshness | scheduled refresh, retries, "what changed when" | In-repo lawful fetcher + Hermes; fetch/update log models exist but no scheduler | Medium |
| G7 | Evaluation & reliability harness | Ragas/DeepEval/Guardrails + gold sets | pytest + homegrown "probe questions" in the source audit | Medium |
| G8 | Address-first API/UX surface | enter address → property profile → ranked issues with "why" | Backend-only by design; project/document-first; `landing/`, `ui/` nascent | Medium |

## What is deliberately *not* a gap (keep these)

These diverge from the research on purpose and should be preserved, not "fixed":

- **Hermes for heavy scraping** instead of bundling Scrapy/Playwright. A delegated scrape/corpus
  service keeps browser automation and rate-limit risk out of the core. Keep it; add orchestration
  *around* it (G6), not inside it.
- **Metadata-only handling of paid Australian Standards.** This is a legal requirement, not a
  shortcut. The `standard_metadata` source type and non-citable handling must stay.
- **Backend-only repository.** Fine to keep the frontend in a separate app; G8 is about exposing
  the right *API surface*, not building UI here.
- **Conservative-by-default statuses** (`likely_pass` / `missing_info` / `needs_human_review`,
  never "compliant/approved"). This is the product's core safety property. Every change below must
  preserve it.

## Sequenced roadmap

Dependencies drive the order: the rule engine's applicability predicates (G2) need the spatial
context (G1); graph retrieval (G4) needs the structured legal model (G3); the address-first surface
(G8) needs spatial resolution (G1).

| Phase | Theme | Gaps | Why first |
|-------|-------|------|-----------|
| **0 — Foundations** | Structure & measurement | G3, G7 (scaffold) | Low-infra; stable clause IDs + a gold set make every later change verifiable |
| **1 — The spine** | Address → applicability | G1, G8 (resolve/profile endpoints) | Highest value; unlocks automatic context and the address-first product |
| **2 — Depth** | Reasoning quality | G2, G4, G5 | Rule packs keyed to spatial context; hybrid + graph retrieval; better extraction |
| **3 — Operations** | Freshness & assurance | G6, G7 (full) | Keep the library current and gate changes on no-regression |

Indicative sizing per gap is given in each section as S (≈1–2 wks), M (≈3–6 wks), L (≈6–12 wks),
for one engineer, excluding data-licensing lead time.

---

## G1 — Spatial applicability engine *(Critical, Phase 1, L)*

**Where we are.** There is no spatial layer at all. Grepping the code returns zero hits for
PostGIS, shapely, geopandas, geometry, parcel, cadastre, G-NAF, geocoding, or zone geometry.
`Property` stores `address` as a string plus hand-entered `zoning`, `lot_area_m2`, `overlays_json`,
and `planning_scheme`; `PlanningOverlay.detected_by` defaults to `"manual"`; the 14 `map_layer`
sources are ingested as documents, not queryable features.

**Target.** Resolve an address to a parcel, then derive zoning, region scheme, overlays, and hazard
layers by spatial intersection — so planning context is *computed with provenance*, not typed in.

**Proposed solution.**

Add three geometry tables and a resolver service, fed by an ingestion job that loads authoritative
datasets.

New models (`packages/core/draftcheck_core/models.py`):

- `AddressPoint` — `gnaf_pid`, `address`, `lon`, `lat`, `parcel_id`, `source_version_id`.
  Geocoding + input validation from the free, quarterly **G-NAF** dataset.
- `Parcel` — `id`, `lot_plan`, `lga`, `geometry` (polygon), `centroid`, `area_m2`,
  `attrs_json`, `source_version_id`. From **Landgate** cadastre (the official WA parcel set).
- `PlanningLayerFeature` — `id`, `layer_type` (`zone` | `region_scheme` | `overlay` | `bushfire`
  | `heritage` | `airport` | `noise`), `code`, `label`, `geometry`, `source_version_id`. From
  **PlanWA / DPLH** layers and **DFES** bushfire-prone areas.

Every geometry row carries a `source_version_id` so the existing evidence/supersession model (a
strength of the codebase) extends to spatial facts — a zone polygon is just another versioned,
cited source.

Resolver service (`packages/spatial/`):

```
resolve(address_or_coords)
  -> AddressPoint (G-NAF match, confidence)
  -> Parcel (point-in-polygon on cadastre)
  -> ApplicabilityContext {
       zoning, r_code_density, region_scheme,
       overlays:[{type,label,source_version_id}], hazard_flags
     }
```

The resolver then **populates `Property` and `PlanningOverlay` automatically** with
`detected_by="spatial"` and a `source_url`/`source_version_id`, replacing manual entry while keeping
a manual override path for edge cases.

Libraries & data:

- `geoalchemy2` + `shapely` + `pyproj` for geometry; `geopandas` for the load/transform job.
- Data tiers, mirroring `SOURCE_GOVERNANCE.md`: **Tier 1** G-NAF, Landgate cadastre, PlanWA/DFES
  layers; **Tier 2 (optional accelerant)** Geoscape planning/property products to shortcut national
  integration — treated as acceleration, never final authority.

Dev/prod wrinkle (call out early): PostGIS needs PostgreSQL, but local dev uses SQLite. Gate spatial
features behind a `SPATIAL_ENABLED` flag; on SQLite, store geometry as WKT/GeoJSON text and do
point-in-polygon in shapely for small dev fixtures, while prod uses real PostGIS indexes. The
`docker-compose.yml` Postgres service should switch to a `postgis/postgis` image.

New endpoint: `POST /v1/properties/resolve {address}` → parcel + `ApplicabilityContext` + provenance.

> **Full Phase-1 design:** see `SPATIAL_ENGINE_DESIGN.md` — package layout, models, the
> `0002_spatial` migration, the resolver/service, DuckDB/`ogr2ogr` loaders, API surface, and tests.
> Stack decisions taken: PostGIS for dev/CI/prod (no SQLite fallback) and DuckDB/`ogr2ogr` for bulk
> geometry loading.

---

## G2 — Rule-evaluation engine *(High, Phase 2, M)*

**Where we are.** `DEFAULT_CHECKS` is a Python list of ~29 dicts (`key/label/category/method/
requirement/source_query`) dispatched to 5 calculators (`min_value`, `max_percentage`,
`trigger_flag`, etc.). The philosophy already matches the research — deterministic, LLM never the
judge, outputs capped at `likely_pass`/`missing_info`/`needs_human_review`. But the rules are code,
not data: not versioned, not jurisdiction-aware, not independently traceable. The service already
imports `yaml`, so externalization is half-anticipated.

**Target.** Declarative, versioned, per-jurisdiction rule packs whose evaluation emits a full trace
(inputs → comparison → result → citations), and that only fire when actually applicable.

**Proposed solution.**

Externalize the in-code checks into versioned rule packs and keep the small deterministic
interpreter you already have (don't adopt OPA/Drools yet — the current `method + requirement` shape
is already a mini-DSL; a new runtime is premature).

New models:

- `RulePack` — `jurisdiction`, `r_code_version`, `lga`, `effective_date`, `status`.
- `RuleDefinition` — `pack_id`, `key`, `applies_when` (JSON predicate), `method`, `params` (JSON),
  `source_version_ids` (JSON), `severity`, `mandatory_or_discretionary`.

The critical addition is **`applies_when`**, evaluated against G1's `ApplicabilityContext`: the
boundary-wall rule only fires in higher-density R-codes; the bushfire check only fires when the
spatial BAL flag is set; heritage only when the parcel intersects a heritage layer. This is the join
between G1 and G2 and removes a large share of today's `needs_human_review` trigger noise.

Reproducibility: link `CheckRun → rule_pack_id` so a result can be re-derived against the exact rule
version that produced it, matching the source-version discipline already used for legislation. The
interpreter returns a structured trace per result (the inputs used, the comparison performed, the
pass/fail, and the citing `source_version_ids`) so a UI "rule card" needs no extra computation.

Revisit a real engine (OPA/Rego) only if rules grow genuinely interdependent (rule outputs feeding
other rules); until then a versioned interpreter is simpler and just as auditable.

---

## G3 — Structured legal / instrument model *(High, Phase 0, M)*

**Where we are.** `SourceDocument → SourceVersion` (SHA-256-keyed) `→ Clause → SourceChunk →
SourceCitation` gives excellent provenance and supersession, but clauses are flat: no hierarchy, no
stable cross-document IDs, no amendment/repeal edges. Re-ingesting a source can churn chunk
identities, which makes it hard for a rule to point durably at "R-Codes clause 5.1.3."

**Target.** Akoma-Ntoso-*inspired* structure: stable hierarchical IDs, clause typing, definitions,
and cross-references — without committing to full AKN XML internally.

**Proposed solution.**

Enrich `Clause` and add a references table:

- `Clause` gains `clause_path` (e.g. `"5.1.3"`), `parent_clause_id`, `clause_type`
  (`definition` | `requirement` | `note` | `table`), and `defines_term`.
- `ClauseReference` — `from_clause_id`, `to_clause_id` *or* `to_external_citation`, `relation`
  (`cites` | `modifies` | `repeals` | `defined_by`).

Populate during ingestion (extend `packages/ingestion`): regex/`LexNLP`-style detection of "clause
X", "Part Y", "as defined in", with LLM assistance for ambiguous references — but the LLM only
*proposes* edges; they are stored as evidence, never as compliance conclusions, consistent with the
existing safety boundary. Keep AKN as a possible *export* format, not internal storage.

Payoff: stable clause IDs let rules (G2) cite durable targets across re-ingestion, and the
`ClauseReference` edges are exactly the graph that G4 traverses.

---

## G4 — Semantic + graph retrieval *(High, Phase 2, M)*

**Where we are.** `RetrievalService._rank_chunks` uses SQLite FTS plus `ILIKE` keyword scoring.
`providers.py` defines `embed()` and `rerank()` but `get_llm_provider()` hard-returns
`MockLlmProvider`; config defaults `embedding_provider="mock"`; `SourceChunk.embedding_ref` and the
`pgvector` dependency are unused. So retrieval is keyword-only and the "discovery then decision"
split the research recommends is impossible.

**Target.** Hybrid keyword + vector retrieval, then graph expansion along cross-references — while
preserving the "unsupported" refusal behavior.

**Proposed solution.**

1. **Real embeddings.** Implement an embedding provider behind the existing `embedding_provider`
   config; add a `Vector` column to `SourceChunk` (pgvector on Postgres; keep the mock + FTS path on
   SQLite for dev). Backfill via a worker job.
2. **Hybrid rank.** In `_rank_chunks`, fuse FTS/BM25 + cosine similarity + the existing `rerank()`
   (e.g. reciprocal-rank fusion). This is an internal change to one method; the `search()`/`ask()`
   contract is unchanged.
3. **Graph expansion (discovery).** After top-k chunks, walk `ClauseReference` (G3) to pull cited,
   modifying, or defining clauses before answering — "this local clause points to this state policy,
   modified by this bulletin." Start on the relational edge table (no new infra); consider
   Neo4j/GraphRAG only if traversal depth/perf demands it.

Decision stays deterministic: retrieval feeds the rule engine (G2) and the cited-answer path; it
never becomes the judge, and the existing `unsupported` refusal when no approved chunk matches is
kept verbatim.

---

## G5 — Document & CAD/BIM intake *(Medium, Phase 2, M)*

**Where we are.** PDF/DOCX/HTML/text parsing uses pypdf + BeautifulSoup + python-docx; DXF is read
by a hand-rolled group-code parser (`document_ai/extraction.py`). No OCR, so image-only PDFs yield
nothing; no IFC/BIM. Extraction is intentionally conservative (ambiguous → `missing_info`), which is
correct and must stay.

**Target.** Robust structured parsing (Docling/Unstructured/Marker), OCR for scans, and
first-class IFC + clean DXF (IfcOpenShell, ezdxf), with DWG converted early.

**Proposed solution.**

- **Parser abstraction** in `packages/document_ai`: pluggable backends with `Docling`/`Unstructured`
  for PDF/DOCX structure and tables, falling back to the current pypdf path. Reconcile multiple
  parsers rather than trusting one.
- **OCR path:** when a PDF has no text layer, route to `PaddleOCR`/Tesseract and tag results
  lower-confidence (so they bias toward `needs_human_review`).
- **CAD:** replace the hand DXF reader with **`ezdxf`** (robust units, layers, DIMENSION entities,
  polyline lengths) and add **`ifcopenshell`** for IFC objects (spaces, walls, boundary geometry
  relevant to setbacks/coverage). Accept DWG only after early conversion to DXF/IFC.

Why it matters here: extracted facts flow into `extracted_measurements`, which feed the rule engine
(G2). Better extraction directly converts today's `missing_info` results into real `likely_pass`/
`likely_fail` findings — without weakening the conservative default.

---

## G6 — Crawl scheduling, lineage & freshness *(Medium, Phase 3, M)*

**Where we are.** `packages/scraper` has a lawful fetcher (httpx + robots.txt checks) and heavy
scraping is delegated to Hermes — a good separation. `SourceFetchLog` and `SourceUpdateEvent` models
exist, but nothing schedules refreshes or surfaces "what's stale." Supersession logic on new content
already works; it just isn't triggered on a cadence.

**Target.** Scheduled re-fetch with retries, change detection, lineage, and freshness observability.

**Proposed solution.**

Keep Hermes; add a thin orchestration layer around it. Redis + RQ are already dependencies, so start
with `rq-scheduler`/APScheduler rather than introducing Airflow/Dagster on day one (graduate to
Dagster if lineage needs grow).

- Add `refresh_cadence` + `next_check_at` to `SourceDocument`.
- A worker job re-fetches due sources, diffs content SHA-256, creates a new `SourceVersion` on
  change (existing supersession logic applies), and writes a `SourceUpdateEvent`.
- Subscribe to the **WA legislation RSS feeds** (Acts, subsidiary legislation, gazettes) as a
  low-cost change signal so re-fetches are event-driven, not just time-driven.
- New endpoint `GET /v1/sources/freshness` surfacing stale/last-checked sources for the ops view.

---

## G7 — Evaluation & reliability harness *(Medium, Phase 0 scaffold → Phase 3 full, M)*

**Where we are.** There is a pytest suite and a homegrown "probe questions" section in
`SOURCE_LIBRARY_AUDIT.md` (e.g. "front setback open space R-Codes" → status/citation counts). Useful,
but not a systematic regression harness, and nothing mechanically enforces the no-final-compliance
wording rule.

**Target.** Versioned gold sets and automated eval across retrieval, rule application, and output
validity (Ragas/DeepEval/Guardrails), gating model/provider changes.

**Proposed solution.**

- **Gold set** under `tests/gold/`: addresses → expected parcel/zone/overlays (validates G1);
  questions → expected citations (validates G4); sample drawings → expected findings (validates
  G2/G5).
- **Three eval tracks:** spatial-resolution accuracy; retrieval faithfulness / citation precision
  (`Ragas`/`DeepEval`); rule-application correctness (matrix output vs. expected).
- **Output validation:** wrap the existing `generate_structured` (already schema-driven) with
  `Guardrails`/Pydantic validators that *mechanically* reject banned final-compliance wording —
  turning a documented policy into an enforced one.
- Wire into CI; block provider/model bumps on regression. Keep human planning/legal QA for any new
  jurisdiction or high-risk rule family.

Scaffold the gold set in Phase 0 (cheap, and it makes G1–G5 verifiable as they land); complete the
automated tracks in Phase 3.

---

## G8 — Address-first API/UX surface *(Medium, Phase 1, S–M)*

**Where we are.** The repo is backend-only by design (`AGENTS.md`), and the flow is
project/document-first: a human enters planning context, then uploads documents. `landing/`, `ui/`,
and `FRONTEND_API_WIRING.md` exist but the address-first product the research describes does not.

**Target.** Enter an address → see a plain-English property profile (zone, overlays, controls,
source freshness) → upload → get issues ranked by severity, each with a "why-this-applies" trail.

**Proposed solution.**

Keep the frontend out of this repo, but expose the API surface an address-first UI needs:

- `POST /v1/properties/resolve` (G1) — address → parcel + applicability context.
- `GET /v1/properties/{id}/profile` — zone, overlays, region scheme, key controls, and per-fact
  provenance (`source_version_id` + currency date).
- Ensure every `CheckResult` serializes a complete **rule card**: rule name, mandatory vs.
  discretionary, why it applies (the G1 trigger), the citing source + version date, and any
  higher-order rule it depends on. Most of this is a serialization task on top of G1–G3, not new
  logic.

The "why-this-applies" trail is the differentiator: a non-technical user sees the evidence chain and
the deterministic result, never a wall of model prose. This preserves the product's core safety
stance while finally making it address-first.

---

## Risks & assumptions

- **Data licensing is the real critical path,** not code. G-NAF is open; Landgate cadastre and some
  PlanWA layers have access/licence terms that need clearing before ingestion. Treat licensing lead
  time as parallel work starting in Phase 0.
- **PostGIS forces a dev/prod database split.** Budget for the SQLite-vs-PostGIS handling in G1 or
  move dev to a local Postgres/PostGIS container to avoid two code paths.
- **Effort sizes are indicative** (one engineer, excluding data-licensing and procurement) and
  assume the existing evidence/version model is reused rather than rebuilt.
- **The safety boundary is non-negotiable** through every phase: assistive only, cite-or-refuse,
  conservative statuses, human signoff before submission. No proposal above relaxes it.
