# DraftCheck WA — Master Implementation Plan

**SUPERSEDED:** See `docs/MASTER_REBUILD_PLAN.md`. This file is background context only
for the V3 rebuild where it conflicts with the rebuild plan.

**Status:** Authoritative, self-contained build plan. Single source of truth.
**Date:** 2026-06-06
**Consolidates:** the VPS Production Fix Plan, the DraftCheck WA Core Gap-Closure Plan, the Gap
Analysis (`GAP_ANALYSIS.md`), and the Spatial Engine Design (`SPATIAL_ENGINE_DESIGN.md`).
**Supersedes where they differ:** this document replaces the earlier `RulePack`/`RuleDefinition`
suggestion in `GAP_ANALYSIS.md` with the `RuleRow` / `CheckDefinition` / `ResolvedRule` /
`DecisionTrace` model, and standardizes the spatial endpoint on `POST /v1/address/resolve` (the
`ApplicabilityContext` shape from `SPATIAL_ENGINE_DESIGN.md` is renamed `AddressProfile` + `AddressFact`).
Where this plan and an older doc disagree, **this plan wins.**

**Required companion docs:** `MASTER_PLAN_ADDENDUM.md`, `REPO_AUDIT.md`, and
`docs/PLAN_LOCK_NOTICE.md`. The addendum contains mandatory corrections from the 2026-06-06 review
and the audit contains current repo-truth deltas. Where this file still contains stale examples, the
addendum wins until this plan is fully normalized.

## Required implementation corrections

These corrections are mandatory before implementation work starts:

1. Address resolver payload:
   - Use `resolution_status`, not `status: "high"`.
   - `confidence` remains `high | medium | low`.
   - `resolution_status` is `resolved | missing_info | needs_human_review | unsupported`.

2. Rule statuses:
   - `RuleExtractionCandidate.status = candidate | pending_review | rejected`.
   - `RuleRow.lifecycle_status = auto_accepted | approved | pending_review | rejected | stale |
     superseded`.
   - Deprecated: `needs_review`.

3. ClauseDisposition:
   - Canonical values: `rule_bearing | definition | procedural | informational | manual_review`.
   - Deprecated aliases: `definitions`, `fluff`.

4. AddressFact:
   - Store as row-per-fact with `fact_type`, `value_json`, `confidence`, `method`,
     `spatial_dataset_id`, `source_version_id`, `planning_layer_feature_id`, `effective_from`,
     `effective_to`, `stale_at`, and `review_status`.
   - Do not store `overlays[]` as an opaque list if each overlay needs independent provenance.

5. Assessment date:
   - Every resolved-rules and compliance run must carry `as_of_date`.
   - Add `lodgement_date` and `assessment_basis` to `Project`.

6. Proposal facts:
   - Add `ProjectProposal`.
   - Do not treat `dwelling_type` or `proposal_type` as address facts.

7. Source/project parsing:
   - A shared parser package is allowed.
   - Agent B alone writes `SourceArtifact`.
   - Agent E alone writes `DocumentArtifact`, `DrawingEntity`, and `DrawingMeasurement`.

8. Property migration:
   - Do not convert `Property` to a DB view until a write-path audit proves it is safe.
   - First add `address_profile_id` and keep backward-compatible fields.

9. DecisionTrace:
   - Add unit conversions, rounding policy, tolerance, input sources, applicability trace,
     precedence trace, engine version, rule snapshot hash, and measurement snapshot hash.

10. DB image:
   - Verify both PostGIS and pgvector are installed.
   - If the selected PostGIS image lacks pgvector, build a custom DB image or use a proven image that
     includes both.

## How to read this document

The plan is organized so that up to nine parallel agents (A–I) can build different layers at once
without colliding. Read in this order: the **Reliability Contract (§1)** first — it constrains every
other section; then the **Architecture (§2)** and **Conflict Resolutions (§3)**; then the **Canonical
Data Model (§4)**, which is the shared vocabulary every agent must speak; then your agent's entry in
the **Agent Roster (§5)**. The **Build Order (§10)** and **Phasing (§11)** tell you *when* your work
lands; the **Coordination Protocol (§12)** tells you how not to break another agent.

## Table of contents

1. The North Star and the non-negotiable reliability contract
2. Target architecture
3. Resolved conflicts and canonical naming
4. Canonical data model (the shared language)
5. Agent roster: ownership, APIs, dependencies, Definition of Done
6. The address-first onboarding wizard
7. Frontend information architecture
8. The reliability and accuracy program (cross-cutting)
9. Hardening additions
10. De-duplicated master build order
11. Phasing and milestones with exit criteria
12. Cross-agent coordination protocol
13. Open-source tool shortlist
14. Risks, licensing critical path, assumptions
15. Appendix: API surface, status enums, key payloads

---

## 1. The North Star and the non-negotiable reliability contract

### 1.1 The one sentence the whole product reduces to

For a given **address** and a given **drawing**, prove what rules apply, prove each rule from an
official source, extract the drawing's facts conservatively, compare facts to rules deterministically,
and **show the result with exact citations — or visibly refuse.**

Expanded into the chain every feature serves:

```text
For a given address:
  1. prove the parcel and council,
  2. prove the zoning / overlays / hazards,
  3. select the applicable state and local rules,
  4. prove each rule from an official, current source,
  5. extract drawing facts conservatively,
  6. compare facts to rules deterministically,
  7. show the user the result with exact citations and evidence,
  8. refuse, or mark human review, whenever proof is incomplete.
```

Everything else — infrastructure, UX, automation, retrieval — exists only to make that chain fast,
maintainable, and trustworthy.

### 1.2 Why reliability is the design driver, not a feature

This product will be shown to professional colleagues who can instantly spot a wrong setback or a
fabricated citation. A single confident-but-wrong answer destroys trust in the whole tool. Therefore
the guiding principle is **calibrated humility**: the app is allowed to say "I don't have enough to
judge this" as often as needed, but it is **never** allowed to assert compliance, a threshold, a
council, a zone, or a measurement it cannot prove.

A tool that says *"likely fail — front setback 3.8 m < 4.5 m required (City of X LPP 2.3, cl. 4.1, eff.
2024-03-01)"* with a clickable source is impressive. A tool that says *"compliant!"* and is wrong is
career-embarrassing. We engineer for the first and structurally forbid the second.

### 1.3 The status taxonomy (mandatory, used everywhere)

Every regulatory output — a rule application, a spatial fact, a chat answer — must carry exactly one
of these statuses. The existing codebase already defines `CheckStatus`; this is the canonical set:

| Status | Meaning | When |
|--------|---------|------|
| `likely_pass` | Measurement satisfies a proven rule | Approved rule **and** measurement **and** stored calculation trace **and** citation all present |
| `likely_fail` | Measurement violates a proven rule | Same four preconditions, comparison fails |
| `missing_info` | Cannot judge — an input is absent | Missing source, missing spatial fact, or missing measurement |
| `needs_human_review` | Judgement requires a person | Conflict, discretion, low-confidence spatial match, trigger flag |
| `not_applicable` | Rule does not apply here | Precedence/applicability excluded it |
| `unsupported` | Approved library cannot answer | No citable source chunk supports the claim (retrieval/chat) |

Note the deliberately conservative wording: **`likely_pass` / `likely_fail`, never `compliant` /
`approved` / `certified`.** The product is assistive; a human signs off before anything is treated as
submission-ready. This is already encoded in `LEGAL_AND_LICENSING_NOTES.md` and must never regress.

### 1.4 The five hard preconditions for a pass/fail

`likely_pass` or `likely_fail` may be emitted **only** when **all** of:

```text
1. an approved ResolvedRule exists for this address/project, and
2. the required DrawingMeasurement (or manual measurement) exists, and
3. a DecisionTrace (inputs → formula → comparison → result) is stored, and
4. a Citation to an official, current source version exists, and
5. the rule was not excluded by precedence (not_applicable).
```

