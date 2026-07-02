"""Export a stratified faithfulness-audit sample of a council's approved rules.

Samples proportionally by check_type (min 1 per stratum) from approved rules
scoped to the council, and writes JSON for the 3-judge audit
(COUNCIL_ROLLOUT_PLAN §1.6).

Run inside the api container:
    python /app/scripts/export_audit_sample.py --council "City of Melville" \
        --size 75 --out /app/reports/melville_audit_sample.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, "/app/src")

import psycopg  # noqa: E402


def db_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--council", required=True)
    ap.add_argument("--size", type=int, default=75)
    ap.add_argument("--seed", type=float, default=0.42)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with psycopg.connect(db_url()) as conn:
        cur = conn.cursor()
        cur.execute("SELECT setseed(%s)", (args.seed,))
        cur.execute(
            """
            SELECT check_type, count(*) FROM rules
            WHERE lifecycle_status='approved' AND council_scope=%s
            GROUP BY 1 ORDER BY 2 DESC
            """,
            (args.council,),
        )
        strata = cur.fetchall()
        total = sum(n for _, n in strata)
        if not total:
            print(f"no approved rules scoped to {args.council!r}", file=sys.stderr)
            return 1

        sample: list[dict] = []
        for check_type, n in strata:
            take = max(1, round(args.size * n / total))
            cur.execute(
                """
                SELECT id::text, rule_key, check_type,
                       rule_logic_json->>'what_it_means',
                       rule_logic_json->>'requirement',
                       rule_logic_json->>'applies_when',
                       rule_logic_json->>'modality', quote
                FROM rules
                WHERE lifecycle_status='approved' AND council_scope=%s AND check_type=%s
                ORDER BY random() LIMIT %s
                """,
                (args.council, check_type, take),
            )
            for r in cur.fetchall():
                sample.append({
                    "id": r[0], "rule_key": r[1], "check_type": r[2],
                    "what_it_means": r[3], "requirement": r[4],
                    "applies_when": r[5], "modality": r[6], "quote": r[7],
                })

    out = {
        "council": args.council,
        "population": total,
        "strata": {ct: n for ct, n in strata},
        "sample_size": len(sample),
        "rules": sample,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k != "rules"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
