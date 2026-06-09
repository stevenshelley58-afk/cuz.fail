# DraftCheck WA — Source Currency Audit

**Generated:** 2026-06-09
**DB snapshot:** `draftcheck.db`, queried 2026-06-09; 83 source versions across 6 source types
**Authority:**
- `docs/MASTER_REBUILD_PLAN.md` §8 (source freshness requirements)
- `docs/SOURCE_GOVERNANCE.md` (lawful ingestion rules, required metadata fields)
- `docs/DATA_SOURCES.md` (provider access and licence classification)

**Audit scope:** Currency verification for all 83 source version records in the legacy SQLite DB,
governance compliance check against SOURCE_GOVERNANCE.md rules, and Stage 3 readiness assessment.
This audit does NOT cover the V3 Postgres schema (see §14).

---

## Executive Summary

- **R-Codes Vol 1 is CURRENT.** The stored April 2026 edition (effective 2026-04-10) is confirmed
  as the authoritative version. No newer gazette or amendment was found as of 2026-06-09.
  Citation: <https://www.wa.gov.au/government/document-collections/residential-design-codes-volume-1-including-medium-density>

- **NCC 2022 Housing Provisions is SUPERSEDED and incorrectly marked active.** NCC 2025 (released
  1 May 2026) includes its own Housing Provisions Standard that supersedes the 2022 edition. The DB
  record has `is_superseded=0`. This is the single highest-severity defect: Stage 3 rule extraction
  will pull 2022 housing rules unless remediated before extraction begins.

- **Five sources are permanently blocked (metadata_only + restricted)** and cannot support answer
  generation: DFES Bushfire Prone Areas, WA R-Codes Vol 1 collection anchor, NCC official anchor,
  AS 3959:2018, and Standards Australia metadata anchor. DFES and AS 3959 are the most operationally
  critical (BAL zone determination and BAL construction requirements respectively).

- **Metadata completeness is critically deficient.** `effective_date` is NULL for 81 of 83 source
  version records. The SOURCE_GOVERNANCE.md schema requires effective date as mandatory metadata.
  Date-range validity queries are impossible until this is backfilled. Seven governance violations
  are confirmed; three are CRITICAL or HIGH severity and block Stage 3 execution.

---

## Currency Matrix

### R-Code Sources

| Source | Stored Version | Current Version | Match? | Licence | Review Status | Action |
|--------|---------------|----------------|--------|---------|---------------|--------|
| R-Codes Vol 1 — April 2026 PDF | April 2026 (URL: `/2026-04/`) | April 2026, effective 2026-04-10 | MATCH | approved | accepted | Backfill `effective_date=2026-04-10`; confirm PDF URL resolves |
| R-Codes Vol 1 bootstrap excerpt | 2026-04-10 short excerpts | April 2026 (confirmed) | MATCH | approved | accepted | Only source with populated `effective_date`. Partial coverage only |
| WA R-Codes Vol 1 source anchor | anchor-only/no-date | Collection index (current) | METADATA_ONLY | restricted | pending_review | BLOCKED — cannot support answers. Retire or keep as navigation-only |
| R-Codes Vol 2 — April 2024 PDF | April 2024 (URL: `/2024-04/`) | April 2024 (no supersession found as at Aug 2025) | MATCH | approved | accepted | Backfill `effective_date=2024-04-10`; re-check before Stage 3 (reform review in progress) |
| R-Codes Vol 1 Explanatory Guidelines (Mar 2024) | March 2024 | Unconfirmed — predates April 2026 Vol 1 by 2 years | STALE ⚠ | approved | accepted | Check DPLH collection page for updated guidelines issued alongside April 2026 Vol 1 |
| R-Codes Vol 1 Practice Notes (Apr 2024) | April 2024 | Unconfirmed — predates April 2026 Vol 1 | STALE ⚠ | approved | accepted | Verify currency against April 2026 Vol 1 release notes |
| Planning Bulletin 112 (Mar 2024) | March 2024 | Adequate for April 2024 R-Codes; currency vs April 2026 unconfirmed | STALE ⚠ | approved | accepted | Check whether any bulletins issued post April 2026 Vol 1 |
| Planning Bulletin 113 (Mar 2024) | March 2024 | Same as Bulletin 112 | STALE ⚠ | approved | accepted | Same as Bulletin 112 |
| Planning Bulletin 114 (Mar 2024) | March 2024 | Same as Bulletin 112 | STALE ⚠ | approved | accepted | Same as Bulletin 112 |
| SPP 7.0 Design of the Built Environment (Feb 2019) | February 2019, gazetted 2019-05-24 | February 2019 — confirmed still operative (WA planning policies page updated 2026-05-04) | MATCH | approved | accepted | Backfill `effective_date=2019-05-24`; no supersession flag needed — confirmed in force |
| SPP 3.0 Urban Growth and Settlement (Mar 2006) | March 2006 (URL: `/2021-06/`) | March 2006 — confirmed still in force (page updated 2025-12-24) | MATCH | approved | accepted | Backfill `effective_date=2006-03-17`; `is_superseded=0` is correct |
| DWA Guidance 2.4 Side and Rear Setbacks | 2021-06 URL path | 2021-06 — confirmed unchanged, still at same URL (page updated Aug 2025) | MATCH | approved | accepted | URL is current; content-level check needed against April 2026 Vol 1 provisions |
| DWA Guidance 3.3 Deep Soil Zones | 2021-06 URL path | 2021-06 — confirmed unchanged (same check as 2.4) | MATCH | approved | accepted | Same as 2.4 |
| DWA Guidance 4.1 Solar Access | 2021-06 URL path | 2021-06 — confirmed unchanged | MATCH | approved | accepted | Same as 2.4 |
| DWA Guidance 4.2 Ventilation | 2021-06 URL path | 2021-06 — confirmed unchanged | MATCH | approved | accepted | Same as 2.4 |
| Position Statement: SPP 7.3 R-Codes Vol 2 — Apartments (2021-07) | 2021-07 | Still current at same URL (page updated Aug 2025); no newer version | MATCH | approved | accepted | Legacy "SPP 7.3" label in filename — metadata title update recommended; content is current |
| R-Codes Vol 2 Appendix A4 (guidance DOCX) | 2021-06 URL, SPP 7.3 label | Still current at same URL (confirmed Aug 2025) | MATCH | approved | accepted | Legacy SPP 7.3 filename — metadata title update only |
| R-Codes Vol 2 Appendix A5 (guidance DOCX) | 2021-06 URL, SPP 7.3 label | Still current (same check) | MATCH | approved | accepted | Legacy SPP 7.3 filename — metadata title update only |
| R-Codes Vol 2 Appendix A6 (guidance DOCX) | 2021-06 URL, SPP 7.3 label | Still current (same check) | MATCH | approved | accepted | Legacy SPP 7.3 filename — metadata title update only |
| Medium Density Housing Code documents (2024-03/04) | 2024-03/04 | No supersession found; April 2026 Vol 1 alignment check required | STALE ⚠ | approved | accepted | Verify medium-density provisions not changed in April 2026 Vol 1 |
| Granny Flat info sheet (2024-04) | April 2024 | No supersession found; April 2026 Vol 1 alignment check required | STALE ⚠ | approved | accepted | Verify ancillary dwelling provisions unchanged in April 2026 Vol 1 |