If any is absent: `missing_info` (missing input), `needs_human_review` (conflict/discretion), or
`unsupported` (no source). There is no sixth path. There is no "best effort guess."

### 1.5 What is structurally forbidden

```text
- No LLM output may become law without validation (quote-anchoring + unit parsing + vocabulary).
- No retrieval/semantic-similarity result may decide compliance or pick a threshold.
- No LGA-only (council-area) match may be treated as parcel-level legal proof.
- No Google Places result may be treated as proof of council, parcel, zoning, or overlay.
- No raster/PDF scale may be inferred as a compliance measurement unless explicitly calibrated.
- No source text change may silently update an already-approved rule.
- No spatial conclusion may be emitted without authoritative geometry (else: missing_info).
- No Australian Standards full text may be scraped/stored (metadata + access notes only).
```

These are invariants. Every agent's Definition of Done (§5) includes "does not violate §1.5."

---

## 2. Target architecture

### 2.1 The single deployment picture

```text
app.cuz.fail ──► Caddy ──► static frontend (separate repo, built to static assets)
api.cuz.fail ──► Caddy ──► FastAPI backend (this repo, backend-only)

FastAPI
  ├─► PostgreSQL + PostGIS + pgvector   (relational + spatial + vector, one database)
  ├─► MinIO                              (object storage: raw/parsed/uploads/exports buckets)
  └─► Redis + RQ                         (job queue)

Workers (RQ, containerized, concurrency-limited)
  ├─ source scraping / import           (Agent B; heavy scraping delegated to Hermes)
  ├─ source parsing (consensus)         (Agent E parsers; Agent B governance)
  ├─ rule extraction (3-pass)           (Agent C)
  ├─ address / spatial resolution       (Agent D)
  ├─ CAD / IFC / DXF extraction         (Agent E)
  ├─ compliance evaluation              (Agent F)
  ├─ source refresh / diff              (Agent B)
  └─ golden evals / canaries            (Agent I)
```

### 2.2 The one change to the VPS plan that matters

The VPS plan must use **`postgis/postgis`** as the database image, with the **`pgvector`** extension
enabled — not plain Postgres. PostGIS provides the parcel / zone / overlay / buffer / intersection
correctness the spatial spine depends on; pgvector stores embeddings in the same database and supports
exact and approximate nearest-neighbour search with HNSW and IVFFlat indexes. One database holds
relational, spatial, and vector data, so "which rules apply to this parcel" is a single transactional
join rather than a cross-system call.

Correction: do not assume the selected `postgis/postgis` image includes pgvector. Use a custom DB
image or a proven image that includes both PostGIS and pgvector, and verify both extensions in
migrations/readiness checks.

```yaml
# docker-compose.yml (excerpt)
db:
  image: custom-postgis-pgvector:16
  # migration must run:
  # CREATE EXTENSION IF NOT EXISTS postgis;
  # CREATE EXTENSION IF NOT EXISTS vector;
```

### 2.3 Environment & domains

```text
app.cuz.fail   static frontend
api.cuz.fail   FastAPI (OpenAPI at /openapi.json, Swagger at /docs)
Caddy          automatic TLS, reverse proxy, security headers
secrets        via environment / secret store, never committed
DATABASE_URL   PostgreSQL/PostGIS (SQLite remains only for non-spatial unit tests)
```

### 2.4 Repository boundaries

The backend repo stays **backend-only** (`AGENTS.md` rule). The frontend is a **separate repo/app**
built to static assets that Caddy serves at `app.cuz.fail`. Frontend code must not leak into the
backend repo unless a monorepo is explicitly adopted. The API contract (§15) is the seam between them.

---

## 3. Resolved conflicts and canonical naming

Five conflicts existed across the source plans. They are resolved as follows and are **final**.

### 3.1 Address endpoint — `POST /v1/address/resolve` is canonical

The resolver entry point is `POST /v1/address/resolve`, returning (and persisting) an `AddressProfile`
plus `AddressFact`s. The project-scoped writer is `POST /v1/projects/{id}/property/resolve`. The older
`POST /v1/properties/resolve` from `SPATIAL_ENGINE_DESIGN.md` survives only as a backwards-compatible
alias. The `ApplicabilityContext` object in that design doc maps onto `AddressProfile` (resolution +
parcel + council) and `AddressFact` (zone, density, overlays, hazards).

### 3.2 Google Places — autocomplete only, never proof

Google Places (or any commercial geocoder) may power **frontend autocomplete only**. Legal
applicability — council, parcel, zoning, overlays — must come from deterministic datasets: G-NAF,
cadastre, PlanWA/DPLH layers, DFES bushfire, heritage layers, and official source documents. When
authoritative geometry is missing, the resolver returns `missing_info`, never a Places-derived guess.

### 3.3 Frontend vs backend-only — no real conflict

Backend repo stays backend-only; frontend is a separate app; Caddy serves the built frontend. Settled.

### 3.4 The rule object model — `RuleRow` is the legal atom

```text
RuleRow         = a source-extracted legal requirement, quote-anchored to a Clause + SourceVersion.
CheckDefinition = evaluator metadata (e.g. "front setback check", method, units). Already in the code.
ResolvedRule    = the specific rule selected for THIS address/project after precedence.
DecisionTrace   = what was checked, against which rule, using which measurement, with which citation.
RulePack        = OPTIONAL later artifact: a published, versioned bundle/snapshot. NOT the core unit.
```

`RuleRow` is primary. `RulePack` is demoted to an optional publishing/snapshot concept. This overrides
the `RulePack`-centric sketch in `GAP_ANALYSIS.md` §G2.

### 3.5 Graph store — relational first, Neo4j only if proven necessary

Cross-references, overrides, carve-outs, supersessions, and amendments are modelled as **relational
tables** (`ClauseReference`, `SourceReference`, `RuleToClause`, `RuleOverride`, `RuleCarveout`,
`SourceSupersession`). Graph expansion is a recursive SQL/ORM walk. Neo4j or GraphRAG is introduced
**only** if traversal becomes a measured bottleneck — not before.

---

## 4. Canonical data model (the shared language)

Every agent must use these names. Entities marked **(exists)** are already in
`packages/core/draftcheck_core/models.py`; **(new)** are to be added; **(extend)** exist but gain
fields. Field lists are the meaningful columns, not exhaustive DDL (see §15).

### 4.1 Sources & evidence

```text
SourceDocument (exists)        official identity: title, jurisdiction, authority,
                               local_government?, source_type, canonical_url, licence notes
SourceVersion (exists)         content_sha256, fetched/effective/published dates,
                               version_label, superseded flag
SourceArtifact (new)           one row per stored representation of a version:
                               kind = raw_pdf | raw_html | raw_docx | parsed_text | ocr_text |
                                      table_json | page_image | extraction_output
                               object_key (MinIO), content_hash, parser_name, parser_version
SourceChunk (exists)           retrieval-only text chunk (+ embedding vector via pgvector)
SourceCitation (exists)        the citable reference object surfaced to users
SourceLicenceReview (new)      licence_url, allowed_use, allowed_storage, allowed_redistribution,
                               allowed_ai_processing, restricted_reason, reviewed_by, reviewed_at
SourceSupersession (new)       from_version_id, to_version_id, reason, detected_at
SourceReference (new)          a source version cites/relies-on another source (external links)
```

### 4.2 Legal structure & rules

