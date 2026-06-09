"""Playwright crawl of City of Joondalup local planning policies.

Extracts LPP names + PDF URLs from the council's LPP index and appends
JOO-LPP-### rows to data/manifest.csv (category=LPP, status=pending).
Idempotent: matches existing rows by normalized name.

Usage: python scripts/joondalup_lpps.py
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from corpus_lib import log, normalize_name, read_manifest, today, write_manifest
from fetch_js import fetch_rendered

INDEX_URL = (
    "https://www.joondalup.wa.gov.au/plan-and-build/"
    "localplanninginformationandpolicies/local-planning-policies"
)


def crawl() -> list[tuple[str, str]]:
    html, final_url, status = fetch_rendered(INDEX_URL)
    if status >= 400:
        raise RuntimeError(f"Joondalup LPP index HTTP {status}")
    soup = BeautifulSoup(html, "lxml")
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text(" ", strip=True).split())
        href = urljoin(final_url, a["href"])
        is_pdf = bool(re.search(r"\.pdf($|\?)", href.lower()))
        looks_lpp = bool(re.search(r"(local planning policy|policy\s+\d|\bLPP\b)", text, re.IGNORECASE))
        if not text or len(text) < 8:
            continue
        if (is_pdf and looks_lpp) or (looks_lpp and "/documents/" in href.lower()) or (is_pdf and "polic" in href.lower()):
            if href not in seen:
                seen.add(href)
                found.append((text[:140], href))
    return found


def main() -> None:
    found = crawl()
    log(f"joondalup crawl: {len(found)} candidate LPP links")
    rows = read_manifest()
    existing_norms = {normalize_name(r["instrument_name"]) for r in rows}
    existing_ids = {r["id"] for r in rows}
    added = 0
    n = 1
    for text, url in sorted(found):
        name = f"City of Joondalup {text}"
        if normalize_name(name) in existing_norms:
            continue
        while f"JOO-LPP-{n:03d}" in existing_ids:
            n += 1
        new_id = f"JOO-LPP-{n:03d}"
        existing_ids.add(new_id)
        existing_norms.add(normalize_name(name))
        rows.append({
            "id": new_id,
            "instrument_name": name,
            "category": "LPP",
            "issuing_authority": "City of Joondalup",
            "index_source_url": INDEX_URL,
            "canonical_url": url,
            "expected_version_hint": "",
            "status": "pending",
            "source_document_id": "",
            "last_checked_at": today(),
            "notes": "discovered by joondalup_lpps.py",
        })
        added += 1
    write_manifest(rows)
    log(f"joondalup: appended {added} rows (manifest now {len(rows)})")


if __name__ == "__main__":
    main()