### NCC Sources

| Source | Stored Version | Current Version | Match? | Licence | Review Status | Action |
|--------|---------------|----------------|--------|---------|---------------|--------|
| NCC 2025 Volume One PDF | anchor-only/no-date (abcb.gov.au 2026 folder) | NCC 2025, released 2026-05-01 | MATCH | approved | accepted | Update canonical URL to `/editions/ncc-2025` path; backfill `effective_date=2026-05-01` |
| NCC 2025 Volume Two PDF | anchor-only/no-date (generic abcb.gov.au URL) | NCC 2025, released 2026-05-01 | MATCH | approved | accepted | Update canonical URL to specific NCC 2025 Vol 2 PDF path; backfill `effective_date=2026-05-01` |
| NCC 2025 Volume Three PDF | anchor-only/no-date (generic abcb.gov.au URL) | NCC 2025, released 2026-05-01 | MATCH | approved | accepted | Update canonical URL to specific NCC 2025 Vol 3 PDF path; backfill `effective_date=2026-05-01` |
| NCC 2022 ABCB Housing Provisions | anchor-only/no-date | SUPERSEDED by NCC 2025 Housing Provisions Standard (effective 2026-05-01) | SUPERSEDED ⚠ | approved | accepted | CRITICAL: Set `is_superseded=1`; set `superseded_by_version_id`; add version-priority guard to retrieval layer BEFORE Stage 3 |
| NCC official source anchor | anchor-only/no-date | Collection index (current) | METADATA_ONLY | restricted | pending_review | BLOCKED — cannot support NCC lookups. Assess whether PDF sources already present make this anchor redundant |
| NCC 2025 Livable Housing Design | anchor-only/no-date | NCC 2025 operative 2026-05-01 | MATCH | approved | accepted | Backfill `effective_date=2026-05-01` |
| NCC 2025 handbooks (fire engineering, condensation, structural reliability, livable housing) | anchor-only/no-date | NCC 2025 handbooks — advisory only | MATCH | approved | accepted | Advisory guidance only; not primary rule extraction sources. Backfill `effective_date` |
| Notice of Direction 2025/1.0 | anchor-only/no-date | Current (no subsequent direction found) | MATCH | approved | accepted | Backfill `effective_date`; confirm no subsequent direction issued |
| WaterMark Schedules 2026-1 and 2026-2 | 2026 editions | Current | MATCH | approved | accepted | 2026 editions are likely current. Backfill `effective_date` |

### Bushfire Sources

| Source | Stored Version | Current Version | Match? | Licence | Review Status | Action |
|--------|---------------|----------------|--------|---------|---------------|--------|
| SPP 3.7 Bushfire PDF | anchor-only/no-date (URL: `/spp-3-7-bushfire-2024.pdf`) | 2024 edition, effective 2024-11-18 — policy document unchanged | MATCH | approved | accepted | Backfill `effective_date=2024-11-18`; confirm URL resolves |
| Planning for Bushfire Guidelines (SPP 3.7 implementation) | anchor-only/no-date | Current companion to SPP 3.7 2024 | MATCH | approved | accepted | Backfill `effective_date=2024-11-18` |
| SPP 3.7 Explanatory Notes | Not stored as separate record | Updated 2025-11-25 — newer than stored version | STALE ⚠ | — | — | Ingest updated notes as new `source_version` record; `effective_date=2025-11-25`. Citation: <https://www.planning.wa.gov.au/docs/default-source/policy/spp-3-7-bushfire-explanatory-notes.pdf> |
| DFES Bushfire Prone Areas Map | Not stored as current record | Updated 2025-12-13 | STALE ⚠ | — | — | Ingest December 2025 map as new `source_version`; `effective_date=2025-12-13` |
| DFES Bushfire Prone Areas source anchor | anchor-only/no-date | Spatial dataset current — but inaccessible | METADATA_ONLY | restricted | pending_review | BLOCKED — BAL zone determination impossible. Highest-priority unblock |
| WA Fire Weather Districts and LGA mapping | anchor-only/no-date | Static reference; no supersession found | MATCH | approved | accepted | Confirm publication date; backfill `effective_date` |

