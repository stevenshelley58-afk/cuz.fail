# M1 Fixture Manifest — Pre-stage Assets

**Session:** B — Pre-stage M1 Fixture Assets  
**Authority:** `docs/MASTER_REBUILD_PLAN.md` §8.4 (check statuses), §9 Phase 5 (M1 gate), §12 (invariants)  
**Date produced:** 2026-06-09  
**Sole output directory:** `data/fixtures/m1/` (do not write to `tests/fixtures/golden/` — that is Stage 2 scope)

> **ALL VALUES ARE ILLUSTRATIVE TEST DATA.** No value in this directory is an authoritative
> R-Codes, LPS, or planning scheme value. Hardcoding any of these illustrative values in
> compliance engine code is a defect (ref: MASTER_REBUILD_PLAN.md §0.23, §12).

---

## Asset Index

| Asset | Type | Supports check | Expected outcome |
|---|---|---|---|
| `site_plan.pdf` | Site plan drawing (PDF) | All 5 Tier-1 checks | See table below |
| `generate_site_plan.py` | Generator script (Python/PyMuPDF) | — | Deterministic re-generation |
| `eval/quote_anchoring.json` | Eval case stub | `extract_rules` | `valid=false` (quote mismatch) |
| `eval/unit_normalization.json` | Eval case stub | `extract_rules` | `likely_fail` after mm→m normalization |
| `eval/no_orphan.json` | Eval case stub | `extract_rules` | `extraction_allowed=false` (orphan) |
| `eval/refuse_not_guess.json` | Eval case stub | `run_compliance_check` | `needs_more_info` (not promoted) |
| `eval/cite_or_refuse.json` | Eval case stub | `search_ask` | `answered=false` (no approved source) |
| `spatial/parcel.geojson` | Parcel polygon | Address resolution | Parcel lookup succeeds |
| `spatial/address_point.geojson` | G-NAF-shaped address point | Address resolution | Address→parcel link present |
| `spatial/zoning.geojson` | LPS zone + R-code | Rule applicability | R60 zone resolved |
| `spatial/lga.geojson` | LGA boundary (simplified) | Jurisdiction gating | City of Vincent confirmed |

---

## Site Plan: Designed-in Outcomes (3 pass / 1 fail / 1 needs_more_info)

All values are illustrative. Real R-Codes values must be bound at Stage 3/5.

The five primary designed outcomes map the session-B brief exactly:

| # | Check key | Drawing element | Illustrative value | Illustrative threshold | Expected outcome | Marker |
|---|---|---|---|---|---|---|
| 1 | `primary_street_setback` | Front setback dimension | 7.0 m | min 6.0 m | `likely_pass` | — |
| 2 | `side_setback` | Left side setback dimension | **0.8 m** | **min 1.0 m** | **`likely_fail`** | **★1** |
| 3 | `open_space` | Rear+side yard annotation | ~65% (~312/480 sqm) | min 45% | `likely_pass` | — |
| 4 | `garage_dominance` | Garage width / lot frontage | 3.0m / 15.0m = 20% | max 50% | `likely_pass` | — |
| 5 | `boundary_wall_length` | Boundary wall with "~9.5m?" label | **~9.5 m? (unverified)** | *(calibration required)* | **`needs_more_info`** | **★2** |

> **Note on site coverage:** The drawing also shows site coverage (168/480 sqm = ~35%, illustrative max 50%, supporting context → `likely_pass`) as a derived annotation on the building footprint. This is additional supporting data, not one of the 5 primary designed outcomes. The `site_cover` Tier-1 check is fully supported by the parcel + footprint dimensions in the spatial and drawing records; Stage 2 can map it as a 4th pass if desired, or leave it as supporting context.

**★1** The left side setback (0.8m) is measurably and unambiguously below the illustrative 1.0m minimum. The drawing labels this in red as "UNDER MIN". This is Designed-in non-pass #1.

**★2** The boundary wall is labeled "~9.5 m?" with "[scale unverified — not promotable]". The "~" and "?" signal an uncalibrated/ambiguous measurement that cannot be promoted under §5.6. This is Designed-in non-pass #2.

---

## Eval Case Stubs

### `eval/quote_anchoring.json`
- **Track / skill:** `extract_rules`
- **Case key:** `quote_anchoring_mismatch_rejected`
- **Purpose:** Validates that rule extraction rejects any candidate whose `quote` field is not a verbatim substring of the source clause text.
- **Input:** Clause text + candidate with a paraphrased (non-verbatim) quote.
- **Expected:** `valid=false`, `error=quote_not_found_verbatim_in_clause`
- **Invariant ref:** MASTER_REBUILD_PLAN.md §8.1 quote-anchor validation

### `eval/unit_normalization.json`
- **Track / skill:** `extract_rules`
- **Case key:** `unit_normalization_mm_to_m`
- **Purpose:** Validates that 1000mm is correctly normalized to 1.0m before comparison, and that the trace records the conversion.
- **Input:** Clause with "1000 millimetres" + proposed measurement of 0.9m.
- **Expected:** Normalized rule=1.0m, proposed=0.9m, comparison "0.9m < 1.0m" → `likely_fail`.
- **Invariant ref:** MASTER_REBUILD_PLAN.md §5.5 `decision_trace_json.unit_conversions`

