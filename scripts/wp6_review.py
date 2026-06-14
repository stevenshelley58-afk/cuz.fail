"""WP-E2 — faithfulness + relevance re-review of decoded rules.

The rich decode (wp6_decode.py) promoted rules straight from structural
``validators_passed`` to ``approved`` WITHOUT the adversarial review the old
numeric pipeline had. A readiness audit found ~40% of decoded rules assert an
obligation/exception/consequence their cited quote does NOT support (fabricated
or reversed), and that non-development law (strata/mining/conveyancing/
wrong-region) leaked into ``relevance='development'``.

This re-review closes both gaps for the cite-or-refuse promise:
1.  Deterministic source denylist rejects wrong-region / non-development sources.
2.  An LLM judge decides, per rule, whether the verbatim QUOTE literally supports
    the CLAIM (faithful) and whether it is genuine development control.
Failures move to ``lifecycle_status='rejected'`` (the engine only surfaces
``approved``), with the verdict recorded in ``metadata_json``.

Runs INSIDE / against the api image, concurrent:

    python /app/scripts/wp6_review.py --apply --workers 16 --model gpt-4o \
        --report /app/reports/wp6_review.json

Idempotent: a rule already carrying a review verdict for this model is skipped
unless ``--redo``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import psycopg  # noqa: E402
from psycopg.types.json import Json  # noqa: E402

# Sources that are never development control for a Cockburn building/development
# proposal (wrong region, or a different body of law a draftsperson never checks
# a proposal against). Matched case-insensitively against source_documents.title.
DENY_SOURCE_SUBSTRINGS = [
    "strata titles",
    "community titles",
    "mining act",
    "transfer of land",
    "public works act",
    "health act",
    "health (miscellaneous",
    "liquor",
    "retirement villages",
    "leeuwin-naturaliste",   # SPP 6.1 — wrong region
    "peel region",
    "greater bunbury",
    "bunbury",
]

SYSTEM = (
    "You are a strict, skeptical auditor of Western Australian town-planning rules for a "
    "CITE-OR-REFUSE compliance tool. A rule must never assert anything its cited source text "
    "does not literally say. You return STRICT JSON only."
)

USER_TMPL = (
    "A planning rule was decoded from a source document and cites a VERBATIM QUOTE.\n\n"
    "QUOTE (verbatim source text):\n\"\"\"{quote}\"\"\"\n\n"
    "CLAIM made by the rule:\n"
    "- what_it_means: {what_it_means}\n"
    "- requirement: {requirement}\n"
    "- applies_when: {applies_when}\n"
    "- check_type: {check_type}\n"
    "- modality: {modality}\n\n"
    "Decide two things. Judge SUBSTANCE, not wording.\n"
    "1. faithful — Does the QUOTE support the CLAIM's substance? Mark FALSE ONLY if the claim:\n"
    "   - REVERSES or NEGATES the quote (e.g. quote prohibits, claim permits or adds an 'unless'); or\n"
    "   - INVENTS a specific threshold, number, distance, condition, exception or consequence that is "
    "absent from the quote; or\n"
    "   - turns a pure DEFINITION, heading, or statement-of-fact into a binding requirement the quote "
    "does not impose.\n"
    "   Do NOT mark unfaithful merely because the claim adds normative framing (must/required) "
    "consistent with the quote, paraphrases, or expands an abbreviation.\n"
    "2. is_development — Is the rule RELEVANT to how land, buildings or development must be designed, "
    "sited, used, built, subdivided, landscaped, serviced, or what physical/environmental constraints "
    "apply to a proposal (including soft design 'consideration' guidance)? Mark FALSE ONLY if it is "
    "clearly NOT about physical development: pure administration/fees/meetings/delegations, conveyancing "
    "or strata/community-title disclosure, mining tenement law, liquor licensing, or a bare definition "
    "with no development effect.\n\n"
    "Return ONLY: {{\"faithful\": true|false, \"is_development\": true|false, \"reason\": \"<=15 words\"}}"
)


def openai_judge(rule: dict, model: str, base_url: str, key: str) -> dict:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER_TMPL.format(
                quote=(rule.get("quote") or "")[:1200],
                what_it_means=(rule.get("what_it_means") or "")[:600],
                requirement=(rule.get("requirement") or "")[:300],
                applies_when=(rule.get("applies_when") or "") or "null",
                check_type=rule.get("check_type") or "",
                modality=rule.get("modality") or "",
            )},
        ],
        "temperature": 0,
        "max_tokens": 200,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    last: Exception | None = None
    for delay in (0.0, 3.0, 8.0, 20.0, 45.0, 90.0):
        if delay:
            time.sleep(delay)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            parsed = json.loads(payload["choices"][0]["message"]["content"])
            return {
                "faithful": bool(parsed.get("faithful")),
                "is_development": bool(parsed.get("is_development")),
                "reason": str(parsed.get("reason") or "")[:200],
            }
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"http_{exc.code}") from exc
        except (urllib.error.URLError, OSError, KeyError, json.JSONDecodeError) as exc:
            last = exc
    code = getattr(last, "code", None)
    raise RuntimeError(f"http_{code}" if code else f"{type(last).__name__}")


def db_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


SELECT_SQL = """
SELECT r.id::text, r.rule_key, r.check_type,
       r.rule_logic_json->>'what_it_means', r.rule_logic_json->>'requirement',
       r.rule_logic_json->>'applies_when', r.rule_logic_json->>'modality',
       r.quote, lower(coalesce(sd.title,''))
