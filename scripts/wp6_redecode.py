"""WP-E3 — faithfulness-first RE-DECODE of the in-scope corpus (Cockburn + state).

Root-cause fix for the ~18% unfaithful rate of the original gpt-4o-mini decode:
re-decode with a stronger model (default gpt-4o) and a prompt that refuses to
turn descriptions / headings / past-tense / definitions into obligations or to
invent thresholds. Scoped to Cockburn + WA STATE planning documents only
(excludes other regions and non-planning statutes via a source denylist), so the
DB is correct AND correctly scoped.

New candidates are written under extractor_model 'openai:<model>:decode2' so they
never collide with the original decode; promote/review/swap happen downstream.

    python /app/scripts/wp6_redecode.py --workers 16 --model gpt-4o \
        --report /app/reports/wp6_redecode.json
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
DECODE_NS = uuid.UUID("00000000-0000-5000-d000-000000000002")

CHECK_TYPES = {
    "numeric_threshold", "categorical", "boolean_presence",
    "qualitative_performance", "conditional",
}
EVALUABLE = {"auto_numeric", "auto_presence", "ai_judgement", "needs_more_info"}
PATHWAY_BY_MODALITY = {
    "deemed_to_comply": "deemed_to_comply", "design_principle": "design_principle",
    "mandatory": "none", "advisory": "none",
}

# Out-of-scope source documents (wrong region / non-planning law). Matched
# case-insensitively on source_documents.title.
DENY_SOURCE_SUBSTRINGS = [
    "strata titles", "community titles", "mining act", "transfer of land",
    "public works act", "health act", "health (miscellaneous", "liquor",
    "retirement villages", "leeuwin-naturaliste", "peel region",
    "greater bunbury", "bunbury",
]

SYSTEM = (
    "You are a meticulous Western Australian town-planning rule extractor for a CITE-OR-REFUSE "
    "compliance tool used on City of Cockburn and WA state planning documents. Your ONE rule: never "
    "assert anything the source text does not literally say. You return STRICT JSON only."
)

USER_TMPL = (
    "Extract the enforceable DEVELOPMENT-CONTROL rules from this planning clause (path: {path}).\n\n"
    "CLAUSE TEXT:\n\"\"\"{text}\"\"\"\n\n"
    "CRITICAL FAITHFULNESS RULES — a wrong rule is worse than no rule:\n"
    "- Extract a rule ONLY if the clause imposes a genuine obligation/standard/prohibition a "
    "development PROPOSAL is assessed against.\n"
    "- The 'what_it_means' must be SUPPORTED by the quoted text. Do NOT add, reverse, or overstate any "
    "obligation, threshold, number, condition, exception or consequence that is not in the text.\n"
    "- Return NO rule (empty array) when the clause is: a heading/title; a definition; a cross-"
    "reference; narrative/background; an objective/aspiration ('to provide...', 'should be "
    "considered'); a DESCRIPTION of what a plan/study does ('the Structure Plan provides for...', "
    "'footpaths are proposed...'); past tense ('was adopted', 'were completed'); or a duty binding an "
    "AUTHORITY/Commission/the scheme document itself ('the Commission must consider...', 'the scheme "
    "must set out...'). These DESCRIBE or administer — they do not impose a development standard.\n"
    "- Put scoping (zone / R-code / use / trigger) in 'applies_when', drawn from the clause.\n"
    "- For numeric_threshold the number MUST appear in the quote.\n\n"
    "Return JSON: {{\"rules\": [ {{\n"
    "  \"rule_key\": snake_case noun phrase naming the regulated thing,\n"
    "  \"relevance\": development|administration|enforcement|definition|other (ONLY physical "
    "development-control rules are 'development'),\n"
    "  \"check_type\": numeric_threshold|categorical|boolean_presence|qualitative_performance|conditional,\n"
    "  \"what_it_is\": short noun phrase,\n"
    "  \"what_it_means\": one plain-English sentence stating the obligation, SUPPORTED BY THE QUOTE,\n"
    "  \"requirement\": the required value/state/quality in a few words,\n"
    "  \"applies_when\": applicability condition (zone/use/R-code/trigger) or null,\n"
    "  \"how_to_query\": what input/fact is needed and what determines pass/fail/judgement,\n"
    "  \"evaluable\": auto_numeric|auto_presence|ai_judgement|needs_more_info,\n"
    "  \"modality\": mandatory|deemed_to_comply|design_principle|advisory,\n"
    "  \"numeric\": {{\"operator\": lte|gte|eq|lt|gt|range, \"value\": <number>, \"unit\": \"m\"|\"m2\"|\"%\"|\"storeys\"|\"count\"|null}} or null,\n"
    "  \"quote\": a VERBATIM substring of the clause text that CONTAINS the obligation\n"
    "}} ] }}\n"
    "An empty array is the correct, expected answer for non-rules. Do not force a rule."
)


def openai_decode(text: str, path: str, model: str, base_url: str, key: str) -> list[dict]:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER_TMPL.format(path=path or "", text=text[:6000])},
        ],
        "temperature": 0, "max_tokens": 1800,
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
    return bool(quote) and whitespace_normalize(quote) in whitespace_normalize(clause_text)


def build_candidate(clause: dict, rule: dict, model_tag: str) -> dict | None:
    rule_key = str(rule.get("rule_key") or "").strip().lower().replace(" ", "_")
    check_type = str(rule.get("check_type") or "").strip()
    quote = str(rule.get("quote") or "").strip()
    what_means = str(rule.get("what_it_means") or "").strip()
    relevance = str(rule.get("relevance") or "").strip().lower()
    if not rule_key or check_type not in CHECK_TYPES or not what_means:
        return None
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
            return None
        operator = str(numeric.get("operator") or "").strip() or None
        unit = normalize_unit(numeric.get("unit"))
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
        "modality": modality, "relevance": "development",
    }
    sig = f"{rule_key}|{check_type}|{operator}|{value}|{unit}|{quote[:40]}"
    cand_id = str(uuid.uuid5(DECODE_NS, f"{clause['clause_id']}|{model_tag}|{sig}"))
    return {
        "id": cand_id, "org_id": ORG_ID, "source_version_id": clause["source_version_id"],
        "clause_id": clause["clause_id"], "rule_key": rule_key[:160], "check_type": check_type,
        "evaluable": evaluable, "rule_logic_json": logic, "rule_type": "standard",
        "pathway": pathway, "operator": operator, "value_json": value_json, "unit": unit,
        "quote": quote, "extractor_model": model_tag,
        "metadata_json": {"open_vocab": True, "decode2": True}, "confidence": 0.8,
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
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--model", default="gpt-4o")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--report", default="/app/reports/wp6_redecode.json")
    args = ap.parse_args()

    key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if not key:
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
        return 2
    model_tag = f"openai:{args.model}:decode2"

    deny = " ".join(
        f"AND lower(coalesce(sd.title,'')) NOT LIKE '%%{s}%%'" for s in DENY_SOURCE_SUBSTRINGS
    )
    skip = "" if args.redo else (
        "AND NOT EXISTS (SELECT 1 FROM rule_candidates rc "
        "WHERE rc.clause_id=c.id AND rc.extractor_model=%(model_tag)s)"
    )
    with psycopg.connect(db_url()) as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT c.id::text, c.source_version_id::text, c.clause_path, c.text
            FROM clauses c
            JOIN source_versions sv ON c.source_version_id = sv.id
            JOIN source_documents sd ON sv.source_id = sd.id
            WHERE c.disposition = ANY(%(disp)s)
              AND length(c.text) BETWEEN 40 AND 8000 {deny} {skip}
            ORDER BY {('random()' if args.limit else 'c.id')} {('LIMIT %(lim)s' if args.limit else '')}
            """,
            {"disp": args.dispositions, "model_tag": model_tag, "lim": args.limit},
        )
        clauses = [
            {"clause_id": r[0], "source_version_id": r[1], "clause_path": r[2], "text": r[3]}
            for r in cur.fetchall()
        ]

    decoded = not_a_rule = errors = written = 0
    by_check_type: dict[str, int] = {}

    def work(clause: dict) -> list[dict]:
        rules = openai_decode(clause["text"], clause.get("clause_path") or "", args.model, base_url, key)
        return [c for c in (build_candidate(clause, r, model_tag) for r in rules) if c]

    out_conn = psycopg.connect(db_url())
    out_cur = out_conn.cursor()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(work, c): c for c in clauses}
        for i, fut in enumerate(as_completed(futs), 1):
            try:
                cands = fut.result()
            except Exception:
                errors += 1
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
        "wp": "redecode", "clauses": len(clauses), "decoded": decoded, "rules_written": written,
        "not_a_rule": not_a_rule, "errors": errors, "by_check_type": by_check_type, "model": model_tag,
    }
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