### `eval/no_orphan.json`
- **Track / skill:** `extract_rules`
- **Case key:** `no_orphan_table_without_clause_context`
- **Purpose:** Validates that table values without a parent normative clause (`clause_id=null`) are rejected as orphans and not promoted to rule candidates.
- **Input:** Isolated table with zone/setback values and `parent_clause_id=null`.
- **Expected:** `extraction_allowed=false`, `error=orphan_table_no_clause_context`
- **Invariant ref:** MASTER_REBUILD_PLAN.md §8.1 no-orphan audit

### `eval/refuse_not_guess.json`
- **Track / skill:** `run_compliance_check`
- **Case key:** `refuse_not_guess_uncalibrated_raster_measurement`
- **Purpose:** Validates that the compliance engine returns `needs_more_info` rather than guessing when a measurement has `promoted_to_measurement=false` and `calibration_evidence=null`.
- **Input:** `boundary_wall_length` check with a raster PDF fact (`review_status=unconfirmed`, `promoted_to_measurement=false`).
- **Expected:** `status=needs_more_info`, no `likely_pass` or `likely_fail` emitted.
- **Invariant ref:** MASTER_REBUILD_PLAN.md §5.6 promotion contract, §8.3, §12

### `eval/cite_or_refuse.json`
- **Track / skill:** `search_ask`
- **Case key:** `cite_or_refuse_no_approved_source`
- **Purpose:** Validates that `/search/ask` refuses (does not hallucinate) when `available_approved_source_version_ids` is empty.
- **Input:** A question about R-Codes setbacks with no approved sources in scope.
- **Expected:** `answered=false`, `refusal_reason=no_approved_source_supports_this_answer`, `job_trace_written=true`.
- **Invariant ref:** MASTER_REBUILD_PLAN.md §7 (cite-or-refuse; substrate required even on refusal)

---

## Spatial Records

All spatial files tagged `synthetic: true`. CRS: **GDA2020 (EPSG:7844)** throughout. Test parcel centroid: ~115.8486°E, 31.9324°S (North Perth / City of Vincent, WA).

### `spatial/parcel.geojson`
Synthetic cadastral parcel polygon. Lot 15 (illustrative), 15.0m × 32.0m = 480 sqm.  
NOT a real Landgate cadastral record. Landgate SLIP licence must be confirmed before production parcel data is used (MASTER_REBUILD_PLAN.md §8.2 risk register).

### `spatial/address_point.geojson`
Synthetic G-NAF-shaped address point. "15 LOFTUS STREET NORTH PERTH WA 6006" (illustrative).  
NOT a real G-NAF record. GNAF-PID: `SYNTHETIC-WA123456789ABC`.

### `spatial/zoning.geojson`
Synthetic LPS zone feature: City of Vincent LPS2, R60 residential zone.  
NOT from a real DPLH WFS or council GIS dataset. R-code R60 is an illustrative test value.

### `spatial/lga.geojson`
Highly simplified (rectangular) City of Vincent LGA boundary. ~11.2 km² approximate extent.  
NOT the real LGA boundary. Real boundary must be obtained from Landgate admin boundaries dataset.

---

## Stage 2 / Stage 3 Handoff

**Stage 2 (Fixtures Owner):**
- Adopt `site_plan.pdf` as the M1 canary drawing input for `tests/fixtures/golden/`.
- Map the drawing's `document_facts` to the five Tier-1 check keys with the outcomes shown above.
- The left side setback (0.8m) must produce `likely_fail` in the golden fixture; the boundary wall (~9.5m?) must produce `needs_more_info`. Do not change these designed-in outcomes.

**Stage 3 (Eval Gate / Legal):**
- Replace all `source_version_id: "__BIND_AT_STAGE_3__"` placeholder strings in `eval/*.json` with the UUID of the approved WA R-Codes source version once it has been extracted, quote-anchored, and promoted in Phase 3.
- The clause texts in the eval stubs are illustrative paraphrases — real R-Codes text must not be stored here until a lawfully-obtained, licence-reviewed source version exists.

**Stage 5 (M1 Gate):**
- The boundary wall `~9.5m?` measurement must remain `needs_more_info` unless calibration evidence is provided and the fact is promoted through the promotion contract (§5.6).
- The M1 demo must show all five Tier-1 checks with the expected outcomes; any `likely_pass`/`likely_fail` requires rule + promoted measurement + citation + trace.

---

## Safety Checklist (Reviewer gate)

- [x] Three primary pass outcomes: front setback (PASS), open space (PASS), garage dominance (PASS). Site coverage is supporting context (also PASS) but not one of the 5 primary designed outcomes.

- [x] The designed-in `likely_fail` (left side setback 0.8m) is measurably and unambiguously below the illustrative minimum (1.0m) and is labeled "UNDER MIN" in red.
- [x] The designed-in `needs_more_info` (boundary wall ~9.5m?) uses "~" and "?" labels plus "scale unverified — not promotable" to signal the ambiguous/uncalibrated nature.
- [x] CRS is GDA2020 (EPSG:7844) in all four spatial files.
- [x] No value is presented as authoritative: all files carry `"synthetic": true`, `"illustrative": true`, and explicit safety notes.
- [x] `source_version_id: "__BIND_AT_STAGE_3__"` placeholder used in all eval stubs; no real source version UUID is present.
- [x] Generator script (`generate_site_plan.py`) is committed alongside the PDF; re-running it produces an identical result.
- [x] No paid Standards Australia text, no real R-Codes values, no real LGA/cadastral data.