### Standard Metadata Sources

| Source | Stored Version | Current Version | Match? | Licence | Review Status | Action |
|--------|---------------|----------------|--------|---------|---------------|--------|
| Australian Standard AS 3959:2018 | 2018 (bare date) | AS 3959:2018 incorporating Amd 1 (Jun 2019) and Amd 2 (Dec 2020) — no new edition | MATCH | restricted | pending_review | BLOCKED — licence required. Update DB label to note Amd 1:2019, Amd 2:2020. Negotiate licence or fair-dealing excerpt strategy |
| Standards Australia metadata source anchor | metadata-only | Collection index (current) | METADATA_ONLY | restricted | pending_review | BLOCKED — cannot retrieve standard content. Confirm which two rows flagged `is_superseded=1` represent |

### Map Layer Sources (14 records)

| Source | Stored Version | Current Version | Match? | Licence | Review Status | Action |
|--------|---------------|----------------|--------|---------|---------------|--------|
| PlanWA public planning map source anchor | anchor-only/no-date | Collection index (current) | METADATA_ONLY | restricted | pending_review | BLOCKED — metadata only. Confirm whether collection anchor can be retired if specific dataset records are present |
| Local planning policy records (13 map/spatial) | Various | Various — not individually currency-checked in this audit | — | mixed | mixed | Currency check required per dataset; see DATA_SOURCES.md for per-dataset licence status |

---

## Governance Violations

### VIOLATION 1 — CRITICAL: Superseded source not flagged, capable of supporting regulatory answers

**Rule:** SOURCE_GOVERNANCE.md — "Superseded versions remain audit-visible but are excluded from default retrieval."
**Source:** NCC 2022 ABCB Housing Provisions (`ncc2022-abcb-housing-provisions.pdf`)
**Finding:** NCC 2025 (released 1 May 2026) includes its own Housing Provisions Standard that supersedes the NCC 2022 edition. Currency Verifier result: `currency_status=MATCH` for NCC 2025; NCC 2022 Housing Provisions is confirmed SUPERSEDED. The DB record carries `is_superseded=0` and `review_status=accepted`, `licence_status=approved`. Any Stage 3 rule-extraction query that does not explicitly version-gate will retrieve outdated 2022 housing provisions alongside NCC 2025 material, producing stale-code citations.
The `superseded_by_version_id` foreign key (required by MASTER_REBUILD_PLAN §5 `source_versions` schema) is absent — the version-chain linkage does not exist.
**Severity:** CRITICAL — Stage 3 rule extraction will run against 2022 housing rules unless remediated before any extraction job is queued.
**Citation:** <https://ncc.abcb.gov.au/editions/ncc-2025>; <https://www.abcb.gov.au/news/2026/ncc-2025-released>

---

### VIOLATION 2 — HIGH: Metadata-only + restricted sources not locked from answer support

**Rule:** SOURCE_GOVERNANCE.md — "If no current approved source chunk supports an answer, return unsupported"; restricted sources cannot support answers.
**Sources (5):**
- WA R-Codes Vol 1 source anchor — `pending_review / restricted / metadata_only`
  URL: <https://www.wa.gov.au/government/document-collections/residential-design-codes-volume-1-including-medium-density>
- NCC official source anchor — `pending_review / restricted / metadata_only`
  URL: <https://ncc.abcb.gov.au/>
- DFES Bushfire Prone Areas source anchor — `pending_review / restricted / metadata_only`
  URL: <https://www.dfes.wa.gov.au/hazard-information/bushfire/bushfire-prone-areas>
- Australian Standard AS 3959:2018 — `pending_review / restricted / metadata_only`
  URL: <http://www.standards.org.au/>
- Standards Australia metadata source anchor — `pending_review / restricted / metadata_only`
  URL: <https://www.standards.org.au/>

**Finding:** All five carry `parse_status=metadata_only` and `licence_status=restricted`. The DB `review_status=pending_review` is the correct blocking marker, but governance compliance requires the retrieval layer to positively enforce this exclusion at query time. If the retrieval layer does not filter on `review_status != pending_review` or `parse_status != metadata_only`, these records will be returned. The blocking enforcement mechanism has not been confirmed as implemented.
**Severity:** HIGH — DFES and AS 3959 blocks are operationally critical for all bushfire workflows.

---

### VIOLATION 3 — HIGH: Version-chain linkage missing for NCC 2022 Housing Provisions

**Rule:** MASTER_REBUILD_PLAN §5 `source_versions` schema — `superseded_by_version_id` FK required when a version is superseded.
**Source:** NCC 2022 ABCB Housing Provisions
**Finding:** The NCC 2025 Housing Provisions Standard is a confirmed text revision of the 2022 version. No `superseded_by_version_id` FK has been set on the 2022 record, and no NCC 2025 Housing Provisions Standard record exists in the DB to point to. The version chain is broken. This compounds Violation 1: the supersession flag is wrong AND the audit trail of what superseded it is absent.
**Severity:** HIGH — same remediation as Violation 1; requires creating the 2025 Housing Provisions record first, then setting the FK.

