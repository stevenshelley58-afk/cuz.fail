"""WP9 — relevance audit over approved rules.

The first golden-fixture engine run showed that some approved rules pass the
deterministic validators (verbatim quote, sane range) but are semantically
mis-keyed: a subdivision public-open-space contribution stored as a dwelling
open_space standard, a glazing requirement stored as open_space, an industrial
separation buffer stored as side_setback, manoeuvring space stored as
garage_width.

This harness asks two independent LLMs, per approved rule:

    "Does this quote, read in the context of its clause, state a general
     residential development standard for <base_rule_key> that a compliance
     engine should apply to an ordinary dwelling proposal?"

Demotion requires BOTH models to answer not_applicable (conservative: ties
keep the rule). Demoted rules get lifecycle_status='pending_review' (never
deleted), metadata records both verdicts, and an audit_events row is written.

Run inside the api container:
    python /app/scripts/wp9_rule_relevance_audit.py [--limit N] \
        --report /app/reports/wp9_relevance_audit.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psycopg  # noqa: E402
from psycopg.types.json import Json  # noqa: E402

from wp6_extract import build_endpoints, parse_llm_json  # noqa: E402

SYSTEM = (
    "You are a planning-regulation auditor for Western Australian residential "
    "development standards. You judge whether an extracted rule is a GENERAL "
    "residential development standard, or something else (a subdivision/POS "
    "contribution, a structure-plan or site-specific provision, a buffer/"
    "separation distance for non-residential uses, a glazing/facade treatment, "
    "vehicle manoeuvring space, or any requirement about a different subject "
    "than the rule key claims). Respond with ONLY a JSON object: "
    '{"applicable": true|false, "reason": "<one sentence>"}. '
    "Answer applicable=false ONLY when the quote clearly does not express a "
    "general residential standard for the stated rule key; if it plausibly "
    "does, answer applicable=true."
)


def prompt_for_rule(rule: dict) -> str:
    return (
        f"Rule key: {rule['base_key']}\n"
        f"Operator/value/unit: {rule['operator']} {rule['value']} {rule['unit']}\n"
        f"Quoted anchor: {rule['quote']}\n\n"
        f"--- FULL CLAUSE CONTEXT START ---\n{rule['clause_text'][:6000]}\n"
        f"--- FULL CLAUSE CONTEXT END ---\n\n"
        "Is this a general residential development standard for the stated "
        "rule key? JSON only."
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--report", default="")
    args = ap.parse_args()

    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    endpoints, escalations = build_endpoints()
    endpoints = [endpoints[0], endpoints[-1]] if len(endpoints) > 1 else endpoints

    stats: dict[str, Any] = {
        "audited": 0, "kept": 0, "demoted": 0, "llm_errors": [],
        "escalations": escalations,
        "models": [f"{e.name}:{e.model}" for e in endpoints],
        "demotions": [],
    }

    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            """
            SELECT r.id, r.rule_key,
                   coalesce(r.value_json->>'base_rule_key', split_part(r.rule_key, '.', 1)),
                   r.operator, r.value_json->>'value', r.unit, r.quote, r.org_id, c.text
            FROM rules r JOIN clauses c ON c.id = r.clause_id
            WHERE r.lifecycle_status = 'approved'
            ORDER BY r.rule_key
            """
        ).fetchall()
        if args.limit:
            rows = rows[: args.limit]

        total = len(rows)
        for n, (rid, rule_key, base_key, op, value, unit, quote, org_id, clause_text) in enumerate(rows, 1):
            rule = {
                "base_key": base_key, "operator": op, "value": value,
                "unit": unit, "quote": quote, "clause_text": clause_text or "",
            }
            verdicts = []
            for ep in endpoints:
                try:
                    raw = ep.complete(SYSTEM, prompt_for_rule(rule), max_tokens=300)
                    payload = parse_llm_json(raw) or {}
                    verdicts.append({
                        "model": f"{ep.name}:{ep.model}",
                        "applicable": bool(payload.get("applicable", True)),
                        "reason": str(payload.get("reason", ""))[:300],
                    })
                except RuntimeError as exc:
                    stats["llm_errors"].append(f"{rule_key}: {exc}")
                    verdicts.append({"model": f"{ep.name}:{ep.model}",
                                     "applicable": True, "reason": f"llm_error: {exc}"})
            stats["audited"] += 1
            demote = len(verdicts) >= 2 and all(not v["applicable"] for v in verdicts)
            print(f"[{n}/{total}] {rule_key}: {'DEMOTE' if demote else 'keep'}", flush=True)

            if not demote:
                stats["kept"] += 1
                continue

            conn.execute(
                "UPDATE rules SET lifecycle_status='pending_review', "
                "metadata_json = metadata_json || %s::jsonb, updated_at=now() WHERE id=%s",
                (Json({"wp9_relevance_audit": {"verdicts": verdicts}}), rid),
            )
            conn.execute(
                """
                INSERT INTO audit_events (id, org_id, actor_user_id, event_type, action,
                    subject_type, subject_id, before_json, after_json, metadata_json, created_at)
                VALUES (gen_random_uuid(), %s, NULL, 'rule.relevance_demoted', 'demoted',
                        'rule', %s, %s, %s, %s, now())
                """,
                (org_id, rid,
                 Json({"lifecycle_status": "approved"}),
                 Json({"lifecycle_status": "pending_review"}),
                 Json({"actor": "system", "wp9": True, "verdicts": verdicts})),
            )
            conn.commit()
            stats["demoted"] += 1
            stats["demotions"].append({
                "rule_key": rule_key, "quote": (quote or "")[:120],
                "reasons": [v["reason"] for v in verdicts],
            })

    out = json.dumps(stats, indent=2, default=str)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(out)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
