"""Shared helpers for Phase 6 LPP rule-candidate builders.

Creates clause rows (like extract_rcodes_v3.ensure_clauses) and writes
extraction reports matching reports/phase1_rcodes_partb_extraction.json schema.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import psycopg


def db_url() -> str:
    return (
        os.environ["DATABASE_URL"]
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
    )


def ensure_clause(sv_id: str, clause_key: str, title: str, text: str) -> str:
    """Create (or fetch) one clause row for a policy section; return clause_id."""
    with psycopg.connect(db_url()) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM clauses WHERE source_version_id = %s AND clause_key = %s",
            (sv_id, clause_key),
        )
        row = cur.fetchone()
        if row:
            return str(row[0])
        cid = str(uuid4())
        cur.execute(
            """INSERT INTO clauses
               (id, source_version_id, clause_key, clause_type, title,
                text, parser_name, parser_version, created_at, updated_at)
               VALUES (%s, %s, %s, 'policy_section', %s, %s,
                       'manual_lpp_extraction', 'phase6-v1', now(), now())""",
            (cid, sv_id, clause_key, title, text),
        )
        conn.commit()
        print(f"  Created clause {clause_key}: {cid}")
        return cid


def cand(
    rule_key: str,
    operator: str,
    value,
    unit: str | None,
    quote: str,
    clause_id: str,
    sv_id: str,
    council_scope: str,
    *,
    canonical_rule_key: str | None = None,
    rule_type: str = "standard",
    pathway: str = "deemed_to_comply",
    r_codes: list[str] | None = None,
    zones: list[str] | None = None,
    condition: dict | None = None,
    instrument_section: str | None = None,
    table_reference: str | None = None,
    dwelling_type: str | None = None,
    check_type: str | None = None,
    evaluable: str = "yes",
    effective_from: str | None = None,
    effective_to: str | None = None,
    extra_value: dict | None = None,
) -> dict:
    if check_type is None:
        check_type = {"gte": "min_value", "lte": "max_value", "eq": "exact_value",
                      "gt": "min_value", "lt": "max_value"}.get(operator, "exact_value")
    vj = {"value": value}
    if extra_value:
        vj.update(extra_value)
    return {
        "rule_key": rule_key,
        "canonical_rule_key": canonical_rule_key or rule_key,
        "rule_type": rule_type,
        "pathway": pathway,
        "dwelling_type": dwelling_type,
        "applicable_r_codes": r_codes if r_codes is not None else [],
        "applicable_zones": zones,
        "council_scope": council_scope,
        "operator": operator,
        "value_json": vj,
        "unit": unit,
        "condition_json": condition or {},
        "quote": quote,
        "instrument_section": instrument_section,
        "table_reference": table_reference,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "source_version_id": sv_id,
        "clause_id": clause_id,
        "extractor_model": "manual_lpp_extraction:phase6-v1",
        "check_type": check_type,
        "evaluable": evaluable,
    }


def write_report(out: str, sv_id: str, source_doc: str, section: str,
                 tables: list[str], candidates: list[dict],
                 warnings: list[str] | None = None) -> None:
    report = {
        "source_version_id": sv_id,
        "source_pdf": source_doc,
        "instrument_section": section,
        "tables_requested": tables,
        "candidates_extracted": len(candidates),
        "warnings": warnings or [],
        "candidates": candidates,
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Wrote {len(candidates)} candidates -> {out}")
