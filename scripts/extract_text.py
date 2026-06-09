"""Extraction engine: PDF/HTML -> full_text.txt, tables.json, summary.json.

Usage:
  python scripts/extract_text.py PC-001            # one id
  python scripts/extract_text.py --all             # every acquired row
Importable: extract_document(row_id, name, category, authority) — used by
pipeline.py inside a ProcessPoolExecutor so extraction runs while downloads
continue.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from corpus_lib import (
    REPORTS_ROOT,
    append_report,
    doc_dir,
    extracted_dir,
    log,
    read_manifest,
    today,
    update_row,
    utcnow,
    write_manifest,
)

EXT_REPORT = REPORTS_ROOT / "extraction_report.json"
MAX_TABLE_PAGES = 300  # beyond this, skip table extraction (noted in summary)

# Instruments cited by name inside WA planning documents.
CROSS_REF_PATTERNS = [
    r"State Planning Policy\s+\d+(?:\.\d+)?(?:\s*[-–—:]\s*[A-Z][A-Za-z ,'()&-]{3,60})?",
    r"Residential Design Codes(?:\s+Volume\s+\d)?",
    r"R[-\s]?Codes(?:\s+Volume\s+\d)?",
    r"Planning and Development Act 2005",
    r"Planning and Development \(Local Planning Schemes\) Regulations 2015",
    r"Planning and Development \(Development Assessment Panels\) Regulations 2011",
    r"Building Act 2011",
    r"Building Regulations 2012",
    r"Building Code of Australia",
    r"National Construction Code",
    r"Environmental Protection Act 1986",
    r"Bush Fires Act 1954",
    r"Heritage Act 2018",
    r"Strata Titles Act 1985",
    r"Metropolitan Region Scheme",
    r"Peel Region Scheme",
    r"Greater Bunbury Region Scheme",
    r"Local Planning Scheme No\.?\s*\d+",
    r"Town Planning Scheme No\.?\s*\d+",
    r"Local Planning Policy\s+\d+(?:\.\d+)?(?:\s*[-–—:]\s*[A-Z][A-Za-z ,'()&-]{3,60})?",
    r"LPP\s*\d+(?:\.\d+)?",
    r"Development Control Policy\s+\d+(?:\.\d+)?",
    r"DC Policy\s+\d+(?:\.\d+)?",
    r"Position Statement[:\s]+[A-Z][A-Za-z ,'()&-]{3,60}",
    r"Planning Bulletin\s+\d+(?:/\d+)?",
    r"Operational Policy\s+\d+(?:\.\d+)?",
    r"Liveable Neighbourhoods",
    r"Better Urban Forest Planning",
    r"Canning Bridge Activity Centre Plan",
    r"State Planning Strategy 2050",
]
CROSS_REF_RE = re.compile("|".join(f"(?:{p})" for p in CROSS_REF_PATTERNS))

HEADING_RE = re.compile(
    r"^(?:"
    r"(?:PART|Part)\s+\d+[A-Z]?\b.*"
    r"|(?:DIVISION|Division)\s+\d+\b.*"
    r"|(?:SCHEDULE|Schedule)\s+\d+\b.*"
    r"|\d+(?:\.\d+)?\s+[A-Z][A-Za-z].{2,70}"
    r"|(?:[A-Z][A-Z &,'-]{6,70})"
    r")$"
)

DATE_PATTERNS = [
    r"(?:gazetted|amended|effective|adopted|published|version|dated|as at)\D{0,20}"
    r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})",
    r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})",
]


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def extract_pdf(pdf_path: Path) -> tuple[str, list[dict], int]:
    import pdfplumber

    pages_text: list[str] = []
    tables: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        n_pages = len(pdf.pages)
        do_tables = n_pages <= MAX_TABLE_PAGES
        for i, page in enumerate(pdf.pages):
            try:
                pages_text.append(page.extract_text() or "")
            except Exception:
                pages_text.append("")
            if do_tables:
                try:
                    for t in page.extract_tables():
                        if t and len(t) > 1:
                            tables.append({"page": i + 1, "rows": t})
                except Exception:
                    pass
    return "\n\n".join(pages_text), tables, n_pages


def extract_html(html_path: Path) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="replace"), "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "form"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.find(id="content") or soup.body or soup
    lines = [_clean_line(x) for x in main.get_text("\n").splitlines()]
    return "\n".join(x for x in lines if x)


def build_summary(text: str, row_id: str, name: str, category: str, authority: str,
                  n_pages: int, tables_skipped: bool) -> dict:
    lines = [_clean_line(x) for x in text.splitlines() if _clean_line(x)]
    title = name
    for line in lines[:15]:
        if len(line) > 12 and not line.lower().startswith(("page ", "western australian planning")):
            title = line
            break

    version_date = ""
    head = "\n".join(lines[:120])
    for pat in DATE_PATTERNS:
        m = re.search(pat, head, re.IGNORECASE)
        if m:
            version_date = m.group(1)
            break

    key_provisions: list[dict] = []
    seen_headings: set[str] = set()
    for idx, line in enumerate(lines):
        if len(key_provisions) >= 30:
            break
        if HEADING_RE.match(line) and 6 <= len(line) <= 90:
            norm = line.lower()
            if norm in seen_headings:
                continue
            seen_headings.add(norm)
            follow = ""
            for nxt in lines[idx + 1: idx + 4]:
                if not HEADING_RE.match(nxt) and len(nxt) > 25:
                    follow = nxt[:160]
                    break
            key_provisions.append({"heading": line, "summary": follow})

    refs: set[str] = set()
    for m in CROSS_REF_RE.finditer(text):
        ref = _clean_line(m.group(0)).rstrip(".,;:")
        if 4 <= len(ref) <= 90:
            refs.add(ref)

    return {
        "id": row_id,
        "title": title,
        "instrument_type": category,
        "issuing_authority": authority,
        "version_date": version_date,
        "pages": n_pages,
        "key_provisions": key_provisions,
        "cross_references": sorted(refs),
        "tables_skipped": tables_skipped,
        "extracted_at": utcnow(),
    }


def extract_document(row_id: str, name: str, category: str, authority: str) -> dict:
    """Process-pool worker entry point. Returns result dict; never raises."""
    try:
        src_pdf = doc_dir(row_id) / "source.pdf"
        src_html = doc_dir(row_id) / "source.html"
        out = extracted_dir(row_id)
        out.mkdir(parents=True, exist_ok=True)

        if src_pdf.exists():
            text, tables, n_pages = extract_pdf(src_pdf)
            tables_skipped = n_pages > MAX_TABLE_PAGES
        elif src_html.exists():
            text, tables, n_pages, tables_skipped = extract_html(src_html), [], 0, False
        else:
            return {"id": row_id, "ok": False, "error": "no source document on disk"}

        if len(text.strip()) < 200:
            return {"id": row_id, "ok": False, "error": f"extraction produced only {len(text.strip())} chars (scan-only PDF?)"}

        (out / "full_text.txt").write_text(text, encoding="utf-8")
        (out / "tables.json").write_text(json.dumps(tables, ensure_ascii=False), encoding="utf-8")
        summary = build_summary(text, row_id, name, category, authority, n_pages, tables_skipped)
        (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"id": row_id, "ok": True, "pages": n_pages, "chars": len(text),
                "tables": len(tables), "refs": len(summary["cross_references"])}
    except Exception as exc:  # noqa: BLE001
        return {"id": row_id, "ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _cli(ids: list[str]) -> None:
    rows = read_manifest()
    by_id = {r["id"]: r for r in rows}
    if ids == ["--all"]:
        ids = [r["id"] for r in rows if r["status"] == "acquired"]
    for row_id in ids:
        row = by_id[row_id]
        res = extract_document(row_id, row["instrument_name"], row["category"], row["issuing_authority"])
        res["extracted_at"] = utcnow()
        append_report(EXT_REPORT, res)
        if res["ok"]:
            update_row(rows, row_id, status="extracted", last_checked_at=today())
            write_manifest(rows)
        log(f"{row_id}: {'OK' if res['ok'] else res['error']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    _cli(sys.argv[1:])
