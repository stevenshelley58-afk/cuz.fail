"""Apply Claude-corrector verdicts to rules (correction pass, subagent flavour).

Input JSON (one file per corrected batch):
    {"model_tag": "claude:haiku-4.5:correct",
     "verdicts": [{"id": "<rule id>", "action": "keep"|"reject",
                   "what_it_means": "...", "requirement": "...",
                   "applies_when": "..."|null, "modality": "...",
                   "reason": "<=15 words"}, ...]}

Semantics mirror wp6_correct.py: keep -> approved with corrected logic;
reject -> rejected. Both stamp metadata_json.correct_model so the rule never
re-enters a correction queue; parked markers are cleared.

    python /app/scripts/apply_corrections.py --json /tmp/verdicts_000.json [--apply]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, "/app/src")

import psycopg  # noqa: E402
from psycopg.types.json import Json  # noqa: E402

ALLOWED_MODALITY = {"mandatory", "deemed_to_comply", "design_principle", "advisory"}

_NUM_WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
              "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}


def _numbers_in(text: str) -> set[str]:
    import re
    out = {m.group(0) for m in re.finditer(r"\d+(?:\.\d+)?", text or "")}
    for w, d in _NUM_WORDS.items():
        if re.search(rf"\b{w}\b", (text or "").lower()):
            out.add(d)
    return out


def numeral_gate(claim: str, quote: str) -> set[str]:
    """Return numbers asserted in the claim that do NOT appear in the quote."""
    claim_nums = _numbers_in(claim)
    quote_nums = _numbers_in(quote)
    return {n for n in claim_nums if n not in quote_nums}

KEEP_SQL = """
UPDATE rules SET updated_at=now(), lifecycle_status='approved',
  rule_logic_json = rule_logic_json || %(logic)s::jsonb,
  metadata_json = (coalesce(metadata_json,'{}'::jsonb) - 'parked') || %(meta)s::jsonb
WHERE id = %(id)s AND extractor_model LIKE '%%decode'
"""

REJECT_SQL = """
UPDATE rules SET updated_at=now(), lifecycle_status='rejected',
  metadata_json = (coalesce(metadata_json,'{}'::jsonb) - 'parked') || %(meta)s::jsonb
WHERE id = %(id)s AND extractor_model LIKE '%%decode'
"""


def db_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    with open(args.json, encoding="utf-8") as fh:
        data = json.load(fh)
    tag = str(data.get("model_tag") or "claude:haiku-4.5:correct")
    verdicts = data.get("verdicts") or []

    kept = rejected = invalid = gated = 0
    gated_ids: list[dict] = []
    with psycopg.connect(db_url()) as conn:
        cur = conn.cursor()
        for v in verdicts:
            rid = str(v.get("id") or "")
            action = str(v.get("action") or "").strip().lower()
            meta = {"correct_model": tag, "correct_action": action,
                    "correct_reason": str(v.get("reason") or "")[:120]}
            if action == "reject":
                rejected += 1
                if args.apply:
                    cur.execute(REJECT_SQL, {"id": rid, "meta": Json(meta)})
            elif action == "keep":
                what = str(v.get("what_it_means") or "").strip()
                modality = str(v.get("modality") or "advisory").strip()
                if not rid or not what or modality not in ALLOWED_MODALITY:
                    invalid += 1
                    continue
                # Numeral gate: the corrected claim must not assert numbers
                # absent from the verbatim quote (fetch quote for comparison).
                cur.execute("SELECT quote FROM rules WHERE id = %s", (rid,))
                row = cur.fetchone()
                quote = row[0] if row else ""
                bad = numeral_gate(what + " " + str(v.get("requirement") or ""), quote)
                if bad:
                    gated += 1
                    gated_ids.append({"id": rid, "numbers_not_in_quote": sorted(bad)})
                    continue
                logic = {"what_it_means": what[:1000],
                         "requirement": str(v.get("requirement") or "")[:400],
                         "applies_when": (str(v["applies_when"])[:400]
                                          if v.get("applies_when") else None),
                         "modality": modality}
                kept += 1
                if args.apply:
                    cur.execute(KEEP_SQL, {"id": rid, "logic": Json(logic), "meta": Json(meta)})
            else:
                invalid += 1
        if args.apply:
            conn.commit()
    print(json.dumps({"file": os.path.basename(args.json), "apply": args.apply,
                      "kept": kept, "rejected": rejected, "invalid": invalid,
                      "numeral_gated": gated, "gated": gated_ids}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
