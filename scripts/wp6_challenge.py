"""WP6 challenge round for single-model-family candidates.

Processes rule_candidates that already passed validators but were held because
all existing votes came from one model family. The challenge passes must come
from a different family. Dry-run is the default.

Run inside the api container:
    python /app/scripts/wp6_challenge.py --apply --report /app/reports/wp6_challenge.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Protocol

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psycopg  # noqa: E402
from psycopg.types.json import Json  # noqa: E402

from draftcheck.extraction.adjudication import model_family  # noqa: E402
from wp6_extract import (  # noqa: E402
    SYSTEM_PROMPT,
    Atom,
    build_endpoints,
    flush_spend_events,
    parse_atoms,
    parse_llm_json,
    promote_rule,
    prompt_for_clause,
    spend_totals,
    validate_atom,
)


class EndpointLike(Protocol):
    name: str
    model: str

    def complete(self, system: str, prompt: str) -> str: ...


def candidate_signature(row: dict[str, Any]) -> tuple[Any, ...]:
    applicability = row["condition_json"] or {}
    codes = tuple(sorted(str(c) for c in (applicability.get("density_codes") or [])))
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


def atom_signature(atom: Atom) -> tuple[Any, ...]:
    codes = tuple(sorted(str(c) for c in (atom.applicability.get("density_codes") or [])))
    return (
        atom.rule_key,
        atom.operator,
        round(float(atom.value), 4),
        atom.unit,
        codes,
        atom.pathway,
        atom.applicability.get("dwelling_type") or "any",
    )


def atom_from_candidate(row: dict[str, Any]) -> Atom:
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


def endpoint_family(endpoint: EndpointLike) -> str:
    return model_family(f"{endpoint.name}:{endpoint.model}")


def select_challenge_endpoints(
    endpoints: list[EndpointLike],
    *,
    stored_family: str,
    passes: int = 2,
) -> list[EndpointLike]:
    challengers = [endpoint for endpoint in endpoints if endpoint_family(endpoint) != stored_family]
    if not challengers:
        return []
    selected: list[EndpointLike] = []
    while len(selected) < passes:
        selected.append(challengers[len(selected) % len(challengers)])
    return selected


def fresh_votes_for_candidate(
    endpoints: list[EndpointLike],
    *,
    clause: dict[str, Any],
    candidate: dict[str, Any],
) -> tuple[int, list[str]]:
    prompt = prompt_for_clause(clause["clause_path"] or "?", clause["text"])
    signature = candidate_signature(candidate)
    errors: list[str] = []
    votes = 0
    for index, endpoint in enumerate(endpoints, start=1):
        try:
            raw = endpoint.complete(SYSTEM_PROMPT, prompt)
            atoms = parse_atoms(parse_llm_json(raw), index, f"{endpoint.name}:{endpoint.model}:challenge")
        except Exception as exc:
            errors.append(f"{endpoint.name}:{endpoint.model}: {exc}")
            continue
        for atom in atoms:
            validate_atom(atom, clause["text"])
            if atom.valid and atom_signature(atom) == signature:
                votes += 1
                break
    return votes, errors


def fetch_candidates(conn: psycopg.Connection, limit: int) -> list[dict[str, Any]]:
    sql = """
        SELECT rc.id, rc.source_version_id, rc.clause_id, rc.rule_key, rc.rule_type,
               rc.pathway, rc.operator, rc.value_json, rc.unit, rc.condition_json,
               rc.quote, rc.extractor_model, rc.metadata_json,
               c.clause_path, c.text
        FROM rule_candidates rc
        JOIN clauses c ON c.id = rc.clause_id
        WHERE rc.review_status = 'validators_passed'
          AND rc.metadata_json->>'pending_reason' = 'single_model_family'
          AND COALESCE((rc.metadata_json->>'challenge_done')::boolean, false) = false
        ORDER BY rc.clause_id, rc.created_at, rc.id
    """
    if limit:
        sql += " LIMIT %s"
        return conn.execute(sql, (limit,)).fetchall()
    return conn.execute(sql).fetchall()


def apply_candidate_result(
    conn: psycopg.Connection,
    *,
    candidate: dict[str, Any],
    votes: int,
    fresh_models: list[str],
) -> str:
    meta_update = {
        "challenge_done": True,
        "wp6_challenge": {
            "fresh_votes": votes,
            "fresh_passes": len(fresh_models),
            "fresh_models": fresh_models,
        },
    }
    if votes >= 2:
        atom = atom_from_candidate(candidate)
        promote_rule(
            conn,
            str(candidate["source_version_id"]),
            str(candidate["clause_id"]),
            str(candidate["id"]),
            atom,
            0.85,
        )
        conn.execute(
            """
            UPDATE rule_candidates
            SET review_status = 'auto_promoted', confidence = 0.85, auto_promoted_at = now(),
                metadata_json = metadata_json || %s::jsonb, updated_at = now()
            WHERE id = %s
            """,
            (Json(meta_update), candidate["id"]),
        )
        return "promoted"
    if votes == 1:
        conn.execute(
            """
            UPDATE rule_candidates
            SET metadata_json = metadata_json || %s::jsonb, updated_at = now()
            WHERE id = %s
            """,
            (Json(meta_update), candidate["id"]),
        )
        return "kept"
    conn.execute(
        """
        UPDATE rule_candidates
        SET review_status = 'rejected', metadata_json = metadata_json || %s::jsonb, updated_at = now()
        WHERE id = %s
        """,
        (Json(meta_update), candidate["id"]),
    )
    return "rejected"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write DB changes; default is dry run")
    parser.add_argument("--limit", type=int, default=0, help="candidate limit")
    parser.add_argument("--report", default="")
    args = parser.parse_args()

    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    endpoints, endpoint_escalations = build_endpoints()
    stats: dict[str, Any] = {
        "mode": "apply" if args.apply else "dry_run",
        "candidates": 0,
        "would_process": 0,
        "promoted": 0,
        "kept": 0,
        "rejected": 0,
        "skipped_no_other_family": 0,
        "skipped_malformed": 0,
        "llm_errors": [],
        "endpoint_escalations": endpoint_escalations,
        "available_models": [f"{endpoint.name}:{endpoint.model}" for endpoint in endpoints],
    }

    with psycopg.connect(dsn, row_factory=psycopg.rows.dict_row) as conn:
        candidates = fetch_candidates(conn, args.limit)
        for index, candidate in enumerate(candidates, start=1):
            stats["candidates"] += 1
            stored_family = model_family(candidate["extractor_model"] or "")
            challenge_endpoints = select_challenge_endpoints(endpoints, stored_family=stored_family)
            if not challenge_endpoints:
                stats["skipped_no_other_family"] += 1
                continue
            stats["would_process"] += 1
            clause = {"clause_path": candidate["clause_path"], "text": candidate["text"]}
            try:
                candidate_signature(candidate)
            except (TypeError, ValueError):
                stats["skipped_malformed"] += 1
                continue
            if not args.apply:
                continue
            print(f"[{index}/{len(candidates)}] {clause['clause_path']} {candidate['rule_key']}", flush=True)
            votes, errors = fresh_votes_for_candidate(challenge_endpoints, clause=clause, candidate=candidate)
            stats["llm_errors"].extend(errors)
            outcome = "kept"
            if votes >= 2:
                outcome = "promoted"
            elif votes == 0:
                outcome = "rejected"
            stats[outcome] += 1
            fresh_models = [f"{endpoint.name}:{endpoint.model}" for endpoint in challenge_endpoints]
            apply_candidate_result(
                conn,
                candidate=candidate,
                votes=votes,
                fresh_models=fresh_models,
            )
            conn.commit()
            flush_spend_events(conn, "wp6_challenge")

        if args.apply:
            flush_spend_events(conn, "wp6_challenge")
            stats["llm_spend"] = spend_totals()

    output = json.dumps(stats, indent=2, default=str)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
