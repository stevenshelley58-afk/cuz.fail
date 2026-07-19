"""WP6 — apply Kimi family-2 vote batches (no LLM calls; deterministic applier).

Kimi Code worker sessions extract rule atoms blind (they never see the
existing MiniMax/OpenAI votes) and write batch JSON files. This script is the
ONLY write path for those votes: it re-fetches the clause text from the DB
(never trusting the batch file), re-runs the universal deterministic
validators, and inserts rule_candidates rows with
``extractor_model='kimi:kimi-k2.7-code'`` and ``extraction_pass=4`` so the
family-aware adjudicator (scripts/wp6_adjudicate.py) can promote cores that
now have two independent model families.

Governance notes:
- Promotion is NEVER done here. Only the deterministic adjudicator promotes.
- Every inserted candidate carries a spend_events row (provider 'kimi',
  cost 0 — subscription runtime, tokens estimated) so the accounting chain
  required by docs/DB_BUILDOUT_KIMI_SWARM_PLAN.md §8 stays intact.
- Idempotent: a clause that already has a kimi pass-4 candidate is skipped
  wholesale, so re-applying a batch is safe.

Run inside the api container:
    docker compose exec -T api python scripts/wp6_kimi_vote_apply.py \
        --input /app/reports/kimi_votes/batch_001.json \
        --report /app/reports/kimi_votes/batch_001.apply.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from typing import Any

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import psycopg  # noqa: E402
from psycopg.types.json import Json  # noqa: E402

from draftcheck.extraction.validators import run_all_validators  # noqa: E402
from draftcheck.extraction.vocabulary import OPERATORS  # noqa: E402

ORG_ID = "1d31c315-5087-47df-a8d4-ebfd08efad5d"  # DraftCheck WA (same as WP6)
KIMI_MODEL = "kimi:kimi-k2.7-code"
KIMI_PASS = 4
RULE_TYPES = {"standard", "exception", "deemed_to_comply", "design_principle"}
PATHWAYS = {"deemed_to_comply", "design_principle", "none"}
PROMPT_TAG = "kimi-family2-vote-v1"


def dsn_from_env() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


def load_clause(conn: psycopg.Connection, clause_id: str) -> dict | None:
    row = conn.execute(
        """
        SELECT c.id, c.source_version_id, c.source_chunk_id, c.text, c.disposition
        FROM clauses c WHERE c.id = %s
        """,
        (clause_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": str(row[0]),
        "source_version_id": str(row[1]),
        "source_chunk_id": str(row[2]) if row[2] else None,
        "text": row[3] or "",
        "disposition": row[4] or "rule_bearing",
    }


def already_voted(conn: psycopg.Connection, clause_id: str) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM rule_candidates
        WHERE clause_id = %s AND extraction_pass = %s AND extractor_model = %s
        LIMIT 1
        """,
        (clause_id, KIMI_PASS, KIMI_MODEL),
    ).fetchone()
    return row is not None


def normalise_atom(atom: dict) -> dict | None:
    """Coerce one worker atom into the candidate shape; None if structurally unusable."""
    try:
        rule_key = str(atom.get("rule_key") or "").strip()
        operator = str(atom.get("operator") or "").strip()
        raw_value = atom.get("value")
        if raw_value is None:
            return None
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    if not rule_key or operator not in OPERATORS:
        return None
    rule_type = str(atom.get("rule_type") or "standard").strip()
    if rule_type not in RULE_TYPES:
        rule_type = "standard"
    pathway = str(atom.get("pathway") or "none").strip()
    if pathway not in PATHWAYS:
        pathway = "none"
    unit = atom.get("unit")
    unit = str(unit).strip() if unit is not None else None
    if unit == "":
        unit = None
    applicability = atom.get("applicability") or {}
    if not isinstance(applicability, dict):
        applicability = {}
    density_codes = applicability.get("density_codes") or []
    if not isinstance(density_codes, list):
        density_codes = []
    condition = {
        "density_codes": [str(c) for c in density_codes],
        "dwelling_type": str(applicability.get("dwelling_type") or "any"),
        "condition": str(applicability.get("condition") or ""),
    }
    return {
        "rule_key": rule_key,
        "rule_type": rule_type,
        "pathway": pathway,
        "operator": operator,
        "value": value,
        "unit": unit,
        "condition": condition,
        "quote": str(atom.get("quote") or ""),
    }


