#!/usr/bin/env python3
"""WP6 — Tier-1 check × density-code rule matrix (CORPUS_COMPLETENESS_PLAN Phase 4 'Speed').

Builds reports/rule_matrix.csv: one row per Tier-1 check key (imported from
src/draftcheck/checks/registry.py — never hardcoded) × one column per density code
R5–R80 (derived from the VALID_R_CODES set in scripts/wp6_extract.py, filtered to
the R5..R80 band the plan names; RAC/R100+ variants are out of matrix scope).

Cell resolution is deterministic — no LLM at query time:
  "<rule_id> | <operator> <value> <unit>"
      An approved `rules` row resolves by direct key lookup: its base rule key
      (rules.value_json->>'base_rule_key', falling back to the rule_key prefix —
      WP6 promotes rules as "<base>.<code-suffix>", see wp6_extract.promote_rule)
      maps to the check key, and rules.applicable_r_codes (JSONB list added by
      migration 0009; NULL = global, same semantics as checks/engine.py
      _get_applicable_rules) covers the density code.
  "n/a (<cited reason>)"
      An approved row explicitly marks non-applicability: not_applicable=true in
      value_json / condition_json / metadata_json (with na_reason or the quote as
      the citation), or value_json.value of "n/a".
  "MISSING"
      Anything else. Every MISSING cell is a defect, listed in
      reports/rule_matrix_gaps.json with the nearest rule_candidates rows
      (validators_passed first, then pending_review) that could fill it — the
      work queue for draining pending_review candidates.

Read-only. Runs INSIDE the api container like wp6_extract.py:

    docker exec draftcheck-wa-v3-api-1 python /app/scripts/wp6_rule_matrix.py \
        --matrix /app/reports/rule_matrix.csv \
        --gaps /app/reports/rule_matrix_gaps.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import UTC, datetime
from typing import Any

sys.path.insert(0, "/app/src")
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))

from draftcheck.checks.registry import TIER1_CHECKS  # noqa: E402
from wp6_extract import VALID_R_CODES  # noqa: E402

DEFAULT_ORG_ID = "1d31c315-5087-47df-a8d4-ebfd08efad5d"  # DraftCheck WA

# Registry check keys → extraction-vocabulary base rule keys (wp6_extract RULE_KEYS).
# The registry's rule_key_pattern namespace ("setback.front") is not what WP6 writes;
# WP6-approved rules carry value_json.base_rule_key from the closed extraction
# vocabulary, so the matrix maps each check onto the base keys that satisfy it.
CHECK_TO_BASE_RULE_KEYS: dict[str, tuple[str, ...]] = {
    "setback_front": ("primary_street_setback",),
    "setback_rear": ("rear_setback",),
    "setback_side_primary": ("side_setback",),
    "setback_side_secondary": ("side_setback", "secondary_street_setback"),
    "site_cover": ("site_cover",),
    "open_space": ("open_space",),
    "garage_width": ("garage_width",),
    "garage_dominance": ("garage_dominance",),
    "boundary_wall_length": ("boundary_wall_length",),
}

# Candidate ordering for gap work queue: validators_passed is the cheapest fill.
_STATUS_PRIORITY = {"validators_passed": 0, "pending_review": 1, "auto_promoted": 2}

_NA_VALUE_TOKENS = {"n/a", "na", "not applicable", "not_applicable"}


# ---------------------------------------------------------------------------
# Pure resolution logic (unit-tested on plain dicts in tests/test_rule_matrix.py)
# ---------------------------------------------------------------------------


def matrix_density_codes() -> list[str]:
    """R5–R80 columns derived from wp6_extract.VALID_R_CODES (plan scope)."""
    out: list[str] = []
    for code in VALID_R_CODES:
        m = re.fullmatch(r"R(\d+(?:\.\d+)?)", code)
        if m and 5.0 <= float(m.group(1)) <= 80.0:
            out.append(code)
    return sorted(out, key=lambda c: float(c[1:]))


def normalize_code(code: Any) -> str:
    return str(code).upper().replace(" ", "")


def base_rule_key(rule_row: dict) -> str:
    """Base extraction-vocabulary key of a rules row.

    WP6 promotion (wp6_extract.promote_rule) writes rule_key as
    "<base>.<code-suffix>" and records the base in value_json.base_rule_key.
    """
    vj = rule_row.get("value_json")
    if isinstance(vj, dict) and vj.get("base_rule_key"):
        return str(vj["base_rule_key"])
    return str(rule_row.get("rule_key") or "").split(".", 1)[0]


def rule_r_codes(rule_row: dict) -> list[str]:
    """Normalized rules.applicable_r_codes; [] means global (NULL in DB)."""
    codes = rule_row.get("applicable_r_codes")
    if isinstance(codes, str):
        try:
            codes = json.loads(codes)
        except json.JSONDecodeError:
            return []
    if not isinstance(codes, list):
        return []
    return [normalize_code(c) for c in codes]


def na_reason(rule_row: dict) -> str | None:
    """Cited reason when the row explicitly marks non-applicability, else None."""
    for field_name in ("value_json", "condition_json", "metadata_json"):
        blob = rule_row.get(field_name)
        if isinstance(blob, dict) and blob.get("not_applicable"):
            reason = blob.get("na_reason") or blob.get("reason") or rule_row.get("quote")
            return str(reason) if reason else "non-applicability recorded without reason"
    vj = rule_row.get("value_json")
    if isinstance(vj, dict) and str(vj.get("value", "")).strip().lower() in _NA_VALUE_TOKENS:
        return str(rule_row.get("quote") or "non-applicability recorded without reason")
    return None


def resolve_cell(check_key: str, r_code: str, rules_rows: list[dict]) -> dict:
    """Resolve one (check_key, r_code) cell against approved rules rows.

    Returns {"status": "filled"|"n/a"|"missing", "cell": str, "rule_id": str|None}.
    Preference order: explicit r-code match over global (NULL) applicability,
    then standard/deemed_to_comply rule_type, then rule_key (deterministic).
    """
    base_keys = CHECK_TO_BASE_RULE_KEYS.get(check_key)
    if base_keys is None:
        return {
            "status": "missing",
            "cell": "MISSING",
            "rule_id": None,
            "reason": f"check key {check_key!r} has no base-rule-key mapping",
        }
    code = normalize_code(r_code)
    ranked: list[tuple[tuple, dict, str | None]] = []
    for row in rules_rows:
        if str(row.get("lifecycle_status")) != "approved":
            continue
        if base_rule_key(row) not in base_keys:
            continue
        codes = rule_r_codes(row)
        explicit = code in codes
        if codes and not explicit:
            continue  # scoped to other density codes
        na = na_reason(row)
        type_pref = 0 if str(row.get("rule_type")) in ("standard", "deemed_to_comply") else 1
        sort_key = (not explicit, na is not None, type_pref, str(row.get("rule_key") or ""))
        ranked.append((sort_key, row, na))
    if not ranked:
        return {
            "status": "missing",
            "cell": "MISSING",
            "rule_id": None,
            "reason": "no approved rule resolves by direct key lookup",
        }
    ranked.sort(key=lambda item: item[0])
    _, row, na = ranked[0]
    rule_id = str(row.get("id"))
    if na is not None:
        return {"status": "n/a", "cell": f"n/a ({na})", "rule_id": rule_id}
    vj = row.get("value_json")
    value = vj.get("value") if isinstance(vj, dict) else None
    parts = [str(p) for p in (row.get("operator"), value, row.get("unit")) if p not in (None, "")]
    return {"status": "filled", "cell": f"{rule_id} | {' '.join(parts)}".strip(), "rule_id": rule_id}


def candidate_r_codes(candidate_row: dict) -> list[str]:
    """Density codes from rule_candidates.condition_json (the applicability dict)."""
    cj = candidate_row.get("condition_json")
    if isinstance(cj, dict):
        codes = cj.get("density_codes")
        if isinstance(codes, list):
            return [normalize_code(c) for c in codes]
    return []


def nearest_candidates(
    check_key: str, r_code: str, candidate_rows: list[dict], limit: int = 5
) -> list[dict]:
    """Best rule_candidates rows that could fill a MISSING cell.

    Ordered validators_passed → pending_review → auto_promoted, explicit density
    match before global, then highest confidence. De-duplicated on atom signature
    (the 3-pass ensemble inserts one candidate row per pass).
    """
    base_keys = CHECK_TO_BASE_RULE_KEYS.get(check_key, ())
    code = normalize_code(r_code)
    scored: list[tuple[tuple, dict]] = []
    for row in candidate_rows:
        status = str(row.get("review_status"))
        if status not in _STATUS_PRIORITY:
            continue
        if str(row.get("rule_key")) not in base_keys:
            continue
        codes = candidate_r_codes(row)
        explicit = code in codes
        if codes and not explicit:
            continue
        conf = row.get("confidence")
        conf_f = float(conf) if conf is not None else 0.0
        scored.append(((_STATUS_PRIORITY[status], not explicit, -conf_f), row))
    scored.sort(key=lambda item: item[0])
    out: list[dict] = []
    seen: set[tuple] = set()
    for _, row in scored:
        vj = row.get("value_json")
        value = vj.get("value") if isinstance(vj, dict) else None
        sig = (
            str(row.get("rule_key")),
            str(row.get("operator")),
            json.dumps(value, default=str),
            row.get("unit"),
            tuple(candidate_r_codes(row)),
        )
        if sig in seen:
            continue
        seen.add(sig)
        sv_id = row.get("source_version_id")
        out.append(
            {
                "candidate_id": str(row.get("id")),
                "review_status": str(row.get("review_status")),
                "rule_key": row.get("rule_key"),
                "operator": row.get("operator"),
                "value": value,
                "unit": row.get("unit"),
                "density_codes": candidate_r_codes(row),
                "confidence": row.get("confidence"),
                "source_version_id": str(sv_id) if sv_id else None,
                "quote": str(row.get("quote") or "")[:160],
            }
        )
        if len(out) >= limit:
            break
    return out


def build_matrix(
    rules_rows: list[dict], candidate_rows: list[dict], candidate_limit: int = 5
) -> dict:
    """Resolve every Tier-1 check × R5–R80 cell; return cells + defects + summary."""
    codes = matrix_density_codes()
    checks = [c.key for c in TIER1_CHECKS]
    cells: dict[str, dict[str, dict]] = {}
    defects: list[dict] = []
    counts = {"filled": 0, "n/a": 0, "missing": 0}
    missing_by_check: dict[str, int] = {}
    for check_key in checks:
        cells[check_key] = {}
        for code in codes:
            res = resolve_cell(check_key, code, rules_rows)
            cells[check_key][code] = res
            counts[res["status"]] += 1
            if res["status"] == "missing":
                missing_by_check[check_key] = missing_by_check.get(check_key, 0) + 1
                defects.append(
                    {
                        "check_key": check_key,
                        "r_code": code,
                        "defect": res.get("reason", "no approved rule resolves by direct key lookup"),
                        "base_rule_keys": list(CHECK_TO_BASE_RULE_KEYS.get(check_key, ())),
                        "nearest_candidates": nearest_candidates(
                            check_key, code, candidate_rows, limit=candidate_limit
                        ),
                    }
                )
    summary = {
        "tier1_checks": len(checks),
        "density_codes": len(codes),
        "cells": len(checks) * len(codes),
        "filled": counts["filled"],
        "na": counts["n/a"],
        "missing": counts["missing"],
        "missing_by_check": missing_by_check,
    }
    return {"checks": checks, "codes": codes, "cells": cells, "defects": defects, "summary": summary}


# ---------------------------------------------------------------------------
# Report writers + DB plumbing
# ---------------------------------------------------------------------------


def write_matrix_csv(result: dict, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["check_key", *result["codes"]])
        for check_key in result["checks"]:
            row_cells = result["cells"][check_key]
            writer.writerow([check_key, *(row_cells[c]["cell"] for c in result["codes"])])


def write_gaps_json(result: dict, path: str, org_id: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "org_id": org_id,
        "summary": result["summary"],
        "defects": result["defects"],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
        fh.write("\n")


def _fetch_dicts(conn, sql: str, params: tuple) -> list[dict]:
    cur = conn.execute(sql, params)
    cols = [d.name for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def fetch_rules(conn, org_id: str) -> list[dict]:
    return _fetch_dicts(
        conn,
        """
        SELECT id, rule_key, rule_type, pathway, lifecycle_status, operator, value_json,
               unit, condition_json, metadata_json, applicable_r_codes, quote,
               source_version_id
        FROM rules
        WHERE lifecycle_status = 'approved' AND (org_id = %s OR org_id IS NULL)
        """,
        (org_id,),
    )


def fetch_candidates(conn, org_id: str) -> list[dict]:
    return _fetch_dicts(
        conn,
        """
        SELECT id, rule_key, review_status, operator, value_json, unit, condition_json,
               quote, confidence, source_version_id
        FROM rule_candidates
        WHERE review_status IN ('validators_passed', 'pending_review', 'auto_promoted')
          AND (org_id = %s OR org_id IS NULL)
        """,
        (org_id,),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--org-id", default=DEFAULT_ORG_ID)
    ap.add_argument("--matrix", default="reports/rule_matrix.csv")
    ap.add_argument("--gaps", default="reports/rule_matrix_gaps.json")
    ap.add_argument("--candidate-limit", type=int, default=5,
                    help="nearest rule_candidates listed per MISSING cell")
    args = ap.parse_args()

    import psycopg

    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    with psycopg.connect(dsn) as conn:
        rules_rows = fetch_rules(conn, args.org_id)
        candidate_rows = fetch_candidates(conn, args.org_id)

    result = build_matrix(rules_rows, candidate_rows, candidate_limit=args.candidate_limit)
    write_matrix_csv(result, args.matrix)
    write_gaps_json(result, args.gaps, args.org_id)

    print(json.dumps({
        "matrix": args.matrix,
        "gaps": args.gaps,
        "approved_rules_loaded": len(rules_rows),
        "candidates_loaded": len(candidate_rows),
        **result["summary"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
