"""WP-E follow-up — curate lot-AREA rule operators to 'gte'.

The open-vocab ``site_area`` cluster (plus ``min_lot_area_per_dwelling`` and
``average_lot_size``) mixes R-Codes Table-1 *minimum / average* lot-size entries
with the wrong extracted operator: many table rows came out as ``eq`` (e.g.
"R20 lots – 450m2", "Min 350", "Av 260") or ``gt`` ("no site is less than
100m2") when the planning intent is "the lot must be AT LEAST this size".

This script normalises the operator to ``gte`` **only** for approved rules whose
quote actually denotes a minimum / table lot size — detected by minimum/average
markers (``Min``/``Av``/``Average``/"not less than"/"at least") or the R-Codes
table pattern (``R20 lots – 450m2`` / ``R50 = 180m2``).  It deliberately leaves
alone:

* genuine maxima        — "not exceed 3000m2", "260 square metres or less" (lte)
* applicability filters  — "lots less than 260m2", "Lots > 900m2" (lt/gt with NO
                           minimum marker; these scope which lots a rule covers,
                           they are not a compliance minimum)
* range bands           — "131-160" (operator ``range``)
* unmarked noise         — bare "9241m2" with no min/table marker (operator ``eq``)
* formula rows           — "R160 lots – calculated by dividing ..." (no numeric
                           after the table dash)

Idempotent: once a row is flipped to ``gte`` it no longer matches the
``operator IN (eq,lt,lte,gt)`` filter, so re-runs are no-ops.  Dry-run is the
default; ``--apply`` commits.  Every flip is stamped into ``metadata_json`` and
recorded as an ``audit_events`` row (standing rule: every override is audited).

Run inside the api container:
    python /app/scripts/wp6_curate_lot_area_operators.py --apply \
        --report /app/reports/wp6_curate_lot_area_operators.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import psycopg  # noqa: E402

CURATION_TAG = "wp6_lot_area_operator_curation_v1"

LOT_AREA_CANONICAL_KEYS = ("site_area", "min_lot_area_per_dwelling", "average_lot_size")

# A quote denotes a minimum / table lot size when ANY of these match (case-
# insensitive).  Kept identical between the SELECT preview and the UPDATE so the
# dry-run report and the applied change can never diverge.
MIN_MARKER_SQL = r"""(
    quote ~* '\m(min|minimum|av|ave|avg|average)\M'
    OR quote ~* 'R[0-9]+(\.[0-9]+)?(-?[A-Za-z]+)?\s*(lots?)?\s*[=–\-:]\s*[0-9]'
    OR quote ~* '(not|no)\s+([a-z]+\s+){0,3}less than'
    OR quote ~* 'at least'
)"""

# Only these operators are candidates for normalisation to 'gte'.  'gte' is
# already correct; 'range' is a band we must not collapse.
CURATABLE_OPERATORS = ("eq", "lt", "lte", "gt")


def _db_url() -> str:
    return (
        os.environ["DATABASE_URL"]
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
    )


def _select_candidates(cur) -> list[dict]:
    cur.execute(
        f"""
        SELECT id::text, org_id::text, canonical_rule_key, operator,
               value_json->>'value' AS value, applicable_r_codes::text AS r_codes,
               left(regexp_replace(quote, '\\s+', ' ', 'g'), 160) AS quote
        FROM rules
        WHERE lifecycle_status = 'approved'
          AND canonical_rule_key = ANY(%s)
          AND operator = ANY(%s)
          AND {MIN_MARKER_SQL}
        ORDER BY canonical_rule_key, operator, value_json->>'value'
        """,
        (list(LOT_AREA_CANONICAL_KEYS), list(CURATABLE_OPERATORS)),
    )
    cols = [d.name for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _flip(cur, rule: dict) -> int:
    """Set operator='gte', stamp metadata, and audit. Returns rows updated."""
    cur.execute(
        """
        UPDATE rules
        SET operator = 'gte',
            metadata_json = COALESCE(metadata_json, '{}'::jsonb)
                || jsonb_build_object(
                    'operator_curated_by', %s::text,
                    'operator_was', operator),
            updated_at = now()
        WHERE id = %s::uuid
          AND lifecycle_status = 'approved'
          AND operator = ANY(%s)
        """,
        (CURATION_TAG, rule["id"], list(CURATABLE_OPERATORS)),
    )
    n = cur.rowcount or 0
    if n:
        cur.execute(
            """
            INSERT INTO audit_events
                (id, org_id, event_type, action, subject_type, subject_id,
                 before_json, after_json, metadata_json, created_at)
            VALUES
                (gen_random_uuid(), %s::uuid, 'rule_operator_curation',
                 'normalize_operator_to_gte', 'rule', %s::uuid,
                 %s::jsonb, %s::jsonb, %s::jsonb, now())
            """,
            (
                rule["org_id"],
                rule["id"],
                json.dumps({"operator": rule["operator"]}),
                json.dumps({"operator": "gte"}),
                json.dumps(
                    {
                        "tag": CURATION_TAG,
                        "canonical_rule_key": rule["canonical_rule_key"],
                        "value": rule["value"],
                        "applicable_r_codes": rule["r_codes"],
                        "quote": rule["quote"],
                        "reason": "quote denotes a minimum/table lot size",
                    }
                ),
            ),
        )
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="commit operator changes")
    ap.add_argument("--report", default="/app/reports/wp6_curate_lot_area_operators.json")
    args = ap.parse_args()

    flipped = 0
    by_cluster_op: dict[str, int] = {}
    with psycopg.connect(_db_url()) as conn:
        cur = conn.cursor()
        candidates = _select_candidates(cur)
        for rule in candidates:
            n = _flip(cur, rule)
            flipped += n
            if n:
                k = f"{rule['canonical_rule_key']}:{rule['operator']}->gte"
                by_cluster_op[k] = by_cluster_op.get(k, 0) + n
        if args.apply:
            conn.commit()
        else:
            conn.rollback()

    report = {
        "wp": "WP-E follow-up",
        "tag": CURATION_TAG,
        "apply": args.apply,
        "canonical_keys": list(LOT_AREA_CANONICAL_KEYS),
        "candidates_matched": len(candidates),
        "rows_flipped": flipped,
        "flips_by_cluster_operator": by_cluster_op,
        "sample": candidates[:25],
        "notes": [
            "Dry-run only; no rows changed." if not args.apply
            else "operator set to 'gte' for minimum/table lot-size rules; audited.",
        ],
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: report[k] for k in
                      ("apply", "candidates_matched", "rows_flipped", "flips_by_cluster_operator")},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
