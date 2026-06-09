"""Citation closure check.

Reads cross_references from every corpus/extracted/*/summary.json and
resolves each against data/instrument_aliases.json + manifest instrument
names. Unresolved citations are printed as corpus gaps and written to
reports/citation_gaps.json.

Usage: python scripts/check_citations.py
"""
from __future__ import annotations

import json
import re
from collections import Counter

from corpus_lib import (
    ALIASES_PATH,
    EXTRACTED_ROOT,
    REPORTS_ROOT,
    normalize_name,
    read_manifest,
    utcnow,
)

GAPS_PATH = REPORTS_ROOT / "citation_gaps.json"


def canonical_ref(ref: str) -> str:
    """Collapse a citation to a comparable key (strip trailing titles)."""
    ref = normalize_name(ref)
    m = re.match(r"(state planning policy \d+(?:\.\d+)?)", ref)
    if m:
        return m.group(1)
    m = re.match(r"(development control policy \d+(?:\.\d+)?)", ref)
    if m:
        return m.group(1)
    m = re.match(r"(local planning policy \d+(?:\.\d+)?)", ref)
    if m:
        return m.group(1)
    m = re.match(r"(planning bulletin \d+)", ref)
    if m:
        return m.group(1)
    return ref


def main() -> None:
    aliases: dict[str, str] = {}
    if ALIASES_PATH.exists():
        aliases = {normalize_name(k): v for k, v in
                   json.loads(ALIASES_PATH.read_text(encoding="utf-8")).items()}

    rows = read_manifest()
    known: set[str] = set(aliases.keys())
    council_lpps: dict[str, set[str]] = {}  # council prefix -> {"1.7", "3.1", ...}
    for r in rows:
        known.add(canonical_ref(r["instrument_name"]))
        known.add(normalize_name(r["instrument_name"]))
        m = re.search(r"\blpp\s*(\d+\.\d+)", normalize_name(r["instrument_name"]))
        if m:
            council_lpps.setdefault(r["id"].split("-")[0], set()).add(m.group(1))

    gap_counter: Counter[str] = Counter()
    gap_sources: dict[str, set[str]] = {}
    n_refs = 0
    n_docs = 0
    for summary_path in sorted(EXTRACTED_ROOT.glob("*/summary.json")):
        n_docs += 1
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        doc_council = data["id"].split("-")[0]
        for ref in data.get("cross_references", []):
            n_refs += 1
            key = canonical_ref(ref)
            if key in known or normalize_name(ref) in known:
                continue
            # intra-council citation: "LPP 1.7" inside a MEL-* doc means that
            # council's LPP 1.7 — match against the same council's rows
            m = re.match(r"(?:local planning policy|lpp)\s*(\d+\.\d+)", key)
            if m and m.group(1) in council_lpps.get(doc_council, set()):
                continue
            # substring containment against known names (e.g. truncated titles)
            if any(key in k or k in key for k in known if len(k) > 12):
                continue
            gap_counter[key] += 1
            gap_sources.setdefault(key, set()).add(data["id"])

    print(f"checked {n_refs} cross-references across {n_docs} extracted documents")
    print(f"\n-- citation gaps ({len(gap_counter)}) — cited but not in manifest --")
    gaps = []
    for key, count in gap_counter.most_common():
        srcs = sorted(gap_sources[key])
        print(f"  {count:3}x  {key}   (cited by: {', '.join(srcs[:6])}{'...' if len(srcs) > 6 else ''})")
        gaps.append({"citation": key, "count": count, "cited_by": srcs})

    GAPS_PATH.parent.mkdir(parents=True, exist_ok=True)
    GAPS_PATH.write_text(json.dumps(
        {"generated_at": utcnow(), "documents": n_docs, "references": n_refs, "gaps": gaps},
        indent=2), encoding="utf-8")
    print(f"\nwritten -> {GAPS_PATH}")


if __name__ == "__main__":
    main()
