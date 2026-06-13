"""Apply adversarial review verdicts to the rules table.

Reads a JSON file of reviews (the workflow output, aggregated) and:
- For verdict starting with `reject_`: sets the rule's lifecycle_status='rejected'
  and writes a metadata entry capturing the verdict + reason.
- For verdict `condition_missed` or `correct_*`: updates condition_json with the
  corrected condition (and other fields if provided).
- For each entry's missed_exceptions: inserts new rules with rule_type='exception'
  and an exception_to legal_edge pointing back to the source rule.

Idempotent and re-runnable.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid

import psycopg
from psycopg.types.json import Json

sys.path.insert(0, "/app/src")
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)

ORG_ID = "1d31c315-5087-47df-a8d4-ebfd08efad5d"
EXCEPTION_NAMESPACE = uuid.UUID("00000000-0000-5000-d000-000000000003")


def db_connect():
    db_url = os.environ["DATABASE_URL"].replace(
        "postgresql+asyncpg://", "postgresql://"
    ).replace("postgresql+psycopg://", "postgresql://")
    return psycopg.connect(db_url)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--reviews", required=True, help="Path to aggregated reviews JSON")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--report", default="/app/reports/wp6_apply_adv_review.json")
    p.add_argument(
        "--min-confidence", type=float, default=0.7, help="Skip review entries below this confidence"
    )
    args = p.parse_args()

    with open(args.reviews, encoding="utf-8") as f:
        agg = json.load(f)
    reviews = agg.get("reviews", []) if isinstance(agg, dict) else agg

    summary = {
        "considered": len(reviews),
        "rejected": 0,
        "condition_updated": 0,
        "exceptions_inserted": 0,
        "skipped_keep": 0,
        "skipped_low_confidence": 0,
        "skipped_missing_rule": 0,
        "rejected_by_verdict": {},
    }

    with db_connect() as conn:
        # Disable transaction wrap so each statement commits independently.
        conn.autocommit = True
        cur = conn.cursor()

        for rev in reviews:
            verdict = rev.get("verdict", "")
            confidence = float(rev.get("confidence", 0) or 0)
            rule_id = rev.get("rule_id")
            if not rule_id:
                continue

            if confidence < args.min_confidence:
                summary["skipped_low_confidence"] += 1
                continue

            # Verify rule exists and is currently approved
            row = cur.execute(
                "SELECT id, rule_key, source_version_id, clause_id, lifecycle_status,"
                "       metadata_json FROM rules WHERE id = %s",
                (rule_id,),
            ).fetchone()
            if not row:
                summary["skipped_missing_rule"] += 1
                continue
            (rid, rule_key, sv_id, clause_id, lifecycle, metadata) = row
            metadata = metadata or {}

            if verdict.startswith("reject_"):
                summary["rejected"] += 1
                summary["rejected_by_verdict"][verdict] = (
                    summary["rejected_by_verdict"].get(verdict, 0) + 1
                )
                if args.apply:
                    new_meta = dict(metadata)
                    new_meta["adv_review"] = {
                        "verdict": verdict,
                        "confidence": confidence,
                        "reasoning": rev.get("reasoning", "")[:500],
                    }
                    cur.execute(
                        "UPDATE rules SET lifecycle_status='rejected',"
                        "       metadata_json = %s,"
                        "       updated_at = now()"
                        " WHERE id = %s",
                        (Json(new_meta), rid),
                    )

            elif verdict in ("condition_missed", "correct_value", "correct_unit", "correct_operator", "correct_scope"):
                corrected = rev.get("corrected") or {}
                cond = corrected.get("condition")
                if cond:
                    summary["condition_updated"] += 1
                    if args.apply:
                        new_meta = dict(metadata)
                        new_meta["adv_review"] = {
                            "verdict": verdict,
                            "confidence": confidence,
                            "reasoning": rev.get("reasoning", "")[:500],
                        }
                        cur.execute(
                            "UPDATE rules"
                            "   SET condition_json = jsonb_set("
                            "         coalesce(condition_json, '{}'::jsonb),"
                            "         '{condition}', to_jsonb(%s::text), true),"
                            "       metadata_json = %s,"
                            "       updated_at = now()"
                            " WHERE id = %s",
                            (cond, Json(new_meta), rid),
                        )
            elif verdict == "keep":
                summary["skipped_keep"] += 1

            # Insert missed_exceptions as new rules with rule_type='exception'.
            for excp in rev.get("missed_exceptions") or []:
                op = excp.get("operator")
                val = excp.get("value")
                unit = excp.get("unit")
                if not op or val is None:
                    continue
                # Derive a rule_key suffix from the parent rule_key's base.
                base_key = rule_key.split(".", 1)[0]
                # Deterministic suffix from operator/value/unit so distinct exceptions
                # under the same parent get unique keys (avoid uq_rules_version_key violations).
                import hashlib as _h
                excp_sig = f"{op}|{val}|{unit}|{(excp.get('quote') or '')[:200]}|{(excp.get('condition') or '')[:200]}"
                excp_hash = _h.sha256(excp_sig.encode()).hexdigest()[:10]
                except_key = f"{base_key}.exception_{excp_hash}"
                new_id = str(
                    uuid.uuid5(
                        EXCEPTION_NAMESPACE,
                        f"{rid}|{except_key}|{op}|{val}|{unit}",
                    )
                )
                existing = cur.execute(
                    "SELECT 1 FROM rules WHERE id = %s", (new_id,)
                ).fetchone()
                if existing:
                    continue
                # Defend against uq_rules_version_key (source_version_id, rule_key)
                sv_rk_collision = cur.execute(
                    "SELECT 1 FROM rules WHERE source_version_id = %s AND rule_key = %s",
                    (sv_id, except_key),
                ).fetchone()
                if sv_rk_collision:
                    # Suffix until unique under this source_version.
                    for n in range(2, 50):
                        candidate_key = f"{except_key}_v{n}"
                        if not cur.execute(
                            "SELECT 1 FROM rules WHERE source_version_id = %s AND rule_key = %s",
                            (sv_id, candidate_key),
                        ).fetchone():
                            except_key = candidate_key
                            break
                    else:
                        continue
                cond_json = {
                    "description": (excp.get("description") or "")[:300],
                    "condition": (excp.get("condition") or "")[:300],
                    "density_codes": excp.get("applicable_r_codes") or [],
                }
                summary["exceptions_inserted"] += 1
                if args.apply:
                    cur.execute(
                        "INSERT INTO rules ("
                        "  id, org_id, source_version_id, clause_id, rule_key, rule_type,"
                        "  pathway, lifecycle_status, operator, value_json, unit,"
                        "  condition_json, quote, extractor_model, metadata_json,"
                        "  created_at, updated_at"
                        ") VALUES ("
                        "  %s, %s, %s, %s, %s, 'exception',"
                        "  'none', 'approved', %s, %s, %s,"
                        "  %s, %s, 'adversarial:wp6_apply_adv_review_v1', %s,"
                        "  now(), now()"
                        ") ON CONFLICT (id) DO NOTHING",
                        (
                            new_id,
                            ORG_ID,
                            sv_id,
                            clause_id,
                            except_key,
                            op,
                            Json({"value": float(val)}),
                            unit,
                            Json(cond_json),
                            (excp.get("quote") or "")[:500],
                            Json(
                                {
                                    "wp6": True,
                                    "exception_from_adv_review": True,
                                    "parent_rule_id": str(rid),
                                    "parent_rule_key": rule_key,
                                }
                            ),
                        ),
                    )
                    # legal_edge: exception_to parent
                    edge_id = str(
                        uuid.uuid5(EXCEPTION_NAMESPACE, f"edge|{new_id}|{rid}")
                    )
                    try:
                        cur.execute(
                            "INSERT INTO legal_edges ("
                            "  id, from_rule_id, to_rule_id, relation, quote, created_at, updated_at"
                            ") VALUES (%s, %s, %s, 'exception_to', %s, now(), now())"
                            " ON CONFLICT (id) DO NOTHING",
                            (
                                edge_id,
                                new_id,
                                str(rid),
                                (excp.get("quote") or "")[:300],
                            ),
                        )
                    except psycopg.Error:
                        pass

        if args.apply:
            conn.commit()

    if args.report:
        os.makedirs(os.path.dirname(args.report), exist_ok=True)
        with open(args.report, "w") as f:
            json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
