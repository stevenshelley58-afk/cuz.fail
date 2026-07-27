"""Extract WAPC Operational Policy 2.2 (Residential Subdivision, May 2024)
textual provisions into rule candidate JSON rows (same report schema as
extract_rcodes_v3.py).

OP 2.2 (9 pp) has no ruled tables; candidates are hand-specified against
verified section text. Each candidate carries an evidence substring that
MUST appear in the PDF text (whitespace-normalised) or the candidate is
dropped with a warning — no invented provisions.

Creates one real `clauses` row per policy section so that
bulk_approve_rules.py satisfies the rules.clause_id FK.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import re
import sys
from pathlib import Path
from uuid import uuid4

try:
    import pdfplumber
except ImportError:
    pdfplumber = None  # type: ignore[assignment]

CLAUSES = {
    "s4_1": "Section 4.1 – General requirements",
    "s4_2": "Section 4.2 – Lot sizes",
    "s4_5": "Section 4.5 – Battleaxe subdivision",
    "s4_6": "Section 4.6 – Vehicle access to residential lots",
    "s4_7": "Section 4.7 – Provision of screen fencing",
}

CODES_R2_R40 = ["R2", "R2.5", "R5", "R10", "R12.5", "R15", "R17.5",
                "R20", "R25", "R30", "R35", "R40"]
CODES_R50_PLUS = ["R50", "R60", "R80", "R100", "R160"]
CODES_R10_R35 = ["R10", "R12.5", "R15", "R17.5", "R20", "R25", "R30", "R35"]
CODES_ALL = CODES_R2_R40 + CODES_R50_PLUS


def make_candidate(rule_key, canonical, operator, value, unit, quote,
                   table_ref, r_codes, clause_id, source_version_id,
                   condition=None, evaluable="yes", raw_text=None):
    vj = {"value": value} if value is not None else {"raw_text": raw_text}
    return {
        "rule_key": rule_key,
        "canonical_rule_key": canonical,
        "rule_type": "standard",
        "pathway": "deemed_to_comply",
        "dwelling_type": None,
        "applicable_r_codes": r_codes,
        "applicable_zones": None,
        "council_scope": None,
        "operator": operator,
        "value_json": vj,
        "unit": unit,
        "condition_json": condition or (
            {"needs_human_review": True} if evaluable != "yes" else {}),
        "quote": quote,
        "instrument_section": "Section 4 — Policy measures",
        "table_reference": table_ref,
        "effective_from": None,
        "effective_to": None,
        "source_version_id": source_version_id,
        "clause_id": clause_id,
        "extractor_model": "targeted_text_extraction:op2_2-may2024",
        "check_type": "min_value" if operator == "gte" else "max_value",
        "evaluable": evaluable,
    }


def ensure_clauses(db_url, sv_id):
    import psycopg
    ids = {}
    with psycopg.connect(db_url) as conn:
        cur = conn.cursor()
        for clause_key, title in CLAUSES.items():
            cur.execute(
                "SELECT id FROM clauses WHERE source_version_id = %s "
                "AND clause_key = %s", (sv_id, clause_key))
            row = cur.fetchone()
            if row:
                ids[clause_key] = str(row[0])
                continue
            cid = str(uuid4())
            cur.execute(
                """INSERT INTO clauses
                   (id, source_version_id, clause_key, clause_type, title,
                    text, parser_name, parser_version, created_at, updated_at)
                   VALUES (%s, %s, %s, 'text', %s, %s,
                           'targeted_text_extraction', 'op2_2-may2024',
                           now(), now())""",
                (cid, sv_id, clause_key, title,
                 (f"{title} — WAPC Operational Policy 2.2 Residential "
                 f"Subdivision (May 2024)")))
            ids[clause_key] = cid
            print(f"  Created clause {clause_key}: {cid}")
        conn.commit()
    return ids


def build_candidates(sv_id, clause_ids):
    """Returns list of (candidate, evidence_substring)."""
    out = []

    # --- 4.2.4(a): 5% variation to minimum lot size (one lot) ---------------
    out.append((
        make_candidate(
            "op22_lot_size_min_variation_max_pct",
            "lot_size_min_variation_max_pct", "lte", 5.0, "%",
            "OP 2.2 s4.2.4(a): the variation reduces the area of that one lot "
            "by no more than five per cent of the minimum lot size specified "
            "in R-Codes Volume 1 Table D or elsewhere in the R-Codes.",
            "s4_2", CODES_ALL, clause_ids["s4_2"], sv_id,
            condition={"applies_to": "one_lot_only",
                       "reference": "R-Codes Volume 1 Table D minimum lot size",
                       "note": "For dual coded land, applicable to base coding only"}),
        ("reduces the area of that one lot by no more than five per cent of the "
        "minimum lot size")))

    # --- 4.2.4(a): 5% variation to average lot size -------------------------
    out.append((
        make_candidate(
            "op22_avg_lot_size_variation_max_pct",
            "avg_lot_size_variation_max_pct", "lte", 5.0, "%",
            "OP 2.2 s4.2.4(a): the variation in the area of that one lot "
            "reduces the average lot size of the overall subdivision by no "
            "more than five per cent of the average lot size specified in the "
            "R-Codes Volume 1 Table D or elsewhere in the R-Codes.",
            "s4_2", CODES_ALL, clause_ids["s4_2"], sv_id,
            condition={"reference": "R-Codes Volume 1 Table D average lot size"}),
        ("reduces the average lot size of the overall subdivision by no more "
        "than five per cent")))

    # --- 4.2.4(b): average variation >5% eligibility (R10-R35, corner) ------
    out.append((
        make_candidate(
            "op22_avg_lot_size_variation_gt5pct_eligibility",
            "avg_lot_size_variation_gt5pct_eligibility", "gte", None, "text",
            "OP 2.2 s4.2.4(b): any average lot size variation greater than "
            "five per cent meets all of the following criteria: a single "
            "residential coding of R10 to R35 applies to the land; the site "
            "is a corner lot with frontage to two different streets ...; all "
            "proposed lots comply with the minimum lot size and frontage "
            "requirements specified in the R-Codes Volume 1 Table D.",
            "s4_2", CODES_R10_R35, clause_ids["s4_2"], sv_id,
            evaluable="needs_human_review",
            raw_text="Average lot size variation >5% only considered for "
                     "single-coded R10-R35 corner lots where all proposed "
                     "lots meet Table D minimum lot size and frontage."),
        "R35 applies to the land"))

    # --- 4.5.5: no lot size reductions for battleaxe lots --------------------
    out.append((
        make_candidate(
            "op22_battleaxe_lot_size_reduction_prohibited",
            "battleaxe_lot_size_reduction_prohibited", "gte", None, "text",
            "OP 2.2 s4.5.5: The minimum battleaxe lot area will be as set out "
            "in the R-Codes Volume 1 Part D clause 1.1 and Table D. The WAPC "
            "will not permit reductions in the minimum or average lot sizes "
            "for battleaxe lots.",
            "s4_5", CODES_ALL, clause_ids["s4_5"], sv_id,
            evaluable="needs_human_review",
            raw_text="Minimum battleaxe lot area per R-Codes Vol 1 Part D "
                     "Table D; no reductions in minimum or average lot sizes "
                     "for battleaxe lots."),
        "average lot sizes for battleaxe lots"))

    # --- 4.5.6: effective lot area, non-R-Code locations ---------------------
    out.append((
        make_candidate(
            "op22_battleaxe_effective_lot_area_min_m2_uncoded",
            "battleaxe_effective_lot_area_min_m2", "gte", 850.0, "m2",
            "OP 2.2 s4.5.6: In locations not subject to the provisions of the "
            "R-Codes, the WAPC will normally require residential battleaxe "
            "lots to have an effective lot area of at least 850m2 to "
            "overcome the sense of confinement from lack of street frontage.",
            "s4_5", ["UNCODED"], clause_ids["s4_5"], sv_id,
            condition={"applies_where": "locations not subject to the "
                                        "provisions of the R-Codes"}),
        "effective lot area of at least 850m2"))

    # --- 4.5.7: battleaxe leg width (per R-code) -----------------------------
    for rc in CODES_R2_R40:
        out.append((
            make_candidate(
                f"op22_battleaxe_leg_width_min_m_{rc.lower().replace('.', '_').replace('-', '_')}",
                "battleaxe_leg_width_min_m", "gte", 4.0, "m",
                "OP 2.2 s4.5.7: A battleaxe leg should be a minimum of: "
                "4 metres in width (R2-R40); or, 3.6 metres in width "
                "(R50 and higher).",
                "s4_5", [rc], clause_ids["s4_5"], sv_id,
                condition={"r_code_band": "R2-R40",
                           "purpose": "allow for a 3m constructed driveway, "
                                      "landscaping space and the necessary "
                                      "public utility services"}),
            "4 metres in width (R2-R40)"))
    for rc in CODES_R50_PLUS:
        out.append((
            make_candidate(
                f"op22_battleaxe_leg_width_min_m_{rc.lower().replace('.', '_').replace('-', '_')}",
                "battleaxe_leg_width_min_m", "gte", 3.6, "m",
                "OP 2.2 s4.5.7: A battleaxe leg should be a minimum of: "
                "4 metres in width (R2-R40); or, 3.6 metres in width "
                "(R50 and higher).",
                "s4_5", [rc], clause_ids["s4_5"], sv_id,
                condition={"r_code_band": "R50 and higher",
                           "purpose": "allow for a 3m constructed driveway, "
                                      "landscaping space and the necessary "
                                      "public utility services"}),
            "3.6 metres in width (R50 and higher)"))

    # --- 4.5.7: constructed driveway width -----------------------------------
    out.append((
        make_candidate(
            "op22_battleaxe_driveway_width_min_m",
            "battleaxe_driveway_width_min_m", "gte", 3.0, "m",
            "OP 2.2 s4.5.7: ... to allow for a 3m constructed driveway, "
            "landscaping space and the necessary public utility services.",
            "s4_5", CODES_ALL, clause_ids["s4_5"], sv_id),
        "to allow for a 3m constructed driveway"))

    # --- 4.5.10: max adjoining access legs -----------------------------------
    out.append((
        make_candidate(
            "op22_battleaxe_access_legs_adjoining_max",
            "battleaxe_access_legs_adjoining_max", "lte", 2.0, "count",
            "OP 2.2 s4.5.10: Battleaxe arrangements involving more than two "
            "access legs will not be accepted unless there are exceptional "
            "circumstances to justify such an arrangement. Where more than "
            "two adjoining battle-axe legs are proposed, access should be "
            "provided by way of a constructed street.",
            "s4_5", CODES_ALL, clause_ids["s4_5"], sv_id,
            condition={"exception": "exceptional circumstances"}),
        "more than two access legs will not be accepted"))

    # --- 4.5.12: truncations --------------------------------------------------
    out.append((
        make_candidate(
            "op22_battleaxe_leg_truncation_at_effective_area_min_m",
            "battleaxe_leg_truncation_at_effective_area_min_m", "gte", 3.0, "m",
            "OP 2.2 s4.5.12: A 3 x 3 metre truncation of 4.24 metres may be "
            "required at the point where the access leg joins the effective "
            "area of the lot, for vehicular access and manoeuvrability.",
            "s4_5", CODES_ALL, clause_ids["s4_5"], sv_id,
            condition={"truncation_diagonal_m": 4.24,
                       "location": "access leg joins effective area of lot"}),
        "3 x 3 metre truncation of 4.24 metres"))
    out.append((
        make_candidate(
            "op22_battleaxe_leg_truncation_at_street_min_m",
            "battleaxe_leg_truncation_at_street_min_m", "gte", 1.5, "m",
            "OP 2.2 s4.5.12: A 1.5 x 1.5 metre truncation of 2.12 metres may "
            "be required at the point where the access leg meets the street "
            "reserve, particularly on major roads and where non visually "
            "permeable street walls and fences exist.",
            "s4_5", CODES_ALL, clause_ids["s4_5"], sv_id,
            condition={"truncation_diagonal_m": 2.12,
                       "location": "access leg meets street reserve"}),
        "1.5 x 1.5 metre truncation of 2.12 metres"))

    # --- 4.5.8: wider legs for rural / long legs (R2-R25) --------------------
    out.append((
        make_candidate(
            "op22_battleaxe_leg_width_rural_long_legs",
            "battleaxe_leg_width_min_m", "gte", None, "text",
            "OP 2.2 s4.5.8: In rural, rural-residential and low-density "
            "(R2-R25) subdivisions requiring long battleaxe legs, and "
            "locations where there are particular physical or topographical "
            "constraints, the WAPC, on the advice of the local government, "
            "may require a battleaxe leg wider than 4 metres.",
            "s4_5", ["R2", "R2.5", "R5", "R10", "R12.5", "R15", "R17.5",
                     "R20", "R25"], clause_ids["s4_5"], sv_id,
            evaluable="needs_human_review",
            raw_text="WAPC may require battleaxe leg wider than 4 metres for "
                     "R2-R25 subdivisions requiring long legs or constrained "
                     "sites."),
        "leg wider than 4 metres"))

    # --- 4.6.2: communal street passing threshold -----------------------------
    out.append((
        make_candidate(
            "op22_communal_street_passing_points_min_dwellings",
            "communal_street_passing_points_min_dwellings", "gte", 5.0,
            "dwellings",
            "OP 2.2 s4.6.2: The communal street must be designed to allow "
            "vehicles to pass in opposite directions at one or more points "
            "where five or more dwellings are served by the driveway in "
            "accordance with the R-Codes Volume 1.",
            "s4_6", CODES_ALL, clause_ids["s4_6"], sv_id,
            condition={"requirement": "passing points at one or more points"}),
        "pass in opposite directions"))

    # --- 4.7.2: screen fencing ------------------------------------------------
    out.append((
        make_candidate(
            "op22_screen_fence_solid_height_max_m",
            "screen_fence_solid_height_max_m", "lte", 1.2, "m",
            "OP 2.2 s4.7.2: the fences will be: substantially of solid "
            "construction to 1.2 metres in height and visually permeable to "
            "a maximum height (between 1.8 metres and 2.4 metres) ...",
            "s4_7", CODES_ALL, clause_ids["s4_7"], sv_id,
            condition={"applies_where": "lots abutting public reserves, where "
                                        "local planning framework does not "
                                        "outline specific standards"}),
        "to 1.2 metres in height and"))
    out.append((
        make_candidate(
            "op22_screen_fence_height_min_m",
            "screen_fence_height_min_m", "gte", 1.8, "m",
            "OP 2.2 s4.7.2: ... visually permeable to a maximum height "
            "(between 1.8 metres and 2.4 metres) ...",
            "s4_7", CODES_ALL, clause_ids["s4_7"], sv_id,
            condition={"applies_where": "lots abutting public reserves, where "
                                        "local planning framework does not "
                                        "outline specific standards"}),
        "between 1.8 metres and 2.4 metres"))
    out.append((
        make_candidate(
            "op22_screen_fence_height_max_m",
            "screen_fence_height_max_m", "lte", 2.4, "m",
            "OP 2.2 s4.7.2: ... visually permeable to a maximum height "
            "(between 1.8 metres and 2.4 metres) ...",
            "s4_7", CODES_ALL, clause_ids["s4_7"], sv_id,
            condition={"applies_where": "lots abutting public reserves, where "
                                        "local planning framework does not "
                                        "outline specific standards"}),
        "between 1.8 metres and 2.4 metres"))

    return out


def page_column_texts(page):
    """Split page into column texts using word x-positions and the widest
    whitespace gutter in the central band of the page."""
    words = page.extract_words()
    if not words:
        return [""]
    w = page.width
    lo, hi = w * 0.35, w * 0.65
    # candidate vertical edges inside the central band
    edges = sorted({round(wd["x0"], 1) for wd in words if lo < wd["x0"] < hi} |
                   {round(wd["x1"], 1) for wd in words if lo < wd["x1"] < hi})
    gutter = None
    best = 0.0
    for a, b in itertools.pairwise(edges):
        if b - a > best:
            best = b - a
            gutter = (a + b) / 2
    if gutter is None:
        return [" ".join(wd["text"] for wd in words)]
    cols = {"left": [], "right": []}
    for wd in words:
        cols["left" if wd["x1"] <= gutter else "right"].append(wd)
    texts = []
    for key in ("left", "right"):
        lines = {}
        for wd in cols[key]:
            lines.setdefault(round(wd["top"], 0), []).append(wd)
        out = []
        for top in sorted(lines):
            out.append(" ".join(wd["text"] for wd in
                                sorted(lines[top], key=lambda x: x["x0"])))
        texts.append("\n".join(out))
    return texts


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Extract OP 2.2 (May 2024) provisions to rule candidates.")
    ap.add_argument("--source-pdf", required=True)
    ap.add_argument("--source-version-id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if pdfplumber is None:
        print("ERROR: pdfplumber not installed", file=sys.stderr)
        return 1
    pdf_path = Path(args.source_pdf)
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        return 1

    clause_ids = {k: None for k in CLAUSES}
    if not args.dry_run:
        db_url = os.environ.get("DATABASE_URL", "").replace(
            "postgresql+asyncpg://", "postgresql://").replace(
            "postgresql+psycopg://", "postgresql://")
        if not db_url:
            print("ERROR: DATABASE_URL not set (required unless --dry-run)",
                  file=sys.stderr)
            return 1
        clause_ids = ensure_clauses(db_url, args.source_version_id)

    # multi-column layout: reconstruct each column from word positions so
    # sentence contiguity is preserved for evidence checks
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for p in pdf.pages:
            parts.extend(page_column_texts(p))
    full_text = " ".join(parts)
    norm = re.sub(r"\s+", " ", full_text)

    print(f"Extracting OP 2.2 provisions from {pdf_path.name}...")
    candidates, warnings = [], []
    for cand, evidence in build_candidates(args.source_version_id, clause_ids):
        if re.sub(r"\s+", " ", evidence) not in norm:
            warnings.append(f"{cand['rule_key']}: evidence text not found in PDF")
            continue
        candidates.append(cand)

    candidates.sort(key=lambda c: c["rule_key"])
    report = {
        "source_version_id": args.source_version_id,
        "source_pdf": str(pdf_path),
        "instrument_section": "Section 4 — Policy measures",
        "tables_requested": list(CLAUSES.keys()),
        "candidates_extracted": len(candidates),
        "warnings": warnings,
        "candidates": candidates,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    eval_yes = sum(1 for c in candidates if c["evaluable"] == "yes")
    print(f"\nExtracted {len(candidates)} rule candidates "
          f"({eval_yes} evaluable) -> {out_path}")
    for w in warnings:
        print(f"  WARNING: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