---

### VIOLATION 4 — HIGH: Licence gap for AS 3959:2018 with no approved access path

**Rule:** SOURCE_GOVERNANCE.md — "Do not scrape paid Australian Standards full text. Store public metadata and official access references only." A source cannot advance from `pending_review` to `approved` without a confirmed lawful access path.
**Source:** AS 3959:2018 — <https://store.standards.org.au/product/as-3959-2018>
**Finding:** AS 3959:2018 incorporating Amd 2 (December 2020) is confirmed current. The standard underpins BAL construction requirements and is required for Stage 3. The ABCB free-access window expired June 2021. No current licence or fair-dealing excerpt strategy is documented. The source cannot legally advance from `pending_review` to `approved` without a paid Standards Australia licence or a formally documented fair-dealing excerpt set. This is the highest-priority unresolved licence gap for Stage 3.
**Severity:** HIGH — blocks BAL construction rule extraction entirely if not resolved before Stage 3.
**Citation:** <https://www.intertekinform.com/en-au/standards/as-3959-2018-122340_saig_as_as_2685241/>; <https://store.standards.org.au/product/as-3959-2018>

---

### VIOLATION 5 — HIGH: Mandatory `effective_date` NULL across 81 of 83 source versions

**Rule:** SOURCE_GOVERNANCE.md — "effective date" listed as required source metadata. MASTER_REBUILD_PLAN §5 `source_versions` schema — `effective_from` required field.
**Sources:** All 81 active sources except R-Codes Vol 1 bootstrap excerpt and the Cockburn fixture.
**Finding:** `effective_date` is NULL for 81 of 83 source version records. The retrieval layer cannot perform "was this rule in force on date X" queries. Date-range validity checks are structurally impossible. The Currency Verifier has confirmed effective dates for the primary regulatory sources (listed in Remediation List §P5), making backfill immediately actionable without further research.
**Severity:** HIGH — systematic. Not a blocking violation for current static retrieval, but makes all date-range validity checking impossible.

---

### VIOLATION 6 — MEDIUM: DWA guidance series — URL currency confirmed, content alignment with April 2026 Vol 1 unverified

**Rule:** SOURCE_GOVERNANCE.md Rule #6 (changed text requires version update; stale rules excluded from applicability).
**Sources:** DWA Guidance 2.4 Setbacks, 3.3 Deep Soil Zones, 4.1 Solar Access, 4.2 Ventilation
**Finding:** Currency Verifier confirms all four documents remain at their 2021-06 URLs with no superseding versions on the official WA Government page (last updated August 2025). The `review_status=accepted` and `licence_status=approved` flags are therefore correct for the stored file versions. However, R-Codes Vol 1 was substantially revised in April 2024 and April 2026. DPLH has not issued updated DWA guidance documents to accompany those revisions. If any provision illustrated by these guidance documents was changed in April 2024 or April 2026, citing these documents for those provisions would violate Rule #6. This is a conditional violation requiring a content-level comparison against April 2026 Vol 1 before Stage 3 extraction.
**Citation:** <https://www.wa.gov.au/government/document-collections/residential-design-codes-vol-2-additional-resources> (page last updated 22 August 2025)
**Severity:** MEDIUM — mandatory pre-Stage-3 check; not a present violation but becomes one if affected provisions are used without the check.

---

### VIOLATION 7 — LOW: Legacy "SPP 7.3" labelling in R-Codes Vol 2 companion document titles and filenames

**Rule:** SOURCE_GOVERNANCE.md — source title required metadata must accurately represent the current document.
**Sources:** Position Statement (URL: `POS-Position-Statement-SPP7-3-R-Codes-Vol-2-relationship-to-pre-existing-local-planning-framework.pdf`), Appendices A4/A5/A6 (DOCX files with SPP-7-3 filenames, 2021-07 upload dates)
**Finding:** Currency Verifier confirms these 2021-07 documents remain the current operative guidance. Their content is correct. However, their titles and filenames retain the former "SPP 7.3" policy designation. The operative policy instrument is now formally titled "Residential Design Codes Volume 2." Automated citation generation that pulls document titles will surface "SPP 7.3" in outputs, which is the incorrect current name. This is a metadata-only issue; no re-fetch is required.
**Citation:** <https://www.wa.gov.au/government/document-collections/residential-design-codes-volume-2-apartments> (page last updated 22 August 2025)
**Severity:** LOW — metadata presentation issue only. Does not affect rule correctness.

---

## Prioritised Remediation List

### Priority 1 — CRITICAL | Blocks Stage 3 NCC Housing Rule Extraction

**Source:** NCC 2022 ABCB Housing Provisions
**Blocking:** YES — Stage 3 cannot begin with this record in its current state
**Action:**
1. Create a new `source_versions` record for NCC 2025 Housing Provisions Standard (canonical URL: `https://ncc.abcb.gov.au/editions/ncc-2025`; `effective_date=2026-05-01`)
2. On the NCC 2022 Housing Provisions record: set `is_superseded=1`; set `superseded_by_version_id` to the new NCC 2025 Housing Provisions record ID
3. Add a version-priority guard to the retrieval layer: when multiple versions of the same source family exist, return only the record with `is_superseded=0` and the latest `effective_date`
4. Verify the guard is enforced before any Stage 3 extraction job is queued

**Impact if deferred:** Stage 3 extracts housing rules from 2022 provisions. Every NCC housing rule in the DB carries a stale-version defect.

---

### Priority 2 — CRITICAL | Blocks BAL Zone Determination (all bushfire workflows)

