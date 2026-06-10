"""Repair RS-002 (Peel Region Scheme) and MEL-SP-005 (Murdoch SAC Structure Plan).

- RS-002: replace corpus/docs/RS-002/source.pdf with the actual scheme text PDF from
  legislation.wa.gov.au (mrdoc_24845.pdf = 'Peel Region Scheme [00-e0-05]' as at 21 May 2013).
  The wa.gov.au collection page only hosts environmental review figures + 5 policy PDFs,
  not the scheme text itself. legislation.wa.gov.au is the official State Law Publisher.

- MEL-SP-005: replace corpus/docs/MEL-SP-005/source.html with Murdoch SAC Structure Plan
  Part 1 PDF (10.2 MB, 20 pages, endorsed January 2014) from wa.gov.au. The City of Melville
  landing page has no download link; the canonical document is on wa.gov.au split into 7
  parts (Part 1 = the main structure plan text + map; Parts 2-7 = appendices/design).

After download, re-run extract_text.extract_document and write a fresh analysis.json
with operative_status='current', the correct version date, and corrected title.

Usage: python scripts/repair_wrong_docs.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import httpx
import pdfplumber

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

UA = "DraftCheck-WA-Corpus/1.0 (planning research; contact stevenshelley58@gmail.com)"


# (id, canonical_url, final_url, description)
REPAIRS = [
    (
        "RS-002",
        "https://www.wa.gov.au/government/document-collections/peel-region-scheme",
        "https://www.legislation.wa.gov.au/legislation/statutes.nsf/RedirectURL?OpenAgent&query=mrdoc_24845.pdf",
        "Peel Region Scheme text (legislation.wa.gov.au, version 00-e0-05, 21 May 2013)",
    ),
    (
        "MEL-SP-005",
        "https://www.melvillecity.com.au/planning-and-building/local-planning-strategy,-scheme-policies-and-plans/activity-centre-and-structure-plans/murdoch-specialised-activity-centre",
        "https://www.wa.gov.au/system/files/2021-05/PRJ-Murdoch-Specialist_activity_Centre_SP_Part_1.pdf",
        "Murdoch Specialised Activity Centre Structure Plan Part 1 (wa.gov.au, endorsed Jan 2014)",
    ),
]


def http_get(url: str) -> bytes:
    c = httpx.Client(
        follow_redirects=True,
        timeout=httpx.Timeout(120.0, connect=30.0),
        headers={"User-Agent": UA, "Accept": "*/*"},
    )
    r = c.get(url)
    r.raise_for_status()
    return r.content


def save_pdf(rid: str, content: bytes, final_url: str) -> tuple[Path, str]:
    target = doc_dir(rid) / "source.pdf"
    target.write_bytes(content)
    h = hashlib.sha256(content).hexdigest()
    meta = {
        "url": final_url,
        "fetched_at": utcnow(),
        "http_status": 200,
        "content_hash": h,
        "mime_type": "application/pdf",
        "final_url": final_url,
        "used_playwright": False,
        "bytes": len(content),
        "repair_round": "round_1",
        "repair_note": "re-acquired from official source after wrong-doc finding",
    }
    (doc_dir(rid) / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return target, h


def extract_text(pdf_path: Path) -> tuple[str, list, int]:
    pages_text: list[str] = []
    tables: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        n_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            try:
                pages_text.append(page.extract_text() or "")
            except Exception:
                pages_text.append("")
            try:
                for t in page.extract_tables():
                    if t and len(t) > 1:
                        tables.append({"page": i + 1, "rows": t})
            except Exception:
                pass
    return "\n\n".join(pages_text), tables, n_pages


# (id, head regex, fallback title)
ANALYSIS_SHAPES = {
    "RS-002": {
        "instrument_name": "Peel Region Scheme",
        "instrument_no": "PRS",
        "category": "region_scheme",
        "issuing_authority": "Western Australian Planning Commission",
        "version_date": "As at 21 May 2013 (version 00-e0-05)",
        "operative_status": "current",
        "scope_summary": (
            "Statutory region scheme made under the Planning and Development Act 2005 that "
            "divides the Peel region into zones and reservations, reserves land for public "
            "purposes (regional roads, regional parks, waterways, etc.), and sets the legal "
            "framework for subdivision, development, and scheme amendments in the City of "
            "Mandurah and the shires of Murray and Waroona. The scheme comprises the scheme "
            "text and the scheme map (sheets 1-20) and is administered by the WAPC."
        ),
    },
    "MEL-SP-005": {
        "instrument_name": "Murdoch Specialised Activity Centre Structure Plan",
        "instrument_no": "Murdoch SAC Structure Plan",
        "category": "structure_plan",
        "issuing_authority": "Western Australian Planning Commission / City of Melville",
        "version_date": "January 2014 (endorsed)",
        "operative_status": "current",
        "scope_summary": (
            "Structure plan for the Murdoch Specialised Activity Centre - a 9.6 ha precinct "
            "at the south-west corner of South Street and the Kwinana Freeway, Murdoch, within "
            "Perth's Health and Knowledge Precinct. Provides for 14 lots, an estimated ultimate "
            "yield of approximately 1,000 dwellings and 33,000 m2 of commercial floorspace, "
            "supported by Design Guidelines. Establishes land use, density, building form and "
            "access arrangements for the precinct, integrating with the Murdoch University "
            "Master Plan and the surrounding health/knowledge land uses."
        ),
    },
}


def build_analysis(rid: str, text: str, n_pages: int) -> dict:
    shape = ANALYSIS_SHAPES[rid]
    head = "\n".join(_clean(x) for x in text.splitlines()[:120] if _clean(x))
    # numeric standards
    numeric: list[dict] = []
    seen: set[str] = set()
    for line in text.splitlines()[:20000]:
        line = _clean(line)
        if 6 <= len(line) <= 200:
            for m in re.finditer(
                r"(\d+(?:\.\d+)?)\s*(m2|m²|%|m|mm|cm|km|ha|metres?|hectares?)\b", line, re.IGNORECASE
            ):
                v, u = m.group(1), m.group(2)
                key = f"{v}{u.lower()}"
                if key in seen:
                    continue
                seen.add(key)
                cm = re.search(
                    r"(?:clause|cl\.?|section|table|part)\s+([\d.]+(?:\.\d+)*[A-Z]?)",
                    line,
                    re.IGNORECASE,
                )
                numeric.append(
                    {
                        "topic": line[:60].rstrip(",.;:") if len(line) > 60 else "value",
                        "value": v,
                        "unit": u.lower(),
                        "applies_to": "",
                        "clause_ref": cm.group(0) if cm else "",
                    }
                )
                if len(numeric) >= 20:
                    break
        if len(numeric) >= 20:
            break
    # cross-refs
    refs: set[str] = set()
    patterns = [
        r"Planning and Development Act 2005",
        r"Metropolitan Region Scheme",
        r"Peel Region Scheme",
        r"State Planning Policy\s+\d+(?:\.\d+)?(?:\s*[-–—:][A-Z][A-Za-z ,'()&-]{3,60})?",
        r"Residential Design Codes(?:\s+Volume\s+\d)?",
        r"Local Planning Scheme No\.?\s*\d+",
        r"Development Control Policy\s+\d+(?:\.\d+)?",
        r"Local Planning Policy\s+\d+(?:\.\d+)?",
    ]
    cre = re.compile("|".join(f"(?:{p})" for p in patterns))
    for m in cre.finditer(text):
        ref = _clean(m.group(0)).rstrip(".,;:")
        if 4 <= len(ref) <= 90:
            refs.add(ref)
        if len(refs) >= 30:
            break
    cross_refs = [{"cited": r, "manifest_id": None} for r in sorted(refs)]

    qflags: list[str] = []
    if "yradnuob" in text or "lacos" in text or "noisnemid" in text:
        qflags.append("mirrored-text artifacts from rotated figure labels")
    if re.search(r"\b\w{40,}\b", text):
        qflags.append("extreme token lengths suggest column interleaving")
    if rid == "MEL-SP-005":
        # Some of the Parts are large; this is Part 1 only.
        qflags.append("Part 1 of 7 - Parts 2-7 (appendices, design guidelines) acquired separately if needed")
    if rid == "RS-002":
        qflags.append(
            "re-acquired in round 1 from legislation.wa.gov.au (the official State Law "
            "Publisher) after the wa.gov.au collection page was found to host only the "
            "environmental review figures and not the scheme text itself"
        )

    return {
        "id": rid,
        "normalized_title": shape["instrument_name"],
        "instrument_no": shape["instrument_no"],
        "version_date": shape["version_date"],
        "operative_status": shape["operative_status"],
        "scope_summary": shape["scope_summary"],
        "key_numeric_standards": numeric,
        "definitions": [],
        "cross_references": cross_refs,
        "residential_relevance": (
            "high" if rid == "MEL-SP-005" else "medium"
        ),
        "quality_flags": qflags,
        "pages": n_pages,
    }


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def main() -> None:
    rows = read_manifest()
    summary: list[dict] = []
    for rid, manifest_url, final_url, desc in REPAIRS:
        log(f"=== {rid} | {desc}")
        try:
            content = http_get(final_url)
        except Exception as e:  # noqa: BLE001
            log(f"  download FAILED: {e}")
            summary.append({"id": rid, "ok": False, "error": str(e)})
            continue
        target, h = save_pdf(rid, content, final_url)
        log(f"  saved {target} ({len(content)} bytes, sha256={h[:12]})")
        # extract
        try:
            text, tables, n_pages = extract_text(target)
        except Exception as e:  # noqa: BLE001
            log(f"  extract FAILED: {e}")
            summary.append({"id": rid, "ok": False, "error": f"extract: {e}"})
            continue
        out = extracted_dir(rid)
        out.mkdir(parents=True, exist_ok=True)
        (out / "full_text.txt").write_text(text, encoding="utf-8")
        (out / "tables.json").write_text(json.dumps(tables, ensure_ascii=False), encoding="utf-8")
        # summary.json (same shape as extract_text.build_summary)
        title = ANALYSIS_SHAPES[rid]["instrument_name"]
        summary_obj = {
            "id": rid,
            "title": title,
            "instrument_type": ANALYSIS_SHAPES[rid]["category"],
            "issuing_authority": ANALYSIS_SHAPES[rid]["issuing_authority"],
            "version_date": ANALYSIS_SHAPES[rid]["version_date"],
            "pages": n_pages,
            "key_provisions": [],
            "cross_references": [],
            "tables_skipped": False,
            "extracted_at": utcnow(),
        }
        (out / "summary.json").write_text(json.dumps(summary_obj, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"  extracted {n_pages} pages, {len(text)} chars")
        # analysis
        analysis = build_analysis(rid, text, n_pages)
        (REPO_ROOT / "corpus" / "analysis" / rid / "analysis.json").write_text(
            json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        log(f"  wrote analysis.json ({len(analysis['key_numeric_standards'])} key standards, "
            f"{len(analysis['cross_references'])} cross-refs)")
        # update manifest
        update_row(
            rows, rid,
            canonical_url=final_url,
            status="extracted",
            last_checked_at=today(),
            notes=(
                f"round_1 re-acquired from {final_url} | previous: {manifest_url} | {desc}"
            ),
        )
        write_manifest(rows)
        summary.append({"id": rid, "ok": True, "bytes": len(content), "pages": n_pages,
                        "url": final_url})
        log(f"  {rid}: OK")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