```text
Clause (extend)                clause_path (stable, e.g. "5.1.3"), parent_clause_id, clause_type,
                               defines_term, source_version_id, text_span
ClauseReference (new)          from_clause_id, to_clause_id | to_external_citation,
                               relation = cites | modifies | defines | overrides | repeals
ClauseDisposition (new)        per-clause label = rule_bearing | definition | procedural |
                               informational | manual_review   (never "fluff" if normative)
RuleExtractionCandidate (new)  proposed rule from a parser/LLM/deterministic extractor (pre-approval);
                               status = candidate | pending_review | rejected
RuleRow (new)                  THE legal rule atom: rule_key (closed vocab), operator, value, unit,
                               condition_text, quote, clause_id, source_version_id,
                               lifecycle_status = auto_accepted | approved | pending_review |
                               rejected | stale | superseded
RuleToClause (new)             rule ↔ clause provenance link
RuleOverride (new)             rule A overrides rule B for a scope (records, never deletes, the loser)
RuleCarveout (new)             exception/exemption attached to a rule
CheckDefinition (exists)       evaluator metadata: key, label, category, method, requirement, unit
```

### 4.3 Spatial & address

```text
SpatialDataset (new)           a versioned geometry dataset edition (G-NAF, cadastre, PlanWA layer,
                               DFES): name, provider, version_label, retrieved_at, source_version_id
Parcel (new)                   lot_plan, local_government, area_m2, geom (PostGIS), source_version_id
AddressPoint (new)             gnaf_pid, address, lon, lat, geom, parcel_id, source_version_id
PlanningLayerFeature (new)     layer_type = zone | region_scheme | overlay | bushfire | heritage |
                               airport | noise; code, label, geom, source_version_id
LocalGovernmentBoundary (new)  name, geom, source_version_id
AddressProfile (new)           resolved address: formatted_address, confidence, parcel_id,
                               local_government, lot_plan, resolver_sources[], dataset_version_ids[]
AddressFact (new)              row-per-fact: fact_type, value_json, confidence, method,
                               spatial_dataset_id, source_version_id, planning_layer_feature_id,
                               effective_from/to, stale_at, review_status
LocalGovernmentFact (new)      method = parcel_intersection | point_intersection | manual_override,
                               confidence, source_dataset_version_id
ProjectProposal (new)          project/proposal facts: proposal_type, dwelling_type, building_class,
                               work_type, occupancy_class, new_or_existing, lot_type,
                               primary/secondary street confirmation, source, confidence
Property (exists → extend)     add address_profile_id first; keep backward-compatible fields until
                               a write-path audit proves a view is safe
PlanningOverlay (exists → extend) detected_by = manual | spatial | spatial_low_confidence
```

### 4.4 Applicability & evaluation

```text
PrecedenceRuleSet / PrecedenceRuleItem (new)  how local vs state instruments override/supplement
ResolvedRule (new)             the rule selected for THIS address/project after precedence:
                               rule_row_id, address_profile_id, project_id, as_of_date,
                               assessment_basis, applies_reason, overridden_rule_ids[], status
ComplianceCheckResult (exists: CheckResult → extend) status, resolved_rule_ids[], measurement_ids[],
                               formula, citations[], human_review_reason, decision_trace_id,
                               as_of_date, assessment_basis
DecisionTrace (new)            inputs JSON, formula, comparison, result, citation_ids[], rule_ids[],
                               unit_conversions_json, rounding_policy, tolerance, input_sources,
                               applicability_trace_json, precedence_trace_json, engine_version,
                               rule_snapshot_hash, measurement_snapshot_hash,
                               measurement_ids[], created_at — fully reproducible
ExtractedMeasurement (exists)  value, unit, evidence ref (document/page/entity/fact)
```

### 4.5 Drawings & document intake

```text
ProjectDocument (exists)       uploaded file metadata + parse/analysis status
DocumentArtifact (new)         parser-comparison row: pypdf_text, docling_text, unstructured_text,
                               ocr_text, table_json, page_image keys; canonical_text_artifact_id,
                               canonical_selection_reason
DrawingEntity (new)            CAD/DXF/IFC/PDF object: layer, label, geometry, units, source_page/obj
DrawingMeasurement (new)       value, unit, drawing_entity_id, page, confidence, calibrated flag
```

### 4.6 Quality, review & ops

```text
GoldenEvalCase (new)           a fixed input→expected pair for a track (rule extraction, spatial,
                               retrieval, drawing extraction, compliance)
GoldenEvalRun (new)            a run over cases: pass/fail per case, metrics, commit/model version
ReviewQueueItem (new)          queue, reason, blocking_level, evidence, suggested_action, assignee,
                               status, audit log  (queues enumerated in §8.6)
AuditEvent (exists)            every workflow action, append-only
BackgroundJob / JobTrace (exists) Hermes/worker delegation + traces
HumanSignoff (exists)          required before any export is submission-ready
```

### 4.7 The two golden rules of the data model

1. **Every regulatory fact carries a `source_version_id` (or `source_dataset_version_id`).** A zone,
   an overlay, a rule, a council assignment — none may exist without pointing at the versioned,
   citable source that proves it. This is what makes §1.5's "refuse without proof" enforceable.
2. **Nothing authoritative is ever deleted.** Superseded versions, overridden rules, and rejected
   candidates are retained and audit-visible; they are merely excluded from default selection.

---

## 5. Agent roster: ownership, APIs, dependencies, Definition of Done

Nine agents (A–I) can work in parallel. Each entry lists what it owns, the tables and endpoints it is
responsible for, its dependencies, and a **Definition of Done (DoD)** — the acceptance bar that must
be green before the workstream is "done." Every DoD implicitly includes: *"introduces no violation of
§1.5 and every new regulatory output carries a status from §1.3 and a citation or an explicit refusal."*

### Agent A — Production infrastructure & security

**Mission:** a reproducible, secure, observable production stack.

**Owns:** Docker Compose; Caddy (TLS, headers, routing); `postgis/postgis` + `pgvector`; Redis/RQ;
MinIO (buckets: `raw-sources`, `parsed-sources`, `uploads`, `exports`); Alembic migration job; secrets;
health checks; worker concurrency limits, per-job timeouts and retry policy; upload security
(ClamAV/file-type sniffing/size limits); structured logs + error tracking; uptime checks; backups +
tested restore.

**Tables/endpoints:** none of the domain model; owns `/health`, `/ready`, and the ops surface.

**Depends on / blocks:** blocks everyone (nothing runs without the stack). Depends on nothing.

**DoD:**

```text
- `docker compose up` brings up Caddy, PostGIS+pgvector, Redis, MinIO, API, worker; /health green.
- Alembic migrates cleanly from empty DB; postgis + vector extensions present.
- MinIO buckets exist; all access via short-expiry signed URLs; no public bucket.
- Daily ENCRYPTED offsite backup of DB and MinIO; restore tested on a clean machine; restore time
  recorded; checksum validated; DR runbook written.
- Uploads scanned (ClamAV), size-limited, type-sniffed (not extension-only); CAD conversion sandboxed.
- Rate limits on upload/chat endpoints; tenant isolation + auth enforced before any public exposure.
- Structured logs + error tracking + uptime checks for app, API, worker, DB, Redis, MinIO.
```

### Agent B — Source archive & governance

**Mission:** the evidence vault. Every rule must trace to an official, current, lawfully-usable source.

**Owns:** corpus import from `data/corpus`; raw + parsed artifacts in MinIO; content hashing; official
URLs; licence metadata + the licence gate; source review API; source freshness, refresh, and diffs.

**Tables:** `SourceDocument`, `SourceVersion`, `SourceArtifact`, `SourceChunk`, `SourceLicenceReview`,
`SourceSupersession`, `SourceReference`.

**Endpoints:** `POST /v1/sources/import`, `POST /v1/sources/hermes-corpus/import` (exists),
`GET /v1/sources`, `GET /v1/sources/{id}`, `POST /v1/sources/{id}/review`, `GET /v1/sources/freshness`.

**Depends on / blocks:** depends on A. Blocks C (rules need clauses/sources) and G (retrieval needs
chunks).

**DoD:**

```text
- Every source has: official URL, jurisdiction (state|local|federal|private|standard|guidance),
  local_government if council-specific, source_type, fetched_at, content_hash, licence/reuse status,
  raw artifact key, parsed artifact key, parser_version, approved|rejected|restricted status.
- Changed source text creates a NEW version and NEVER silently updates an approved rule.
- Stale versions are excluded from applicability resolution and flagged in /freshness.
- Australian Standards remain metadata-only, non-citable, unless lawfully supplied and licence-reviewed.
- A licence review exists for every source before its text can support an answer.
```

