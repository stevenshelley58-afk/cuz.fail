"""Repair data/manifest.csv — v2 with note-preservation:

  Bug A: For each MEL-LPP-### row, set status to "extracted" if
         corpus/extracted/<id>/full_text.txt exists and len > 400,
         else "blocked" with a one-command unblock note. PRESERVE
         any pre-existing rich notes (do not overwrite).

  Bug B: For each MEL-SP-### row, repair the canonical_url to a real
         PDF URL (verified application/pdf responses). STRIP stale
         "domain swapped" / "no PDF resolved" / "saved page HTML" notes
         from the row's notes column so the row no longer contradicts
         itself.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(r"C:\Dev\Cuz\.claude\worktrees\objective-rubin-7d1432")
MANIFEST = ROOT / "data" / "manifest.csv"
EXTRACTED = ROOT / "corpus" / "extracted"

# Verified real-PDF URLs (HEAD-checked Content-Type: application/pdf).
SP_FIXES: dict[str, str] = {
    "MEL-SP-001": "https://www.wa.gov.au/system/files/2026-04/spn-0754m-8-canning-bridge-activity-centre-amendment-no-7.pdf",
    "MEL-SP-002": "https://www.melvillecity.com.au/getContentAsset/925b2e15-e85f-429b-acec-07339d5e5757/3ca954ad-3848-47c6-8f97-68cebe0b47a2/Kardinya-District-Centre-Precinct-Structure-Plan-WAPC-Reference-(1).pdf?language=en",
    "MEL-SP-003": "https://www.melvillecity.com.au/getContentAsset/7966c166-d3f6-4b98-b57a-5c43bfa7aabc/3ca954ad-3848-47c6-8f97-68cebe0b47a2/Melville-City-Centre-Structure-Plan-(lr).pdf?language=en",
    "MEL-SP-004": "https://www.melvillecity.com.au/getContentAsset/40638c7f-62b6-4e6e-9870-952ad7449112/3ca954ad-3848-47c6-8f97-68cebe0b47a2/Melville-District-Activity-Centre-Plan.pdf?language=en",
    "MEL-SP-005": "https://www.wa.gov.au/system/files/2021-05/PRJ-Murdoch-Specialist_activity_Centre_SP_Part_1.pdf",
    "MEL-SP-006": "https://www.wa.gov.au/system/files/2025-05/riseley-activity-centre-structure-plan-wapc.pdf",
    "MEL-SP-007": "https://www.wa.gov.au/system/files/2023-05/willagee-structure-plan-amendment-no2-wapc-reference-spn0789m-2.pdf",
}

# Stale notes to strip from MEL-SP rows once the canonical_url is a real PDF.
# These notes were valid when the row pointed to a melvillecity HTML landing
# page, but are now misleading.
STALE_SP_NOTE_FRAGMENTS = [
    "domain swapped to melvillecity.com.au (melville.wa.gov.au serves self-signed cert)",
    "no PDF resolved; saved page HTML",
]


def lpp_status(row_id: str) -> tuple[str, str]:
    """Return (new_status, repair_marker) for a MEL-LPP-### row.

    The marker is appended to the existing notes only if the row transitions
    to blocked — we never overwrite rich pre-existing notes.
    """
    ft = EXTRACTED / row_id / "full_text.txt"
    if ft.exists() and ft.stat().st_size > 400:
        return "extracted", ""
    return "blocked", (
        f"corpus/extracted/{row_id}/full_text.txt missing or <400 bytes. "
        f"Unblock: `python scripts/extract_text.py {row_id}` after re-acquiring the source."
    )


def clean_sp_notes(notes: str) -> tuple[str, list[str]]:
    """Strip stale SP fragments from the notes column. Return (cleaned, stripped)."""
    if not notes:
        return notes, []
    parts = [p.strip() for p in notes.split("|")]
    stripped: list[str] = []
    kept: list[str] = []
    for p in parts:
        if any(frag in p for frag in STALE_SP_NOTE_FRAGMENTS):
            stripped.append(p)
        else:
            kept.append(p)
    return " | ".join(kept), stripped


def main() -> None:
    if not MANIFEST.exists():
        sys.exit(f"manifest not found: {MANIFEST}")

    with MANIFEST.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    lpp_changes: list[dict] = []
    sp_changes: list[dict] = []

    for r in rows:
        rid = r["id"]
        if rid.startswith("MEL-LPP-"):
            new_status, marker = lpp_status(rid)
            old_status = r["status"]
            if old_status != new_status:
                lpp_changes.append({"id": rid, "old": old_status, "new": new_status})
            r["status"] = new_status
            if marker:
                # Append marker only if not already present.
                if marker not in r["notes"]:
                    if r["notes"]:
                        r["notes"] = r["notes"] + " | " + marker
                    else:
                        r["notes"] = marker
        elif rid.startswith("MEL-SP-"):
            if rid in SP_FIXES:
                new_url = SP_FIXES[rid]
                old_url = r["canonical_url"]
                url_changed = old_url != new_url
                # Always clean stale notes when this is one of the target rows.
                cleaned_notes, stripped = clean_sp_notes(r["notes"])
                if stripped:
                    r["notes"] = cleaned_notes
                if url_changed:
                    r["canonical_url"] = new_url
                    sp_changes.append({
                        "id": rid,
                        "old_url": old_url,
                        "new_url": new_url,
                        "stripped_notes": stripped,
                    })

    with MANIFEST.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)

    print("=== MEL-LPP status changes ===")
    for c in lpp_changes:
        print(f"  {c['id']}: {c['old']!r} -> {c['new']!r}")
    print(f"  total: {len(lpp_changes)}")

    print("\n=== MEL-SP canonical_url changes ===")
    for c in sp_changes:
        print(f"  {c['id']}:")
        print(f"    old: {c['old_url']}")
        print(f"    new: {c['new_url']}")
        if c["stripped_notes"]:
            print(f"    stripped notes: {c['stripped_notes']}")
    print(f"  total: {len(sp_changes)}")

    # Re-summarise post-state.
    with MANIFEST.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        post = list(reader)
    empty = [r for r in post if not r["status"].strip()]
    print(f"\n=== Post-repair state ===")
    print(f"  total rows: {len(post)}")
    print(f"  empty statuses: {len(empty)}")
    sp_rows = [r for r in post if r["id"].startswith("MEL-SP-")]
    print(f"  MEL-SP rows: {len(sp_rows)}")
    for r in sp_rows:
        url = r["canonical_url"]
        looks_like_pdf = url.lower().endswith(".pdf") or "application/pdf" in url
        print(f"    {r['id']}: pdf_url={looks_like_pdf}  {url[:80]}")


if __name__ == "__main__":
    main()