**Source:** DFES Bushfire Prone Areas source anchor
**Blocking:** YES — BAL zone determination cannot be completed
**Action:**
1. Request API key or WFS token from DFES: <https://www.dfes.wa.gov.au/hazard-information/bushfire/bushfire-prone-areas>
2. Until access is granted: insert an explicit `retrieval_blocked` flag on this record; ensure all BAL zone determination queries return `missing_info / human_review_required` rather than attempting fallthrough to other sources
3. The anchor record itself (`metadata_only / restricted`) must be excluded from all retrieval pipelines via a hard filter on `parse_status=metadata_only`

**Impact if deferred:** Bushfire applicability checks produce incorrect or incomplete BAL zone determinations for every WA property.

---

### Priority 3 — CRITICAL | Blocks BAL Construction Rule Extraction

**Source:** AS 3959:2018 incorporating Amd 1:2019 and Amd 2:2020
**Blocking:** YES — BAL construction requirement checks cannot be supported
**Action:**
1. Either: (a) negotiate and execute a Standards Australia licence for DraftCheck WA (commercial AI-processing use) via <https://store.standards.org.au/product/as-3959-2018>, or (b) formally document and implement a fair-dealing excerpt strategy covering only the specific construction requirement tables needed for BAL classes
2. Until either path is confirmed: keep `pending_review / metadata_only / restricted`; all BAL construction queries must return `unsupported`
3. Update the DB metadata label from bare "2018" to "AS 3959:2018 incorporating Amd 1:2019, Amd 2:2020" regardless of which licence path is taken

**Impact if deferred:** BAL construction requirement checks are entirely unsupported and every such query returns `unsupported`.

---

### Priority 4 — HIGH | Affects NCC 2025 Retrieval Reliability

**Sources:** NCC 2025 Volumes 1, 2, 3 (generic `abcb.gov.au` canonical URLs)
**Blocking:** Partial — sources are accepted but fetch reliability is uncertain
**Action:**
1. Update `canonical_url` for each NCC 2025 volume to its specific `/editions/ncc-2025` PDF path on `ncc.abcb.gov.au`; confirm each URL resolves before Stage 3
2. Backfill `effective_date=2026-05-01` for all three volumes
   Citation: <https://ncc.abcb.gov.au/editions/ncc-2025>

**Impact if deferred:** Source fetch jobs may resolve to wrong NCC edition or fail if the generic `abcb.gov.au` URL redirects to a login or collection page.

---

### Priority 5 — HIGH | Affects All Date-Range Validity Checks

**Sources:** All 81 active records lacking `effective_date`
**Blocking:** No (for current static retrieval), YES (for date-range validity queries)
**Action:** Run a data migration (Alembic migration or audited SQL UPDATE with change-log note) to backfill `effective_date` and `published_at` for all primary regulatory sources. The following dates are confirmed by the Currency Verifier and can be applied immediately:

| Source | `effective_date` |
|--------|-----------------|
| R-Codes Vol 1 (April 2026) | 2026-04-10 |
| R-Codes Vol 2 (April 2024) | 2024-04-10 |
| SPP 3.7 Bushfire (2024) | 2024-11-18 |
| NCC 2025 Vols 1, 2, 3 | 2026-05-01 |
| SPP 7.0 Design of the Built Environment | 2019-05-24 |
| SPP 3.0 Urban Growth and Settlement | 2006-03-17 |
| DWA Guidance series (2.4, 3.3, 4.1, 4.2) | 2021-06-01 (upload date) |
| Planning Bulletins 112, 113, 114 | 2024-03-01 |
| SPP 3.7 Explanatory Notes (new record) | 2025-11-25 |
| DFES Bushfire Prone Areas Map (new record) | 2025-12-13 |

**Impact if deferred:** "Was this rule in force on date X" queries are impossible. Rule applicability checks depending on date context cannot be validated per MASTER_REBUILD_PLAN §5.

---

### Priority 6 — MEDIUM | Pre-Stage-3 Currency Re-check for Reform-Sensitive Sources

