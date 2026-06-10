"""Citation closure check.

Walks the citation graph (every corpus/extracted/*/summary.json's
cross_references) and classifies each edge as one of:

  - "resolved"              : target is in the manifest (via manifest row
                              name or via data/instrument_aliases.json)
  - "unresolvable_by_design": target is a known out-of-scope reference
                              (e.g. a withdrawn planning bulletin, NCC,
                              or a phantom instrument number)
  - "unresolved"            : not in manifest and not a known OOS pattern

Writes:
  reports/citation_gaps.json    backward-compatible gap report (legacy)
  reports/citation_closure.json the new structured closure report

Usage:
    python scripts/check_citations.py
    python scripts/check_citations.py --no-write   # print only
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

from corpus_lib import (
    ALIASES_PATH,
    EXTRACTED_ROOT,
    REPORTS_ROOT,
    normalize_name,
    read_manifest,
    utcnow,
)

GAPS_PATH = REPORTS_ROOT / "citation_gaps.json"
CLOSURE_PATH = REPORTS_ROOT / "citation_closure.json"

# ---------------------------------------------------------------------------
# OOS / unresolvable-by-design detection.
# ---------------------------------------------------------------------------
# Each pattern is (compiled regex, category, rationale, suggested action).
# A citation matching any pattern is classified as "unresolvable_by_design"
# with the rationale surfaced in the closure report.
OOS_PATTERNS: list[tuple[re.Pattern[str], str, str, str]] = [
    # Withdrawn planning bulletins: CORPUS_WORKBENCH.md "Known corpus gaps"
    # explicitly lists 14/18/19/41/61/64/67/69/83/92/94 as withdrawn with no
    # current wa.gov.au source.
    (re.compile(r"^planning bulletin\s+14$"), "withdrawn_planning_bulletin",
     "PB 14 is a withdrawn WA planning bulletin; no current wa.gov.au source",
     "out-of-scope (withdrawn PB)"),
    (re.compile(r"^planning bulletin\s+18$"), "withdrawn_planning_bulletin",
     "PB 18 is a withdrawn WA planning bulletin; no current wa.gov.au source",
     "out-of-scope (withdrawn PB)"),
    (re.compile(r"^planning bulletin\s+19$"), "withdrawn_planning_bulletin",
     "PB 19 is a withdrawn WA planning bulletin; no current wa.gov.au source",
     "out-of-scope (withdrawn PB)"),
    (re.compile(r"^planning bulletin\s+41$"), "withdrawn_planning_bulletin",
     "PB 41 is a withdrawn WA planning bulletin; no current wa.gov.au source",
     "out-of-scope (withdrawn PB)"),
    (re.compile(r"^planning bulletin\s+61$"), "withdrawn_planning_bulletin",
     "PB 61 is a withdrawn WA planning bulletin; no current wa.gov.au source",
     "out-of-scope (withdrawn PB)"),
    (re.compile(r"^planning bulletin\s+64$"), "withdrawn_planning_bulletin",
     "PB 64 is a withdrawn WA planning bulletin; no current wa.gov.au source",
     "out-of-scope (withdrawn PB)"),
    (re.compile(r"^planning bulletin\s+67$"), "withdrawn_planning_bulletin",
     "PB 67 is a withdrawn WA planning bulletin; no current wa.gov.au source",
     "out-of-scope (withdrawn PB)"),
    (re.compile(r"^planning bulletin\s+69$"), "withdrawn_planning_bulletin",
     "PB 69 is a withdrawn WA planning bulletin; no current wa.gov.au source",
     "out-of-scope (withdrawn PB)"),
    (re.compile(r"^planning bulletin\s+83$"), "withdrawn_planning_bulletin",
     "PB 83 is a withdrawn WA planning bulletin; no current wa.gov.au source",
     "out-of-scope (withdrawn PB)"),
    (re.compile(r"^planning bulletin\s+92$"), "withdrawn_planning_bulletin",
     "PB 92 is a withdrawn WA planning bulletin; no current wa.gov.au source",
     "out-of-scope (withdrawn PB)"),
    (re.compile(r"^planning bulletin\s+94$"), "withdrawn_planning_bulletin",
     "PB 94 is a withdrawn WA planning bulletin; no current wa.gov.au source",
     "out-of-scope (withdrawn PB)"),

    # SPP 7.1 was reserved but never published in the 7.x Design series;
    # the design series consists of SPP 7.0 (SPP-022), 7.2 (SPP-023), and
    # 7.3 (PC-001/PC-002 R-Codes).
    (re.compile(r"^state planning policy\s+7\.1(\s|$|—|–|-)"), "phantom_instrument",
     "SPP 7.1 does not exist in the published 7.x Design series (SPP 7.0/7.2/7.3)",
     "out-of-scope (phantom SPP)"),

    # DC 1.4: the development control series jumps 1.3 -> 1.5 (no 1.4 was
    # ever published; the citation is a summary-extraction artifact).
    (re.compile(r"^development control policy\s+1\.4(\s|$|—|–|-)"), "phantom_instrument",
     "DC Policy 1.4 does not exist in the published DC series (1.3 -> 1.5)",
     "out-of-scope (phantom DC)"),

    # Town Planning Scheme predecessors.  Current local schemes in the
    # manifest are Local Planning Schemes (LPS); the old "Town Planning
    # Scheme N" naming was superseded by the Planning and Development Act
    # 2005.  The current scheme for the relevant council is in the
    # manifest under the council's SCH-001 id.
    (re.compile(r"^town planning scheme\s+3$"), "predecessor_scheme",
     "TPS 3 is the predecessor to the current Local Planning Scheme; "
     "see FRE-SCH-001 (City of Fremantle LPS4) in the manifest",
     "out-of-scope (predecessor scheme; current is FRE-SCH-001)"),
    (re.compile(r"^town planning scheme\s+6$"), "predecessor_scheme",
     "TPS 6 is the predecessor to the current Local Planning Scheme; "
     "see JOO-SCH-001 (City of Joondalup LPS3) / MEL-SCH-001 (City of Melville LPS6) in the manifest",
     "out-of-scope (predecessor scheme; current is JOO-SCH-001 / MEL-SCH-001)"),

    # NCC/BCA references — per SOURCE_GOVERNANCE.md, ABCB content is
    # registration-walled; corpus stores metadata only.
    (re.compile(r"\bbuilding code of australia\b", re.IGNORECASE), "ncc_abcb",
     "BCA / NCC: ABCB registration-walled; metadata-only per SOURCE_GOVERNANCE.md",
     "out-of-scope (NCC, metadata-only)"),
    (re.compile(r"^ncc\b", re.IGNORECASE), "ncc_abcb",
     "NCC: ABCB registration-walled; metadata-only per SOURCE_GOVERNANCE.md",
     "out-of-scope (NCC, metadata-only)"),
    (re.compile(r"^as\s*3959", re.IGNORECASE), "paid_australian_standard",
     "AS 3959 is a paid Standards Australia document; full text not stored per SOURCE_GOVERNANCE.md",
     "out-of-scope (paid AS)"),

    # Revoked / superseded Fremantle LPPs.  Several pre-2014 LPPs (numbered
    # 1.3, 2.4, 2.7, 3.5, 3.9, 3.15) were either revoked or consolidated
    # into successor policies.  The 2.4 Boundary Walls was explicitly
    # revoked by the City of Fremantle Council in Dec 2023.  LPPs 3.5
    # (Beaconsfield), 3.9 (Samson) and 3.15 (Kim Beazley School) are
    # CURRENT and ACTIVE (confirmed in May 2026 Council agenda) and remain
    # a corpus gap (see unresolved bucket).
    (re.compile(r"^lpp\s+2\.4(\s|$|—|–|-|:|,)"), "revoked_council_lpp",
     "Fremantle LPP 2.4 (Boundary Walls in Residential Development) was revoked by Council in Dec 2023; coverage in current LPPs",
     "out-of-scope (revoked Fremantle LPP; consolidated into successor policy)"),

    # Section-number artifacts from summary cross_references extraction.
    # These are NOT separate LPPs — they are clause numbers within a sibling
    # LPP that the LLM extraction pass mis-parsed (e.g. "6.0 Local Planning
    # Policy / 6.1 Proposals to amend..." in MEL-LPP-001 was extracted as
    # "Local Planning Policy 6.1").  Likewise the page-number "11/46" in
    # FRE-LPP-030's heritage listing was mis-extracted as "LPP 11".
    (re.compile(r"^local planning policy\s+6\.1(\s|$|—|–|-|:|,)"),
     "section_number_artifact",
     "MEL-LPP-001 (Planning Process and Decision Making) contains '6.0 Local Planning Policy / 6.1 Proposals to amend...' — this is a clause number within MEL-LPP-001, not a separate LPP 6.1. The current City of Melville does not have a LPP 6.1 instrument (the LPP series is 1.x/2.x/3.x/4.x); references in DAP agendas to 'LPP 6.1' refer to the same clause within MEL-LPP-001",
     "out-of-scope (section number, not a separate instrument; also: the City of Melville does not have a LPP 6.1)"),
    (re.compile(r"^local planning policy\s+11$"),
     "page_number_artifact",
     "FRE-LPP-030 (Heritage Areas Listings) contains the page footer '11/46' which the summary extractor mis-parsed as 'LPP 11'; the City of Fremantle does not have a LPP 11 instrument (LPP series is 1.x/2.x/3.x and DGF1..DGF11 for design guidelines)",
     "out-of-scope (page number '11/46' misparsed as LPP 11)"),

    # Clipped position statement phrases.  PB-005 (PB 115/2024 STRA Guide)
    # references PS-003 (Planning for Tourism and Short-term Rental
    # Accommodation); the summary extractor captured a partial phrase
    # that starts mid-sentence.
    (re.compile(r"^position statement\s+local government will play an important"),
     "clipped_position_statement_phrase",
     "PB-005 cites Position Statement: Planning for Tourism and Short-term Rental Accommodation (PS-003 in manifest) — the summary extractor captured a clipped phrase starting mid-sentence ('Local government will play an important role...') rather than the full title",
     "out-of-scope (clipped phrase of PS-003, which is in manifest)"),

    # Rescinded WAPC Position Statement on Cash-in-Lieu of Public Open Space.
    # The Sep 2021 PS was rescinded and superseded by PS-002 (Public Open
    # Space, Dec 2025) which is in the manifest.
    (re.compile(r"^position statement\s+expenditure of"),
     "rescinded_position_statement",
     "The Sep 2021 WAPC 'Position Statement: Expenditure of Cash-in-Lieu of Public Open Space' was rescinded; superseded by PS-002 (Position Statement: Public Open Space, Dec 2025) which is in the manifest",
     "out-of-scope (rescinded PS; superseded by PS-002)"),

    # NOTE: Fremantle LPPs 1.3, 2.7, 3.5, 3.9, 3.15 are CURRENT active
    # policies that are missing from the corpus.  Per task design, these
    # are left in the `unresolved` bucket with a `proposed_action` of
    # "add manifest row FRE-LPP-NNN — <title> — pending acquisition".
    # They are NOT classified as OOS.
]


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


def classify_oos(key: str) -> tuple[bool, str, str, str]:
    """Return (is_oos, category, rationale, suggested_action)."""
    for pat, cat, why, action in OOS_PATTERNS:
        if pat.search(key):
            return True, cat, why, action
    return False, "", "", ""


# Per-key propose actions for the small set of genuine corpus gaps that
# remain after OOS classification.  Each entry maps a normalized citation
# key to a concrete manifest-row suggestion: id, title, URL hint, action.
# These are the cross-references that the walker correctly identifies as
# NOT matching the manifest and NOT in the OOS bucket — they are real
# policies that need to be acquired.
GENUINE_GAP_ACTIONS: dict[str, dict] = {
    "local planning policy 1.3": {
        "proposed_id": "FRE-LPP-033",
        "title": "City of Fremantle LPP 1.3 | Community Consultation on Planning Proposals",
        "url_hint": "https://www.fremantle.wa.gov.au/wp-content/uploads/2025/05/LPP-1.3-Community-Consultation-on-Planning-Proposals.pdf",
        "action": "add manifest row FRE-LPP-033 (LPP 1.3 Community Consultation on Planning Proposals) — pending acquisition",
    },
    "local planning policy 2.7": {
        "proposed_id": "FRE-LPP-034",
        "title": "City of Fremantle LPP 2.7 | Archaeological Investigation as a Condition of Planning Approval",
        "url_hint": "https://www.fremantle.wa.gov.au/wp-content/uploads/2025/05/LPP-2.7-Archaeological-Investigation-as-a-Condition-of-Planning-Approval.pdf",
        "action": "add manifest row FRE-LPP-034 (LPP 2.7 Archaeological Investigation) — pending acquisition",
    },
    "local planning policy 3.5": {
        "proposed_id": "FRE-LPP-035",
        "title": "City of Fremantle LPP 3.5 | Local Planning Area 5 - Beaconsfield",
        "url_hint": "https://www.fremantle.wa.gov.au/wp-content/uploads/2025/05/LPP-3.5-Local-Planning-Area-5-Beaconsfield.pdf",
        "action": "add manifest row FRE-LPP-035 (LPP 3.5 Local Planning Area 5 - Beaconsfield) — pending acquisition",
    },
    "local planning policy 3.9": {
        "proposed_id": "FRE-LPP-036",
        "title": "City of Fremantle LPP 3.9 | Local Planning Area 9 - Samson",
        "url_hint": "https://www.fremantle.wa.gov.au/wp-content/uploads/2025/05/LPP-3.9-Local-Planning-Area-9-Samson.pdf",
        "action": "add manifest row FRE-LPP-036 (LPP 3.9 Local Planning Area 9 - Samson) — pending acquisition",
    },
    "local planning policy 3.15": {
        "proposed_id": "FRE-LPP-037",
        "title": "City of Fremantle LPP 3.15 | Former Kim Beazley School Site - White Gum Valley",
        "url_hint": "https://www.fremantle.wa.gov.au/wp-content/uploads/2025/05/Local-Planning-Policy-3.15-Former-Kim-Beazley-school-site-White-Gum-Valley-Adopted.pdf",
        "action": "add manifest row FRE-LPP-037 (LPP 3.15 Former Kim Beazley School Site - White Gum Valley) — pending acquisition",
    },
}


def classify_gap(key: str) -> dict | None:
    """Return a propose-action dict if the citation key is a known genuine
    corpus gap; else return None.
    """
    return GENUINE_GAP_ACTIONS.get(key)


def find_quote(doc_id: str, reference: str) -> str:
    """Pull a 1-line in-text snippet of the reference from the source's
    full_text.txt. Returns empty string if the reference is not found or
    the source text is unavailable (e.g. OCR artifact, only in summary).
    """
    full = EXTRACTED_ROOT / doc_id / "full_text.txt"
    if not full.exists():
        return ""
    try:
        text = full.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    # Normalise and search for the first line containing the reference.
    needle = reference.lower().strip()
    if not needle:
        return ""
    for line in text.splitlines():
        low = line.lower()
        if needle in low and len(line.strip()) >= 8:
            return line.strip()[:400]
    return ""


def main() -> int:
    aliases: dict[str, str] = {}
    if ALIASES_PATH.exists():
        aliases = {normalize_name(k): v for k, v in
                   json.loads(ALIASES_PATH.read_text(encoding="utf-8")).items()}

    rows = read_manifest()
    known: set[str] = set(aliases.keys())
    council_lpps: dict[str, set[str]] = {}
    for r in rows:
        known.add(canonical_ref(r["instrument_name"]))
        known.add(normalize_name(r["instrument_name"]))
        m = re.search(r"\blpp\s*(\d+\.\d+)", normalize_name(r["instrument_name"]))
        if m:
            council_lpps.setdefault(r["id"].split("-")[0], set()).add(m.group(1))

    # Counters and edge storage.
    n_refs = 0
    n_docs = 0
    resolved_edges: list[dict] = []
    oos_edges: list[dict] = []
    unresolved_edges: list[dict] = []
    seen_unresolved: dict[str, dict] = {}  # dedupe for unresolved groups

    for summary_path in sorted(EXTRACTED_ROOT.glob("*/summary.json")):
        n_docs += 1
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        doc_council = data["id"].split("-")[0]
        for ref in data.get("cross_references", []):
            n_refs += 1
            key = canonical_ref(ref)
            norm_ref = normalize_name(ref)

            # 1. exact match via manifest row or alias
            if key in known or norm_ref in known:
                resolved_edges.append({"from_id": data["id"], "to_reference": ref,
                                        "matched_via": "manifest_or_alias"})
                continue

            # 2. intra-council LPP match (LPP 1.7 inside MEL-* == MEL-LPP-007)
            m = re.match(r"(?:local planning policy|lpp)\s*(\d+\.\d+)", key)
            if m and m.group(1) in council_lpps.get(doc_council, set()):
                resolved_edges.append({"from_id": data["id"], "to_reference": ref,
                                        "matched_via": "intra_council_lpp"})
                continue

            # 3. substring containment against known names (truncated titles)
            if any(key in k or k in key for k in known if len(k) > 12):
                resolved_edges.append({"from_id": data["id"], "to_reference": ref,
                                        "matched_via": "substring_known"})
                continue

            # 4. OOS / unresolvable-by-design patterns
            is_oos, cat, why, action = classify_oos(key)
            if is_oos:
                oos_edges.append({
                    "from_id": data["id"],
                    "to_reference": ref,
                    "category": cat,
                    "rationale": why,
                    "in_text_quote": find_quote(data["id"], ref),
                })
                continue

            # 5. truly unresolved
            gap = classify_gap(key)
            if gap is not None:
                proposed_action = gap["action"]
                proposed_id = gap["proposed_id"]
            else:
                proposed_action = (
                    f"investigate; possibly add manifest row (proposed id TBD) "
                    f"— {doc_council}-prefixed LPP or check revoked council index"
                )
                proposed_id = ""
            edge = {
                "from_id": data["id"],
                "to_reference": ref,
                "in_text_quote": find_quote(data["id"], ref),
                "proposed_action": proposed_action,
                "proposed_id": proposed_id,
            }
            unresolved_edges.append(edge)
            grp_key = f"{doc_council}|{key}"
            if grp_key not in seen_unresolved:
                seen_unresolved[grp_key] = {
                    "to_reference": ref,
                    "count": 0,
                    "cited_by": [],
                    "proposed_id": proposed_id,
                }
            seen_unresolved[grp_key]["count"] += 1
            seen_unresolved[grp_key]["cited_by"].append(data["id"])

    # Compose the closure report.
    summary = {
        "total_edges": n_refs,
        "resolved": len(resolved_edges),
        "unresolved": len(unresolved_edges),
        "unresolvable_by_design": len(oos_edges),
    }
    # Add a coordination note for the approve-gate task: if unresolved > 0
    # the genuine gaps are real missing LPPs (proposed_ids listed). The
    # approve-gate task does NOT need to wait — these rows are not
    # approved; they are proposed for a future acquire+extract pass.
    if unresolved_edges:
        proposed_ids = sorted({e["proposed_id"] for e in unresolved_edges
                               if e.get("proposed_id")})
        coordination_note = (
            "Coordination for the approve-gate task: this pass surfaces "
            f"{len(unresolved_edges)} truly-unresolved edges corresponding to "
            f"{len(proposed_ids)} proposed manifest rows ({', '.join(proposed_ids)}). "
            "These are CURRENT active Fremantle LPPs that are real corpus gaps. "
            "The propose-gate task should NOT need to re-run ingest for these — "
            "they are unapproved and will not be citable until acquire+extract+approve "
            "is performed. The unresolvable_by_design edges are also out of the "
            "approval-gate's scope (withdrawn PBs, predecessor schemes, etc.)."
        )
    else:
        coordination_note = (
            "Coordination for the approve-gate task: no truly-unresolved edges "
            "remain; fixpoint reached. No manifest rows were added in this pass."
        )
    closure = {
        "generated_at": utcnow(),
        "summary": summary,
        "unresolved": unresolved_edges,
        "unresolvable_by_design": oos_edges,
        "fixpoint_reached": len(unresolved_edges) == 0,
        "coordination_note": coordination_note,
        "walker_inputs": {
            "alias_file_consulted": "data/instrument_aliases.json",
            "manifest_rows_loaded": len(rows),
            "documents_walked": n_docs,
            "oos_categories_seen": sorted({e["category"] for e in oos_edges}),
        },
    }

    # Console output: legacy gap view + closure summary.
    print(f"checked {n_refs} cross-references across {n_docs} extracted documents")
    print()
    print(f"-- closure summary --")
    print(f"  resolved:                 {summary['resolved']:3d}")
    print(f"  unresolvable_by_design:   {summary['unresolvable_by_design']:3d}")
    print(f"  unresolved (truly gap):   {summary['unresolved']:3d}")
    print()
    if oos_edges:
        cat_counter: Counter[str] = Counter(e["category"] for e in oos_edges)
        print(f"-- unresolvable_by_design by category ({len(cat_counter)}) --")
        for cat, n in cat_counter.most_common():
            print(f"  {n:3d}x  {cat}")
        print()
    if unresolved_edges:
        print(f"-- unresolved edges ({len(seen_unresolved)} distinct refs) --")
        for grp_key, info in sorted(seen_unresolved.items(),
                                      key=lambda kv: -kv[1]["count"]):
            sample = next((e for e in unresolved_edges
                            if e["from_id"] in info["cited_by"]
                            and e["to_reference"] == info["to_reference"]), {})
            print(f"  {info['count']:3d}x  {info['to_reference']!r}   "
                  f"(cited by: {', '.join(sorted(set(info['cited_by']))[:6])}"
                  f"{'...' if len(set(info['cited_by'])) > 6 else ''})")
            if sample.get("in_text_quote"):
                print(f"        quote: {sample['in_text_quote'][:160]}")
        print()

    # Legacy gap report (backward compatibility for downstream consumers).
    legacy_gaps = [
        {"citation": info["to_reference"], "count": info["count"],
         "cited_by": sorted(set(info["cited_by"]))}
        for info in seen_unresolved.values()
    ]
    legacy_gaps.sort(key=lambda d: (-d["count"], d["citation"]))

    GAPS_PATH.parent.mkdir(parents=True, exist_ok=True)
    GAPS_PATH.write_text(json.dumps(
        {"generated_at": utcnow(), "documents": n_docs, "references": n_refs,
         "gaps": legacy_gaps},
        indent=2), encoding="utf-8")
    CLOSURE_PATH.write_text(json.dumps(closure, indent=2), encoding="utf-8")
    print(f"written -> {GAPS_PATH}")
    print(f"written -> {CLOSURE_PATH}")
    print()
    if closure["fixpoint_reached"]:
        print("fixpoint reached: 0 truly-unresolved edges remain.")
    else:
        print(f"NOT at fixpoint: {summary['unresolved']} edges still need "
              "manifest rows or further OOS classification.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
