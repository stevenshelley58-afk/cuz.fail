"""Extract R-Codes Vol 1 (April 2026) tables into rule candidate JSON rows.

Schema-aware successor to extract_rcodes_tables.py for the 2026-04-amended
edition. Uses pdfplumber line-ruled table geometry (merged-cell spans are
read from actual cell rectangles, never inferred).

Differences from extract_rcodes_tables.py:
- Table-specific parsers for the real April 2026 layouts:
  Table B, Table 2a, Table 2b, Table 3 (Part B) and Table C (Part C).
- --instrument-section flag (original hardcoded "Part B").
- Creates one real `clauses` row per table (live schema) so that
  bulk_approve_rules.py satisfies the rules.clause_id FK. Skipped with
  --dry-run (candidates then carry clause_id=None and must be re-run
  non-dry before approval).
- No rule_candidates inserts (live rule_candidates schema is incompatible
  with this pipeline; bulk_approve_rules.py works from the report JSON).

Determinism: same PDF + same table list -> identical candidates
(sorted by rule_key).
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

PART_B_CODES = [
    "R2",
    "R2.5",
    "R5",
    "R10",
    "R12.5",
    "R15",
    "R17.5",
    "R20",
    "R25",
    "R30",
    "R35",
    "R40",
]
PART_C_CODES = ["R30", "R35", "R40", "R50", "R60", "R80", "R100-SL2"]

LINES = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def parse_num(cell: str) -> float | None:
    cleaned = cell.strip().replace(",", "")
    cleaned = re.sub(r"\s*(m|m²|m2|%|metres?|hours?)\.?$", "", cleaned, flags=re.IGNORECASE)
    try:
        return float(cleaned)
    except ValueError:
        return None


def find_page(pdf: Any, pattern: str) -> int | None:
    rx = re.compile(pattern, re.IGNORECASE)
    for i, page in enumerate(pdf.pages):
        if rx.search(page.extract_text() or ""):
            return i
    return None


def make_candidate(
    rule_key,
    canonical,
    operator,
    value,
    unit,
    quote,
    section,
    table,
    r_codes,
    clause_id,
    source_version_id,
    dwelling_type=None,
    condition=None,
    evaluable="yes",
    raw_text=None,
):
    vj = {"value": value} if value is not None else {"raw_text": raw_text}
    return {
        "rule_key": rule_key,
        "canonical_rule_key": canonical,
        "rule_type": "standard",
        "pathway": "deemed_to_comply",
        "dwelling_type": dwelling_type,
        "applicable_r_codes": r_codes,
        "applicable_zones": None,
        "council_scope": None,
        "operator": operator,
        "value_json": vj,
        "unit": unit,
        "condition_json": condition or ({"needs_human_review": True} if evaluable != "yes" else {}),
        "quote": quote,
        "instrument_section": section,
        "table_reference": table,
        "effective_from": None,
        "effective_to": None,
        "source_version_id": source_version_id,
        "clause_id": clause_id,
        "extractor_model": "deterministic_table_parser:v2-april2026",
        "check_type": "min_value" if operator == "gte" else "max_value",
        "evaluable": evaluable,
    }


# ---------------------------------------------------------------- Table B
def parse_table_b(pdf, section, sv_id, clause_id):
    out = []
    page_idx = find_page(pdf, r"Table B\s+Primary controls")
    if page_idx is None:
        return out, "Table B header page not found"
    tables = pdf.pages[page_idx].extract_tables(LINES)
    grid = None
    for t in tables:
        if t and len(t[0]) == 7 and t[0][0] and "R-Code" in t[0][0]:
            grid = t
            break
    if grid is None:
        return out, "Table B grid not found"

    measures = [
        (
            2,
            "open_space_min_total_pct",
            "open_space_min_total_pct",
            "gte",
            "%",
            "Min total open space (% of site)",
        ),
        (
            3,
            "outdoor_living_area_min_m2",
            "outdoor_living_area_min_m2",
            "gte",
            "m2",
            "Min outdoor living area (m2)",
        ),
        (
            4,
            "setback_primary_street_min_m",
            "setback_primary_street_min_m",
            "gte",
            "m",
            "Min primary street setback (m)",
        ),
        (
            5,
            "setback_secondary_street_min_m",
            "setback_secondary_street_min_m",
            "gte",
            "m",
            "Min secondary street setback (m)",
        ),
        (
            6,
            "setback_other_rear_min_m",
            "setback_other_rear_min_m",
            "gte",
            "m",
            "Min other/rear setback (m)",
        ),
    ]
    dwelling_map = {
        "single house or\ngrouped dwelling": "single_house|grouped_dwelling",
        "multiple dwelling": "multiple_dwelling",
        "single house": "single_house",
    }
    current_rc = None
    for row in grid[2:]:
        if not row:
            continue
        rc_cell = (row[0] or "").strip() if row[0] else ""
        if re.fullmatch(r"R\d+(\.\d+)?", rc_cell):
            current_rc = rc_cell
        # merged R-code cell: multiple-dwelling row inherits code above
        rc = current_rc
        if rc is None:
            continue
        dw_raw = (row[1] or "").strip().lower()
        dw = dwelling_map.get(dw_raw)
        suffix = "_multiple" if dw == "multiple_dwelling" else ""
        for col, key, canon, op, unit, label in measures:
            cell = (row[col] or "").strip()
            if cell in ("", "-", "*", "*/6", "N/A"):
                continue
            val = parse_num(cell)
            if val is None:
                continue
            quote = f"Table B: {rc} {dw_raw.replace(chr(10), ' ')} — {label} — {cell}"
            out.append(
                make_candidate(
                    f"{key}_{slugify(rc)}{suffix}",
                    canon,
                    op,
                    val,
                    unit,
                    quote,
                    section,
                    "Table B",
                    [rc],
                    clause_id,
                    sv_id,
                    dwelling_type=dw,
                )
            )
    return out, None


# ----------------------------------------------------------- Tables 2a/2b
def parse_table_2x(pdf, section, sv_id, clause_ids, requested_tables=None):
    out = []
    warnings = []
    page_idx = find_page(pdf, r"Table 2a\s+Boundary setbacks")
    if page_idx is None:
        return out, ["Table 2a page not found"]
    tables = [t for t in pdf.pages[page_idx].extract_tables(LINES) if t and len(t[0]) == 15]
    tables = tables[:2]
    names = ["Table 2a", "Table 2b"]
    bases = ["boundary_setback_no_major_openings_min_m", "boundary_setback_major_openings_min_m"]
    if len(tables) < 2:
        warnings.append(f"expected 2 setback matrices, found {len(tables)}")
    for t, name, base in zip(tables, names, bases):
        if requested_tables is not None and name not in requested_tables:
            continue
        lengths = [(c or "").strip() for c in t[1][1:]]
        for row in t[3:]:
            h_label = (row[0] or "").strip()
            if not h_label:
                continue
            h_val = parse_num(re.sub(r"\s*or less\*?$", "", h_label))
            for ci, cell in enumerate(row[1:]):
                cell = (cell or "").strip()
                val = parse_num(cell)
                if val is None or ci >= len(lengths):
                    continue
                l_label = lengths[ci]
                l_key = (
                    "25plus"
                    if "over" in l_label.lower()
                    else slugify(re.sub(r"\s*or less$", "", l_label))
                )
                l_val = parse_num(re.sub(r"(?i)(over\s*|\s*or less)", "", l_label))
                cond = {
                    "wall_height_m": h_val,
                    "wall_height_label": h_label,
                    "wall_length_m": l_val,
                    "wall_length_label": l_label,
                }
                quote = f"{name}: wall height {h_label}, wall length {l_label} — {cell} m"
                out.append(
                    make_candidate(
                        f"{base}_h{slugify(str(h_val))}_l{l_key}",
                        base,
                        "gte",
                        val,
                        "m",
                        quote,
                        section,
                        name,
                        PART_B_CODES,
                        clause_ids.get(name),
                        sv_id,
                        condition=cond,
                    )
                )
    return out, warnings


# -------------------------------------------------------------- Table 3
def parse_table_3(pdf, section, sv_id, clause_id):
    out = []
    page_idx = find_page(pdf, r"Table 3\s+Maximum building heights")
    if page_idx is None:
        return out, "Table 3 page not found"
    tables = [
        t
        for t in pdf.pages[page_idx].extract_tables(LINES)
        if t and len(t[0]) == 4 and t[0][0] and "Building category" in t[0][0]
    ]
    if not tables:
        return out, "Table 3 grid not found"
    grid = tables[0]
    measures = [
        (1, "building_height_wall_max_m", "Max wall height (m)"),
        (
            2,
            "building_height_total_gable_skillion_max_m",
            "Max total height, gable/skillion/concealed roof (m)",
        ),
        (
            3,
            "building_height_total_hipped_pitched_max_m",
            "Max total height, hipped/pitched roof (m)",
        ),
    ]
    for row in grid[2:]:
        cat = (row[0] or "").strip()
        m = re.fullmatch(r"Category ([ABC])", cat)
        if not m:
            continue
        cat_slug = f"cat_{m.group(1).lower()}"
        for col, key, label in measures:
            val = parse_num((row[col] or "").strip())
            if val is None:
                continue
            quote = f"Table 3: {cat} — {label} — {row[col].strip()}"
            out.append(
                make_candidate(
                    f"{key}_{cat_slug}",
                    key,
                    "lte",
                    val,
                    "m",
                    quote,
                    section,
                    "Table 3",
                    PART_B_CODES,
                    clause_id,
                    sv_id,
                )
            )
    return out, None


# -------------------------------------------------------------- Table C
def col_spans(header_cells):
    """x-ranges of the 7 R-code data columns (cols 2..8)."""
    spans = []
    for ci in range(2, 9):
        c = header_cells[ci]
        spans.append((c[0], c[2]))
    return spans


def covered_codes(cell_bbox, spans):
    """R-code columns whose x-range overlaps the cell bbox."""
    codes = []
    for rc, (x0, x1) in zip(PART_C_CODES, spans):
        if cell_bbox[0] < x1 - 1 and cell_bbox[2] > x0 + 1:
            codes.append(rc)
    return codes


def parse_table_c(pdf, section, sv_id, clause_id):
    out = []
    warnings = []
    page_idx = None
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if re.search(r"Table C\s+Primary controls", text) and "R100-SL2" in text:
            page_idx = i
            break
    if page_idx is None:
        return out, ["Table C page not found"]
    page = pdf.pages[page_idx]
    found = page.find_tables(LINES)
    tbl = None
    for t in found:
        if len(t.rows) >= 10 and len(t.rows[0].cells) == 9:
            tbl = t
            break
    if tbl is None:
        return out, ["Table C grid not found"]

    rows = tbl.rows
    spans = col_spans(rows[0].cells)

    # Measure per row index: (key, operator, unit, label)
    # Row geometry verified against 2026-04 edition page 111.
    # Rows 3-6 (building height block) are handled separately below:
    # R30-R80 cells are vertically merged with 4 stacked values in row 3.
    simple_rows = {
        1: ("soft_landscaping_min_pct", "gte", "%", "Soft landscaping (% of site area)"),
        2: ("site_cover_max_pct", "lte", "%", "Maximum site cover (% of site area)"),
        7: ("setback_primary_street_min_m", "gte", "m", "Primary street setback (m)"),
        8: ("setback_secondary_street_min_m", "gte", "m", "Secondary street setback (m)"),
        9: ("setback_communal_street_min_m", "gte", "m", "Communal street setback (m)"),
        10: (
            "setback_laneway_primary_street_min_m",
            "gte",
            "m",
            "Adjoining laneway/ROW as primary street setback (m)",
        ),
        11: ("setback_laneway_min_m", "gte", "m", "Adjoining laneway/ROW setback (m)"),
    }
    storey_rows = {
        12: ("setback_lot_boundary_storey1_min_m", "Up to 3.5m (1st storey)"),
        13: ("setback_lot_boundary_storey2_min_m", "3.6m-7m (2nd storey)"),
        14: ("setback_lot_boundary_storey3_min_m", "7.1m-10m (3rd storey)"),
        15: ("setback_lot_boundary_storey4_min_m", "10.1m and above (4th storey)"),
    }
    boundary_wall_row = 16

    # Part C keys are namespaced to avoid uq_rules_version_key collisions
    # with same-named Part B measures on the same source version.
    kp = "partc_"

    def row_cells(ri):
        return [(ci, c) for ci, c in enumerate(rows[ri].cells) if c is not None and ci >= 2]

    # --- building height block (rows 3-6) ---
    height_block = [
        ("storeys_max", "lte", "count", "Maximum storeys"),
        (
            "building_height_wall_roof_skillion_max_m",
            "lte",
            "m",
            "Max wall/roof height – skillion (m)",
        ),
        (
            "building_height_wall_pitched_hipped_max_m",
            "lte",
            "m",
            "Max wall height – pitched/hipped (m)",
        ),
        (
            "building_height_roof_pitched_hipped_max_m",
            "lte",
            "m",
            "Max roof height – pitched/hipped (m)",
        ),
    ]
    # R30-R80: vertically merged cells in row 3 with 4 stacked values
    for ci, bbox in row_cells(3):
        codes = covered_codes(bbox, spans)
        if not codes or codes[0] == "R100-SL2":
            continue  # R100-SL2 has per-row cells, handled below
        lines = [
            line.strip()
            for line in (page.crop(bbox).extract_text() or "").split("\n")
            if line.strip()
        ]
        if len(lines) != 4:
            warnings.append(
                f"Table C height block: expected 4 stacked values for {codes}, got {lines!r}"
            )
            continue
        rc = codes[0]
        for (key, op, unit, label), raw in zip(height_block, lines):
            val = parse_num(raw)
            if val is None:
                warnings.append(f"Table C {key} {rc}: unparsable {raw!r}")
                continue
            out.append(
                make_candidate(
                    f"{key}_{slugify(rc)}",
                    key,
                    op,
                    val,
                    unit,
                    f"Table C: {label} — {rc} — {raw}",
                    section,
                    "Table C",
                    [rc],
                    clause_id,
                    sv_id,
                )
            )
    # R100-SL2: one cell per row, rows 3-6, column 8
    for ri, (key, op, unit, label) in zip((3, 4, 5, 6), height_block):
        bbox = rows[ri].cells[8]
        if bbox is None:
            warnings.append(f"Table C {key} R100-SL2: missing cell")
            continue
        raw = (page.crop(bbox).extract_text() or "").strip()
        val = parse_num(raw)
        if val is None:
            warnings.append(f"Table C {key} R100-SL2: unparsable {raw!r}")
            continue
        out.append(
            make_candidate(
                f"{key}_r100_sl2",
                key,
                op,
                val,
                unit,
                f"Table C: {label} — R100-SL2 — {raw}",
                section,
                "Table C",
                ["R100-SL2"],
                clause_id,
                sv_id,
            )
        )

    for ri, (key, op, unit, label) in simple_rows.items():
        for ci, bbox in row_cells(ri):
            codes = covered_codes(bbox, spans)
            # cell text
            text = page.crop(bbox).extract_text() or ""
            text = text.strip().replace("\n", " ")
            if not codes:
                continue
            val = parse_num(text)
            if val is None:
                out.append(
                    make_candidate(
                        f"{key}_{slugify(codes[0])}",
                        key,
                        op,
                        None,
                        unit,
                        f"Table C: {label} — {text}",
                        section,
                        "Table C",
                        codes,
                        clause_id,
                        sv_id,
                        evaluable="needs_human_review",
                        raw_text=text,
                    )
                )
                continue
            for rc in codes:
                out.append(
                    make_candidate(
                        f"{key}_{slugify(rc)}",
                        key,
                        op,
                        val,
                        unit,
                        f"Table C: {label} — {rc} — {text}",
                        section,
                        "Table C",
                        [rc],
                        clause_id,
                        sv_id,
                    )
                )

    for ri, (key, range_label) in storey_rows.items():
        for ci, bbox in row_cells(ri):
            codes = covered_codes(bbox, spans)
            text = (page.crop(bbox).extract_text() or "").strip().replace("\n", " ")
            val = parse_num(text)
            if val is None:
                continue
            for rc in codes:
                out.append(
                    make_candidate(
                        f"{key}_{slugify(rc)}",
                        key,
                        "gte",
                        val,
                        "m",
                        f"Table C: lot boundary setback {range_label} — {rc} — {text}",
                        section,
                        "Table C",
                        [rc],
                        clause_id,
                        sv_id,
                        condition={"storey_height_range": range_label},
                    )
                )

    # Maximum boundary wall height: cells carry "7m\n(2 storey)"
    for ci, bbox in row_cells(boundary_wall_row):
        codes = covered_codes(bbox, spans)
        raw_lines = [
            line.strip()
            for line in (page.crop(bbox).extract_text() or "").split("\n")
            if line.strip()
        ]
        if not raw_lines:
            continue
        val = parse_num(raw_lines[0])
        m = re.search(r"\(([^)]+)\)", " ".join(raw_lines[1:]))
        label = m.group(1) if m else f"group{ci}"
        if val is None:
            warnings.append(f"Table C boundary wall {codes}: unparsable {raw_lines!r}")
            continue
        for rc in codes:
            out.append(
                make_candidate(
                    f"boundary_wall_height_max_m_{slugify(rc)}",
                    "boundary_wall_height_max_m",
                    "lte",
                    val,
                    "m",
                    f"Table C: max boundary wall height ({label}) — {rc} — {raw_lines[0]}",
                    section,
                    "Table C",
                    [rc],
                    clause_id,
                    sv_id,
                    condition={"boundary_wall_label": label},
                )
            )

    # Namespace all Part C rule keys (see kp note above)
    for c in out:
        c["rule_key"] = kp + c["rule_key"]
    return out, warnings


PARSERS = {
    "Table B": (parse_table_b, "table_b", "Table B – Primary controls (Part B)"),
    "Table 2a": (None, "table_2a", "Table 2a – Boundary setbacks, walls with no major openings"),
    "Table 2b": (None, "table_2b", "Table 2b – Boundary setbacks, walls with major openings"),
    "Table 3": (parse_table_3, "table_3", "Table 3 – Maximum building heights"),
    "Table C": (parse_table_c, "table_c", "Table C – Primary controls (Part C)"),
}


def ensure_clauses(db_url, sv_id, table_names):
    """Create one clause row per table; return {table_name: clause_id}."""
    import psycopg

    ids = {}
    with psycopg.connect(db_url) as conn:
        cur = conn.cursor()
        for name in table_names:
            _, clause_key, title = PARSERS[name]
            cur.execute(
                "SELECT id FROM clauses WHERE source_version_id = %s AND clause_key = %s",
                (sv_id, clause_key),
            )
            row = cur.fetchone()
            if row:
                ids[name] = str(row[0])
                continue
            cid = str(uuid4())
            cur.execute(
                """INSERT INTO clauses
                   (id, source_version_id, clause_key, clause_type, title,
                    text, parser_name, parser_version, created_at, updated_at)
                   VALUES (%s, %s, %s, 'table', %s, %s,
                           'deterministic_table_parser', 'v2-april2026',
                           now(), now())""",
                (cid, sv_id, clause_key, title, f"{title} — R-Codes Volume 1 (April 2026)"),
            )
            ids[name] = cid
            print(f"  Created clause {clause_key}: {cid}")
        conn.commit()
    return ids


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Extract R-Codes April 2026 tables to rule candidates."
    )
    ap.add_argument("--source-pdf", required=True)
    ap.add_argument("--source-version-id", required=True)
    ap.add_argument("--tables", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--instrument-section", default="Part B")
    ap.add_argument("--dry-run", action="store_true", help="Report only; no clause rows created")
    args = ap.parse_args()

    if pdfplumber is None:
        print("ERROR: pdfplumber not installed", file=sys.stderr)
        return 1

    pdf_path = Path(args.source_pdf)
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        return 1

    table_names = [t.strip() for t in args.tables.split(",") if t.strip()]
    unknown = [t for t in table_names if t not in PARSERS]
    if unknown:
        print(f"ERROR: unsupported tables for this parser: {unknown}", file=sys.stderr)
        return 1

    clause_ids = {t: None for t in table_names}
    if not args.dry_run:
        db_url = (
            os.environ.get("DATABASE_URL", "")
            .replace("postgresql+asyncpg://", "postgresql://")
            .replace("postgresql+psycopg://", "postgresql://")
        )
        if not db_url:
            print("ERROR: DATABASE_URL not set (required unless --dry-run)", file=sys.stderr)
            return 1
        clause_ids = ensure_clauses(db_url, args.source_version_id, table_names)

    print(
        f"Extracting {len(table_names)} tables from {pdf_path.name} [{args.instrument_section}]..."
    )
    all_candidates: list[dict[str, Any]] = []
    warnings: list[str] = []

    with pdfplumber.open(pdf_path) as pdf:
        if any(t in ("Table 2a", "Table 2b") for t in table_names):
            cands, w = parse_table_2x(
                pdf,
                args.instrument_section,
                args.source_version_id,
                clause_ids,
                requested_tables=set(table_names),
            )
            all_candidates.extend(cands)
            warnings.extend(w)
        for name in table_names:
            if name in ("Table 2a", "Table 2b"):
                continue
            parser, _, _ = PARSERS[name]
            print(f"  Processing: {name}")
            cands, w = parser(
                pdf, args.instrument_section, args.source_version_id, clause_ids.get(name)
            )
            all_candidates.extend(cands)
            if w:
                warnings.extend(w if isinstance(w, list) else [w])

    # de-duplicate by rule_key (defensive)
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
        "instrument_section": args.instrument_section,
        "tables_requested": table_names,
        "candidates_extracted": len(deduped),
        "warnings": warnings,
        "candidates": deduped,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    eval_yes = sum(1 for c in deduped if c["evaluable"] == "yes")
    print(f"\nExtracted {len(deduped)} rule candidates ({eval_yes} evaluable) -> {out_path}")
    for w in warnings:
        print(f"  WARNING: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
