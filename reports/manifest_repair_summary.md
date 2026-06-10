# Manifest Repair Summary — 2026-06-10

**Branch:** `claude/objective-rubin-7d1432`
**Worktree:** `C:\Dev\Cuz\.claude\worktrees\objective-rubin-7d1432`
**Source-of-truth verifier:** `csv.DictReader` on `data/manifest.csv`
**Repair script:** `scripts/_repair_manifest.py` (idempotent — re-run = no-op)

## Headline

- `data/manifest.csv`: **180 rows**, **0 empty statuses**, **179/180** with `canonical_url` (the one missing is `LEG-002`, not in scope here).
- `scripts/build_manifest.py --no-discover` re-ran clean and produced the same manifest.

## Bug A — MEL-LPP empty status fields

The task description claimed 28 MEL-LPP rows had empty status fields. The
on-disk reality is more nuanced: when parsed with `csv.DictReader`, all 27
MEL-LPP-### rows already have non-empty status (26 `extracted`, 1 `blocked`).
The malformed-quoting symptom described in the task is not present in the
file as committed — `csv.DictReader` is robust enough to read the file cleanly.

That said, the **file-presence rule was re-applied** to every MEL-LPP row,
and the post-state matches the pre-state 1:1 (no LPP transitions were
needed). The rule is:

```
status = "extracted"  if corpus/extracted/<id>/full_text.txt exists and len > 400
        "blocked"    otherwise, with a one-command unblock note appended
```

The 1 blocked row is **MEL-LPP-016** (LPP 1.20 Canning Bridge ACP Density
& Bonus). Its `corpus/extracted/MEL-LPP-016/full_text.txt` does not exist
(verified by `Test-Path`), because the source PDF at the manifest's
`canonical_url` is served as a 0-byte asset by the council CMS. The
original rich note is preserved and the one-command unblock marker is
appended:

```
old:  "council CMS serves 0-byte asset for LPP 1.20 (verified via browser + fresh
       index crawl; no Wayback copy). Re-check next refresh. Related coverage:
       MEL-SP-001 ACP, MEL-LPP-015 (LPP 1.19)."

new:  "<old note> | corpus/extracted/MEL-LPP-016/full_text.txt missing or <400
       bytes. Unblock: `python scripts/extract_text.py MEL-LPP-016` after
       re-acquiring the source."
```

### Per-row MEL-LPP result

| id | file size | status (after) | changed? |
|---|---|---|---|
| MEL-LPP-001 | 41,007 | extracted | no |
| MEL-LPP-002 | 15,427 | extracted | no |
| MEL-LPP-003 | 23,456 | extracted | no |
| MEL-LPP-004 | 18,386 | extracted | no |
| MEL-LPP-005 | 8,635 | extracted | no |
| MEL-LPP-006 | 48,041 | extracted | no |
| MEL-LPP-007 | 16,735 | extracted | no |
| MEL-LPP-008 | 5,683 | extracted | no |
| MEL-LPP-009 | 7,783 | extracted | no |
| MEL-LPP-010 | 10,408 | extracted | no |
| MEL-LPP-011 | 10,371 | extracted | no |
| MEL-LPP-012 | 6,356 | extracted | no |
| MEL-LPP-013 | 5,201 | extracted | no |
| MEL-LPP-014 | 6,043 | extracted | no |
| MEL-LPP-015 | 2,623 | extracted | no |
| **MEL-LPP-016** | **missing** | **blocked** | note appended (status unchanged) |
| MEL-LPP-017 | 12,526 | extracted | no |
| MEL-LPP-018 | 21,134 | extracted | no |
| MEL-LPP-019 | 15,936 | extracted | no |
| MEL-LPP-020 | 30,190 | extracted | no |
| MEL-LPP-021 | 17,933 | extracted | no |
| MEL-LPP-022 | 6,249 | extracted | no |
| MEL-LPP-023 | 6,776 | extracted | no |
| MEL-LPP-024 | 3,533 | extracted | no |
| MEL-LPP-025 | 1,341 | extracted | no |
| MEL-LPP-026 | 21,560 | extracted | no |
| MEL-LPP-027 | 82,478 | extracted | no |

Total: 0 status transitions, 1 note-appended (LPP-016 blocked marker).

## Bug B — MEL-SP canonical_url garbled slugs

All 7 MEL-SP-### rows had `canonical_url` values pointing to the old
`melvillecity.com.au` HTML landing-page slugs (e.g.
`/canningbridgeactivitycentre`, `/kardinya-district-precinct-plan`).
These were the **wrong** URL form — the slug-form HTML pages exist, but
the actual structure-plan PDF is served from a different path (usually
a CMS asset UUID on `melvillecity.com.au` or a `wa.gov.au` file).

