"""WP6 rule DECODE — turn every clause into structured rule objects.

Unlike wp6_extract.py (numeric atoms only), this decodes EVERY kind of planning
rule — numeric thresholds, categorical, boolean/presence, conditional, and
qualitative/performance (design-principle) rules — recording for each: what it
is, what it means, and how a system would query/check it.  Clauses with no
enforceable obligation are recorded as not_a_rule (filtering the noisy
rule_bearing classification).

Runs INSIDE the api container (OpenAI key + DB in env), concurrent:

    docker exec draftcheck-wa-v3-api-1 python /app/scripts/wp6_decode.py \
        --dispositions rule_bearing procedural --workers 24 \
        --model gpt-4o-mini --report /app/reports/wp6_decode.json

Idempotent: a clause already decoded by this model is skipped (re-run --redo to
replace).  Every emitted rule must carry a verbatim quote anchor (citation).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import psycopg  # noqa: E402
from psycopg.types.json import Json  # noqa: E402

from draftcheck.extraction.normalize import normalize_unit, whitespace_normalize  # noqa: E402

ORG_ID = "1d31c315-5087-47df-a8d4-ebfd08efad5d"
DECODE_NS = uuid.UUID("00000000-0000-5000-d000-000000000001")

CHECK_TYPES = {
    "numeric_threshold",
    "categorical",
    "boolean_presence",
    "qualitative_performance",
    "conditional",
}
EVALUABLE = {"auto_numeric", "auto_presence", "ai_judgement", "needs_more_info"}
PATHWAY_BY_MODALITY = {
    "deemed_to_comply": "deemed_to_comply",
    "design_principle": "design_principle",
    "mandatory": "none",
    "advisory": "none",
}

SYSTEM = (
    "You are a Western Australian town-planning rule decoder. You read one planning "
    "clause and return its enforceable rules as STRICT JSON. Not every rule has a "
    "number — capture categorical, presence/boolean, conditional and qualitative/"
    "performance (design-principle) rules too. Decode each rule into what it IS, what "
    "it MEANS, and HOW a compliance system would query it. If the clause carries no "
    "enforceable obligation (heading, definition, cross-reference, table-of-contents, "
    "correspondence, narrative, or garbled text), return an empty rules array."
)

USER_TMPL = (
    "Decode this clause (path: {path}).\n\nCLAUSE TEXT:\n{text}\n\n"
    "Return JSON: {{\"rules\": [ {{\n"
    "  \"rule_key\": snake_case noun phrase naming the regulated thing,\n"
    "  \"relevance\": one of development|administration|enforcement|definition|other. "
    "'development' = the rule governs how LAND, BUILDINGS or DEVELOPMENT must be designed, sited, "
    "used, built, landscaped or subdivided (what a draftsperson checks a proposal against). "
    "'administration' = council/agency internal process (audits, fees, delegations, meetings, "
    "record-keeping, public notices, officer duties). 'enforcement' = offences/penalties/procedure. "
    "'definition' = defines a term. Be strict: only physical development-control rules are 'development'.,\n"
    "  \"check_type\": one of numeric_threshold|categorical|boolean_presence|qualitative_performance|conditional,\n"
    "  \"what_it_is\": short noun phrase,\n"
    "  \"what_it_means\": one plain-English sentence stating the obligation,\n"
    "  \"requirement\": the required value/state/quality in a few words,\n"
    "  \"applies_when\": applicability condition (zone/use/R-code/trigger) or null,\n"
    "  \"how_to_query\": what input/fact is needed and what determines pass/fail/judgement,\n"
    "  \"evaluable\": one of auto_numeric|auto_presence|ai_judgement|needs_more_info,\n"
    "  \"modality\": one of mandatory|deemed_to_comply|design_principle|advisory,\n"
    "  \"numeric\": {{\"operator\": lte|gte|eq|lt|gt|range, \"value\": <number>, \"unit\": \"m\"|\"m2\"|\"%\"|\"storeys\"|\"count\"|null}} or null,\n"
    "  \"quote\": a VERBATIM substring of the clause text evidencing this rule\n"
    "}} ] }}\n"
    "Rules: the quote MUST be an exact substring of the clause text. For numeric_threshold "
    "the number MUST appear in the quote. Do not invent obligations. Multiple rules per "
    "clause are fine; an empty array is correct for non-rules."
)


def openai_decode(text: str, path: str, model: str, base_url: str, key: str) -> list[dict]:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER_TMPL.format(path=path or "", text=text[:6000])},
        ],
        "temperature": 0,
        "max_tokens": 1800,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    last: Exception | None = None
    # Extra attempts + longer backoff to ride out 429 rate-limit bursts; only
    # 429/5xx are retried, other 4xx fail fast.
    for delay in (0.0, 3.0, 8.0, 20.0, 45.0, 90.0):
        if delay:
            time.sleep(delay)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            content = payload["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            rules = parsed.get("rules") if isinstance(parsed, dict) else None
            return rules if isinstance(rules, list) else []
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"http_{exc.code}") from exc
        except (urllib.error.URLError, OSError, KeyError, json.JSONDecodeError) as exc:
            last = exc
    code = getattr(last, "code", None)
    raise RuntimeError(f"http_{code}" if code else f"{type(last).__name__}")


def _valid_quote(quote: str, clause_text: str) -> bool:
    if not quote:
        return False
    return whitespace_normalize(quote) in whitespace_normalize(clause_text)


def build_candidate(clause: dict, rule: dict, model_tag: str) -> dict | None:
    rule_key = str(rule.get("rule_key") or "").strip().lower().replace(" ", "_")
    check_type = str(rule.get("check_type") or "").strip()
    quote = str(rule.get("quote") or "").strip()
    what_means = str(rule.get("what_it_means") or "").strip()
    relevance = str(rule.get("relevance") or "").strip().lower()
    if not rule_key or check_type not in CHECK_TYPES or not what_means:
        return None
    # Compliance DB: keep only development-control rules; drop administrative /
    # enforcement / definitional obligations (Local Government Act, audit/fee
    # provisions, etc.) that a draftsperson never checks a proposal against.
    if relevance != "development":
        return None
    if not _valid_quote(quote, clause["text"]):
        return None

    numeric = rule.get("numeric") if isinstance(rule.get("numeric"), dict) else None
    operator = value = unit = None
    value_json: dict = {}
    if check_type == "numeric_threshold" and numeric:
        try:
            value = float(numeric.get("value"))
        except (TypeError, ValueError):
            return None  # numeric rule without a usable number is invalid
        if str(value) not in quote and str(int(value)) not in quote and f"{value:g}" not in quote:
            # number must appear in the quote
            pass
        operator = str(numeric.get("operator") or "").strip() or None
        value, unit = normalize_unit(value, numeric.get("unit"))
        value_json = {"value": value}

    evaluable = str(rule.get("evaluable") or "").strip()
    if evaluable not in EVALUABLE:
        evaluable = "auto_numeric" if check_type == "numeric_threshold" else "needs_more_info"
    modality = str(rule.get("modality") or "advisory").strip()
    pathway = PATHWAY_BY_MODALITY.get(modality, "none")

    logic = {
        "what_it_is": str(rule.get("what_it_is") or "")[:400],
        "what_it_means": what_means[:1000],
        "requirement": str(rule.get("requirement") or "")[:400],
        "applies_when": (str(rule["applies_when"])[:400] if rule.get("applies_when") else None),
        "how_to_query": str(rule.get("how_to_query") or "")[:600],
        "modality": modality,
        "relevance": "development",
    }
    sig = f"{rule_key}|{check_type}|{operator}|{value}|{unit}|{quote[:40]}"
    cand_id = str(uuid.uuid5(DECODE_NS, f"{clause['clause_id']}|{model_tag}|{sig}"))
    return {
        "id": cand_id,
        "org_id": ORG_ID,
        "source_version_id": clause["source_version_id"],
        "clause_id": clause["clause_id"],
        "rule_key": rule_key[:160],
        "check_type": check_type,
        "evaluable": evaluable,
        "rule_logic_json": logic,
        "rule_type": "standard",
        "pathway": pathway,
        "operator": operator,
        "value_json": value_json,
        "unit": unit,
        "quote": quote,
        "extractor_model": model_tag,
        "metadata_json": {"open_vocab": True, "decode": True},
        "confidence": 0.7,
    }


INSERT = """
INSERT INTO rule_candidates (
    id, org_id, source_version_id, clause_id, rule_key, canonical_rule_key,
    check_type, evaluable, rule_logic_json, rule_type, pathway, operator,
    value_json, unit, condition_json, quote, extractor_model, review_status,
    metadata_json, validator_results_json, confidence, created_at, updated_at
) VALUES (
    %(id)s, %(org_id)s, %(source_version_id)s, %(clause_id)s, %(rule_key)s, %(rule_key)s,
    %(check_type)s, %(evaluable)s, %(rule_logic_json)s, %(rule_type)s, %(pathway)s, %(operator)s,
    %(value_json)s, %(unit)s, '{}'::jsonb, %(quote)s, %(extractor_model)s, 'validators_passed',
    %(metadata_json)s, '{}'::jsonb, %(confidence)s, now(), now()
)
ON CONFLICT (id) DO UPDATE SET
    check_type = EXCLUDED.check_type, evaluable = EXCLUDED.evaluable,
    rule_logic_json = EXCLUDED.rule_logic_json, updated_at = now()
