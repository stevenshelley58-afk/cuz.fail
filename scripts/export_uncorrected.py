"""Export uncorrected decode rules to JSON batches for Claude-subagent correction.

Selects rules from a council's docs that no correction model has processed —
both live-approved rules and rules parked as
``metadata_json.parked='awaiting_correction_openai_quota'`` — and writes
batches of --batch-size for the corrector agents.

Run inside the api container:
    python /app/scripts/export_uncorrected.py --council "City of Rockingham" \
        --out-dir /app/reports/correct_batches --batch-size 60
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
    ap.add_argument("--batch-size", type=int, default=60)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    with psycopg.connect(db_url()) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT r.id::text, r.rule_key, r.check_type,
                   r.rule_logic_json->>'what_it_means', r.rule_logic_json->>'requirement',
                   r.rule_logic_json->>'applies_when', r.rule_logic_json->>'modality',
                   r.quote, r.lifecycle_status
            FROM rules r
            WHERE r.extractor_model LIKE '%%decode'
              AND NOT (r.metadata_json ? 'correct_model')
              AND (r.lifecycle_status = 'approved'
                   OR r.metadata_json->>'parked' = 'awaiting_correction_openai_quota')
              AND EXISTS (
                SELECT 1 FROM source_versions sv JOIN source_documents sd ON sv.source_id = sd.id
                WHERE sv.id = r.source_version_id AND sd.local_government = %(council)s)
            ORDER BY r.id
            """ + (" LIMIT %(lim)s" if args.limit else ""),
            {"council": args.council, "lim": args.limit},
        )
        rules = [
            {"id": r[0], "rule_key": r[1], "check_type": r[2], "what_it_means": r[3],
             "requirement": r[4], "applies_when": r[5], "modality": r[6],
             "quote": r[7], "lifecycle_status": r[8]}
            for r in cur.fetchall()
        ]

    os.makedirs(args.out_dir, exist_ok=True)
    batches = 0
    for i in range(0, len(rules), args.batch_size):
        batch = rules[i:i + args.batch_size]
        path = os.path.join(args.out_dir, f"batch_{i // args.batch_size:03d}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"council": args.council, "rules": batch}, fh, indent=0, ensure_ascii=False)
        batches += 1
    print(json.dumps({"council": args.council, "rules": len(rules), "batches": batches,
                      "out_dir": args.out_dir}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
