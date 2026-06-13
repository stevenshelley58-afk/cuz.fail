# WP4 Blocked Manifest Triage — 2026-06-13

Generated: 2026-06-13. Reduced 179 blocked rows → 0 across 5 deterministic SQL passes (no LLM).

## Before / after

| Status         | Before (2026-06-12) | After (2026-06-13) |
|----------------|---------------------|--------------------|
| acquired       | 281                 | 281                |
| metadata_only  | 14                  | 19                 |
| out_of_scope   | 17                  | 191                |
| blocked        | 179                 | 0                  |
| pending        | 0                   | 0                  |
| **total**      | 491                 | 491                |

## Pass-by-pass

| Pass | Rule | Rows |
|------|------|------|
| 1 | AS/NZS standards → metadata_only (paid per CORPUS_SCOPE.md) | 5 |
| 1 | Aboriginal Cultural Heritage Acts → out_of_scope (per CORPUS_SCOPE.md: heritage *mapping* only) | 4 |
| 1 | Building Act 2011 / Heritage Act → out_of_scope (process, not design rules; NCC carries technical) | 2 |
| 1 | Strata Titles Act → out_of_scope (tenure) | 3 |
| 1 | Environmental Protection / EPBC → out_of_scope (assessment process) | 6 |
| 1 | Commonwealth law (except NCC) → out_of_scope | 5 |
| 1 | OCR garbage titles (`Bas UNDER...`, `Assent Commencement...`, `Framework...`, OCR of `Planning`) | 12 |
| 1 | Phantom SPPs (SPP 10/16/18/29/57 — no such SPPs exist; extraction citation errors) | 5 |
| 1 | Niche acts (Cement Works, Bunbury Pipeline, Caravan & Camping, Explosives & Dangerous Goods, etc.) | 10 |
| 1 | CALM Act / Contamination Sites Act → out_of_scope | 2 |
| 2 | Section/citation fragments (`OF...`, `Part X of...`, `Statements STATE PLANNING...`) | 10 |
| 2 | "The X" duplicates of acquired Acts/Regs | 14 |
| 2 | Out-of-scope topics (income tax, legal profession, mining, telecoms, native title, wildlife, fisheries) | 32 |
| 2 | Amendment/superseded Acts and Regulations (consolidated parent already acquired) | 27 |
| 2 | Heritage of WA Act 1990 (legacy) → out_of_scope per scope | 2 |
| 2 | LPS No. 3 orphan citations (City of Cockburn TPS 3 acquired) | 2 |
| 2 | UPPERCASE SPP duplicates (case-insensitive dedup) | 2 |
| 2 | Unqualified SPPs (SPP 2 / 3 / 5 without version) | 3 |
| 3 | Remaining OCR/fragment titles (Note the.../OF.../Part.../Statements.../etc.) | 14 |
| 3 | Strata Titles Amendment Acts → out_of_scope per scope | 3 |
| 3 | Term Rental Accommodation Act 2024 → out_of_scope (short-term rentals, not residential design) | 1 |
| 3 | Biodiversity Conservation Regs 2018 → out_of_scope per scope | 1 |
| 3 | WA P&D Regulations 2009 (legacy/superseded variant citation) | 1 |
| 4 | "Planning and Development Local Planning Scheme Regulations 2015" dup of acquired LPS Regs 2015 | 1 |
| 4 | "Planning and Development Regulations 2015" — no such standalone; extraction error | 1 |
| 5 | SPP 2.1/2.2/2.3/2.7/2.10 → out_of_scope (consolidated into SPP 2.9 Planning for Water, acquired) | 5 |
| 5 | SPP 3.1 → out_of_scope (consolidated into SPP 7.3 R-Codes under Design WA Stage 1, acquired) | 1 |
| 5 | SPP 4.3 → out_of_scope (legacy SPP not in current wa.gov.au SPP listing) | 1 |
| 5 | SPP 7.1 → out_of_scope (consolidated into SPP 7.0 Design of the Built Environment, acquired) | 1 |
| 5 | DCP 1.4 (legacy 1988 Functional Road Classification) → out_of_scope (covered by DC1.7, acquired) | 1 |
| 5 | DCP 2.3 → out_of_scope (legacy; covered by Liveable Neighbourhoods + SPP 2.6 framework) | 1 |
| 5 | DCP 3.7 → out_of_scope (no such DCP; SPP 3.7 Bushfire is acquired) | 1 |
| **Total** |  | **179** |

## Verification queries

```sql
SELECT status, count(*) FROM target_manifest GROUP BY status ORDER BY 1;
--   acquired      | 281
--   metadata_only |  19
--   out_of_scope  | 191
SELECT count(*) FROM target_manifest WHERE status IN ('blocked','pending'); -- 0

-- Spot-check the out_of_scope notes are present and meaningful:
SELECT instrument_name, substring(notes, 1, 100)
FROM target_manifest
WHERE status='out_of_scope'
ORDER BY random()
LIMIT 10;
```

## Reproducibility

The 5 SQL passes are committed at `reports/wp4/triage_pass*.sql`. They are idempotent
(every UPDATE is gated on `status='blocked'`), so re-running them on a manifest with
new blocked rows will only touch new matches and leave the existing decisions intact.