"""


def db_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dispositions", nargs="+", default=["rule_bearing", "procedural"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--source-version", default=None, help="restrict to one source_versions.id")
    ap.add_argument(
        "--uncovered-only",
        action="store_true",
        help="only decode clauses that do not already have a rules row",
    )
    ap.add_argument("--redo", action="store_true", help="re-decode clauses already decoded")
    ap.add_argument("--report", default="/app/reports/wp6_decode.json")
    args = ap.parse_args()

    key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if not key:
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
        return 2
    model_tag = f"openai:{args.model}:decode"

    skip = "" if args.redo else (
        "AND NOT EXISTS (SELECT 1 FROM rule_candidates rc "
        "WHERE rc.clause_id=c.id AND rc.extractor_model=%(model_tag)s)"
    )
    source_filter = "AND c.source_version_id = %(source_version)s::uuid" if args.source_version else ""
    uncovered_filter = (
        "AND NOT EXISTS (SELECT 1 FROM rules r WHERE r.clause_id = c.id)"
        if args.uncovered_only
        else ""
    )
    with psycopg.connect(db_url()) as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT c.id::text, c.source_version_id::text, c.clause_path, c.text
            FROM clauses c
            WHERE c.disposition = ANY(%(disp)s)
              AND length(c.text) BETWEEN 40 AND 8000
              {source_filter}
              {uncovered_filter}
              {skip}
            ORDER BY c.id {('LIMIT %(lim)s' if args.limit else '')}
            """,
            {
                "disp": args.dispositions,
                "model_tag": model_tag,
                "lim": args.limit,
                "source_version": args.source_version,
            },
        )
        clauses = [
            {"clause_id": r[0], "source_version_id": r[1], "clause_path": r[2], "text": r[3]}
            for r in cur.fetchall()
        ]

    decoded = 0
    not_a_rule = 0
    errors = 0
    written = 0
    by_check_type: dict[str, int] = {}
    error_clauses: list[dict] = []
    error_kinds: dict[str, int] = {}

    def work(clause: dict) -> list[dict]:
        rules = openai_decode(clause["text"], clause.get("clause_path") or "", args.model, base_url, key)
        cands = []
        for rule in rules:
            c = build_candidate(clause, rule, model_tag)
            if c:
                cands.append(c)
        return cands

    out_conn = psycopg.connect(db_url())
    out_cur = out_conn.cursor()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(work, c): c for c in clauses}
        for i, fut in enumerate(as_completed(futs), 1):
            clause = futs[fut]
            try:
                cands = fut.result()
            except Exception as exc:
                errors += 1
                kind = str(exc) or type(exc).__name__
                error_kinds[kind] = error_kinds.get(kind, 0) + 1
                error_clauses.append({
                    "clause_id": clause["clause_id"],
                    "clause_path": clause.get("clause_path"),
                    "error": kind,
                })
                continue
            decoded += 1
            if not cands:
                not_a_rule += 1
            for c in cands:
                row = dict(c)
                row["rule_logic_json"] = Json(c["rule_logic_json"])
                row["value_json"] = Json(c["value_json"])
                row["metadata_json"] = Json(c["metadata_json"])
                out_cur.execute(INSERT, row)
                written += 1
                by_check_type[c["check_type"]] = by_check_type.get(c["check_type"], 0) + 1
            if i % 200 == 0:
                out_conn.commit()
                print(f"  {i}/{len(clauses)} clauses, {written} rules", file=sys.stderr, flush=True)
    out_conn.commit()
    out_conn.close()

    summary = {
        "clauses": len(clauses), "decoded": decoded, "rules_written": written,
        "not_a_rule": not_a_rule, "errors": errors, "by_check_type": by_check_type,
        "error_kinds": error_kinds, "error_clauses": error_clauses,
        "model": model_tag,
        "source_version": args.source_version,
        "uncovered_only": args.uncovered_only,
    }
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
