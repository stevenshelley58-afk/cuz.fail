# WA Planning Corpus — Scope Declaration

Date: 2026-06-10
Authority: `docs/MASTER_REBUILD_PLAN.md` (V3); operationalizes §8.1 (sources pipeline) and §9 (gates)
Gates: every "is this doc needed?" question; every "should we cite this?" question
Status: **Phase 0 of `docs/CORPUS_COMPLETENESS_PLAN.md` closed**

This file is the single source of truth for corpus scope. The manifest (`data/manifest.csv`) carries row-level status (`acquired | metadata_only | blocked | out_of_scope`); the alias map (`data/instrument_aliases.json`) names every instrument under every alias; the gap report (`reports/citation_gaps.json`) records citations the corpus cannot yet answer. When any of those three disagrees with this document, **this document wins** until a Phase-0 amendment updates it.

---

## In scope (M1 / pilot LGA list)

### WA-published codes and policies (state-level)

| Category | What we hold | Manifest rows |
|---|---|---|
| Planning codes | R-Codes Volume 1 (SPP 7.3, current consolidation), R-Codes Volume 2 (Apartments) | PC-001, PC-002 |
| Explanatory guidelines | R-Codes Vol 1 Explanatory Guidelines | PC-003 |
| State Planning Policies (SPPs) | SPP 1 through current, consolidated in force; supersedes older SPP 2.x sub-policies (2.1/2.2/2.3/2.7/2.10 aliased to SPP 2.9) | SPP-001 … SPP-029 |
| Operational / Development Control Policies | Current operational policies (formerly DC) | DC-001 … DC-018 |
| Position statements | Current set | PS-001 … PS-011 |
| Planning bulletins | Current set (only the non-superseded ones) | PB-001 … PB-013 |
| Region schemes | Metropolitan Region Scheme text + index; PRS, GBRS (where published) | RS-001, RS-002, RS-003 |

### Legislation (subsidiary to Planning and Development Act 2005)

| Act / Regulation | Manifest row |
|---|---|
| Planning and Development Act 2005 | LEG-001 |
| Building Act 2011 | LEG-002 |
| Building Regulations 2012 | LEG-003 |
| Strata Titles Act 1985 | LEG-004 |
| Environmental Protection Act 1986 | LEG-005 |
| Bush Fires Act 1954 | LEG-006 |
| Heritage Act 2018 | LEG-007 |
| Planning and Development (Local Planning Schemes) Regulations 2015 (deemed provisions) | REG-001 |
| Planning and Development (Development Assessment Panels) Regulations 2011 | REG-002 |
| Planning and Development Regulations 2009 | REG-003 |

### National Construction Code (free ABCB registration-walled)

| Volume | Manifest row |
|---|---|
| NCC 2022 Volume One | NCC-001 |
| NCC 2022 Volume Two | NCC-002 |
| NCC 2022 Volume Three (Housing Provisions) | NCC-003 |

### Local planning instruments — pilot LGA list (M1)

Per `docs/MASTER_REBUILD_PLAN.md` §2.5, the M1 pilot LGAs are:

- **City of Melville** (most-developed coverage): LPS6 + scheme maps + every LPP + structure plans (Canning Bridge, Kardinya, Murdoch, Riseley, Willagee, Melville District)
- **City of Joondalup**: LPS3 + scheme maps + LPPs
- **City of Fremantle**: LPS4 + scheme maps + LPPs

Manifest rows for these:
- `MEL-SCH-001`, `MEL-SCH-002`, `MEL-MAP-001` … `MEL-MAP-008`, `MEL-LPP-001` … `MEL-LPP-021` (except `MEL-LPP-016` which is a known broken asset — see gaps), `MEL-SP-001` … `MEL-SP-007`
- `JOO-SCH-001`, `JOO-LPP-001` … `JOO-LPP-009`
- `FRE-SCH-001`, `FRE-LPP-001` … `FRE-LPP-032`

---

## Metadata-only / licence-blocked (recorded in manifest with `status=blocked` or `metadata_only`)

The manifest row is kept (so a citation of the instrument is still resolvable to a stable ID), but the corpus holds only canonical metadata — no full text, no chunks, no embeddings.