### Agent C — Legal structure & rule extraction

**Mission:** turn official text into quote-anchored, structured, validated `RuleRow`s — without letting
the LLM invent law.

**Owns:** the 3-pass pipeline; `Clause` hierarchy; cross-references; `ClauseDisposition`; `RuleRow`;
quote anchoring; closed rule vocabulary + operators; unit normalization; rule review workflow; table
extraction; the audits in §8.4–8.5.

**Tables:** `Clause` (extend), `ClauseReference`, `ClauseDisposition`, `RuleExtractionCandidate`,
`RuleRow`, `RuleToClause`, `RuleOverride`, `RuleCarveout`.

**Endpoints:** `GET /v1/clauses/{id}`, `GET /v1/rules?source_version=...`, `POST /v1/rules/{id}/review`.

**Depends on / blocks:** depends on B. Blocks F (compliance needs `RuleRow`/`ResolvedRule`) and G
(graph expansion needs `ClauseReference`).

**DoD:**

```text
- Pass 1 parses document → hierarchy, clauses, tables, definitions with stable clause_path.
- Pass 2 extracts candidates under a STRICT JSON schema; rule_key ∈ closed vocabulary.
- Pass 3 validates: quote must appear verbatim in normalized clause text; numeric values parse into
  standard units; unsupported condition text is STORED, never discarded; then approve/auto-accept/review.
- No-orphan audit passes (§8.4): no orphan numbers, %, distances, dates, exceptions, definitions,
  table cells, cross-references, amendment notes.
- Normative-language audit passes (§8.5): every must/shall/required/unless/except/deemed-to-comply/
  performance-criteria clause is rule_bearing | definition | procedural | manual_review — never fluff.
- Every RuleRow is quote-anchored to a Clause + SourceVersion.
```

### Agent D — Spatial / address spine

**Mission:** turn an address into proven parcel + council + zoning + overlays + hazards. **This is the
highest-priority product gap** (see `GAP_ANALYSIS.md` G1 and `SPATIAL_ENGINE_DESIGN.md`).

**Owns:** the address resolver; parcel matching; LGA matching; zoning; R-Code density; overlays; hazard
layers; dataset versioning; stale spatial facts. Implementation detail lives in `SPATIAL_ENGINE_DESIGN.md`
(PostGIS for dev/CI/prod; DuckDB/`ogr2ogr` loaders).

**Tables:** `SpatialDataset`, `Parcel`, `AddressPoint`, `PlanningLayerFeature`,
`LocalGovernmentBoundary`, `AddressProfile`, `AddressFact`, `LocalGovernmentFact`; populates
`Property`/`PlanningOverlay`.

**Endpoints:** `POST /v1/address/resolve` (canonical), `POST /v1/projects/{id}/property/resolve`,
`GET /v1/projects/{id}/property/profile`.

**Depends on / blocks:** depends on A. Blocks F (applicability needs `AddressFact`) and H (the wizard's
first step calls resolve).

**DoD:**

```text
- /v1/address/resolve returns AddressProfile + AddressFact with confidence and dataset versions.
- Parcel match by point-in-polygon on cadastre; council by parcel intersection.
- HARD RULE: no LGA-only match is treated as parcel-level proof.
- Multiple parcel candidates or low geocode confidence → needs_human_review; never auto-pick.
- Every derived fact carries source_dataset_version_id; missing geometry → missing_info (never a guess).
- Google Places used only for autocomplete; never as legal proof.
- Manual override path preserved; detected_by records provenance.
```

### Agent E — CAD, drawing, IFC & document intake

**Mission:** extract drawing facts conservatively, with parser consensus, never inventing measurements.

**Owns:** PDF/DXF/IFC intake; DWG conversion policy; parser consensus (Docling + Unstructured + OCR);
`DrawingEntity`; `DrawingMeasurement`; evidence refs; the parser-comparison table.

**Tables:** `DocumentArtifact`, `DrawingEntity`, `DrawingMeasurement`; feeds `ExtractedMeasurement`.

**Endpoints:** `POST /v1/projects/{id}/documents/upload` (exists, extend), `GET .../documents/{id}/facts`.

**Depends on / blocks:** depends on A (sandboxed conversion, MinIO). Blocks F (compliance needs
measurements) and H (issue cards show drawing evidence).

**DoD:**

```text
- Multi-parser intake: Docling + Unstructured for structure/tables, PaddleOCR/Tesseract for scans;
  outputs stored side-by-side with a chosen canonical_text + canonical_selection_reason.
- DXF via ezdxf (units, layers, dimensions, polyline lengths). IFC via IfcOpenShell (object evidence).
- DWG only after successful conversion; otherwise unsupported.
- Unlabelled dimensions stay DRAWING FACTS, not compliance measurements.
- No raster/PDF scale inference as a measurement unless explicitly calibrated.
- Every measurement carries a document/page/entity/fact evidence ref.
```

### Agent F — Compliance engine

**Mission:** deterministic evaluation of resolved rules against measurements + spatial facts, with a
reproducible `DecisionTrace` on every result.

**Owns:** `ComplianceInputBuilder`; precedence resolver; `ResolvedRuleEvaluator`; calculation formulas;
status outputs; fallback labelling; `DecisionTrace`.

**Tables:** `PrecedenceRuleSet`/`Item`, `ResolvedRule`, `DecisionTrace`; extends `CheckResult`.

**Endpoints:** `POST /v1/projects/{id}/resolved-rules`, `POST /v1/projects/{id}/compliance/run`,
`GET /v1/projects/{id}/compliance/matrix`.

**Depends on / blocks:** depends on C (`RuleRow`), D (`AddressFact`), E (measurements). Blocks H (issue
cards render results).

**DoD:**

```text
- Precedence resolver selects ResolvedRules; overridden rules recorded (RuleOverride), never deleted.
- Evaluator emits likely_pass/likely_fail ONLY when §1.4's five preconditions hold; else missing_info /
  needs_human_review / not_applicable / unsupported.
- Every result stores a DecisionTrace (inputs → formula → comparison → result → citations).
- Default code checks remain FALLBACK only and never claim source-derived authority.
- Retrieval/semantic similarity is NOT used to decide pass/fail or pick a threshold.
```

### Agent G — Retrieval & chat

**Mission:** help users find and understand rules with citations — without ever judging compliance.

**Owns:** source chunk search; hybrid ranking (keyword + pgvector + rerank); citation/graph expansion
via `ClauseReference`; answer generation; the `unsupported` refusal; project-document retrieval.

**Tables:** reads `SourceChunk` (+ embeddings), `ClauseReference`; owns no authoritative facts.

**Endpoints:** `POST /v1/ask`, `GET /v1/projects/{id}/document-search`.

**Depends on / blocks:** depends on B (chunks), C (`ClauseReference`). Supports H (explanations, chat).

**DoD:**

```text
- Hybrid retrieval (FTS/BM25 + cosine via pgvector + rerank); refuses with `unsupported` when no
  approved chunk supports the answer.
- Used ONLY to explain rules, find/relate clauses, answer with citations.
- NEVER decides compliance, selects thresholds, or resolves precedence.
- Every answer is citation-backed or an explicit refusal; no uncited prose.
```

### Agent H — Frontend UX & the onboarding wizard

**Mission:** an address-first product a non-technical user can run end-to-end and proudly demo. Details
in §6–7.

**Owns:** the address-first guided wizard (onboarding = the core flow); project dashboard; matched-sources
panel; upload status; issue cards; evidence drawer; source-review screens. Chat is secondary, not the
front door.

**Tables/endpoints:** none owned; consumes the API contract (§15).

