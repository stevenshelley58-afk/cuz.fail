"""Apply Claude-subagent decode output as rule_candidates (wp6_decode semantics).

Input JSON per batch:
    {"model_tag": "claude:haiku-4.5:decode",
     "decoded": [{"clause_id": "...", "rules": [{rule_key, relevance, check_type,
                  what_it_is, what_it_means, requirement, applies_when,
                  how_to_query, evaluable, modality,
                  numeric: {operator, value, unit}|null, quote}, ...]}, ...]}

Validators (all mechanical, mirror wp6_decode.build_candidate):
- relevance must be 'development';
- check_type in the allowed set; what_it_means non-empty;
- quote must be a VERBATIM substring of the clause text (whitespace-normalised);
- numeric_threshold rules must carry a parseable value and the value must
  appear in the quote.
Candidates are inserted idempotently (uuid5 over clause|model|signature) with
review_status='validators_passed', same as the OpenAI decode path.

    python /app/scripts/apply_decoded.py --json /tmp/decoded_000.json [--apply]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid

sys.path.insert(0, "/app/src")

import psycopg  # noqa: E402
from psycopg.types.json import Json  # noqa: E402

from draftcheck.extraction.normalize import normalize_unit, whitespace_normalize  # noqa: E402

ORG_ID = "1d31c315-5087-47df-a8d4-ebfd08efad5d"
DECODE_NS = uuid.UUID("00000000-0000-5000-d000-000000000001")
CHECK_TYPES = {"numeric_threshold", "categorical", "boolean_presence",
               "qualitative_performance", "conditional"}
EVALUABLE = {"auto_numeric", "auto_presence", "ai_judgement", "needs_more_info"}
PATHWAY_BY_MODALITY = {"deemed_to_comply": "deemed_to_comply",
                       "design_principle": "design_principle",
                       "mandatory": "none", "advisory": "none"}

INSERT = """
INSERT INTO rule_candidates (
    id, org_id, source_version_id, clause_id, rule_key, canonical_rule_key,
    check_type, evaluable, rule_logic_json, rule_type, pathway, operator,
    value_json, unit, condition_json, quote, extractor_model, review_status,
    metadata_json, validator_results_json, confidence, created_at, updated_at
) VALUES (
    %(id)s, %(org_id)s, %(source_version_id)s, %(clause_id)s, %(rule_key)s, %(rule_key)s,
    %(check_type)s, %(evaluable)s, %(rule_logic_json)s, 'standard', %(pathway)s, %(operator)s,
    %(value_json)s, %(unit)s, '{}'::jsonb, %(quote)s, %(extractor_model)s, 'validators_passed',
    %(metadata_json)s, '{}'::jsonb, 0.7, now(), now()
)
ON CONFLICT (id) DO NOTHING
"""


def db_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


def build_candidate(clause_id: str, sv_id: str, clause_text: str, rule: dict, tag: str):
    rule_key = str(rule.get("rule_key") or "").strip().lower().replace(" ", "_")
    check_type = str(rule.get("check_type") or "").strip()
    quote = str(rule.get("quote") or "").strip()
    what_means = str(rule.get("what_it_means") or "").strip()
    if str(rule.get("relevance") or "").strip().lower() != "development":
        return None, "relevance"
    if not rule_key or check_type not in CHECK_TYPES or not what_means:
        return None, "shape"
    if not quote or whitespace_normalize(quote) not in whitespace_normalize(clause_text):
        return None, "quote_not_verbatim"

    numeric = rule.get("numeric") if isinstance(rule.get("numeric"), dict) else None
    operator = value = unit = None
    value_json: dict = {}
    if check_type == "numeric_threshold":
        if not numeric:
            return None, "numeric_missing"
        try:
            value = float(numeric.get("value"))
        except (TypeError, ValueError):
            return None, "numeric_unparseable"
        vt = f"{value:g}"
        if vt not in quote and str(int(value)) not in quote and str(value) not in quote:
            return None, "number_not_in_quote"
        operator = str(numeric.get("operator") or "").strip() or None
        value, unit = normalize_unit(value, numeric.get("unit"))
        value_json = {"value": value}

    evaluable = str(rule.get("evaluable") or "").strip()
    if evaluable not in EVALUABLE:
        evaluable = "auto_numeric" if check_type == "numeric_threshold" else "needs_more_info"
    modality = str(rule.get("modality") or "advisory").strip()
    logic = {
        "what_it_is": str(rule.get("what_it_is") or "")[:400],
        "what_it_means": what_means[:1000],
        "requirement": str(rule.get("requirement") or "")[:400],
        "applies_when": (str(rule["applies_when"])[:400] if rule.get("applies_when") else None),
        "how_to_query": str(rule.get("how_to_query") or "")[:600],
        "modality": modality, "relevance": "development",
    }
    sig = f"{rule_key}|{check_type}|{operator}|{value}|{unit}|{quote[:40]}"
    return {
        "id": str(uuid.uuid5(DECODE_NS, f"{clause_id}|{tag}|{sig}")),
        "org_id": ORG_ID, "source_version_id": sv_id, "clause_id": clause_id,
        "rule_key": rule_key[:160], "check_type": check_type, "evaluable": evaluable,
        "rule_logic_json": Json(logic), "pathway": PATHWAY_BY_MODALITY.get(modality, "none"),
        "operator": operator, "value_json": Json(value_json), "unit": unit,
        "quote": quote, "extractor_model": tag,
        "metadata_json": Json({"open_vocab": True, "decode": True, "claude_decode": True}),
    }, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    with open(args.json, encoding="utf-8") as fh:
        data = json.load(fh)
    tag = str(data.get("model_tag") or "claude:haiku-4.5:decode")

    written = 0
    dropped: dict[str, int] = {}
    with psycopg.connect(db_url()) as conn:
        cur = conn.cursor()
        for entry in data.get("decoded") or []:
            cid = str(entry.get("clause_id") or "")
            cur.execute("SELECT source_version_id::text, text FROM clauses WHERE id = %s", (cid,))
            row = cur.fetchone()
            if row is None:
                dropped["unknown_clause"] = dropped.get("unknown_clause", 0) + 1
                continue
            sv_id, clause_text = row
            for rule in entry.get("rules") or []:
                cand, why = build_candidate(cid, sv_id, clause_text, rule, tag)
                if cand is None:
                    dropped[why] = dropped.get(why, 0) + 1
                    continue
                written += 1
                if args.apply:
                    cur.execute(INSERT, cand)
        if args.apply:
            conn.commit()
    print(json.dumps({"file": os.path.basename(args.json), "apply": args.apply,
                      "candidates_written": written, "dropped": dropped}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
