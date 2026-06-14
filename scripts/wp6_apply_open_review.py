"""WP-E — apply open-vocab adversarial-review verdicts.

Reads the per-batch verdict JSONs produced by the review workflow and rejects
the rules flagged as mislabelled (quote contradicts canonical_rule_key). Rejection
is idempotent: it only touches currently-approved rules and stamps a traceable
marker into metadata_json.  Dry-run by default; --apply commits.

    python scripts/wp6_apply_open_review.py --verdict-dir <dir> [--apply]
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

REVIEW_TAG = "wp6_open_adversarial_review_v1"


def collect_rejections(verdict_dir: Path) -> dict[str, str]:
    """rule_id -> short reason, for every verdict == 'reject'."""
    rejects: dict[str, str] = {}
    for f in sorted(verdict_dir.glob("v_*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for v in data.get("verdicts", []):
            if str(v.get("verdict")) == "reject" and v.get("rule_id"):
                rejects[str(v["rule_id"])] = str(v.get("reason") or "")[:300]
    return rejects


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verdict-dir", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", default="/app/reports/wp6_open_review_apply.json")
    args = ap.parse_args()

    rejects = collect_rejections(Path(args.verdict_dir))
    db_url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )

    rejected = 0
    with psycopg.connect(db_url) as conn:
        cur = conn.cursor()
        for rule_id, reason in rejects.items():
            cur.execute(
                """
                UPDATE rules
                SET lifecycle_status = 'rejected',
                    metadata_json = COALESCE(metadata_json, '{}'::jsonb)
                        || jsonb_build_object('rejected_by', %s, 'reject_reason', %s),
                    updated_at = now()
                WHERE id = %s AND lifecycle_status = 'approved'
                """,
                (REVIEW_TAG, reason, rule_id),
            )
            rejected += cur.rowcount or 0
        if args.apply:
            conn.commit()
        else:
            conn.rollback()

    report = {
        "wp": "WP-E",
        "apply": args.apply,
        "verdicts_reject": len(rejects),
        "rules_rejected": rejected,
        "tag": REVIEW_TAG,
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
