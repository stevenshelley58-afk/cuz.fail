"""WP9 — re-adjudicate WP6 pending_review rule candidates.

WP6 left candidates at review_status='pending_review' when the 3-pass blind
ensemble had no majority (1/3 votes) or a failed challenge round (2/3 with
dissent upheld). This harness gives every pending signature a fresh, fully
automated second adjudication:

  For each clause with pending candidates:
    1. Run 2 fresh blind extraction passes (temperature 0, same validators).
    2. For each pending candidate signature:
         - reproduced by BOTH fresh passes  -> promote (confidence 0.85)
         - reproduced by ONE fresh pass     -> stays pending_review
         - reproduced by NEITHER            -> review_status='rejected'
           (original extraction not reproducible; never silently deleted)

Promotion uses the same promote_rule() path as WP6 (lifecycle 'approved',
rule_clause_links row, ON CONFLICT upsert), so the doctrine of a single
insertion path per harness is preserved.

Run inside the api container:
    python /app/scripts/wp9_pending_adjudicate.py [--limit N] [--workers K] \
        --report /app/reports/wp9_adjudication.json
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

from wp6_extract import (  # noqa: E402
    SYSTEM_PROMPT,
    Atom,
    build_endpoints,
    parse_atoms,
    parse_llm_json,
    promote_rule,
    prompt_for_clause,
    validate_atom,
)


def candidate_signature(row: dict) -> tuple:
    applicability = row["condition_json"] or {}
    codes = tuple(sorted(applicability.get("density_codes") or []))
    value = (row["value_json"] or {}).get("value")
    return (
        row["rule_key"],
        row["operator"],
        round(float(value), 4) if value is not None else None,
        row["unit"],
        codes,
        row["pathway"],
        applicability.get("dwelling_type") or "any",
    )


def atom_from_candidate(row: dict) -> Atom:
    applicability = row["condition_json"] or {}
    return Atom(
        rule_key=row["rule_key"],
        rule_type=row["rule_type"],
        pathway=row["pathway"],
        operator=row["operator"],
        value=float((row["value_json"] or {}).get("value")),
        unit=row["unit"],
        applicability=applicability,
        quote=row["quote"],
        extraction_pass=0,
        model=row["extractor_model"] or "wp6",
    )


def adjudicate_clause(
    conn: psycopg.Connection,
    plain_conn: psycopg.Connection,
    endpoints: list,
    clause: dict,
    candidates: list[dict],
    stats: dict,
) -> None:
    prompt = prompt_for_clause(clause["clause_path"] or "?", clause["text"])
    fresh_sigs: list[set] = []
    for i, ep in enumerate(endpoints, start=1):
        try:
            raw = ep.complete(SYSTEM_PROMPT, prompt)
        except RuntimeError as exc:
            stats["llm_errors"].append(f"{clause['clause_path']} pass{i}: {exc}")
            fresh_sigs.append(set())
            continue
        atoms = parse_atoms(parse_llm_json(raw), i, f"{ep.name}:{ep.model}")
        valid = []
        for atom in atoms:
            validate_atom(atom, clause["text"])
            if atom.valid:
                valid.append(atom)
        fresh_sigs.append({a.signature() for a in valid})

    for cand in candidates:
        try:
            sig = candidate_signature(cand)
        except (TypeError, ValueError):
            stats["skipped_malformed"] += 1
            continue
        votes = sum(1 for s in fresh_sigs if sig in s)
        meta_update = {
            "wp9_adjudication": {"fresh_votes": votes, "fresh_passes": len(fresh_sigs)}
        }
        if votes >= 2:
            atom = atom_from_candidate(cand)
            # promote_rule indexes rows positionally — use the tuple-row connection.
            promote_rule(plain_conn, str(cand["source_version_id"]), str(cand["clause_id"]),
                         str(cand["id"]), atom, 0.85)
            plain_conn.commit()
            conn.execute(
                "UPDATE rule_candidates SET review_status='auto_promoted', confidence=0.85, "
                "auto_promoted_at=now(), metadata_json = metadata_json || %s::jsonb, updated_at=now() "
                "WHERE id = %s",
                (Json(meta_update), cand["id"]),
            )
            stats["promoted"] += 1
        elif votes == 1:
            conn.execute(
                "UPDATE rule_candidates SET metadata_json = metadata_json || %s::jsonb, "
                "updated_at=now() WHERE id = %s",
                (Json(meta_update), cand["id"]),
            )
            stats["still_pending"] += 1
        else:
            conn.execute(
                "UPDATE rule_candidates SET review_status='rejected', "
                "metadata_json = metadata_json || %s::jsonb, updated_at=now() WHERE id = %s",
                (Json(meta_update), cand["id"]),
            )
            stats["rejected"] += 1
    conn.commit()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="cap clauses processed")
    ap.add_argument("--report", default="")
    args = ap.parse_args()

    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    endpoints, escalations = build_endpoints()
    # Two fresh passes: first and last endpoint (different families when available).
    endpoints = [endpoints[0], endpoints[-1]] if len(endpoints) > 1 else endpoints

    stats: dict[str, Any] = {
        "clauses": 0, "candidates": 0, "promoted": 0, "still_pending": 0,
        "rejected": 0, "skipped_malformed": 0, "llm_errors": [],
        "escalations": escalations,
        "fresh_models": [f"{e.name}:{e.model}" for e in endpoints],
    }

    with psycopg.connect(dsn, row_factory=psycopg.rows.dict_row) as conn, \
            psycopg.connect(dsn) as plain_conn:
        rows = conn.execute(
            """
            SELECT rc.id, rc.source_version_id, rc.clause_id, rc.rule_key, rc.rule_type,
                   rc.pathway, rc.operator, rc.value_json, rc.unit, rc.condition_json,
                   rc.quote, rc.extractor_model,
                   c.clause_path, c.text
            FROM rule_candidates rc
            JOIN clauses c ON c.id = rc.clause_id
            WHERE rc.review_status = 'pending_review'
              AND rc.metadata_json->>'wp6' = 'true'
            ORDER BY rc.clause_id
            """
        ).fetchall()

        by_clause: dict[str, list[dict]] = {}
        for r in rows:
            by_clause.setdefault(str(r["clause_id"]), []).append(r)
        clause_items = list(by_clause.items())
        if args.limit:
            clause_items = clause_items[: args.limit]

        total = len(clause_items)
        for n, (_clause_id, cands) in enumerate(clause_items, start=1):
            clause = {"clause_path": cands[0]["clause_path"], "text": cands[0]["text"]}
            stats["clauses"] += 1
            stats["candidates"] += len(cands)
            print(f"[{n}/{total}] {clause['clause_path']} ({len(cands)} candidates)", flush=True)
            adjudicate_clause(conn, plain_conn, endpoints, clause, cands, stats)

    out = json.dumps(stats, indent=2, default=str)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(out)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
