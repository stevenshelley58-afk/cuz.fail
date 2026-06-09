"""Manifest gap checks.

  - rows with blank canonical_url
  - rows whose URL slug contains "draft" while the row is not marked draft
  - rows still pending after acquisition attempts (fetch-failed notes)

Usage: python scripts/verify_urls.py
"""
from __future__ import annotations

from corpus_lib import read_manifest


def main() -> None:
    rows = read_manifest()
    blank = [r for r in rows if not r.get("canonical_url", "").strip()
             and r["status"] not in ("metadata_only", "out_of_scope", "blocked")]
    draft_slug = [r for r in rows
                  if "draft" in r.get("canonical_url", "").lower()
                  and "draft" not in r["instrument_name"].lower()]
    failed = [r for r in rows if r["status"] == "pending" and "fetch failed" in r.get("notes", "")]

    print(f"manifest rows: {len(rows)}")
    print(f"\n-- blank canonical_url ({len(blank)}) --")
    for r in blank:
        print(f"  {r['id']:14} {r['instrument_name'][:70]}  index={r['index_source_url'][:60]}")
    print(f"\n-- 'draft' slug on current instrument ({len(draft_slug)}) --")
    for r in draft_slug:
        print(f"  {r['id']:14} {r['instrument_name'][:70]}")
        print(f"                 -> {r['canonical_url']}")
    print(f"\n-- pending with failed fetches ({len(failed)}) --")
    for r in failed:
        print(f"  {r['id']:14} {r['notes'][-110:]}")


if __name__ == "__main__":
    main()
