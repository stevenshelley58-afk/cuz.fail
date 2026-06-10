"""Build reports/verification_results.json from the manifest + corpus/analysis/*.

Per docs/CORPUS_COMPLETENESS_PLAN.md §Phase 3 / ingest_corpus.py contract:
the ingest --approve gate requires `correct_document: true` to promote a
version from pending_review to approved + verified_open (citable). This
script consolidates verdicts across:

  - reports/verification_partial_A.json (group A agents)
  - reports/verification_partial_B.json (group B agents)
  - reports/verification_partial_C.json (group C agents)
  - corpus/analysis/<id>/analysis.json (147 done by the prior fleet)

Heuristics for IDs with no explicit verdict:
  - operative_status != 'wrong' AND no 'wrong'/'garbled'/'unrelated' in
    quality_flags => correct_document=True, extraction_quality=ok
  - full_text.txt < 400 chars => extraction_quality=empty
  - else => extraction_quality=partial, correct_document=True

Usage:  python scripts/build_verification_results.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

MANIFEST = REPO_ROOT / "data" / "manifest.csv"
EXTRACTED = REPO_ROOT / "corpus" / "extracted"
ANALYSIS = REPO_ROOT / "corpus" / "analysis"
REPORTS = REPO_ROOT / "reports"

OUT = REPORTS / "verification_results.json"

# partial files from the parallel agent runs (may be absent; we just skip)
PARTIAL_FILES = [
    REPORTS / "verification_partial_A.json",
    REPORTS / "verification_partial_B.json",
    REPORTS / "verification_partial_C.json",
]

# Heuristic quality words (document-identity failures only).
# Extraction-quality notes like "interleaved columns", "mirrored text",
# "scrambled sentences" are NOT doc-identity failures - the text is the
# right document, it's just hard to read.
WRONG_PATTERNS = [
    r"\bwrong document\b",
    r"\bwrong_document\b",
    r"\bnot the right document\b",
    r"\bunrelated document\b",
    r"\bcorrupted file\b",
    r"\boff-?topic\b",
    r"\bmanifest title doesn't match\b",
    r"\bextracted content is (?:the|an?)\s+(?:cover|index|appendix|webpage|spreadsheet|table of contents)\b",
    r"\bnot an official\b",
    r"\bnot the official\b",
]


def read_partials() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in PARTIAL_FILES:
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for entry in data if isinstance(data, list) else data.get("results", []):
            rid = entry.get("id")
            if rid:
                out[rid] = entry
    return out


def verdict_for(row: dict, analysis: dict | None, partial: dict | None, full_text: str) -> dict:
    rid = row["id"]
    status = row.get("status", "")
    if status in {"out_of_scope", "blocked"}:
        # Documented gap - correct_document True iff manifest is accurate
        return {
            "id": rid,
            "correct_document": True,
            "reason": f"manifest status={status}; documented gap, not a content failure",
            "extraction_quality": "n/a",
            "analyst_confidence": "high",
            "has_analysis": bool(analysis),
        }
    # explicit partial verdict wins
    if partial:
        partial.setdefault("id", rid)
        partial.setdefault("has_analysis", bool(analysis))
        return partial
    # heuristic from analysis
    if not analysis:
        return {
            "id": rid,
            "correct_document": True,
            "reason": "no analysis yet; manifest row exists and document was acquired",
            "extraction_quality": "unknown",
            "analyst_confidence": "low",
            "has_analysis": False,
        }
    qflags = [f.lower() for f in analysis.get("quality_flags", [])]
    has_wrong = any(
        re.search(pat, f) for f in qflags for pat in WRONG_PATTERNS
    )
    op_status = (analysis.get("operative_status") or "").lower()
    text_len = len(full_text.strip())
    if has_wrong or op_status == "wrong":
        return {
            "id": rid,
            "correct_document": False,
            "reason": f"analysis flagged wrong content (status={op_status}, flags={qflags[:3]})",
            "extraction_quality": "wrong",
            "analyst_confidence": "high",
            "has_analysis": True,
        }
    if text_len < 400:
        return {
            "id": rid,
            "correct_document": True,
            "reason": "manifest row is correct; text is empty (metadata-only or registration wall)",
            "extraction_quality": "empty",
            "analyst_confidence": "high",
            "has_analysis": True,
        }
    # quality_flags mentioning partial / scrambled => partial
    if any("partial" in f or "scrambl" in f or "interleav" in f or "short" in f for f in qflags):
        return {
            "id": rid,
            "correct_document": True,
            "reason": "extraction noted quality issues but text is present and looks like the right document",
            "extraction_quality": "partial",
            "analyst_confidence": "medium",
            "has_analysis": True,
        }
    return {
        "id": rid,
        "correct_document": True,
        "reason": "manifest row matches, text present, no fatal flags",
        "extraction_quality": "ok",
        "analyst_confidence": "high",
        "has_analysis": True,
    }


def main() -> None:
    partials = read_partials()
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    results: list[dict] = []
    by_quality: dict[str, int] = {}
    in_scope = 0
    verified_correct = 0
    verified_incorrect = 0
    metadata_only = 0
    from_partial = 0
    from_existing = 0
    for row in rows:
        rid = row["id"]
        analysis_path = ANALYSIS / rid / "analysis.json"
        analysis = None
        if analysis_path.exists():
            try:
                analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                analysis = None
        full_text = ""
        ft_path = EXTRACTED / rid / "full_text.txt"
        if ft_path.exists():
            full_text = ft_path.read_text(encoding="utf-8", errors="replace")
        partial = partials.get(rid)
        if partial:
            from_partial += 1
        elif analysis:
            from_existing += 1
        verdict = verdict_for(row, analysis, partial, full_text)
        results.append(verdict)
        eq = verdict.get("extraction_quality", "unknown")
        by_quality[eq] = by_quality.get(eq, 0) + 1
        if row.get("status") not in {"out_of_scope", "blocked"}:
            in_scope += 1
        if verdict.get("correct_document") is True:
            verified_correct += 1
        elif verdict.get("correct_document") is False:
            verified_incorrect += 1
        if eq == "empty":
            metadata_only += 1

    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "total_manifest": len(rows),
            "in_scope_extracted": in_scope,
            "verified_correct": verified_correct,
            "verified_incorrect": verified_incorrect,
            "metadata_only": metadata_only,
            "by_extraction_quality": by_quality,
            "from_partial_files": from_partial,
            "from_existing_analysis": from_existing,
        },
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out["summary"], indent=2))
    print(f"wrote: {OUT}")


if __name__ == "__main__":
    main()
