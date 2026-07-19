"""WP-E4 — faithfulness CORRECTION pass (correct-don't-delete).

The original decode has high recall but ~18% of rules distort their cited quote.
A strict re-decode fixes faithfulness but loses ~60% of genuine rules (recall).
This pass keeps recall AND fixes faithfulness: for each approved decode rule an
LLM either

  - REJECTs it (the quote carries no development-control obligation — heading,
    definition, description of a plan, aspiration, past-tense, authority/scheme
    duty, or non-development), or
  - KEEPs it with a CORRECTED ``what_it_means`` / ``requirement`` / ``applies_when``
    / ``modality`` that states ONLY what the verbatim quote supports (removing
    invented obligations, fixing reversals, matching the quote's modality).

The quote (verbatim source) is never changed — only the interpretation is made
faithful to it. Idempotent per model tag.

    python /app/scripts/wp6_correct.py --apply --workers 16 --model gpt-4o \
        --report /app/reports/wp6_correct.json
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

SYSTEM = (
    "You are a faithfulness editor for a CITE-OR-REFUSE WA town-planning compliance tool. You make a "
    "rule say EXACTLY what its cited source quote supports — no more, no less — or you reject it. "
    "You return STRICT JSON only."
)

USER_TMPL = (
    "A development rule cites this VERBATIM QUOTE from a planning document:\n\"\"\"{quote}\"\"\"\n\n"
    "Its current decoded CLAIM:\n"
    "- what_it_means: {what_it_means}\n- requirement: {requirement}\n"
    "- applies_when: {applies_when}\n- check_type: {check_type}\n- modality: {modality}\n\n"
    "Produce the most FAITHFUL version of this rule, or reject it.\n\n"
    "REJECT (action='reject') only if the quote gives NOTHING to assess a proposal against — i.e. it is:\n"
    "  - a heading/title, definition, cross-reference, or narrative/background;\n"
    "  - a pure OBJECTIVE/aspiration that sets a goal but no standard ('to provide a range of housing', "
    "'should be cost-effective', 'ensure good amenity') — with no design/siting/use/measure to test;\n"
    "  - a DESCRIPTION or statement of fact about what a plan/study does or about existing allocations "
    "('the Structure Plan provides for...', 'allocates R20 to lots 160061', 'X is proposed', 'was adopted');\n"
    "  - an ADMINISTRATIVE / form-format / lodgement / report-preparation requirement ('must be in an "
    "approved form', 'a report must be prepared');\n"
    "  - a statement about the ASSESSMENT PROCESS or a duty binding an AUTHORITY/Commission/scheme "
    "document ('will be considered as part of the assessment', 'the Commission must consider...');\n"
    "  - an OPERATIONAL/utility/post-approval provision not tested at the development-application stage; "
    "or non-development matter (conveyancing, strata, mining, liquor).\n"
    "KEEP (and correct) any genuine standard a proposal's DESIGN is judged against — including design "
    "PRINCIPLES and PERFORMANCE criteria ('massing should be compatible with adjoining built form', "
    "'buildings should address the street'), measurable standards (setbacks, widths, heights, densities), "
    "and siting/use/subdivision/servicing/environmental controls — even when phrased softly ('should').\n\n"
    "Otherwise KEEP (action='keep') and return a CORRECTED claim that asserts ONLY what the quote "
    "supports:\n"
    "- remove any obligation, threshold, number, condition, exception or consequence not in the quote;\n"
    "- match the quote's modality — if the quote says 'should' or 'may', do NOT say 'must'/'required';\n"
    "- fix any reversal/negation;\n"
    "- keep genuine zone/use/R-code scoping in applies_when.\n"
    "If the current claim is already fully faithful, return it unchanged with action='keep'.\n\n"
    "Return ONLY: {{\"action\": \"keep\"|\"reject\", \"what_it_means\": \"...\", \"requirement\": \"...\", "
    "\"applies_when\": \"...\"|null, \"modality\": \"mandatory\"|\"deemed_to_comply\"|\"design_principle\"|"
    "\"advisory\", \"reason\": \"<=15 words\"}}"
)


def openai_correct(rule: dict, model: str, base_url: str, key: str) -> dict:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER_TMPL.format(
                quote=(rule.get("quote") or "")[:1400],
                what_it_means=(rule.get("what_it_means") or "")[:600],
                requirement=(rule.get("requirement") or "")[:300],
                applies_when=(rule.get("applies_when") or "") or "null",
                check_type=rule.get("check_type") or "",
                modality=rule.get("modality") or "",
            )},
        ],
        "temperature": 0, "max_tokens": 350,
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
            p = json.loads(payload["choices"][0]["message"]["content"])
            action = "reject" if str(p.get("action")).lower() == "reject" else "keep"
            return {
                "action": action,
                "what_it_means": str(p.get("what_it_means") or "")[:1000],
                "requirement": str(p.get("requirement") or "")[:400],
                "applies_when": (str(p["applies_when"])[:400] if p.get("applies_when") else None),
                "modality": str(p.get("modality") or rule.get("modality") or "advisory")[:40],
                "reason": str(p.get("reason") or "")[:200],
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


# Process the KEPT set AND the judgment-call rejected pool (to recover the
# gate's ~10% false-rejects) — but NOT the source-denylist rejections, which are
# correctly out of scope (wrong region / non-planning law).
SELECT_SQL = """
SELECT r.id::text, r.rule_key, r.check_type,
       r.rule_logic_json->>'what_it_means', r.rule_logic_json->>'requirement',
       r.rule_logic_json->>'applies_when', r.rule_logic_json->>'modality', r.quote