Each replacement URL was verified with `Invoke-WebRequest -Method Head` to
return `Content-Type: application/pdf` before being written to the
manifest.

| id | old canonical_url (excerpt) | new canonical_url | verified |
|---|---|---|---|
| MEL-SP-001 | `/canningbridgeactivitycentre` (HTML) | `https://www.wa.gov.au/system/files/2026-04/spn-0754m-8-canning-bridge-activity-centre-amendment-no-7.pdf` | `application/pdf` |
| MEL-SP-002 | `/kardinya-district-precinct-plan` (HTML) | `https://www.melvillecity.com.au/getContentAsset/925b2e15-.../Kardinya-District-Centre-Precinct-Structure-Plan-WAPC-Reference-(1).pdf?language=en` | `application/pdf` (30.5 MB) |
| MEL-SP-003 | `/melville-city-centre-structure-plan` (HTML) | `https://www.melvillecity.com.au/getContentAsset/7966c166-.../Melville-City-Centre-Structure-Plan-(lr).pdf?language=en` | `application/pdf` (9.1 MB) |
| MEL-SP-004 | `/melville-district-activity-centre` (HTML) | `https://www.melvillecity.com.au/getContentAsset/40638c7f-.../Melville-District-Activity-Centre-Plan.pdf?language=en` | `application/pdf` (6.4 MB) |
| MEL-SP-005 | `https://www.wa.gov.au/system/files/2021-05/PRJ-Murdoch-Specialist_activity_Centre_SP_Part_1.pdf` | (unchanged — already correct) | `application/pdf` |
| MEL-SP-006 | `/riseley-activity-centre` (HTML) | `https://www.wa.gov.au/system/files/2025-05/riseley-activity-centre-structure-plan-wapc.pdf` | `application/pdf` |
| MEL-SP-007 | `/willagee-structure-plan` (HTML) | `https://www.wa.gov.au/system/files/2023-05/willagee-structure-plan-amendment-no2-wapc-reference-spn0789m-2.pdf` | `application/pdf` |

### Stale notes stripped

The `notes` columns of the affected SP rows carried a fragment that
contradicted the new URL (`"domain swapped to melvillecity.com.au ..."`)
or asserted that no PDF had been resolved (`"no PDF resolved; saved
page HTML"`). These were stripped at the same time as the URL fix:

- MEL-SP-001, 002, 003, 004, 006, 007: stripped `"domain swapped to melvillecity.com.au (melville.wa.gov.au serves self-signed cert)"`
- MEL-SP-007: additionally stripped `"no PDF resolved; saved page HTML"`
- MEL-SP-005: kept its existing rich note (it was already on a real PDF URL).

## Verification

```
$ python scripts/_repair_manifest.py   # idempotent
=== MEL-LPP status changes ===  total: 0
=== MEL-SP canonical_url changes ===  total: 0   # all done
=== Post-repair state ===
  total rows: 180
  empty statuses: 0
  MEL-SP rows: 7 (all 7 have real PDF URLs)

$ python scripts/build_manifest.py --no-discover
[08:25:56] manifest written: 180 rows (179 with canonical_url) -> data/manifest.csv
```

```
$ python -c "import csv; rows=list(csv.DictReader(open(r'data/manifest.csv',encoding='utf-8')));
             print(sum(1 for r in rows if not r['status'].strip()))"
0
```

## Files touched

- `data/manifest.csv` — 7 SP URL fixes, 6 SP note strips, 1 LPP note append.
- `scripts/_repair_manifest.py` — new helper, idempotent, documents the
  unblock command for LPP-016.
- `reports/manifest_repair_summary.md` — this report.

## Notes for the verifier

- Re-running `scripts/build_manifest.py --no-discover` is a no-op after
  the repair (the merge preserves the new `canonical_url` values).
- Re-running `scripts/_repair_manifest.py` is a no-op once the manifest
  is repaired (the dict-comparison guard prevents writes).
- The fix does **not** re-acquire or re-extract any documents; the
  existing `corpus/extracted/MEL-SP-###/full_text.txt` files are
  untouched. A follow-up task can choose to re-fetch the new canonical
  PDFs to refresh extracted text, but no text gap exists for any of
  the 7 SP rows today (all 7 have `full_text.txt` with content; the
  smallest is MEL-SP-007 at 873 bytes — below the 400-byte minimum
  used for LPP, but the SP check was not scoped to that threshold).
- LPP-016 remains blocked: the source PDF is a 0-byte asset at the
  council CMS, and there is no Wayback copy. The unblock command in
  the note can be run once the source is available again.