| Source | Why blocked | One-command unblock |
|---|---|---|
| Australian Standards (AS 3959 — Construction in bushfire-prone areas; others) | Standards Australia paid, no lawful public redistribution | Operator adds a paid AS-3959 PDF under `corpus/docs/` and re-runs `pipeline.py` |
| NCC full text (NCC-001/002/003) | ABCB free access requires user registration; only the metadata record is held in the manifest | Operator registers a personal ABCB account, exports each volume to PDF, places under `corpus/docs/NCC-00X/source.pdf`; re-runs `pipeline.py` |
| Landgate cadastre (SLIP public) | Personal-use-licensed subset, not commercial | Operator negotiates a commercial SLIP licence; bulk data lands in `infra/spatial/slip/`; re-run the spatial importer |
| DPLH bulk spatial vectors | Pending licence | Operator obtains a written DPLH data-licence agreement; importer under `src/draftcheck/domain/spatial/` is run from `/srv/draftcheck` |
| DC 2.3 Public Open Space (wa.gov.au page removed) | Replaced by Operational Policy 2.3 draft | DC-018 marked `blocked`; cite the draft + carry forward a documented gap |

---

## Out of scope (explicit)

These are not corpus material. Every reference in `data/instrument_aliases.json` that resolves to a non-manifest name traces back to a row in this section.

| Out of scope | Why |
|---|---|
| Strata Titles Act 1985 detailed body (sections beyond the citations) | Not a residential-drafting check input; cite only by section |
| Local Government Act 1995 | Not a planning instrument; only interacts with schemes via delegation |
| Town Planning Scheme No. 1 / No. 2 (predecessor schemes) | Superseded; historic only |
| Town Planning Scheme 3 (Fremantle predecessor) | Historic; current is LPS4 |
| Town Planning Scheme 6 (Melville predecessor) | Historic; current is LPS6 |
| Heritage Council State Register listings | Not a general drafting check; out of scope for V1 |
| Court / SAT / SCWA decisions | Cite-only; not corpus material |
| Internal council policies not publicly published | Not a corpus target; only publicly published LPPs are |
| Drafts of any in-scope instrument when a current consolidated version exists | If the current version is in corpus, the draft is a duplicate of the manifest row; if it is the only version, the manifest records it as `proposed` (e.g. SPP-014, PS-004, PS-011 — all four confirmed draft-only) |
| Withdrawn planning bulletins (PB 14, 18, 19, 41, 61, 64, 67, 69, 83, 92, 94) | Historic citations; no current legal weight; recorded as `out_of_scope` in the manifest |
| Other-state planning instruments (VIC, NSW, etc.) | Not WA |
| Commonwealth planning instruments (EPBC Act) | Not WA |
| AS 1100 / AS 1428 / other non-3959 Australian Standards | Not a planning-drafting check input |
| Federal income tax / GST rulings on housing | Out of scope |

---

## Pilot LGA expansion (future)

After M1, the pilot LGA list expands per `docs/MASTER_REBUILD_PLAN.md` §2.5. The expansion procedure:

1. Add the LGA to the table above.
2. Re-run `scripts/joondalup_lpps.py` (or the equivalent per-council crawler) to seed LPP rows.
3. Re-run `scripts/pipeline.py --priority-only` to fetch the new rows.
4. Re-run `scripts/check_citations.py` and update `reports/citation_gaps.json`.
5. Re-run `scripts/ingest_corpus.py --approve` to bring them to citable status.
6. Update the closure reports under `reports/` so CI is green.

---

## Operational consequences

- **A citation that resolves to an `out_of_scope` row** is answered with a verbatim `needs_more_info` and a pointer to the in-scope successor (e.g. PB 14 → "PB 14 is withdrawn; see SPP 7.3 / current planning bulletin in force"). The retrieval layer must not pretend a withdrawn document is current.
- **A citation that resolves to a `metadata_only` row** is answered with the canonical metadata + a one-line unblock instruction (e.g. "NCC Vol 1 — full text not in corpus; to unblock, see [one-command] in docs/CORPUS_SCOPE.md"). The cite-or-refuse gate refuses to invent standards.
- **A citation that resolves to a `blocked` row** gets the same treatment as `metadata_only` plus a record of the reason in `version_metadata.fetch.note`.
- **A citation that does not resolve at all** triggers a citation-closure finding: the `gap-hunter` agent investigates the manifest + index pages; if the instrument exists, a new `pending` manifest row is added; if it is genuinely out of scope, an explicit `out_of_scope` row is added here.

---

## Out-of-scope bookkeeping rule

Every `status=out_of_scope` row in `data/manifest.csv` and every alias in `data/instrument_aliases.json` that points to a non-manifest name must trace to a row in the "Out of scope (explicit)" table above. CI verifies this in `reports/manifest_closure.json` (Phase 1 exit gate).