def insert_candidate(
    conn: psycopg.Connection,
    clause: dict,
    atom: dict,
    group_id: str,
    review_status: str,
    validators: dict,
    worker: str,
) -> str:
    cid = str(uuid.uuid4())
    prompt_hash = hashlib.sha256(f"{PROMPT_TAG}:{clause['id']}".encode()).hexdigest()
    conn.execute(
        """
        INSERT INTO rule_candidates (id, org_id, source_version_id, clause_id, source_chunk_id,
            rule_key, rule_type, pathway, operator, value_json, unit, condition_json, quote,
            extractor_model, skill_version_id, prompt_hash, confidence, review_status,
            metadata_json, extraction_group_id, extraction_pass, validator_results_json,
            created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s, %s,
                %s, %s, %s, %s, now(), now())
        """,
        (
            cid,
            ORG_ID,
            clause["source_version_id"],
            clause["id"],
            clause["source_chunk_id"],
            atom["rule_key"],
            atom["rule_type"],
            atom["pathway"],
            atom["operator"],
            Json({"value": atom["value"]}),
            atom["unit"],
            Json(atom["condition"]),
            atom["quote"],
            KIMI_MODEL,
            prompt_hash,
            None,
            review_status,
            Json({"wp6": True, "kimi_family_vote": True, "worker": worker}),
            group_id,
            KIMI_PASS,
            Json(validators),
        ),
    )
    return cid


def record_spend(conn: psycopg.Connection, clause: dict, atom_count: int, worker: str) -> None:
    est_in = max(len(clause["text"]) // 4, 1)
    est_out = atom_count * 60
    conn.execute(
        """
        INSERT INTO spend_events (id, org_id, job_trace_id, provider, model, event_type,
            input_tokens, output_tokens, total_tokens, cost_usd, currency, metadata_json, created_at)
        VALUES (gen_random_uuid(), %s, NULL, 'kimi', %s, 'wp6_kimi_vote', %s, %s, %s, 0, 'USD',
                %s, now())
        """,
        (
            ORG_ID,
            KIMI_MODEL,
            est_in,
            est_out,
            est_in + est_out,
            Json({"worker": worker, "clause_id": clause["id"], "cost_note": "subscription; no marginal API cost"}),
        ),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="batch JSON from a Kimi worker")
    ap.add_argument("--report", default="")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as fh:
        batch = json.load(fh)
    worker = str(batch.get("worker") or "unknown")
    clauses = batch.get("clauses") or []

    stats: dict[str, Any] = {
        "worker": worker,
        "clauses_in_batch": len(clauses),
        "clauses_applied": 0,
        "clauses_skipped_already_voted": 0,
        "clauses_missing": 0,
        "atoms_inserted": 0,
        "atoms_validators_passed": 0,
        "atoms_validator_failed": 0,
        "atoms_structurally_rejected": 0,
        "no_rules_clauses": 0,
        "errors": [],
    }

    with psycopg.connect(dsn_from_env()) as conn:
        for item in clauses:
            clause_id = str(item.get("clause_id") or "")
            if not clause_id:
                stats["clauses_missing"] += 1
                continue
            clause = load_clause(conn, clause_id)
            if clause is None:
                stats["clauses_missing"] += 1
                stats["errors"].append(f"clause not found: {clause_id}")
                continue
            if already_voted(conn, clause_id):
                stats["clauses_skipped_already_voted"] += 1
                continue
            group_id = str(uuid.uuid4())
            atoms = item.get("atoms") or []
            if not atoms and item.get("no_rules"):
                stats["no_rules_clauses"] += 1
            inserted = 0
            for raw in atoms:
                atom = normalise_atom(raw)
                if atom is None:
                    stats["atoms_structurally_rejected"] += 1
                    continue
                validators = run_all_validators(
                    quote=atom["quote"],
                    clause_text=clause["text"],
                    disposition=clause["disposition"],
                    value_json={"value": atom["value"]},
                    unit=atom["unit"],
                    rule_key=atom["rule_key"],
                )
                ok = all(v["pass"] for v in validators.values())
                review_status = "validators_passed" if ok else "validator_failed"
                insert_candidate(conn, clause, atom, group_id, review_status, validators, worker)
                inserted += 1
                stats["atoms_validators_passed" if ok else "atoms_validator_failed"] += 1
            stats["atoms_inserted"] += inserted
            stats["clauses_applied"] += 1
            record_spend(conn, clause, inserted, worker)
        conn.commit()

    out = json.dumps(stats, indent=2, default=str)
    if args.report:
        os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
