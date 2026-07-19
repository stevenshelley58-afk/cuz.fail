"""Promote decode candidates -> approved rules, carrying the rich rule logic.

The decoder (wp6_decode.py) writes development-relevant rule_candidates with
check_type / evaluable / rule_logic_json. This promotes them to approved rules
(advisory, cited) so the engine can surface and evaluate them. Idempotent: the
rule id == candidate id, so re-runs no-op. rule_key is suffixed with the
candidate id so it is unique per source_version while base_rule_key (in
value_json) and canonical_rule_key keep the clean key for clustering.

    python scripts/wp6_promote_decode.py --apply --report /app/reports/wp6_promote_decode.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import psycopg  # noqa: E402

PROMOTE_SQL = """
INSERT INTO rules (
    id, org_id, source_version_id, clause_id, candidate_id,
    rule_key, canonical_rule_key, rule_type, pathway, lifecycle_status,
    check_type, evaluable, rule_logic_json,
    operator, value_json, unit, condition_json, quote,
    extractor_model, metadata_json, created_at, updated_at
)
SELECT
    rc.id, rc.org_id, rc.source_version_id, rc.clause_id, rc.id,
    rc.rule_key || '.d' || left(rc.id::text, 8) AS rule_key,
    rc.rule_key AS canonical_rule_key,
    COALESCE(rc.rule_type, 'standard'), COALESCE(rc.pathway, 'none'), 'approved',
    rc.check_type, rc.evaluable, rc.rule_logic_json,
    rc.operator,
    rc.value_json || jsonb_build_object('base_rule_key', rc.rule_key),
    rc.unit, '{}'::jsonb, rc.quote,
    rc.extractor_model,
    COALESCE(rc.metadata_json, '{}'::jsonb) || jsonb_build_object('promoted_from', 'decode'),
    now(), now()
FROM rule_candidates rc
WHERE rc.extractor_model LIKE '%%decode'
  AND rc.review_status = 'validators_passed'
  AND (rc.rule_logic_json->>'relevance') = 'development'
  AND rc.rule_key IS NOT NULL AND btrim(rc.rule_key) <> ''
ON CONFLICT (id) DO NOTHING
"""


def db_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", default="/app/reports/wp6_promote_decode.json")
    args = ap.parse_args()

    with psycopg.connect(db_url()) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM rule_candidates rc "
            "WHERE rc.extractor_model LIKE '%%decode' "
            "AND rc.review_status='validators_passed' "
            "AND (rc.rule_logic_json->>'relevance')='development'"
        )
        eligible = int(cur.fetchone()[0])
        promoted = 0
        if args.apply:
            cur.execute(PROMOTE_SQL)
            promoted = cur.rowcount or 0
            conn.commit()
        else:
            conn.rollback()

    report = {"wp": "decode-promote", "apply": args.apply,
              "eligible_candidates": eligible, "rules_promoted": promoted}
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
