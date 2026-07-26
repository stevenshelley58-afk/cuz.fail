"""Extract R-Codes PDF tables into rule candidate JSON rows.

Parses structured tables from the R-Codes PDF using pdfplumber, producing
rule candidates conforming to the §2.2 schema.

Usage:
    python scripts/extract_rcodes_tables.py \
        --source-pdf data/raw-sources/rcodes_vol1_april2026.pdf \
        --source-version-id <uuid> \
        --tables "Table B,Table 1.1a,Table 2.1a" \
        --out reports/rcodes_table_extraction.json \
        --dry-run

Determinism: Same PDF + same table list → identical output (sorted by rule_key).
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

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

try:
    import pdfplumber
except ImportError:
    pdfplumber = None  # type: ignore[assignment]

# R-Codes density codes in standard column order.
R_CODES = ["R2", "R5", "R10", "R15", "R17.5", "R20", "R25", "R30", "R35", "R40", "R50", "R60", "R80"]

# Row header → operator inference.
MIN_KEYWORDS = ("minimum", "min", "at least", "not less than")
MAX_KEYWORDS = ("maximum", "max", "not exceed", "not more than", "does not exceed")

# Row header → unit inference.
UNIT_PATTERNS: list[tuple[str, str]] = [
    (r"\bmetre|(\bm\b)", "m"),
    (r"square metre|m²|m2|area", "m2"),
    (r"per cent|percent|%", "%"),
    (r"count|number of|trees", "count"),
    (r"hours?", "hours"),
]


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def infer_operator(row_header: str) -> str:
    lower = row_header.lower()
    for kw in MIN_KEYWORDS:
        if kw in lower:
            return "gte"
    for kw in MAX_KEYWORDS:
        if kw in lower:
            return "lte"
    return "gte"  # default to minimum


def infer_unit(row_header: str) -> str:
    lower = row_header.lower()
    for pattern, unit in UNIT_PATTERNS:
        if re.search(pattern, lower):
            return unit
    return "m"  # default


def parse_numeric(cell_text: str) -> float | None:
    """Extract numeric value from a table cell."""
    cleaned = cell_text.strip().replace(",", "")
    # Remove footnote markers like (a), (b), etc.
    cleaned = re.sub(r"\s*\([a-z]\)", "", cleaned)
    # Remove units suffix
    cleaned = re.sub(r"\s*(m|m²|m2|%|metres?|hours?)\.?$", "", cleaned, flags=re.IGNORECASE)
    try:
        return float(cleaned)
    except ValueError:
        return None


def find_table_pages(pdf: Any, table_name: str) -> list[int]:
    """Find pages containing a table header."""
    pages = []
    pattern = re.compile(re.escape(table_name), re.IGNORECASE)
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if pattern.search(text):
            pages.append(i)
    return pages


def extract_table_candidates(
    pdf: Any,
    table_name: str,
    source_version_id: str,
    clause_id: str,
) -> list[dict[str, Any]]:
    """Extract rule candidates from a named table in the PDF."""
    candidates: list[dict[str, Any]] = []
    pages = find_table_pages(pdf, table_name)

    if not pages:
        print(f"  WARNING: Table '{table_name}' not found in PDF", file=sys.stderr)
        return candidates

    for page_idx in pages:
        page = pdf.pages[page_idx]
        tables = page.extract_tables()

        for table in tables:
            if not table or len(table) < 2:
                continue

            # First row should be headers (density codes)
            headers = [str(h).strip() if h else "" for h in table[0]]

            # Find R-code columns
            rcode_cols: list[tuple[int, str]] = []
            for col_idx, header in enumerate(headers):
                for rc in R_CODES:
                    if rc.lower() in header.lower() or header.strip() == rc:
                        rcode_cols.append((col_idx, rc))
                        break

            if not rcode_cols:
                continue

            # Process data rows
            for row in table[1:]:
                if not row or not row[0]:
                    continue

                row_header = str(row[0]).strip()
                if not row_header or row_header.startswith("Table"):
                    continue

                operator = infer_operator(row_header)
                unit = infer_unit(row_header)
                base_key = slugify(row_header)

                for col_idx, r_code in rcode_cols:
                    if col_idx >= len(row):
                        continue

                    cell = row[col_idx]
                    if not cell or str(cell).strip() in ("", "-", "—", "N/A", "n/a"):
                        continue

                    cell_text = str(cell).strip()
                    value = parse_numeric(cell_text)

                    if value is None:
                        # Non-numeric cell — flag for human review
                        candidates.append({
                            "rule_key": f"{base_key}_{slugify(r_code)}",
                            "canonical_rule_key": base_key,
                            "rule_type": "standard",
                            "pathway": "deemed_to_comply",
                            "dwelling_type": None,
                            "applicable_r_codes": [r_code],
                            "applicable_zones": None,
                            "council_scope": None,
                            "operator": operator,
                            "value_json": {"raw_text": cell_text},
                            "unit": unit,
                            "condition_json": {"needs_human_review": True},
                            "quote": f"{table_name}: {row_header} — {r_code} — {cell_text}",
                            "instrument_section": "Part B",
                            "table_reference": table_name,
                            "effective_from": None,
                            "effective_to": None,
                            "source_version_id": source_version_id,
                            "clause_id": clause_id,
                            "extractor_model": "deterministic_table_parser:v1",
                            "check_type": "min_value" if operator == "gte" else "max_value",
                            "evaluable": "needs_human_review",
                        })
                        continue

                    rule_key = f"{base_key}_{slugify(r_code)}"
                    candidates.append({
                        "rule_key": rule_key,
                        "canonical_rule_key": base_key,
                        "rule_type": "standard",
                        "pathway": "deemed_to_comply",
                        "dwelling_type": None,
                        "applicable_r_codes": [r_code],
                        "applicable_zones": None,
                        "council_scope": None,
                        "operator": operator,
                        "value_json": {"value": value},
                        "unit": unit,
                        "condition_json": {},
                        "quote": f"{table_name}: {row_header} — {r_code} — {cell_text}",
                        "instrument_section": "Part B",
                        "table_reference": table_name,
                        "effective_from": None,
                        "effective_to": None,
                        "source_version_id": source_version_id,
                        "clause_id": clause_id,
                        "extractor_model": "deterministic_table_parser:v1",
                        "check_type": "min_value" if operator == "gte" else "max_value",
                        "evaluable": "yes",
                    })

    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract R-Codes tables to rule candidates.")
    parser.add_argument("--source-pdf", required=True, help="Path to R-Codes PDF")
    parser.add_argument("--source-version-id", required=True, help="Source version UUID")
    parser.add_argument("--tables", required=True, help="Comma-separated table names")
    parser.add_argument("--out", required=True, help="Output JSON report path")
    parser.add_argument("--dry-run", action="store_true", help="Write report only, no DB insert")
    args = parser.parse_args()

    if pdfplumber is None:
        print("ERROR: pdfplumber not installed. Run: pip install pdfplumber", file=sys.stderr)
        return 1

    pdf_path = Path(args.source_pdf)
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        return 1

    table_names = [t.strip() for t in args.tables.split(",") if t.strip()]
    clause_id = str(uuid4())  # Placeholder clause for table extraction

    print(f"Extracting {len(table_names)} tables from {pdf_path.name}...")

    all_candidates: list[dict[str, Any]] = []
    warnings: list[str] = []

    with pdfplumber.open(pdf_path) as pdf:
        for table_name in table_names:
            print(f"  Processing: {table_name}")
            candidates = extract_table_candidates(
                pdf, table_name, args.source_version_id, clause_id
            )
            if not candidates:
                warnings.append(f"Table '{table_name}' not found or empty")
            all_candidates.extend(candidates)

    # Sort for determinism
    all_candidates.sort(key=lambda c: (c["rule_key"], c.get("applicable_r_codes", [""])[0]))

    # Build report
    report = {
        "source_version_id": args.source_version_id,
        "source_pdf": str(pdf_path),
        "tables_requested": table_names,
        "candidates_extracted": len(all_candidates),
        "warnings": warnings,
        "candidates": all_candidates,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\nExtracted {len(all_candidates)} rule candidates → {out_path}")
    if warnings:
        print(f"Warnings: {len(warnings)}")
        for w in warnings:
            print(f"  - {w}")

    # Insert into DB unless dry-run
    if not args.dry_run and all_candidates:
        db_url = os.environ.get("DATABASE_URL", "").replace(
            "postgresql+asyncpg://", "postgresql://"
        ).replace("postgresql+psycopg://", "postgresql://")

        if not db_url:
            print("WARNING: DATABASE_URL not set; skipping DB insert", file=sys.stderr)
        else:
            import psycopg
            with psycopg.connect(db_url) as conn:
                cur = conn.cursor()
                inserted = 0
                for c in all_candidates:
                    if c.get("evaluable") == "needs_human_review":
                        continue
                    try:
                        cur.execute(
                            """INSERT INTO rule_candidates
                               (id, source_version_id, clause_id, rule_key, canonical_rule_key,
                                rule_type, pathway, operator, value_json, unit, condition_json,
                                quote, extractor_model, check_type, evaluable,
                                applicable_r_codes, dwelling_type, instrument_section,
                                table_reference, lifecycle_status, created_at, updated_at)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                       %s, %s, %s, %s, 'pending_review', now(), now())
                               ON CONFLICT DO NOTHING""",
                            (
                                str(uuid4()), c["source_version_id"], c["clause_id"],
                                c["rule_key"], c["canonical_rule_key"], c["rule_type"],
                                c["pathway"], c["operator"], json.dumps(c["value_json"]),
                                c["unit"], json.dumps(c["condition_json"]), c["quote"],
                                c["extractor_model"], c["check_type"], c["evaluable"],
                                json.dumps(c["applicable_r_codes"]), c.get("dwelling_type"),
                                c.get("instrument_section"), c.get("table_reference"),
                            ),
                        )
                        inserted += 1
                    except Exception as e:
                        print(f"  DB insert error for {c['rule_key']}: {e}", file=sys.stderr)
                conn.commit()
                print(f"Inserted {inserted} rule candidates into DB")

    return 0


if __name__ == "__main__":
    sys.exit(main())
