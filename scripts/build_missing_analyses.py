"""Generate analysis.json for every manifest row that doesn't have one yet.

Mechanical "dumb agent" pass per docs/CORPUS_COMPLETENESS_PLAN.md §Phase 2.
For each missing analysis, read summary + full_text + manifest row, and
produce a minimal analysis.json with the canonical schema. Heuristics
keep it simple: if text is short, mark empty/metadata-only; otherwise
mine a small set of key numeric standards via regex.

Usage:  python scripts/build_missing_analyses.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

MANIFEST = REPO_ROOT / "data" / "manifest.csv"
EXTRACTED = REPO_ROOT / "corpus" / "extracted"
ANALYSIS = REPO_ROOT / "corpus" / "analysis"

# Patterns that look like numeric standards
NUMERIC_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(m2|m²|%|m|mm|cm|km|ha|metres?|percent|metres squared)\b",
    re.IGNORECASE,
)
M_DASH_RE = re.compile(r"(\d+)\s*[-–—]\s*(\d+)\s*(m2|m²|%|m|mm|cm|km|ha|metres?)\b", re.IGNORECASE)

# Categories that typically yield numeric standards
RULES_HEAVY = {"planning_code", "DC", "LPP", "scheme", "position_statement", "planning_bulletin"}


def slug_instr(name: str) -> str:
    """E.g. 'State Planning Policy 3.7' -> 'SPP 3.7'; 'Local Planning Policy 1.1' -> 'LPP 1.1'."""
    n = name.lower()
    if "state planning policy" in n:
        m = re.search(r"state planning policy\s+([\d.]+)", n)
        return f"SPP {m.group(1)}" if m else "SPP"
    if "development control" in n or "operational policy" in n:
        m = re.search(r"(?:development control|operational) policy\s+([\d.]+)", n)
        prefix = "OP" if "operational" in n else "DC"
        return f"{prefix} {m.group(1)}" if m else prefix
    if "local planning policy" in n:
        m = re.search(r"local planning policy\s+([\d.]+)", n)
        return f"LPP {m.group(1)}" if m else "LPP"
    if "planning bulletin" in n:
        m = re.search(r"planning bulletin\s+(\d+)", n)
        return f"PB {m.group(1)}" if m else "PB"
    if "position statement" in n:
        return "PS"
    if "structure plan" in n:
        return "SP"
    if "region scheme" in n:
        return "RS"
    if "local planning scheme" in n:
        m = re.search(r"scheme\s+(?:no\.\s*)?(\d+)", n)
        return f"LPS{m.group(1)}" if m else "LPS"
    return ""


def extract_operative_status(name: str, text: str) -> str:
    """Best-effort operative status."""
    t = text.lower()[:5000]
    if "superseded" in t and ("previous" in t or "former" in t):
        return "superseded"
    if "draft" in t and "consultation" in t:
        return "proposed"
    if "withdrawn" in t:
        return "historical"
    return "current"


def extract_key_standards(text: str, max_rows: int = 12) -> list[dict]:
    """Pull out a small set of plausible numeric standards from the text.

    Cheap heuristic: take the first 12k chars, then mine lines that look
    like numeric + unit + clause/table reference. Not exhaustive — only
    used to seed key_numeric_standards with reasonable values.
    """
    if not text:
        return []
    out: list[dict] = []
    seen: set[str] = set()
    # limit scanning cost
    scan = text[:25000]
    # pattern: "X m" or "X%" near a clause ref
    for line in scan.splitlines():
        line = line.strip()
        if len(line) < 6 or len(line) > 200:
            continue
        m = M_DASH_RE.search(line)
        if m:
            v1, v2, u = m.group(1), m.group(2), m.group(3)
            key = f"{v1}-{v2}{u}"
            if key in seen:
                continue
            seen.add(key)
            clause = ""
            cm = re.search(r"(?:clause|cl\.?|section|table|part)\s+([\d.]+(?:\.\d+)*[A-Z]?)", line, re.IGNORECASE)
            if cm:
                clause = cm.group(0)
            out.append({
                "topic": line[:60].rstrip(",.;:") if len(line) > 60 else "range",
                "value": f"{v1}-{v2}",
                "unit": u.lower(),
                "applies_to": "",
                "clause_ref": clause,
            })
            if len(out) >= max_rows:
                break
            continue
        m = NUMERIC_RE.search(line)
        if m:
            v, u = m.group(1), m.group(2)
            key = f"{v}{u}"
            if key in seen:
                continue
            seen.add(key)
            clause = ""
            cm = re.search(r"(?:clause|cl\.?|section|table|part)\s+([\d.]+(?:\.\d+)*[A-Z]?)", line, re.IGNORECASE)
            if cm:
                clause = cm.group(0)
            out.append({
                "topic": line[:60].rstrip(",.;:") if len(line) > 60 else "value",
                "value": v,
                "unit": u.lower(),
                "applies_to": "",
                "clause_ref": clause,
            })
            if len(out) >= max_rows:
                break
    return out


def extract_cross_references(text: str, aliases: dict[str, str]) -> list[dict]:
    """Pull out plausible instrument-name references from the text."""
    if not text:
        return []
    refs: list[dict] = []
    seen: set[str] = set()
    for raw_name, mid in aliases.items():
        if not raw_name or len(raw_name) < 4:
            continue
        if raw_name.lower() in text.lower():
            key = raw_name.lower()
            if key in seen:
                continue
            seen.add(key)
            refs.append({"cited": raw_name, "manifest_id": mid})
            if len(refs) >= 30:
                break
    return refs


def residential_relevance(category: str, name: str) -> str:
    n = (name or "").lower()
    c = (category or "").lower()
    if c == "planning_code" or "residential design codes" in n or "r-codes" in n:
        return "high"
    if c in {"scheme", "LPP"} and ("residential" in n or "housing" in n or "dwelling" in n):
        return "high"
    if c in {"DC", "position_statement", "planning_bulletin"} and "residential" in n:
        return "medium"
    if c in {"SPP"} and "residential" in n:
        return "medium"
    if c in {"scheme", "region_scheme", "strategy", "building_code"}:
        return "low"
    if c in {"LPP", "DC", "position_statement"}:
        return "low"
    return "none"


def build_one(row: dict, aliases: dict[str, str]) -> tuple[str, dict]:
    rid = row["id"]
    name = row["instrument_name"]
    category = row["category"]
    ext_dir = EXTRACTED / rid
    summary = {}
    full_text = ""
    if (ext_dir / "summary.json").exists():
        try:
            summary = json.loads((ext_dir / "summary.json").read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            summary = {}
    if (ext_dir / "full_text.txt").exists():
        full_text = (ext_dir / "full_text.txt").read_text(encoding="utf-8", errors="replace")
    full_text_len = len(full_text.strip())

    is_empty = full_text_len < 400
    if is_empty:
        scope = "(metadata-only / registration wall)" if category in {"building_code", "NCC"} else "(no extracted text)"
        analysis = {
            "id": rid,
            "normalized_title": name,
            "instrument_no": slug_instr(name),
            "version_date": (row.get("expected_version_hint") or "").strip() or None,
            "operative_status": "current" if (row.get("status") or "") in {"extracted", "acquired"} else (row.get("status") or "current"),
            "scope_summary": scope,
            "key_numeric_standards": [],
            "definitions": [],
            "cross_references": [],
            "residential_relevance": "none" if category in {"building_code", "NCC"} else residential_relevance(category, name),
            "quality_flags": ["empty full_text.txt (< 400 chars); treated as metadata-only"] if not full_text_len else ["partial full_text.txt"],
        }
        return rid, analysis

    # Otherwise do real extraction
    key_standards = extract_key_standards(full_text)
    cross_refs = extract_cross_references(full_text, aliases)
    # scope_summary from summary.json headings if present
    headings = summary.get("key_provisions", []) if isinstance(summary, dict) else []
    if headings:
        scope_bits = []
        for h in headings[:5]:
            if isinstance(h, dict) and h.get("summary"):
                scope_bits.append(h["summary"][:120])
            elif isinstance(h, str):
                scope_bits.append(h[:120])
        scope_summary = "; ".join(b for b in scope_bits if b)[:600] or name
    else:
        scope_summary = (full_text[:400].replace("\n", " ").strip() or name)

    # Detect quality issues
    qflags: list[str] = []
    if full_text_len < 1000:
        qflags.append(f"short full_text.txt ({full_text_len} chars)")
    if "yradnuob" in full_text or "lacos" in full_text or "noisnemid" in full_text:
        qflags.append("mirrored-text artifacts from rotated figure labels")
    if re.search(r"\b\w{40,}\b", full_text):
        qflags.append("extreme token lengths suggest column interleaving")

    analysis = {
        "id": rid,
        "normalized_title": name,
        "instrument_no": slug_instr(name),
        "version_date": (row.get("expected_version_hint") or "").strip() or None,
        "operative_status": extract_operative_status(name, full_text),
        "scope_summary": scope_summary,
        "key_numeric_standards": key_standards,
        "definitions": [],
        "cross_references": cross_refs,
        "residential_relevance": residential_relevance(category, name),
        "quality_flags": qflags,
    }
    return rid, analysis


def main() -> None:
    aliases_path = REPO_ROOT / "data" / "instrument_aliases.json"
    aliases: dict[str, str] = {}
    if aliases_path.exists():
        try:
            aliases = json.loads(aliases_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            aliases = {}

    with open(MANIFEST, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    existing = {p.name for p in ANALYSIS.iterdir() if p.is_dir() and (p / "analysis.json").exists()} if ANALYSIS.exists() else set()
    made: list[str] = []
    skipped: list[str] = []
    for row in rows:
        rid = row["id"]
        if rid in existing:
            skipped.append(rid)
            continue
        rid2, analysis = build_one(row, aliases)
        out_dir = ANALYSIS / rid2
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "analysis.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
        made.append(rid)
    print(f"made: {len(made)} -> {made[:10]}{'...' if len(made) > 10 else ''}")
    print(f"skipped (already existed): {len(skipped)}")


if __name__ == "__main__":
    main()
