"""Export undecoded clauses to JSON batches for Claude-subagent decode.

Mirrors wp6_decode.py's queue (rule_bearing + procedural clauses, 40-8000
chars, no existing decode candidate from ANY decode model) for one council.

Run inside the api container:
    python /app/scripts/export_clauses.py --council "City of Rockingham" \
        --out-dir /app/reports/decode_batches/rk --batch-size 40
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
    ap.add_argument("--batch-size", type=int, default=40)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    with psycopg.connect(db_url()) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT c.id::text, c.source_version_id::text, c.clause_path, c.text
            FROM clauses c
            JOIN source_versions sv ON c.source_version_id = sv.id
            JOIN source_documents sd ON sv.source_id = sd.id
            WHERE sd.local_government = %(council)s
              AND c.disposition = ANY(ARRAY['rule_bearing','procedural'])
              AND length(c.text) BETWEEN 40 AND 8000
              AND NOT EXISTS (
                SELECT 1 FROM rule_candidates rc
                WHERE rc.clause_id = c.id AND rc.extractor_model LIKE '%%decode')
            ORDER BY c.id
            """ + (" LIMIT %(lim)s" if args.limit else ""),
            {"council": args.council, "lim": args.limit},
        )
        clauses = [
            {"clause_id": r[0], "source_version_id": r[1], "clause_path": r[2], "text": r[3]}
            for r in cur.fetchall()
        ]

    os.makedirs(args.out_dir, exist_ok=True)
    batches = 0
    for i in range(0, len(clauses), args.batch_size):
        with open(os.path.join(args.out_dir, f"clauses_{i // args.batch_size:03d}.json"),
                  "w", encoding="utf-8") as fh:
            json.dump({"council": args.council, "clauses": clauses[i:i + args.batch_size]},
                      fh, indent=0, ensure_ascii=False)
        batches += 1
    print(json.dumps({"council": args.council, "clauses": len(clauses), "batches": batches,
                      "out_dir": args.out_dir}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
