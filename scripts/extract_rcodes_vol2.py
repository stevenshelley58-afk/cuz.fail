"""Extract R-Codes Vol 2 (Apartments, Version 4 April 2024) tables into rule
candidate JSON rows, in the same report schema as extract_rcodes_v3.py.

Cell values were verified against the rendered PDF pages (Apr 2024 edition).
Quotes are extracted live from the PDF at runtime; candidates whose live
cell text does not contain the expected value are dropped with a warning
(never invent numbers).

Creates one real `clauses` row per table/section (live schema) so that
bulk_approve_rules.py satisfies the rules.clause_id FK.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    import pdfplumber
except ImportError:
    pdfplumber = None  # type: ignore[assignment]

LINES = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}

ALL_CODES = ["R80", "R100", "R160", "R-AC4", "R-AC3", "R-AC2", "R-AC1", "R-AC0"]
DWELLING = "multiple_dwelling"

CLAUSES = {
    "Table 2.1": ("table_2_1", "Table 2.1 – Primary controls table (Part 2)"),
    "Table 2.2": ("table_2_2", "Table 2.2 – Indicative building height (Part 2)"),
    "Table 2.7": ("table_2_7", "Table 2.7 – Building separation (Part 2)"),
    "Table 3.3a": ("table_3_3a", "Table 3.3a – Minimum deep soil area and tree provision (Part 3)"),
    "Table 3.3b": ("table_3_3b", "Table 3.3b – Tree sizes (Part 3)"),
    "Table 3.4": ("table_3_4", "Table 3.4 – Provision of communal open space (Part 3)"),
    "Table 3.5": ("table_3_5", "Table 3.5 – Required privacy setback to adjoining sites (Part 3)"),
    "Table 3.9": ("table_3_9", "Table 3.9 – Parking ratio (Part 3)"),
    "Table 4.3a": ("table_4_3a", "Table 4.3a – Minimum internal floor areas for dwelling types (Part 4)"),
    "Table 4.3b": ("table_4_3b", "Table 4.3b – Minimum internal floor areas and dimensions for habitable rooms (Part 4)"),
    "Table 4.4": ("table_4_4", "Table 4.4 – Private open space requirements (Part 4)"),
    "Table 4.6": ("table_4_6", "Table 4.6 – Storage requirements (Part 4)"),
    "A 3.9": ("sec_3_9_text", "Section 3.9 – Car and bicycle parking (text provisions)"),
    "A 4.3": ("sec_4_3_text", "Section 4.3 – Size and layout of dwellings (text provisions)"),
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def make_candidate(rule_key, canonical, operator, value, unit, quote,
                   section, table, r_codes, clause_id, source_version_id,
                   condition=None, evaluable="yes", raw_text=None,
                   check_type=None):
    vj = {"value": value} if value is not None else {"raw_text": raw_text}
    return {
        "rule_key": rule_key,
        "canonical_rule_key": canonical,
        "rule_type": "standard",
        "pathway": "deemed_to_comply",
        "dwelling_type": DWELLING,
        "applicable_r_codes": r_codes,
        "applicable_zones": None,
        "council_scope": None,
        "operator": operator,
        "value_json": vj,
        "unit": unit,
        "condition_json": condition or (
            {"needs_human_review": True} if evaluable != "yes" else {}),
        "quote": quote,
        "instrument_section": section,
        "table_reference": table,
        "effective_from": None,
        "effective_to": None,
        "source_version_id": source_version_id,
        "clause_id": clause_id,
        "extractor_model": "deterministic_table_parser:v3-vol2-apr2024",
        "check_type": check_type or ("min_value" if operator == "gte" else "max_value"),
        "evaluable": evaluable,
    }


def first_num(text: str) -> float | None:
    m = re.match(r"\s*(\d+(?:\.\d+)?)", text)
    return float(m.group(1)) if m else None


def ensure_clauses(db_url, sv_id):
    import psycopg
    ids = {}
    with psycopg.connect(db_url) as conn:
        cur = conn.cursor()
        for table, (clause_key, title) in CLAUSES.items():
            cur.execute(
                "SELECT id FROM clauses WHERE source_version_id = %s "
                "AND clause_key = %s", (sv_id, clause_key))
            row = cur.fetchone()
            if row:
                ids[table] = str(row[0])
                continue
            cid = str(uuid4())
            cur.execute(
                """INSERT INTO clauses
                   (id, source_version_id, clause_key, clause_type, title,
                    text, parser_name, parser_version, created_at, updated_at)
                   VALUES (%s, %s, %s, 'table', %s, %s,
                           'deterministic_table_parser', 'v3-vol2-apr2024',
                           now(), now())""",
                (cid, sv_id, clause_key, title,
                 f"{title} — R-Codes Volume 2 Apartments (Version 4, April 2024)"))
            ids[table] = cid
            print(f"  Created clause {clause_key}: {cid}")
        conn.commit()
    return ids


def get_grid(pdf, page_idx, min_rows, min_cols):
    for t in pdf.pages[page_idx].extract_tables(LINES):
        if t and len(t) >= min_rows and len(t[0]) >= min_cols:
            return t
    return None


def find_row(grid, label_rx):
    rx = re.compile(label_rx, re.IGNORECASE)
    for row in grid:
        if row and row[0] and rx.search(row[0].replace("\n", " ")):
            return row
        # label may be in second column (e.g. Table 2.7)
        if row and len(row) > 1 and row[1] and rx.search(row[1].replace("\n", " ")):
            return row
    return None


def cell(row, idx):
    if row is None or idx >= len(row) or row[idx] is None:
        return ""
    return row[idx].replace("\n", " ").strip()


# ---------------------------------------------------------------- Table 2.1
T21_SPANS = [("R80", 140, 191), ("R100", 191, 241), ("R160", 241, 291),
             ("R-AC4", 291, 354), ("R-AC3", 354, 416), ("R-AC2", 416, 465),
             ("R-AC1", 465, 514), ("R-AC0", 514, 563)]

T21_MEASURES = [
    # (find_tables row index, key, canonical, op, unit, expected per code, condition extras)
    (3, "building_height_storeys_max", "building_height_storeys_max", "lte",
     "storeys",
     {"R80": 4, "R100": 4, "R160": 5, "R-AC4": 3, "R-AC3": 6, "R-AC2": 7, "R-AC1": 9},
     {}),
    (4, "boundary_wall_height_storeys_max", "boundary_wall_height_storeys_max",
     "lte", "storeys",
     {"R80": 2, "R100": 2, "R160": 2, "R-AC4": 2, "R-AC3": 3, "R-AC2": 4, "R-AC1": 4},
     {"note_3": "Boundary wall only permitted on one boundary, and shall not exceed 2/3 length."}),
    (5, "setback_primary_secondary_street_min_m",
     "setback_primary_secondary_street_min_m", "gte", "m",
     {"R80": 2, "R100": 2, "R160": 2, "R-AC4": 2, "R-AC3": 2, "R-AC2": 2, "R-AC1": 2},
     {}),
    (6, "setback_side_min_m", "setback_side_min_m", "gte", "m",
     {"R80": 3, "R100": 3, "R160": 3}, {}),
    (7, "setback_rear_min_m", "setback_rear_min_m", "gte", "m",
     {"R80": 3, "R100": 6, "R160": 6, "R-AC4": 6}, {}),
    (8, "setback_side_avg_min_m", "setback_side_avg_min_m", "gte", "m",
     {"R80": 3.5, "R100": 3.5, "R160": 4.0},
     {"building_length_m_gt": 16}),
    (9, "plot_ratio_max", "plot_ratio_max", "lte", "ratio",
     {"R80": 1.0, "R100": 1.3, "R160": 2.0, "R-AC4": 1.2, "R-AC3": 2.0,
      "R-AC2": 2.5, "R-AC1": 3.0}, {}),
]


def covered_codes(bbox):
    codes = []
    for rc, x0, x1 in T21_SPANS:
        if bbox[0] < x1 - 1 and bbox[2] > x0 + 1:
            codes.append(rc)
    return codes


def parse_table_21(pdf, sv_id, clause_id):
    out, warnings = [], []
    page = pdf.pages[24]
    found = [t for t in page.find_tables(LINES) if len(t.rows) >= 10]
    if not found:
        return out, ["Table 2.1 grid not found"]
    rows = found[0].rows
    for ri, key, canon, op, unit, expected, extra_cond in T21_MEASURES:
        label = (page.crop(rows[ri].cells[0]).extract_text() or "").replace("\n", " ").strip()
        for ci, bbox in enumerate(rows[ri].cells):
            if bbox is None or ci == 0:
                continue
            codes = [c for c in covered_codes(bbox) if c in expected]
            if not codes:
                continue
            text = (page.crop(bbox).extract_text() or "").replace("\n", " ").strip()
            val = first_num(text)
            exp = expected[codes[0]]
            if val is None or any(expected[c] != val for c in codes) or val != exp:
                warnings.append(f"Table 2.1 {key} {codes}: cell {text!r} != expected {exp}")
                continue
            cond = dict(extra_cond)
            if "or Nil" in text:
                cond["alternative"] = ("Nil setback applicable if commercial use "
                                       "at ground floor (Note 5)")
            quote = f"Table 2.1: {label} — {text}"
            for rc in codes:
                out.append(make_candidate(
                    f"vol2_{key}_{slugify(rc)}", canon, op, val, unit, quote,
                    "Part 2", "Table 2.1", [rc], clause_id, sv_id,
                    condition=cond or None))
    return out, warnings


# ---------------------------------------------------------------- Table 2.2
T22_EXPECTED = {2: 9, 3: 12, 4: 15, 5: 18, 6: 21, 7: 24, 8: 27, 9: 30, 10: 33}


def parse_table_22(pdf, sv_id, clause_id):
    out, warnings = [], []
    text = pdf.pages[25].extract_text() or ""
    for storeys, metres in T22_EXPECTED.items():
        # two-column page: pair may appear at end of an interleaved line
        if not re.search(rf"(?m)(?:^|\s){storeys}\s+{metres}\s*$", text):
            warnings.append(f"Table 2.2: pair {storeys}/{metres} not found on page 26")
            continue
        quote = (f"Table 2.2 Indicative building height: {storeys} storeys — "
                 f"{metres} m (indicative overall building height in metres)")
        out.append(make_candidate(
            f"vol2_building_height_indicative_max_m_{storeys}storeys",
            "building_height_indicative_max_m", "lte", float(metres), "m", quote,
            "Part 2", "Table 2.2", ALL_CODES, clause_id, sv_id,
            condition={"storeys": storeys}))
    return out, warnings


# ---------------------------------------------------------------- Table 2.7
T27_ROWS = [
    ("Habitable rooms/balconies", "within_site", "habitable_balconies",
     [12.0, 18.0, 24.0]),
    ("Habitable and non-habitable", "within_site", "habitable_and_non_habitable",
     [7.5, 12.0, 18.0]),
    ("^Non-habitable rooms", "within_site", "non_habitable",
     [4.5, 6.0, 9.0]),
    ("Habitable rooms/balconies and boundary", "to_adjoining_property_boundary",
     "habitable_balconies_boundary", [None, 9.0, 12.0]),
]
T27_BANDS = [("le_4_storeys", "≤ 4 storeys (up to 15m)"),
             ("5_8_storeys", "5-8 storeys (up to 28m)"),
             ("ge_9_storeys", "≥ 9 storeys (over 28m)")]


def parse_table_27(pdf, sv_id, clause_id):
    out, warnings = [], []
    grid = get_grid(pdf, 36, 5, 5)
    if grid is None:
        return out, ["Table 2.7 grid not found"]
    for label, loc, otype, values in T27_ROWS:
        row = find_row(grid, label)
        if row is None:
            warnings.append(f"Table 2.7: row {label!r} not found")
            continue
        for ci, (band, band_label), exp in zip((2, 3, 4), T27_BANDS, values):
            if exp is None:
                continue
            text = cell(row, ci)
            val = first_num(text)
            if val != exp:
                warnings.append(f"Table 2.7 {otype} {band}: cell {text!r} != {exp}")
                continue
            quote = (f"Table 2.7 Building separation: {label} — "
                     f"{band_label} — {text}")
            out.append(make_candidate(
                f"vol2_building_separation_min_m_{loc}_{otype}_{band}",
                "building_separation_min_m", "gte", val, "m", quote,
                "Part 2", "Table 2.7", ALL_CODES, clause_id, sv_id,
                condition={"location": loc, "opening_type": otype,
                           "building_height_band": band_label}))
    return out, warnings


# ---------------------------------------------------------------- Table 3.3a
def parse_table_33a(pdf, sv_id, clause_id):
    out, warnings = [], []
    page = pdf.pages[46]
    grids = [t for t in page.extract_tables(LINES) if t and len(t) >= 4]
    grid = next((t for t in grids if t[0] and "Site Area" in (t[0][0] or "")), None)
    if grid is None:
        return out, ["Table 3.3a grid not found"]
    bands = [(1, "Less than 700m2", "lt_700m2"),
             (2, "700 – 1,000m2", "700_1000m2"),
             (3, "> 1,000m2", "gt_1000m2")]
    for ri, band_label, band_key in bands:
        row = grid[ri]
        dsa_text = cell(row, 1)
        if not dsa_text:  # merged cell: take from row 1
            dsa_text = cell(grid[1], 1)
        if "10%" not in dsa_text:
            warnings.append(f"Table 3.3a {band_key}: deep soil cell {dsa_text!r} missing 10%")
            continue
        quote = (f"Table 3.3a: Site area {band_label} — Minimum deep soil area — "
                 f"{dsa_text}")
        out.append(make_candidate(
            f"vol2_deep_soil_area_min_pct_{band_key}", "deep_soil_area_min_pct",
            "gte", 10.0, "%", quote, "Part 3", "Table 3.3a", ALL_CODES,
            clause_id, sv_id,
            condition={"site_area_band": band_label,
                       "alternative": "7% if existing tree(s) retained on site"}))
        tree_text = cell(row, 2)
        if tree_text:
            out.append(make_candidate(
                f"vol2_tree_provision_{band_key}", "tree_provision_requirement",
                "gte", None, "text",
                f"Table 3.3a: Site area {band_label} — Minimum requirement for trees — {tree_text}",
                "Part 3", "Table 3.3a", ALL_CODES, clause_id, sv_id,
                evaluable="needs_human_review", raw_text=tree_text))
    return out, warnings


# ---------------------------------------------------------------- Table 3.3b
def parse_table_33b(pdf, sv_id, clause_id):
    out, warnings = [], []
    page = pdf.pages[46]
    grids = [t for t in page.extract_tables(LINES) if t and len(t) >= 4]
    grid = next((t for t in grids if t[0] and "Tree size" in (t[0][0] or "")), None)
    if grid is None:
        return out, ["Table 3.3b grid not found"]
    sizes = [(1, "Small", 9.0, 2.0), (2, "Medium", 36.0, 3.0), (3, "Large", 64.0, 6.0)]
    for ri, size, dsa, width in sizes:
        row = grid[ri]
        dsa_text, width_text = cell(row, 3), cell(row, 4)
        if first_num(dsa_text) != dsa:
            warnings.append(f"Table 3.3b {size} DSA: {dsa_text!r} != {dsa}")
        else:
            out.append(make_candidate(
                f"vol2_tree_dsa_min_m2_{slugify(size)}", "tree_dsa_min_m2",
                "gte", dsa, "m2",
                f"Table 3.3b: {size} tree — Required DSA per tree — {dsa_text}",
                "Part 3", "Table 3.3b", ALL_CODES, clause_id, sv_id,
                condition={"tree_size": size}))
        if first_num(width_text) != width:
            warnings.append(f"Table 3.3b {size} width: {width_text!r} != {width}")
        else:
            out.append(make_candidate(
                f"vol2_tree_dsa_width_min_m_{slugify(size)}", "tree_dsa_width_min_m",
                "gte", width, "m",
                f"Table 3.3b: {size} tree — Recommended minimum DSA width — {width_text}",
                "Part 3", "Table 3.3b", ALL_CODES, clause_id, sv_id,
                condition={"tree_size": size, "recommendation": True}))
    return out, warnings


# ---------------------------------------------------------------- Table 3.4
def parse_table_34(pdf, sv_id, clause_id):
    out, warnings = [], []
    grid = get_grid(pdf, 50, 3, 4)
    if grid is None:
        return out, ["Table 3.4 grid not found"]
    row = find_row(grid, "More than 10 dwellings")
    if row is None:
        return out, ["Table 3.4 '>10 dwellings' row not found"]
    cond = {"development_size": "more_than_10_dwellings"}
    specs = [(1, "communal_open_space_total_min_m2_per_dwelling", 6.0, "m2_per_dwelling", 300.0),
             (2, "communal_open_space_accessible_min_m2_per_dwelling", 2.0, "m2_per_dwelling", 100.0),
             (3, "communal_open_space_dimension_min_m", 4.0, "m", None)]
    for ci, key, exp, unit, cap in specs:
        text = cell(row, ci)
        pat = r"(\d+(?:\.\d+)?)\s*m2" if unit != "m" else r"(\d+(?:\.\d+)?)\s*m\b"
        m = re.search(pat, text)
        if not m or float(m.group(1)) != exp:
            warnings.append(f"Table 3.4 {key}: cell {text!r} != {exp}")
            continue
        c2 = dict(cond)
        if cap is not None:
            c2["cap_m2"] = cap
        out.append(make_candidate(
            f"vol2_{key}", key, "gte", exp, unit,
            f"Table 3.4: More than 10 dwellings — {text}",
            "Part 3", "Table 3.4", ALL_CODES, clause_id, sv_id, condition=c2))
    return out, warnings


# ---------------------------------------------------------------- Table 3.5
T35_ROWS = [
    ("Major opening to bedroom", "bedroom_study_walkways", [4.5, 3.0]),
    ("Major openings to habitable rooms other than bedrooms",
     "habitable_other_than_bedrooms", [6.0, 4.5]),
    ("Unenclosed private outdoor", "unenclosed_private_outdoor_spaces", [7.5, 6.0]),
]
T35_COLS = [("adjoining_R50_or_lower", "Adjoining sites coded R50 or lower"),
            ("adjoining_higher_than_R50", "Adjoining sites coded higher than R50")]


def parse_table_35(pdf, sv_id, clause_id):
    out, warnings = [], []
    grid = get_grid(pdf, 54, 4, 3)
    if grid is None:
        return out, ["Table 3.5 grid not found"]
    for label, otype, values in T35_ROWS:
        row = find_row(grid, label)
        if row is None:
            warnings.append(f"Table 3.5: row {label!r} not found")
            continue
        for ci, (band, band_label), exp in zip((1, 2), T35_COLS, values):
            text = cell(row, ci)
            if first_num(text) != exp:
                warnings.append(f"Table 3.5 {otype} {band}: cell {text!r} != {exp}")
                continue
            out.append(make_candidate(
                f"vol2_visual_privacy_setback_min_m_{otype}_{band}",
                "visual_privacy_setback_min_m", "gte", exp, "m",
                f"Table 3.5: {label} — {band_label} — {text}",
                "Part 3", "Table 3.5", ALL_CODES, clause_id, sv_id,
                condition={"opening_type": otype,
                           "adjoining_site_code": band_label,
                           "storeys": "first_4_storeys"}))
    return out, warnings


# ---------------------------------------------------------------- Table 3.9
def parse_table_39(pdf, sv_id, clause_id):
    out, warnings = [], []
    page = pdf.pages[64]
    text = page.extract_text() or ""

    def line_quote(rx):
        m = re.search(rx, text, re.IGNORECASE)
        return m.group(0).strip() if m else None

    specs = [
        ("car_parking_min_bays_per_dwelling_1bed_loc_a", 0.75, "bays_per_dwelling",
         r"1 bedroom dwellings\s+0\.75 bay per dwelling",
         {"dwelling_size": "1_bedroom", "location": "A"}),
        ("car_parking_min_bays_per_dwelling_1bed_loc_b", 1.0, "bays_per_dwelling",
         r"1 bedroom dwellings\s+0\.75 bay per dwelling\s+1 bay per dwelling",
         {"dwelling_size": "1_bedroom", "location": "B"}),
        ("car_parking_min_bays_per_dwelling_2plus_loc_a", 1.0, "bays_per_dwelling",
         r"2\+ bedroom dwellings\s+1 bay per dwelling",
         {"dwelling_size": "2plus_bedroom", "location": "A"}),
        ("car_parking_min_bays_per_dwelling_2plus_loc_b", 1.25, "bays_per_dwelling",
         r"2\+ bedroom dwellings\s+1 bay per dwelling\s+1\.25 bays per dwelling",
         {"dwelling_size": "2plus_bedroom", "location": "B"}),
        ("visitor_car_parking_min_bays_per_dwelling_up_to_12", 0.25, "bays_per_dwelling",
         r"1 bay per four dwellings up to 12 dwellings",
         {"visitor": True, "up_to_12_dwellings": True}),
        ("visitor_car_parking_min_bays_per_dwelling_from_13th", 0.125, "bays_per_dwelling",
         r"1 bay per eight dwellings for the 13th dwelling and above",
         {"visitor": True, "from_13th_dwelling": True}),
        ("bicycle_parking_min_spaces_per_dwelling_resident", 0.5, "spaces_per_dwelling",
         r"Resident\s+0\.5 space per dwelling", {"bicycle": True, "resident": True}),
        ("bicycle_parking_min_spaces_per_dwelling_visitor", 0.1, "spaces_per_dwelling",
         r"Visitor\s+1 space per 10 dwellings", {"bicycle": True, "visitor": True}),
        ("motorcycle_parking_min_spaces_per_car_bay", 0.1, "spaces_per_car_bay",
         r"1 motorcycle/scooter space for every 10 car bays",
         {"motorcycle_scooter": True, "development_size": "exceeding_20_dwellings"}),
    ]
    for key, val, unit, rx, cond in specs:
        q = line_quote(rx)
        if q is None:
            warnings.append(f"Table 3.9 {key}: pattern not found on page 65")
            continue
        out.append(make_candidate(
            f"vol2_{key}", re.sub(r"_(loc_[ab]|up_to_12|from_13th|resident|visitor)$", "", key),
            "gte", val, unit, f"Table 3.9 Parking ratio: {q}",
            "Part 3", "Table 3.9", ALL_CODES, clause_id, sv_id, condition=cond))
    return out, warnings


# --------------------------------------------------------------- Table 4.3a
def parse_table_43a(pdf, sv_id, clause_id):
    out, warnings = [], []
    page = pdf.pages[78]
    grids = [t for t in page.extract_tables(LINES) if t and len(t) >= 4]
    grid = next((t for t in grids if t[0] and "Dwelling type" in (t[0][0] or "")
                 and len(t[0]) == 2), None)
    if grid is None:
        return out, ["Table 4.3a grid not found"]
    specs = [("Studio", "studio", 36.0, {}),
             ("1 bed", "1bed", 47.0, {}),
             ("2 bed", "2bed_1bath", 67.0,
              {"note_1": "An additional 3m2 shall be provided for designs that include a second or separate toilet, and 5m2 for designs that include a second bathroom."}),
             ("3 bed", "3bed_1bath", 90.0,
              {"note_1": "An additional 3m2 shall be provided for designs that include a second or separate toilet, and 5m2 for designs that include a second bathroom."})]
    for label, dtype, exp, cond in specs:
        row = find_row(grid, rf"^{re.escape(label)}")
        if row is None:
            warnings.append(f"Table 4.3a: row {label!r} not found")
            continue
        text = cell(row, 1)
        if first_num(text) != exp:
            warnings.append(f"Table 4.3a {dtype}: cell {text!r} != {exp}")
            continue
        out.append(make_candidate(
            f"vol2_dwelling_floor_area_min_m2_{dtype}", "dwelling_floor_area_min_m2",
            "gte", exp, "m2",
            f"Table 4.3a: {cell(row, 0)} — Minimum internal floor area — {text}",
            "Part 4", "Table 4.3a", ALL_CODES, clause_id, sv_id,
            condition={"dwelling_size": dtype, **cond}))
    return out, warnings


# --------------------------------------------------------------- Table 4.3b
def parse_table_43b(pdf, sv_id, clause_id):
    out, warnings = [], []
    page = pdf.pages[78]
    grids = [t for t in page.extract_tables(LINES) if t and len(t) >= 4]
    grid = next((t for t in grids if t[0] and "Habitable room type" in (t[0][0] or "")),
                None)
    if grid is None:
        return out, ["Table 4.3b grid not found"]
    specs = [
        ("Master bedroom", "master_bedroom", 10.0, 3.0),
        ("Other bedrooms", "other_bedrooms", 9.0, 3.0),
        ("Living room – studio", "living_room_studio_1bed", None, 3.6),
        ("Living room – other", "living_room_other", None, 4.0),
    ]
    for label, rtype, area, dim in specs:
        row = find_row(grid, re.escape(label))
        if row is None:
            warnings.append(f"Table 4.3b: row {label!r} not found")
            continue
        area_text, dim_text = cell(row, 1), cell(row, 2)
        cond = {"room_type": rtype, "note_1": "Excluding robes"}
        if area is not None:
            if first_num(area_text) != area:
                warnings.append(f"Table 4.3b {rtype} area: {area_text!r} != {area}")
            else:
                out.append(make_candidate(
                    f"vol2_room_floor_area_min_m2_{rtype}", "room_floor_area_min_m2",
                    "gte", area, "m2",
                    f"Table 4.3b: {cell(row, 0)} — Minimum internal floor area — {area_text}",
                    "Part 4", "Table 4.3b", ALL_CODES, clause_id, sv_id,
                    condition=cond))
        # dimension cell carries footnote superscript (e.g. '13m' = note 1 + 3m)
        m = re.search(r"(\d+(?:\.\d+)?)\s*m", dim_text)
        dim_val = float(m.group(1)) if m else None
        if dim_val is not None and dim_val > 10 and dim_text.startswith("1"):
            dim_val = float(dim_text[1:].replace("m", "").strip())
        if dim_val != dim:
            warnings.append(f"Table 4.3b {rtype} dim: {dim_text!r} != {dim}")
        else:
            out.append(make_candidate(
                f"vol2_room_dimension_min_m_{rtype}", "room_dimension_min_m",
                "gte", dim, "m",
                f"Table 4.3b: {cell(row, 0)} — Minimum internal dimension — {dim_text}",
                "Part 4", "Table 4.3b", ALL_CODES, clause_id, sv_id,
                condition=cond))
    return out, warnings


# ---------------------------------------------------------------- Table 4.4
def parse_table_44(pdf, sv_id, clause_id):
    out, warnings = [], []
    grid = get_grid(pdf, 82, 4, 3)
    if grid is None:
        return out, ["Table 4.4 grid not found"]
    specs = [("Studio apartment", "studio_1bed", 8.0, 2.0),
             ("2 bedroom", "2bed", 10.0, 2.4),
             ("3 bedroom", "3bed", 12.0, 2.4),
             ("Ground floor", "ground_floor", 15.0, 3.0)]
    for label, dtype, area, dim in specs:
        row = find_row(grid, re.escape(label))
        if row is None:
            warnings.append(f"Table 4.4: row {label!r} not found")
            continue
        area_text, dim_text = cell(row, 1), cell(row, 2)
        if first_num(area_text) != area:
            warnings.append(f"Table 4.4 {dtype} area: {area_text!r} != {area}")
            continue
        if first_num(dim_text) != dim:
            warnings.append(f"Table 4.4 {dtype} dim: {dim_text!r} != {dim}")
            continue
        cond = {"dwelling_size": dtype}
        out.append(make_candidate(
            f"vol2_private_open_space_area_min_m2_{dtype}",
            "private_open_space_area_min_m2", "gte", area, "m2",
            f"Table 4.4: {cell(row, 0)} — Minimum Area — {area_text}",
            "Part 4", "Table 4.4", ALL_CODES, clause_id, sv_id, condition=cond))
        out.append(make_candidate(
            f"vol2_private_open_space_dimension_min_m_{dtype}",
            "private_open_space_dimension_min_m", "gte", dim, "m",
            f"Table 4.4: {cell(row, 0)} — Minimum Dimension — {dim_text}",
            "Part 4", "Table 4.4", ALL_CODES, clause_id, sv_id, condition=cond))
    return out, warnings


# ---------------------------------------------------------------- Table 4.6
def parse_table_46(pdf, sv_id, clause_id):
    out, warnings = [], []
    grid = get_grid(pdf, 90, 4, 4)
    if grid is None:
        return out, ["Table 4.6 grid not found"]
    specs = [("Studio dwelling", "studio", 3.0), ("1 bedroom dwelling", "1bed", 3.0),
             ("2 bedroom dwellings", "2bed", 4.0), ("3 bedroom dwellings", "3bed", 5.0)]
    for label, dtype, area in specs:
        row = find_row(grid, re.escape(label))
        if row is None:
            warnings.append(f"Table 4.6: row {label!r} not found")
            continue
        text = cell(row, 1)
        if first_num(text) != area:
            warnings.append(f"Table 4.6 {dtype}: cell {text!r} != {area}")
            continue
        out.append(make_candidate(
            f"vol2_storage_area_min_m2_{dtype}", "storage_area_min_m2",
            "gte", area, "m2",
            f"Table 4.6: {cell(row, 0)} — Storage area — {text}",
            "Part 4", "Table 4.6", ALL_CODES, clause_id, sv_id,
            condition={"dwelling_size": dtype}))
    # merged dimension/height cells (1.5m / 2.1m apply to all rows)
    row = find_row(grid, "Studio dwelling")
    dim_text, height_text = cell(row, 2), cell(row, 3)
    for key, text, exp in (("storage_dimension_min_m", dim_text, 1.5),
                           ("storage_height_min_m", height_text, 2.1)):
        if first_num(text) != exp:
            warnings.append(f"Table 4.6 {key}: cell {text!r} != {exp}")
            continue
        out.append(make_candidate(
            f"vol2_{key}", key, "gte", exp, "m",
            f"Table 4.6 Storage requirements: {key.replace('_', ' ')} — {text}",
            "Part 4", "Table 4.6", ALL_CODES, clause_id, sv_id))
    return out, warnings


# ----------------------------------------------------- text provisions (A-x)
def parse_text_rules(pdf, sv_id, clause_ids):
    out, warnings = [], []
    t64 = pdf.pages[64].extract_text() or ""
    t78 = pdf.pages[78].extract_text() or ""
    specs = [
        ("vol2_ceiling_height_habitable_min_m", "ceiling_height_habitable_min_m",
         "gte", 2.7, "m", t78,
         r"A 4\.3\.3[^—]*—\s*Habitable rooms\s*–\s*2\.7m",
         "A 4.3.3: minimum ceiling heights — Habitable rooms – 2.7m",
         "A 4.3", "Part 4", {"room_type": "habitable"}),
        ("vol2_ceiling_height_non_habitable_min_m",
         "ceiling_height_non_habitable_min_m", "gte", 2.4, "m", t78,
         r"Non-habitable rooms\s*–\s*2\.4m",
         "A 4.3.3: minimum ceiling heights — Non-habitable rooms – 2.4m",
         "A 4.3", "Part 4", {"room_type": "non_habitable"}),
        ("vol2_car_parking_max_multiple_of_minimum",
         "car_parking_max_multiple_of_minimum", "lte", 2.0, "x_table_minimum", t64,
         r"A 3\.9\.3 Maximum parking provision does not exceed double",
         "A 3.9.3: Maximum parking provision does not exceed double the minimum number of bays specified in Table 3.9.",
         "A 3.9", "Part 3", {}),
        ("vol2_uncovered_parking_trees_min_per_bay",
         "uncovered_parking_trees_min_per_bay", "gte", 0.25, "trees_per_bay", t64,
         r"A 3\.9\.9 Uncovered at-grade parking is planted with trees at",
         "A 3.9.9: Uncovered at-grade parking is planted with trees at a minimum rate of one tree per four bays.",
         "A 3.9", "Part 3", {}),
        ("vol2_basement_parking_protrusion_max_m",
         "basement_parking_protrusion_max_m", "lte", 1.0, "m", t64,
         r"A 3\.9\.10\s*Basement parking does not protrude more than 1m",
         "A 3.9.10: Basement parking does not protrude more than 1m above ground, and where it protrudes above ground is designed or screened to prevent negative visual impact on the streetscape.",
         "A 3.9", "Part 3", {}),
    ]
    for key, canon, op, val, unit, ptext, rx, quote, clause_key, section, cond in specs:
        if not re.search(rx, ptext, re.DOTALL):
            warnings.append(f"{key}: operative text not found for {quote[:60]}")
            continue
        out.append(make_candidate(
            key, canon, op, val, unit, quote, section, clause_key,
            ALL_CODES, clause_ids[clause_key], sv_id, condition=cond or None))
    return out, warnings


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Extract R-Codes Vol 2 (Apr 2024) tables to rule candidates.")
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

    clause_ids = {t: None for t in CLAUSES}
    if not args.dry_run:
        db_url = os.environ.get("DATABASE_URL", "").replace(
            "postgresql+asyncpg://", "postgresql://").replace(
            "postgresql+psycopg://", "postgresql://")
        if not db_url:
            print("ERROR: DATABASE_URL not set (required unless --dry-run)",
                  file=sys.stderr)
            return 1
        clause_ids = ensure_clauses(db_url, args.source_version_id)

    print(f"Extracting Vol 2 tables from {pdf_path.name}...")
    all_candidates: list[dict[str, Any]] = []
    warnings: list[str] = []

    with pdfplumber.open(pdf_path) as pdf:
        for name, fn in (
            ("Table 2.1", lambda: parse_table_21(pdf, args.source_version_id, clause_ids["Table 2.1"])),
            ("Table 2.2", lambda: parse_table_22(pdf, args.source_version_id, clause_ids["Table 2.2"])),
            ("Table 2.7", lambda: parse_table_27(pdf, args.source_version_id, clause_ids["Table 2.7"])),
            ("Table 3.3a", lambda: parse_table_33a(pdf, args.source_version_id, clause_ids["Table 3.3a"])),
            ("Table 3.3b", lambda: parse_table_33b(pdf, args.source_version_id, clause_ids["Table 3.3b"])),
            ("Table 3.4", lambda: parse_table_34(pdf, args.source_version_id, clause_ids["Table 3.4"])),
            ("Table 3.5", lambda: parse_table_35(pdf, args.source_version_id, clause_ids["Table 3.5"])),
            ("Table 3.9", lambda: parse_table_39(pdf, args.source_version_id, clause_ids["Table 3.9"])),
            ("Table 4.3a", lambda: parse_table_43a(pdf, args.source_version_id, clause_ids["Table 4.3a"])),
            ("Table 4.3b", lambda: parse_table_43b(pdf, args.source_version_id, clause_ids["Table 4.3b"])),
            ("Table 4.4", lambda: parse_table_44(pdf, args.source_version_id, clause_ids["Table 4.4"])),
            ("Table 4.6", lambda: parse_table_46(pdf, args.source_version_id, clause_ids["Table 4.6"])),
            ("Text provisions", lambda: parse_text_rules(pdf, args.source_version_id, clause_ids)),
        ):
            print(f"  Processing: {name}")
            cands, w = fn()
            all_candidates.extend(cands)
            warnings.extend(w)

    seen = set()
    deduped = []
    for c in all_candidates:
        if c["rule_key"] in seen:
            warnings.append(f"duplicate rule_key dropped: {c['rule_key']}")
            continue
        seen.add(c["rule_key"])
        deduped.append(c)
    deduped.sort(key=lambda c: c["rule_key"])

    report = {
        "source_version_id": args.source_version_id,
        "source_pdf": str(pdf_path),
        "instrument_section": "Parts 2-4",
        "tables_requested": list(CLAUSES.keys()),
        "candidates_extracted": len(deduped),
        "warnings": warnings,
        "candidates": deduped,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    eval_yes = sum(1 for c in deduped if c["evaluable"] == "yes")
    print(f"\nExtracted {len(deduped)} rule candidates "
          f"({eval_yes} evaluable) -> {out_path}")
    for w in warnings:
        print(f"  WARNING: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