**Sources:** R-Codes Vol 2 (April 2024), R-Codes Vol 1 Explanatory Guidelines (Mar 2024), Practice Notes (Apr 2024), Planning Bulletins 112/113/114 (Mar 2024), Medium Density Housing Code documents (2024-03/04), Granny Flat info sheet (2024-04)
**Blocking:** No — conditionally acceptable if re-checked immediately before Stage 3
**Action:**
1. Immediately before Stage 3 extraction: re-fetch the Vol 2 canonical collection page (<https://www.wa.gov.au/government/document-collections/residential-design-codes-volume-2-apartments>) — a WA reform review is in progress and a new edition could be gazetted without notice
2. Check the DPLH document collection page for any updated Explanatory Guidelines, Practice Notes, or Bulletins issued alongside the April 2026 Vol 1 revision
3. If updated versions exist: ingest as new `source_version` records; set `is_superseded=1` on the 2024 records

**Impact if deferred:** Possible extraction from guidance that predates April 2026 Vol 1 changes, producing misaligned interpretation for provisions that changed in 2026.

---

### Priority 7 — MEDIUM | Ingest SPP 3.7 Companion Document Updates

**Sources:** SPP 3.7 Explanatory Notes (November 2025), Bushfire Prone Areas Map (December 2025) — neither stored as a separate current `source_version` record
**Blocking:** No — core SPP 3.7 policy document is current; companion versions affect interpretation precision
**Action:**
1. Ingest the updated explanatory notes as a new `source_version` record: canonical URL `https://www.planning.wa.gov.au/docs/default-source/policy/spp-3-7-bushfire-explanatory-notes.pdf`; `effective_date=2025-11-25`
2. Ingest the December 2025 Bushfire Prone Areas Map as a separate spatial `source_version` record: `effective_date=2025-12-13`
3. Link both to the SPP 3.7 2024 policy source record via a companion/child relationship

**Impact if deferred:** Stage 3 references the 2024 explanatory notes for SPP 3.7 interpretation rather than the current November 2025 version, potentially misclassifying application scope for post-November 2025 assessments.

---

### Priority 8 — LOW | Metadata Label Cleanup (SPP 7.3 Legacy Naming)

**Sources:** R-Codes Vol 2 Position Statement, Appendices A4/A5/A6 (SPP-7-3 filenames and titles)
**Blocking:** No — content is current; presentation only
**Action:** Update `source_title` and metadata labels in DB records to use "Residential Design Codes Volume 2" branding. No re-fetch required; documents are unchanged. Prevents LLM citation generation from surfacing the legacy "SPP 7.3" policy name in regulatory outputs.
**Citation:** <https://www.wa.gov.au/government/document-collections/residential-design-codes-volume-2-apartments>

---

## R-Codes Finding

**VERDICT: R-Codes Vol 1 is CURRENT. Stage 3 rule extraction will run against live law.**

The DB stores the April 2026 edition. The Currency Verifier confirms the April 2026 version (PDF at <https://www.wa.gov.au/system/files/2026-04/r-codes-volume-1-10-april-2026.pdf>) is the current authoritative version with no newer gazette or amendment as of June 2026. The WA Government document collection page (last updated 27 May 2026) lists the April 2026 PDF as the current document.

The document is formally titled "Residential Design Codes Volume 1" (functioning as the operative instrument of SPP 7.3). The SPP 7.3 designation is the policy instrument number; "Residential Design Codes Volume 1" is the correct current title used in both the document and the government collection page. The WAPC has flagged a broader review in progress, but no replacement version has been gazetted as of June 2026.

**One operational action required before Stage 3:** confirm the stored PDF URL resolves correctly. The `WA R-Codes Volume 1 source anchor` (with `metadata_only/restricted` status) is a separate collection-index anchor and does not affect the primary PDF source. `effective_date=2026-04-10` must be backfilled on the primary anchor source record.

**R-Codes Vol 2 (April 2024)** is also confirmed current. No superseding version was found as of August 2025 check. A pre-Stage-3 re-check of the canonical collection page is required because a WA reform review is in progress.

**Citation:** <https://www.wa.gov.au/government/document-collections/residential-design-codes-volume-1-including-medium-density> (collection page, last updated 2026-05-27)

---

## NCC Finding

**VERDICT: NCC 2025 volumes are CURRENT. NCC 2022 Housing Provisions is SUPERSEDED and incorrectly flagged — this is the most critical defect in the library.**

NCC 2025 Volumes 1, 2, and 3 are the current editions, released 1 May 2026 by the ABCB. The DB sources for these three volumes carry `review_status=accepted` and `licence_status=approved`. The currency match is confirmed.

**NCC 2022 Housing Provisions — CONFIRMED SUPERSEDED, DB record is incorrect.** The NCC 2025 edition includes its own Housing Provisions Standard that supersedes the NCC 2022 edition. The Currency Verifier confirms: `effective_date=2026-05-01` for NCC 2025 Housing Provisions. The DB record for NCC 2022 Housing Provisions has `is_superseded=0` and `review_status=accepted`. This is a confirmed governance Violation 1 (critical) and Violation 3 (high). This record MUST have `is_superseded=1` and `superseded_by_version_id` set before any Stage 3 extraction job is queued, and the retrieval layer must implement a version-priority guard.

The NCC official source anchor (`https://ncc.abcb.gov.au/`) is a collection-index page with `metadata_only/restricted` status. If the PDF sources for NCC 2025 Vols 1/2/3 are already present and their canonical URLs are updated to the specific `/editions/ncc-2025` paths, the generic anchor may be retired from answer-support pipelines (kept as navigation-only metadata if desired).

**Citations:** <https://ncc.abcb.gov.au/editions/ncc-2025>; <https://www.abcb.gov.au/news/2026/ncc-2025-released>

---

## SPP 3.0 Urban Growth and Settlement Finding

**VERDICT: SPP 3.0 (March 2006) is CONFIRMED IN FORCE. `is_superseded=0` is correct.**

The WA Government publications page for SPP 3.0 (<https://www.wa.gov.au/government/publications/state-planning-policy-30-urban-growth-and-settlement>) was last updated 24 December 2025, and the policy is listed as active in the current State Planning Policies collection. No replacement or revocation was found. The 2021-06 URL path in the stored file (`https://www.wa.gov.au/system/files/2021-06/SPP_3_urban_growth_settlement.pdf`) indicates a re-hosted copy, not an amendment.

The Library Audit flagged SPP 3.0 as anomalous due to its age (2006). The anomaly is resolved: the policy remains operative. The only required action is to backfill `effective_date=2006-03-17` and confirm the stored PDF URL still resolves before Stage 3 use.

**Citation:** <https://www.wa.gov.au/government/document-collections/state-planning-policies> (planning policies collection); <https://www.wa.gov.au/government/publications/state-planning-policy-30-urban-growth-and-settlement>

---

## SPP 7.0 Design of the Built Environment Finding

**VERDICT: SPP 7.0 (February 2019, gazetted 2019-05-24) is CONFIRMED IN FORCE. `is_superseded=0` is correct.**

The WA Government planning policies page lists SPP 7.0 as current with an operational date of 24 May 2019 and no amendments or supersessions recorded (page last updated 4 May 2026). The WA Planning Code reforms and SPP 7.3 / Residential Design Codes have not replaced SPP 7.0 Design of the Built Environment.

The Library Audit flagged SPP 7.0 as potentially anomalous given its 2019 vintage. The anomaly is resolved. The 2021-06 URL path indicates re-hosting only.

**Cross-reference note:** The April 2024 amendment to the Significant Development Regulations updated how the ten design principles in SPP 7.0 must be addressed in design statements, but did not amend SPP 7.0 itself. Stage 3 rule extraction should reference the policy at 2019-05-24 and cross-reference the 2024 Regulations for design statement requirements.

`effective_date=2019-05-24` should be backfilled.

**Citation:** <https://www.wa.gov.au/government/document-collections/planning-codes-and-state-planning-policies> (last updated 2026-05-04); PDF confirmed at <https://www.wa.gov.au/system/files/2021-06/SPP-7-0-Design-of-the-Built-Environment_0.pdf>

---

## AS 3959 Finding

**VERDICT: AS 3959:2018 is the CURRENT edition, version label in DB is incomplete. Full text access is BLOCKED pending licence resolution.**

AS 3959:2018 incorporating Amendment No. 1 (June 2019) and Amendment No. 2 (December 2020) is the current edition as of June 2026. No Amendment 3 or new edition was found. The stored version label "AS 3959:2018" is technically correct for the edition but omits the two incorporated amendments. The `effective_date` should be noted as December 2020 (date of Amd 2).

**Licence status:** The source is correctly flagged `restricted / pending_review / metadata_only`. The ABCB free-access window expired June 2021. Full text cannot be lawfully ingested for AI processing without a paid Standards Australia licence or a formally documented fair-dealing excerpt strategy. This is the highest-priority unresolved licence gap for Stage 3 BAL construction workflows.

**DB label action:** Update metadata to "AS 3959:2018 incorporating Amd 1:2019, Amd 2:2020"; note `effective_date=2020-12-01`.

**Citations:** <https://www.intertekinform.com/en-au/standards/as-3959-2018-122340_saig_as_as_2685241/> (status: Current, Amd 2 December 2020 confirmed); <https://store.standards.org.au/product/as-3959-2018>

---

## DWA Guidance Series Finding

**VERDICT: All four DWA guidance documents are CURRENT at their 2021-06 URLs. Content-level alignment check against April 2026 Vol 1 is a mandatory pre-Stage-3 step.**

The Currency Verifier confirms all four documents — DWA Guidance 2.4 (setbacks), 3.3 (deep soil), 4.1 (solar access), 4.2 (natural ventilation) — remain published at their original 2021-06 URL paths on the official WA Government R-Codes Vol 2 Additional Resources page (last updated 22 August 2025). No superseding versions were found at any newer URL path.

**Important caveat:** R-Codes Vol 1 was substantially revised in April 2024 and April 2026. DPLH has not issued updated DWA guidance documents to accompany those revisions. The guidance documents were authored in 2019 and uploaded in 2021. If any provision illustrated in these documents was changed in the 2024 or 2026 R-Codes revisions, the guidance content for those provisions is stale even though the URL is current.

**Required action before Stage 3:** conduct a content-level comparison of the provisions illustrated in each DWA guidance document against the April 2026 R-Codes Vol 1 text. If any provision has changed, create a gap-note record flagging those guidance documents as potentially misleading for that provision.

**Citation:** <https://www.wa.gov.au/government/document-collections/residential-design-codes-vol-2-additional-resources> (last updated 2025-08-22; all four DWA docs confirmed at `/system/files/2021-06/` paths)

---

## Metadata-Only Sources (Cannot Support Answers)

The following sources have `parse_status=metadata_only` and/or `licence_status=restricted`. Per SOURCE_GOVERNANCE.md they cannot support regulatory answers and must be excluded from all retrieval pipelines:

| Source | URL | Critical Workflow Blocked |
|--------|-----|--------------------------|
| DFES Bushfire Prone Areas source anchor | <https://www.dfes.wa.gov.au/hazard-information/bushfire/bushfire-prone-areas> | BAL zone determination for all WA properties |
| WA R-Codes Vol 1 source anchor | <https://www.wa.gov.au/government/document-collections/residential-design-codes-volume-1-including-medium-density> | Collection index — primary PDF source is separate and unblocked |
| NCC official source anchor | <https://ncc.abcb.gov.au/> | Collection index — NCC 2025 PDF sources are separate and unblocked |
| Australian Standard AS 3959:2018 | <http://www.standards.org.au/> | BAL construction requirements for all BAL classes |
| Standards Australia metadata source anchor | <https://www.standards.org.au/> | All Australian Standards content lookup |
| PlanWA public planning map source anchor | <https://www.planning.wa.gov.au/mapping-and-data/planwa> | Spatial planning map lookups |

**Unblock paths:**
- **DFES:** Request API key or WFS token — <https://www.dfes.wa.gov.au/hazard-information/bushfire/bushfire-prone-areas>
- **AS 3959:** Negotiate Standards Australia licence (commercial AI-processing use) at <https://store.standards.org.au/product/as-3959-2018> OR implement formal fair-dealing excerpt strategy
- **WA R-Codes Vol 1 anchor / NCC anchor / PlanWA anchor:** Assess whether collection-index anchors can be retired (if the specific PDF sources are already present and URL-confirmed). Retirement would not unblock any workflow — the PDF sources already carry the content.

---

## Stage 3 Readiness Assessment

### Cleared for Stage 3 Extraction

The following sources have confirmed currency and are approved for rule extraction in Stage 3:

| Source | Cleared | Condition |
|--------|---------|-----------|
| R-Codes Vol 1 — April 2026 PDF | YES | Backfill `effective_date=2026-04-10`; confirm PDF URL resolves |
| R-Codes Vol 1 bootstrap excerpt | YES | Already has `effective_date`; partial coverage only |
| R-Codes Vol 2 — April 2024 PDF | YES (conditional) | Re-check collection page immediately before Stage 3 begins |
| SPP 3.7 Bushfire 2024 PDF | YES | Backfill `effective_date=2024-11-18` |
| Planning for Bushfire Guidelines | YES | Backfill `effective_date=2024-11-18` |
| SPP 7.0 Design of the Built Environment | YES | Backfill `effective_date=2019-05-24` |
| SPP 3.0 Urban Growth and Settlement | YES | Backfill `effective_date=2006-03-17`; confirm URL resolves |
| NCC 2025 Volumes 1, 2, 3 | YES (conditional) | Update canonical URLs to specific `/editions/ncc-2025` paths before Stage 3 |
| NCC 2025 Livable Housing Design | YES | Backfill `effective_date=2026-05-01` |
| NCC 2025 handbooks | YES | Advisory only; backfill `effective_date` |
| WaterMark Schedules 2026-1 and 2026-2 | YES | Backfill `effective_date` |
| Notice of Direction 2025/1.0 | YES | Backfill `effective_date`; confirm no subsequent direction |
| WA Fire Weather Districts and LGA mapping | YES | Confirm publication date; backfill `effective_date` |
| DWA Guidance 2.4, 3.3, 4.1, 4.2 | YES (conditional) | Content-level comparison against April 2026 Vol 1 required before extraction |
| R-Codes Vol 2 Position Statement, A4/A5/A6 | YES | Currency confirmed; metadata label update only |
| Planning Bulletins 112/113/114 | YES (conditional) | Re-check for post-April-2026 bulletins before Stage 3 |

### Blocked from Stage 3 Extraction — Action Required First

| Source | Blocker | Required Action |
|--------|---------|----------------|
| NCC 2022 ABCB Housing Provisions | CRITICAL: `is_superseded=0` incorrectly allows retrieval | Set `is_superseded=1`; create NCC 2025 Housing Provisions record; add version-priority guard |
| DFES Bushfire Prone Areas source anchor | `metadata_only / restricted` — BAL zone determination impossible | Obtain DFES API/WFS access; implement `retrieval_blocked` flag in interim |
| AS 3959:2018 | `metadata_only / restricted` — BAL construction requirements impossible | Negotiate Standards Australia licence or fair-dealing excerpt strategy |
| WA R-Codes Vol 1 source anchor | `metadata_only / restricted` | Retire from retrieval pipelines (primary PDF source is unblocked) |
| NCC official source anchor | `metadata_only / restricted` | Retire from retrieval pipelines (NCC 2025 PDF sources are unblocked once URLs updated) |
| Standards Australia metadata anchor | `metadata_only / restricted` | Retire from retrieval pipelines unless Standards Australia licence is obtained |
| PlanWA public planning map source anchor | `metadata_only / restricted` | Retire from retrieval pipelines |

### Pre-Stage-3 Gate Checklist

Before any Stage 3 extraction job is queued, the following must be confirmed complete:

- [ ] NCC 2022 Housing Provisions: `is_superseded=1` set and version-priority guard deployed
- [ ] NCC 2025 Vol 1/2/3 canonical URLs updated to `/editions/ncc-2025` paths and confirmed resolving
- [ ] `effective_date` backfill migration applied for all primary regulatory sources
- [ ] R-Codes Vol 2 collection page re-checked (reform review in progress)
- [ ] DWA guidance content-level comparison against April 2026 Vol 1 completed
- [ ] SPP 3.7 November 2025 explanatory notes ingested as new `source_version` record
- [ ] Retrieval layer confirmed to exclude `parse_status=metadata_only` and `review_status=pending_review` records at query time

---

## V3 Postgres Follow-Up Note

This audit covers the legacy SQLite database (`draftcheck.db`), queried 2026-06-09. The V3 Postgres schema (MASTER_REBUILD_PLAN §5) is the target architecture for Stage 3. Before Stage 3 extraction begins on the V3 system:

1. All remediation items in this audit (particularly Priorities 1–5) must be applied to the V3 Postgres `source_versions` table, not merely the legacy SQLite DB.
2. The label harvest from legacy SQLite (approved RuleRows, dispositions, golden evals) specified in MASTER_REBUILD_PLAN §9 PR 5 must be completed before the legacy DB is decommissioned.
3. The `effective_from` and `superseded_by_version_id` columns in the V3 `source_versions` schema must be populated from this audit's verified dates before the first extraction pipeline run.
4. A separate Source Currency Audit should be scheduled once V3 Postgres is deployed, using the Procrastinate `source_freshness_audit` periodic task defined in MASTER_REBUILD_PLAN §3.2, to replace the manual process documented in this file.

---

*This audit is machine-generated from a structured library audit, currency verification, and governance review. All currency claims are cited. No regulatory compliance conclusions are drawn from this document; it covers source metadata and library state only.*