**Depends on / blocks:** depends on D (resolve), F (results), B (matched sources), E (drawing evidence),
G (explanations). Blocks nothing downstream; it is the product surface.

**DoD:**

```text
- New user completes the §6 wizard end-to-end against a real or demo address with zero docs read.
- Every issue card shows status, rule, requirement, proposed, result, why-it-applies, source citation,
  drawing evidence, calculation, and (if any) human-review reason.
- Evidence drawer exposes rule quote, official source, parsed text, raw PDF, spatial source, drawing
  evidence, and the DecisionTrace.
- No wall of model prose anywhere; structured cards with expandable evidence.
- Low-confidence / missing_info / needs_human_review states render clearly, never as a fake pass.
```

### Agent I — Reliability & evaluation (the spine)

**Mission:** make "always accurate" measurable and enforced. Owns the machinery that lets us ship
without embarrassment.

**Owns:** golden eval cases/runs across all tracks; canaries; parser-consensus harness; the human-review
queue framework; accuracy metrics; **release gates**.

**Tables:** `GoldenEvalCase`, `GoldenEvalRun`, `ReviewQueueItem`; reads everything.

**Endpoints:** `POST /v1/evals/run`, `GET /v1/evals/runs/{id}`, `GET /v1/review-queues`,
`GET /v1/ops/dashboard`.