FROM rules r
WHERE r.extractor_model LIKE 'openai%%decode'
  AND {scope}
  {council}
  {skip}
"""

# Restrict a pass to one council's documents (e.g. a --redo filter run that must
# not churn another council's already-audited rules).
_COUNCIL_FILTER = (
    "AND EXISTS (SELECT 1 FROM source_versions sv JOIN source_documents sd "
    "ON sv.source_id = sd.id WHERE sv.id = r.source_version_id "
    "AND sd.local_government = %(council)s)"
)

_SCOPE_COMBINED = (
    "(r.lifecycle_status = 'approved' OR (r.lifecycle_status = 'rejected' "
    "AND coalesce(r.metadata_json->>'review_denylist','false') <> 'true'))"
)
_SCOPE_APPROVED = "r.lifecycle_status = 'approved'"

REJECT_SQL = """
UPDATE rules SET lifecycle_status='rejected', updated_at=now(),
  metadata_json = coalesce(metadata_json,'{}'::jsonb) || %(meta)s::jsonb
WHERE id = %(id)s
"""

# 'keep' also restores rejected-but-genuine rules to approved (false-reject recovery).
KEEP_SQL = """
UPDATE rules SET updated_at=now(), lifecycle_status='approved',
  rule_logic_json = rule_logic_json || %(logic)s::jsonb,
  metadata_json = coalesce(metadata_json,'{}'::jsonb) || %(meta)s::jsonb
WHERE id = %(id)s
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--model", default="gpt-4o")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--scope", choices=["combined", "approved"], default="combined",
                    help="'combined' = approved + recoverable rejected; 'approved' = re-filter approved only")
    ap.add_argument("--council", default=None,
                    help="restrict to rules from this council's docs (source_documents.local_government)")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--report", default="/app/reports/wp6_correct.json")
    args = ap.parse_args()

    key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if not key:
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
        return 2
    tag = f"openai:{args.model}:correct"

    skip = "" if args.redo else (
        "AND NOT (r.metadata_json ? 'correct_model' AND r.metadata_json->>'correct_model' = %(tag)s)"
    )
    with psycopg.connect(db_url()) as conn:
        cur = conn.cursor()
        scope_clause = _SCOPE_APPROVED if args.scope == "approved" else _SCOPE_COMBINED
        council_clause = _COUNCIL_FILTER if args.council else ""
        sql = SELECT_SQL.format(skip=skip, scope=scope_clause, council=council_clause) + (
            " ORDER BY random() LIMIT %(lim)s" if args.limit else "")
        cur.execute(sql, {"tag": tag, "lim": args.limit, "council": args.council})
        rules = [
            {"id": r[0], "rule_key": r[1], "check_type": r[2], "what_it_means": r[3],
             "requirement": r[4], "applies_when": r[5], "modality": r[6], "quote": r[7]}
            for r in cur.fetchall()
        ]

    kept = corrected = rejected = errors = 0

    def work(rule: dict) -> dict:
        return openai_correct(rule, args.model, base_url, key)

    out_conn = psycopg.connect(db_url())
    out_cur = out_conn.cursor()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(work, r): r for r in rules}
        for i, fut in enumerate(as_completed(futs), 1):
            rule = futs[fut]
            try:
                v = fut.result()
            except Exception:
                errors += 1
                continue
            changed = (v["what_it_means"].strip() and
                       v["what_it_means"].strip() != (rule["what_it_means"] or "").strip())
            if args.debug:
                tag_d = "REJECT" if v["action"] == "reject" else ("FIXED" if changed else "OK")
                print(f"[{tag_d}] {rule['rule_key']} :: {v['reason']}", file=sys.stderr, flush=True)
                if changed and v["action"] == "keep":
                    print(f"    was: {(rule['what_it_means'] or '')[:120]}", file=sys.stderr)
                    print(f"    now: {v['what_it_means'][:120]}", file=sys.stderr)
            meta = {"correct_model": tag, "correct_action": v["action"], "correct_reason": v["reason"]}
            if v["action"] == "reject":
                rejected += 1
                if args.apply:
                    out_cur.execute(REJECT_SQL, {"id": rule["id"], "meta": Json(meta)})
            else:
                kept += 1
                if changed:
                    corrected += 1
                logic = {"what_it_means": v["what_it_means"], "requirement": v["requirement"],
                         "applies_when": v["applies_when"], "modality": v["modality"]}
                if args.apply:
                    out_cur.execute(KEEP_SQL, {"id": rule["id"], "logic": Json(logic), "meta": Json(meta)})
            if i % 200 == 0:
                if args.apply:
                    out_conn.commit()
                print(f"  {i}/{len(rules)} kept={kept} corrected={corrected} rejected={rejected} err={errors}",
                      file=sys.stderr, flush=True)
    if args.apply:
        out_conn.commit()
    out_conn.close()

    summary = {
        "wp": "rule-correct", "apply": args.apply, "model": tag, "candidates": len(rules),
        "kept": kept, "corrected": corrected, "rejected": rejected, "errors": errors,
        "kept_rate": round(kept / len(rules), 4) if rules else None,
    }
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