FROM rules r
JOIN source_versions sv ON r.source_version_id = sv.id
JOIN source_documents sd ON sv.source_id = sd.id
WHERE r.extractor_model LIKE 'openai%%decode'
  AND r.lifecycle_status = 'approved'
  {skip}
"""

REJECT_SQL = """
UPDATE rules SET lifecycle_status='rejected', updated_at=now(),
  metadata_json = coalesce(metadata_json,'{}'::jsonb) || %(verdict)s::jsonb
WHERE id = %(id)s
"""

PASS_SQL = """
UPDATE rules SET updated_at=now(),
  metadata_json = coalesce(metadata_json,'{}'::jsonb) || %(verdict)s::jsonb
WHERE id = %(id)s
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--model", default="gpt-4o")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--debug", action="store_true", help="print per-rule verdicts (calibration)")
    ap.add_argument("--report", default="/app/reports/wp6_review.json")
    args = ap.parse_args()

    key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if not key:
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
        return 2
    tag = f"openai:{args.model}:review"

    skip = "" if args.redo else (
        "AND NOT (r.metadata_json ? 'review_model' AND r.metadata_json->>'review_model' = %(tag)s)"
    )
    with psycopg.connect(db_url()) as conn:
        cur = conn.cursor()
        sql = SELECT_SQL.format(skip=skip) + (
            " ORDER BY random() LIMIT %(lim)s" if args.limit else "")
        cur.execute(sql, {"tag": tag, "lim": args.limit})
        rules = [
            {"id": r[0], "rule_key": r[1], "check_type": r[2], "what_it_means": r[3],
             "requirement": r[4], "applies_when": r[5], "modality": r[6], "quote": r[7],
             "source_title": r[8]}
            for r in cur.fetchall()
        ]

    denied = 0
    kept = 0
    rejected = 0
    errors = 0
    reject_reasons: dict[str, int] = {}

    def judge(rule: dict) -> dict:
        title = rule.get("source_title") or ""
        for sub in DENY_SOURCE_SUBSTRINGS:
            if sub in title:
                return {"faithful": False, "is_development": False,
                        "reason": f"denylist_source:{sub}", "denylist": True}
        v = openai_judge(rule, args.model, base_url, key)
        v["denylist"] = False
        return v

    out_conn = psycopg.connect(db_url())
    out_cur = out_conn.cursor()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(judge, r): r for r in rules}
        for i, fut in enumerate(as_completed(futs), 1):
            rule = futs[fut]
            try:
                v = fut.result()
            except Exception:
                errors += 1
                if i % 200 == 0:
                    print(f"  {i}/{len(rules)} judged, kept={kept} rejected={rejected} err={errors}",
                          file=sys.stderr, flush=True)
                continue
            ok = v["faithful"] and v["is_development"]
            if args.debug:
                print(f"[{'KEEP' if ok else 'REJECT'}] {rule['rule_key']} "
                      f"faithful={v['faithful']} dev={v['is_development']} :: {v['reason']}\n"
                      f"    QUOTE: {(rule.get('quote') or '')[:140]}\n"
                      f"    MEANS: {(rule.get('what_it_means') or '')[:140]}",
                      file=sys.stderr, flush=True)
            verdict = Json({
                "review_model": tag,
                "review_faithful": v["faithful"],
                "review_is_development": v["is_development"],
                "review_reason": v["reason"],
                "review_denylist": v["denylist"],
            })
            if v["denylist"]:
                denied += 1
            if ok:
                kept += 1
                if args.apply:
                    out_cur.execute(PASS_SQL, {"id": rule["id"], "verdict": verdict})
            else:
                rejected += 1
                reason = "denylist" if v["denylist"] else (
                    "unfaithful" if not v["faithful"] else "not_development")
                reject_reasons[reason] = reject_reasons.get(reason, 0) + 1
                if args.apply:
                    out_cur.execute(REJECT_SQL, {"id": rule["id"], "verdict": verdict})
            if i % 200 == 0:
                if args.apply:
                    out_conn.commit()
                print(f"  {i}/{len(rules)} judged, kept={kept} rejected={rejected} err={errors}",
                      file=sys.stderr, flush=True)
    if args.apply:
        out_conn.commit()
    out_conn.close()

    summary = {
        "wp": "rule-review", "apply": args.apply, "model": tag,
        "candidates": len(rules), "kept_approved": kept, "rejected": rejected,
        "denylist_rejected": denied, "errors": errors,
        "reject_reasons": reject_reasons,
        "kept_rate": round(kept / len(rules), 4) if rules else None,
    }
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