**Depends on / blocks:** depends on all (needs each agent's outputs to evaluate). **Gates releases for
all.**

**DoD:**

```text
- Golden sets exist for: rule extraction, spatial resolution, retrieval faithfulness, drawing
  extraction, compliance correctness — each with known expected outputs.
- CI blocks merge/deploy when any track regresses below threshold (release gate).
- Source approval is BLOCKED on eval failure (§8.3).
- Weekly canaries run on a fixed address+drawing set; drift alerts before users see it.
- Six review queues (§8.6) are first-class, each item with reason/blocking_level/evidence/action/owner.
- Ops dashboard (§8.7) reports freshness, unsupported rate, missing-info rate, eval pass/fail, last
  successful backup + restore test.
```

---

## 6. The address-first onboarding wizard

This is the feature that turns the app from "a backend with endpoints" into something a non-technical
person can run and proudly demo. **The wizard is not a throwaway tour — it IS the core workflow.** A
first-time user is walked through the exact path they will use every time; the only difference is that
on the first run we add framing, a demo option, and confidence-building footers.

### 6.1 Design principles

```text
- Address-first, not chat-first. Chat is a secondary helper, never the front door.
- One decision per screen. A non-technical user is never shown two questions at once.
- Trust footer on every step: "Where did this come from?" — datasets + versions, always visible.
- Honest states. missing_info / needs_human_review render as themselves, never disguised as a pass.
- Replayable. The walkthrough can be re-launched any time from Help; it is not a one-shot.
- The demo path always works (it is a pinned golden case — see 6.4).
```

### 6.2 The steps

A persistent left/top progress rail shows all steps; the user can go back but not skip ahead past an
unresolved blocker.

**Step 0 — Welcome (first run only).** One short sentence on what the app does and what it will not do
(*"DraftCheck checks drawings against WA planning rules and shows you the exact source for every issue.
It's an assistant — a human signs off before submission."*). Two buttons: **"Try the demo"** and
**"Start with my address."**

**Step 1 — Enter the address.** A single autocomplete field (Google Places powers autocomplete only).
On select, call `POST /v1/address/resolve`.

```text
States:
  loading        "Resolving parcel and council from official datasets…"
  high confidence go straight to Step 2
  low confidence / multiple parcels → show candidate parcels on a small map; user picks; if still
                   unresolved → needs_human_review banner with "continue without verified parcel?"
  no geometry    missing_info: "We can't verify this parcel from authoritative data yet. You can still
                   explore, but results will be marked unverified." (never a fake result)
```

**Step 2 — Confirm the property profile.** Show what was *proven*, each line with a confidence chip and
a "source" link:

```text
Address      12 Example St, Suburb WA 6000        (G-NAF, v2026-05)
Parcel       Lot 41 on Plan 12345 · 512 m²        (Landgate cadastre, v2026-05)  ✓ high
Council      City of Example                       (parcel intersection)          ✓ high
Zone         Residential R40                       (PlanWA, v2026-04)             ✓ high
Overlays     Bushfire prone: No · Heritage: No     (DFES v2026-03 · Heritage v…)
```

Anything unproven is shown as `missing_info` with a "needs verification" tag, not hidden. The user
confirms or corrects (manual override is allowed and recorded as `detected_by=manual`).

**Step 3 — See the sources that apply.** The matched-sources panel (§7.2): which state and local
instruments apply to *this* parcel, and — equally important — which were **excluded and why** (wrong
council, stale, superseded, restricted, duplicate). This is a trust moment: the user sees the app
reasoning about authority before it judges anything.

**Step 4 — Upload drawings.** Drag-and-drop (or "use the demo drawings"). Show live processing status
per file and the parser-consensus result:

```text
site_plan.pdf   parsing… → text+tables (Docling) ✓ · OCR not needed · 3 measurements found
floorplan.dxf   parsing… → ezdxf ✓ · units: mm · 12 dimensions, 4 usable measurements
elevation.pdf   scanned → OCR (PaddleOCR) · low confidence → flagged for review
```

**Step 5 — Review extracted facts.** Before any judgement, the user confirms the measurements the app
will use (setbacks, areas, heights…). Unlabelled or ambiguous values are shown as **drawing facts,
not measurements**, and the user can promote/correct them. Nothing is invented; gaps stay gaps.

**Step 6 — See the compliance issue list.** Issues ranked by severity (`likely_fail` →
`needs_human_review` → `missing_info` → `likely_pass`). Each is a card (§7.3). A summary header shows
counts per status so the user grasps the shape instantly.

**Step 7 — Open an issue card → why it applies → evidence.** Expanding a card reveals the why-this-applies
trail and the evidence drawer (§7.4): the rule quote, the official source + version + clause, the
spatial trigger, the drawing evidence, and the full `DecisionTrace` (the literal `3.8 m < 4.5 m`).

**Step 8 — Export the review pack.** Generate the JSON/DOCX/XLSX/HTML pack (exists) with the liability
notice and human-signoff block. The wizard ends by making explicit that this is a **draft for human
review**, reinforcing the product's assistive stance.

### 6.3 After onboarding

The user lands on the project dashboard (§7.1). The wizard's steps become the dashboard's tabs, so the
mental model is continuous. A **"Replay walkthrough"** item lives in Help; onboarding is never lost.

### 6.4 The demo project — the anti-embarrassment device

The "Try the demo" path loads a **pinned, curated demo address + demo drawings** whose every output is
a **golden eval case owned by Agent I**. It deliberately includes a mix of statuses — at least one
`likely_fail` with a crisp citation, one `needs_human_review`, one `missing_info`, and several
`likely_pass` — so a colleague sees the full, honest range and the citations behind each. Because it is
a golden case, the **weekly canary (§8.2) re-runs it and alarms if any output drifts**, so the demo a
person shows off is guaranteed to still be correct on the day they show it.

### 6.5 Accessibility & polish

```text
- Keyboard navigable; visible focus; ARIA on the stepper and cards.
- Colour is never the only signal (status has icon + label, not just red/green).
- Mobile-responsive: the wizard collapses to a single column; the demo works on a phone.
- Every async step has a real message ("Resolving parcel…"), never a bare spinner.
- Empty, error, low-confidence, and refusal states are designed, not afterthoughts.
```

---

## 7. Frontend information architecture

For a non-technical user, structure the UI around the property and its evidence — not around documents
or chat.

### 7.1 Project dashboard

```text
Header:   Address · Council · Zone · R-Code · Lot area · Overlays · Bushfire/Heritage flags
Status:   Source freshness · Drawing processing status · Last compliance run
Tabs:     Profile · Sources · Drawings · Issues · Chat (secondary) · Export
```

### 7.2 Matched-sources panel

```text
Included sources
  - State planning sources        (e.g. R-Codes, SPP)
  - Council planning scheme
  - Local planning policies
  - Structure / local development plans
  - Overlays / hazard sources
Excluded sources (with reason)
  - wrong council · stale · restricted · duplicate · superseded
```

Every included source links to its official URL, version date, and parsed text. Exclusions are shown,
not hidden — the user can see *why* something was left out, which is itself trust-building.

### 7.3 Issue cards

Each card is fully self-describing:

```text
Status:            likely_fail | likely_pass | missing_info | needs_human_review | unsupported
Rule:              Front setback minimum
Requirement:       4.5 m minimum
Proposed:          3.8 m
Result:            likely_fail
Why this applies:  Address is in City of Example, Zone R40; no relevant override found
Source:            Council LPP 2.3, clause 4.1, eff. 2024-03-01, <official URL>
Drawing evidence:  Sheet A101, dimension entity #d-204, parser run #pr-99
Calculation:       3.8 m < 4.5 m
Human review:      (only if relevant) planning discretion may apply
```

Cards are sorted by severity and filterable by status and category (planning / building-trigger /
drawing-QA).

### 7.4 Evidence drawer

Opening any card slides out a drawer with tabs, so the evidence is one click from the conclusion:

```text
Rule quote        the exact normative text, highlighted in the clause
Official source   publisher, version, effective date, canonical URL
Parsed text       the parsed/normalized text the rule was anchored to
Raw PDF           the original page image (so a reviewer can eyeball it)
Spatial source    the dataset + version that proved zone/overlay/council
Drawing evidence  the DXF/IFC entity or PDF region the measurement came from
Decision trace    inputs → formula → comparison → result → citations (reproducible)
```

### 7.5 The cardinal UI rule

**No wall of model prose anywhere.** Every regulatory statement is a structured card with a status, a
citation, and expandable evidence. If the system can't back a statement with evidence, the UI shows a
refusal/needs-info state — it does not generate reassuring text. This is §1 expressed as pixels.

---

## 8. The reliability and accuracy program (cross-cutting, owned by Agent I)

This section is the answer to "what if it's wrong in front of her colleagues?" The answer is: it is
structurally hard to be confidently wrong, and we measure correctness continuously and block releases
on regression.

### 8.1 Golden eval tracks

Five tracks, each a versioned set of input→expected cases under `tests/gold/`, run by `POST /v1/evals/run`:

| Track | Input | Expected | Primary metric |
|-------|-------|----------|----------------|
| Rule extraction | clause text | `RuleRow`(s): key, operator, value, unit, quote | exact-match rate; zero fabricated quotes |
| Spatial resolution | address | parcel, council, zone, overlays | parcel-match accuracy; overlay precision/recall |
| Retrieval faithfulness | question | expected citing source/clause | citation precision; `unsupported` correctly returned |
| Drawing extraction | sample drawing | expected measurements | measurement accuracy; false-measurement rate = 0 |
| Compliance correctness | address + drawing | expected statuses + citations | status accuracy; **zero false `likely_pass`** |

The non-negotiable metric is the last one: **a false `likely_pass` (saying something passes when it
fails) is a release-blocking defect.** A false `missing_info` is acceptable (calibrated humility); a
false pass is not.

### 8.2 Canaries

A weekly job re-runs a fixed set of real addresses + drawings — including the **demo project (§6.4)** —
and diffs every output against the last known-good. Any drift (a status flips, a citation changes, a
measurement moves) raises an alert **before** a user sees it. The demo a person shows off is therefore
protected by a canary.

### 8.3 Release gates

```text
- CI runs all five eval tracks on every PR; merge is BLOCKED if any track regresses below threshold.
- Deploy is BLOCKED if the compliance track shows any new false likely_pass.
- Source approval (Agent B) is BLOCKED when the source's extracted rules fail the rule-extraction or
  no-orphan/normative audits.
- Model/provider/prompt changes must pass the retrieval + rule-extraction tracks before rollout.
```

### 8.4 The "no orphan law" audit (Agent C)

After extraction, nothing normative may be left unaccounted for. The audit flags any orphaned:

```text
numbers · percentages · distances · dates · exceptions · definitions ·
table cells · cross-references · amendment notes
```

An orphan blocks source approval or routes to the rule-review queue. This is what stops "the parser
silently dropped clause 4.1(b)" from ever reaching a user as a clean pass.

### 8.5 The normative-language audit (Agent C)

Every clause containing normative language —

```text
must · shall · required · not permitted · unless · except · may be approved ·
deemed-to-comply · performance criteria · acceptable outcome
```

— must be dispositioned as `rule_bearing`, `definition`, `procedural`, or `manual_review`. It may
**never** be labelled `informational`/fluff. If the extractor can't turn a normative clause into a
`RuleRow`, that clause goes to human review — it is never silently ignored.

### 8.6 First-class human-review queues (Agent I framework; fed by all)

Review is a product surface, not an afterthought. Six queues:

```text
Source review · Rule review · Spatial ambiguity review ·
Drawing extraction review · Conflict review · Licence review · Eval-failure review
```

Each `ReviewQueueItem` carries: `reason`, `blocking_level`, `evidence`, `suggested_action`, `assignee`,
`status`, and an audit log. Items with `blocking_level=blocking` prevent the affected output from being
shown as a confident result until cleared.

### 8.7 Ops & freshness dashboard (Agent I)

`GET /v1/ops/dashboard` surfaces:

```text
sources current/stale · rules approved/pending/stale · address profiles current/stale ·
spatial datasets current/stale · job failures · unsupported-answer rate · missing-info rate ·
eval pass/fail per track · last successful backup · last successful restore test
```

A rising `unsupported`/`missing_info` rate is a *health signal*, not a bug — it means the library needs
more sources, and it's far safer than a rising false-pass rate.

### 8.8 Parser consensus (Agent E)

Because cost is no object, do not trust a single parser. For each parsed artifact, run pypdf, Docling,
Unstructured, and OCR; store all outputs in `DocumentArtifact`; select a canonical text with a recorded
`canonical_selection_reason` (agreement, table fidelity, or human correction). Disagreement above a
threshold routes to drawing/source review.

### 8.9 Honest calibration

We report two numbers that matter and never hide them: **(a) accuracy on the things we *do* judge**
(target: extremely high, zero false passes), and **(b) coverage — the share of questions we can answer
at all** (lower is fine; it grows as the library grows). We optimize (a) ruthlessly and grow (b)
deliberately. Saying "I can't prove this yet" is a feature.

---

## 9. Hardening additions (folded in and assigned)

These close gaps present in none of the original plans on their own. Each is assigned to an owning agent.

```text
A. Source licence gate            (Agent B)  SourceLicenceReview before any text can support an answer.
B. Jurisdiction normalization     (Agents B/C/D) canonical fields everywhere: jurisdiction_level
   (state|local|federal|private|standard|guidance), state, local_government_id, applies_statewide,
   instrument_type, effective_from/to, supersedes_source_version_id — this is what lets the system
   answer "for THIS address, which statewide and council rules apply?"
C. Council as a spatial/legal fact (Agent D) LocalGovernmentFact with method
   (parcel_intersection|point_intersection|manual_override) + confidence + dataset version. Never infer
   council from a document URL or a Google address.
D. Parser comparison table        (Agent E)  DocumentArtifact stores every parser's output + canonical
   selection + reason (consensus, not blind trust).
E. Clause page images             (Agents B/E)  store page render images in MinIO so reviewers can
   compare raw PDF page → OCR/text/table → extracted rule.
F. Extended no-orphan audit       (Agent C)  §8.4.
G. First-class review queues      (Agent I)  §8.6.
H. Upload & scraping security     (Agent A)  malware scan, size limits, type sniffing (not extension),
   sandboxed CAD conversion, no public bucket, short-expiry signed URLs, per-job limits, endpoint rate
   limits, auth + tenant isolation before public use.
I. Backup/restore acceptance      (Agent A)  daily encrypted offsite DB + MinIO backups, restore tested
   on a clean machine, restore time recorded, checksum validation, DR runbook.
J. Data freshness dashboard       (Agent I)  §8.7.
```

---

## 10. De-duplicated master build order

The single ordered sequence, each step tagged with its owning agent and phase. Order reflects the
dependency logic: applicability needs spatial context; graph retrieval needs structured legal
references; the address-first wizard needs spatial resolution; everything needs the production base.

```text
PHASE 0 — Foundations
  1.  Convert VPS stack to PostGIS + pgvector + MinIO + Redis/RQ + Caddy.            [A]
  2.  Import existing corpus → SourceDocument, SourceVersion, SourceArtifact, SourceChunk. [B]
  3.  Stand up the source review UI/API BEFORE expanding chat.                        [B]
  4.  Scaffold the golden eval runner + first cases; wire CI release gate (empty-but-real). [I]

PHASE 1 — The spine (legal structure + spatial)
  5.  Add Clause hierarchy, ClauseReference, source-version diffs.                    [C]
  6.  Add RuleRow, RuleExtractionCandidate, ClauseDisposition, quote-anchor validators. [C]
  7.  Build deterministic single-source rule extraction (3-pass).                     [C]
  8.  Add no-orphan + normative-language + table audits; block approval on failure.   [C+I]
  9.  Add SpatialDataset, Parcel, AddressPoint, PlanningLayerFeature, LGA boundaries. [D]
  10. Build POST /v1/address/resolve → AddressProfile + AddressFact (PostGIS).        [D]
  11. Build the wizard SHELL against resolve + stubbed results (steps 0–3 live).      [H]

PHASE 2 — Real results (applicability + drawings + compliance + full wizard)
  12. Build precedence resolver + POST /v1/projects/{id}/resolved-rules.              [F]
  13. Switch compliance engine to use ResolvedRule before any default check.         [F]
  14. Add DecisionTrace to every ComplianceCheckResult.                              [F]
  15. Upgrade DXF extraction with ezdxf; add IFC via IfcOpenShell.                    [E]
  16. Add parser abstraction: Docling + Unstructured + OCR fallback + consensus.      [E]
  17. Complete the wizard (steps 4–8) + issue cards + evidence drawer + matched sources. [H]

PHASE 3 — Explanation & maintenance
  18. Add hybrid retrieval (FTS + pgvector + rerank) + graph expansion; keep it OUT of
      compliance decisions; wire chat as a secondary helper.                         [G]
  19. Add source refresh, staleness, diffs, supersession detection, weekly canaries.  [B+I]

PHASE 4 — Scale & polish
  20. Monitoring, encrypted offsite backups + tested restore, upload security, tenant
      isolation, ops/freshness dashboards; then expand council coverage.             [A+I+D]
```

This is the same 20-step spine from the merged plan, re-tagged to agents and phases and reconciled to
the canonical names in §3–4.

---

## 11. Phasing and milestones with exit criteria

A phase is "done" only when its exit criteria are green. Do not start a later phase's user-facing
claims on an earlier phase's incomplete foundation.

### Phase 0 — Foundations *(Agents A, B, I)*

**Goal:** a secure, observable stack with the evidence vault loaded and an eval harness that can fail a
build.

```text
Exit criteria:
  - docker compose up → all services healthy; PostGIS + pgvector enabled; Alembic migrates clean.
  - Corpus imported; every source has provenance + licence status; source review API live.
  - Eval runner exists and is wired into CI as a (currently lenient) release gate.
  - Encrypted offsite backup running; a restore has been performed on a clean machine once.
```

### Phase 1 — The spine *(Agents C, D, early H)*

**Goal:** prove rules from sources, and resolve an address to parcel/zone/overlays — the two halves
that make any honest compliance claim possible.

```text
Exit criteria:
  - RuleRows are quote-anchored and pass no-orphan + normative audits on the seed corpus.
  - /v1/address/resolve returns proven parcel + council + zone + overlays with confidence + versions,
    and correctly returns missing_info / needs_human_review on ambiguous inputs.
  - Wizard steps 0–3 work end-to-end against the real resolver.
  - Spatial + rule-extraction eval tracks are green above threshold.
```

### Phase 2 — Real results *(Agents E, F, H)*

**Goal:** turn drawings + resolved rules into cited issue cards with decision traces — the demo.

```text
Exit criteria:
  - Precedence resolver selects ResolvedRules; overrides recorded, never deleted.
  - Compliance engine emits pass/fail only under §1.4; every result has a DecisionTrace + citation.
  - DXF (ezdxf) + IFC (IfcOpenShell) + multi-parser/OCR consensus produce evidence-linked measurements.
  - Wizard runs end-to-end; the demo project (§6.4) produces a correct mixed-status result.
  - Compliance eval track green with ZERO false likely_pass.
```

### Phase 3 — Explanation & maintenance *(Agents G, B, I)*

```text
Exit criteria:
  - Hybrid retrieval + chat answer with citations or refuse (unsupported); never judge compliance.
  - Source refresh/diff/supersession runs on a cadence; weekly canaries green; drift alerts wired.
```

### Phase 4 — Scale & polish *(Agents A, I, D)*

```text
Exit criteria:
  - Monitoring + uptime checks across all services; ops/freshness dashboard live.
  - Backups encrypted + offsite; restore tested + timed + checksum-validated; DR runbook signed off.
  - Upload security + auth + tenant isolation enforced before any public exposure.
  - A documented process exists to add a new council (datasets + sources + evals) repeatably.
```

---

## 12. Cross-agent coordination protocol

Nine agents touching one codebase need rules to avoid collisions and integration drift.

### 12.1 The contract is the canonical data model

§4's entity names and §15's API shapes are the **shared contract**. An agent may not rename a shared
entity or change a shared payload without updating §4/§15 and notifying dependents. The data model is
the lingua franca; speak it exactly.

### 12.2 Single-writer ownership

Each table has exactly one owning agent that may write it (the owner in §5). Other agents **read** via
that agent's service/endpoint, never by writing the table directly. Examples: only D writes
`AddressProfile`/`AddressFact`; only C writes `RuleRow`; only F writes `ResolvedRule`/`DecisionTrace`;
only B writes `SourceVersion`. This prevents two agents racing on the same rows.

### 12.3 Dependency DAG (who unblocks whom)

```text
A ──► everyone
B ──► C, G
C ──► F, G
D ──► F, H
E ──► F, H
F ──► H
G ──► H (secondary)
I ──► gates all (release authority)
```

Build leaf-first: A and B before C/D; C/D/E before F; F before H's result views. H can start its shell
(steps 0–3) as soon as D's resolve endpoint exists, against stubs for the rest.

### 12.4 Integration checkpoints

```text
- Contract tests: each producer endpoint (resolve, resolved-rules, compliance/run, ask) ships with a
  schema contract test; consumers (H, F) test against the recorded contract, not a live service.
- Weekly integration run: full pipeline on the demo address; result diffed by Agent I's canary.
- Migration discipline: every schema change is one Alembic revision + a §4 update in the same PR.
- Status discipline: no PR merges if it can emit a regulatory output without a §1.3 status + citation.
```

### 12.5 Branch & review discipline

```text
- One agent, one workstream branch; small PRs; green CI (lint, types, tests, eval gate) before merge.
- Any PR that adds a regulatory output path requires an Agent I eval case in the same PR.
- §1.5 invariants are enforced in code review and, where possible, in tests (e.g., a unit test that a
  result with no citation can never carry likely_pass).
```

---

## 13. Open-source tool shortlist

Use these as **components, not as the product architecture**. The architecture is §2; these are the
parts that snap into it.

| Area | Tool | Use | Owner |
|------|------|-----|-------|
| Spatial database | **PostGIS** | parcel/council/zone/overlay/buffer/intersection queries | A, D |
| Vector search | **pgvector** | embeddings in Postgres; HNSW/IVFFlat ANN search | A, G |
| Document parsing | **Docling** | PDF/DOCX/table → structured (MIT-licensed) | E |
| Document ETL | **Unstructured** | second parser path for PDF/HTML/Word/image/text | E |
| OCR | **PaddleOCR** (or Tesseract) | scanned/image-only documents | E |
| DXF | **ezdxf** | DXF read/inspect across versions; layers/entities/dimensions | E |
| IFC / BIM | **IfcOpenShell** | IFC parsing + geometry; object-level evidence | E |
| Policy export (later) | **OPA** | optional future policy-engine export — NOT a v1 runtime dep | F |
| RAG orchestration (optional) | **Haystack** | only if retrieval orchestration gets messy | G |
| Crawling (delegated) | **Hermes** + lawful fetcher | heavy scraping stays delegated; in-repo fetcher does robots/licence checks | B |

Decision reminders baked in elsewhere: **no Neo4j** until traversal is a proven bottleneck (§3.5);
**no OPA runtime** in v1 — deterministic Python evaluator first, OPA-compatible export later (§5 F);
loaders use **DuckDB/`ogr2ogr`**, not geopandas, for statewide scale (`SPATIAL_ENGINE_DESIGN.md`).

---

## 14. Risks, licensing critical path, and assumptions

```text
CRITICAL PATH — data licensing (start in Phase 0, parallel to infra):
  - Landgate cadastre + some PlanWA/DPLH layers have access/licence terms to clear before ingestion.
  - The SourceLicenceReview gate (Agent B) must pass before any source text supports an answer.
  - Australian Standards stay metadata-only unless lawfully licensed and reviewed.

KEY RISKS & MITIGATIONS:
  - False likely_pass (the embarrassment risk) → §1.4 preconditions + §8.1 zero-false-pass gate +
    §8.2 canaries protect the demo specifically.
  - Spatial mis-resolution → no LGA-only proof; ambiguous → human review; provenance on every fact.
  - Parser error dropping a clause → no-orphan + normative audits block approval (§8.4–8.5).
  - Source drift → versioned sources, supersession detection, freshness dashboard (§8.7).
  - Scope creep across agents → single-writer ownership + the canonical contract (§12).

ASSUMPTIONS:
  - WA-first; the schema stays jurisdiction-generic so other states are an adapter, not a rewrite.
  - Cost is not the binding constraint; correctness and maintainability are (hence parser consensus).
  - The backend stays backend-only; the frontend is a separate app served by Caddy.
  - Effort: this is a multi-month program; phases gate user-facing claims, not calendar dates.
```

---

## 15. Appendix: API surface, status enums, key payloads

### 15.1 Status enums

```text
CheckStatus (regulatory results):
  likely_pass | likely_fail | missing_info | needs_human_review | not_applicable | unsupported

Confidence (spatial/resolution):
  high | medium | low

AddressResolutionStatus:
  resolved | missing_info | needs_human_review | unsupported

ClauseDisposition:
  rule_bearing | definition | procedural | informational | manual_review

RuleExtractionCandidate.status:
  candidate | pending_review | rejected

RuleRow.lifecycle_status:
  auto_accepted | approved | pending_review | rejected | stale | superseded

detected_by (overlays/facts):
  manual | spatial | spatial_low_confidence

jurisdiction_level:
  state | local | federal | private | standard | guidance
```

### 15.2 Canonical endpoints (the frontend/backend seam)

```text
# Spatial / address (Agent D)
POST /v1/address/resolve                         → AddressProfile + AddressFact
POST /v1/projects/{id}/property/resolve          → writes Property from resolution
GET  /v1/projects/{id}/property/profile          → property profile + provenance
POST /v1/properties/resolve                       (deprecated alias)

# Sources (Agent B)
POST /v1/sources/import
POST /v1/sources/hermes-corpus/import            (exists)
GET  /v1/sources  ·  GET /v1/sources/{id}
POST /v1/sources/{id}/review
GET  /v1/sources/freshness

# Rules / clauses (Agent C)
GET  /v1/clauses/{id}  ·  GET /v1/rules  ·  POST /v1/rules/{id}/review

# Drawings (Agent E)
POST /v1/projects/{id}/documents/upload          (exists, extended)
GET  /v1/projects/{id}/documents/{id}/facts

# Compliance (Agent F)
POST /v1/projects/{id}/resolved-rules
POST /v1/projects/{id}/compliance/run
GET  /v1/projects/{id}/compliance/matrix

# Retrieval / chat (Agent G)
POST /v1/ask  ·  GET /v1/projects/{id}/document-search

# Quality / ops (Agent I)
POST /v1/evals/run  ·  GET /v1/evals/runs/{id}
GET  /v1/review-queues  ·  GET /v1/ops/dashboard
```

### 15.3 `POST /v1/address/resolve` response

```json
{
  "address_profile_id": "uuid",
  "formatted_address": "12 Example St, Suburb WA 6000",
  "resolution_status": "resolved",
  "confidence": "high",
  "resolver_sources": ["gnaf", "cadastre", "planwa", "dfes"],
  "parcel": { "lot_plan": "41/12345", "area_m2": 512.4, "source_dataset_version_id": "uuid" },
  "local_government": { "name": "City of Example", "confidence": "high",
                        "method": "parcel_intersection", "source_dataset_version_id": "uuid" },
  "facts": [
    { "fact_type": "zone", "value_json": { "label": "Residential", "code": "R40" },
      "confidence": "high", "method": "parcel_intersection",
      "source_version_id": "uuid", "spatial_dataset_id": "uuid" },
    { "fact_type": "bushfire_prone", "value_json": { "value": false },
      "confidence": "high", "method": "feature_intersection",
      "source_version_id": "uuid", "spatial_dataset_id": "uuid" }
  ],
  "planning": { "zone": "Residential R40", "r_code_density": "R40" },
  "issues": []
}
```

When geometry is missing: `resolution_status: "missing_info"`, `confidence: "low"`, `planning` as
`null`, and a clear `issues: ["parcel_not_verified"]` — never a fabricated zone/overlay.

### 15.4 Issue card / `ComplianceCheckResult` shape

```json
{
  "status": "likely_fail",
  "rule": "Front setback minimum",
  "requirement": { "operator": ">=", "value": 4.5, "unit": "m" },
  "proposed": { "value": 3.8, "unit": "m" },
  "why_this_applies": "City of Example, Zone R40; no override found",
  "resolved_rule_ids": ["rr_..."],
  "citations": [{ "source_title": "City of Example LPP 2.3", "clause_id": "4.1",
                  "version_label": "2024-03-01", "canonical_url": "https://…" }],
  "drawing_evidence": { "sheet": "A101", "entity_id": "d-204", "parser_run_id": "pr-99" },
  "decision_trace_id": "dt_...",
  "human_review_reason": null
}
```

### 15.5 `DecisionTrace` shape

```json
{
  "id": "dt_...",
  "inputs": { "front_setback_m": 3.8, "required_min_m": 4.5 },
  "formula": "proposed >= required",
  "comparison": "3.8 >= 4.5",
  "result": "likely_fail",
  "rule_ids": ["rr_..."],
  "measurement_ids": ["dm_..."],
  "citation_ids": ["cit_..."]
}
```

### 15.6 The rule the whole product reduces to (repeated, because it governs everything)

```text
For a given address: prove the parcel and council, prove the zoning/overlays, select the applicable
state and local rules, prove each rule from an official source, extract drawing facts conservatively,
compare facts to rules deterministically, show the result with exact citations and evidence, and
refuse or mark human review whenever proof is incomplete.
```

*End of master plan.*
# SUPERSEDED - see docs/MASTER_REBUILD_PLAN.md

This file is background context only for the V3 rebuild. Do not use it as implementation
authority where it conflicts with `docs/MASTER_REBUILD_PLAN.md`.
