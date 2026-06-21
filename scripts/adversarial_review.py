"""WP8 adversarial review runner.

This is the DB-coordinated entrypoint for Phase 5. The first implementation is
deliberately deterministic: it opens findings for concrete defects the database
can prove, emits closure reports, and provides a queue for later frontier-model
defense/judge passes.

Run inside the api container:
    python /app/scripts/adversarial_review.py attack --round 1 --role gap_hunter --apply
    python /app/scripts/adversarial_review.py report --report /app/reports/adversarial_closure.json
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

DEFAULT_REPORT = Path(__file__).resolve().parent.parent / "reports" / "adversarial_closure.json"
NS = uuid.UUID("0b8d8b6f-8ee3-4f7d-a98f-f9a3b3cdd7d8")

ATTACKER_ROLES = {"re_extractor", "prosecutor", "gap_hunter", "conflict_prosecutor"}
ALL_ROLES = ATTACKER_ROLES | {"defense", "judge"}


@dataclass(frozen=True)
class Finding:
    id: str
    round: int
    agent_role: str
    target: str
    claim: str
    evidence_quote: str | None
    severity: str
    status: str = "open"


def deterministic_id(*parts: object) -> str:
    return str(uuid.uuid5(NS, "|".join(str(part) for part in parts)))


def database_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql+psycopg://")


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def finding_for(round_number: int, role: str, target: str, claim: str, evidence_quote: str | None, severity: str) -> Finding:
    return Finding(
        id=deterministic_id("wp8", round_number, role, target, claim),
        round=round_number,
        agent_role=role,
        target=target[:300],
        claim=claim,
        evidence_quote=evidence_quote,
        severity=severity,
    )


def _limit_sql(limit: int) -> str:
    return " LIMIT :limit" if limit > 0 else ""


def load_gap_hunter_findings(conn: Any, round_number: int, limit: int) -> list[Finding]:
    rows = conn.execute(
        text(
            f"""
            SELECT id::text, instrument_name, category, status, notes
            FROM target_manifest
            WHERE status IN ('pending', 'blocked')
            ORDER BY status, category, instrument_name
            {_limit_sql(limit)}
            """
        ),
        {"limit": limit},
    ).mappings()
    return [
        finding_for(
            round_number,
            "gap_hunter",
            f"target_manifest:{row['id']}",
            f"Manifest row remains {row['status']} and cannot support answers: {row['instrument_name']}",
            str(row["notes"] or row["instrument_name"])[:1000],
            "major",
        )
        for row in rows
    ]


def load_re_extractor_findings(conn: Any, round_number: int, limit: int) -> list[Finding]:
    rows = conn.execute(
        text(
            f"""
            SELECT c.id::text, sd.title, c.clause_path, left(c.text, 1000) AS quote
            FROM clauses c
            JOIN source_versions sv ON sv.id = c.source_version_id
            JOIN source_documents sd ON sd.id = sv.source_id
            WHERE c.disposition = 'rule_bearing'
              AND NOT EXISTS (SELECT 1 FROM rules r WHERE r.clause_id = c.id)
            ORDER BY sd.title, c.clause_path NULLS LAST, c.id
            {_limit_sql(limit)}
            """
        ),
        {"limit": limit},
    ).mappings()
    return [
        finding_for(
            round_number,
            "re_extractor",
            f"clause:{row['id']}",
            f"Rule-bearing clause has no rule atom: {row['title']} {row['clause_path'] or ''}".strip(),
            row["quote"],
            "critical",
        )
        for row in rows
    ]


def load_prosecutor_findings(conn: Any, round_number: int, limit: int) -> list[Finding]:
    rows = conn.execute(
        text(
            f"""
            SELECT id::text, status, rule_key, decision_trace_json::text AS trace
            FROM check_results
            WHERE status IN ('likely_pass', 'likely_fail')
              AND (
                citations_json IS NULL
                OR citations_json::text IN ('null', '[]')
                OR decision_trace_json IS NULL
                OR decision_trace_json::text IN ('null', '{{}}')
              )
            ORDER BY created_at DESC, id
            {_limit_sql(limit)}
            """
        ),
        {"limit": limit},
    ).mappings()
    return [
        finding_for(
            round_number,
            "prosecutor",
            f"check_result:{row['id']}",
            f"{row['status']} check result lacks required citation or decision trace for {row['rule_key']}",
            row["trace"],
            "critical",
        )
        for row in rows
    ]


def load_conflict_prosecutor_findings(conn: Any, round_number: int, limit: int) -> list[Finding]:
    rows = conn.execute(
        text(
            f"""
            WITH approved AS (
                SELECT r.rule_key, r.pathway, COALESCE(r.council_scope, '') AS council_scope,
                       COALESCE(r.applicable_r_codes::text, 'ALL') AS r_codes,
                       count(DISTINCT sv.source_id) AS instruments,
                       count(*) AS rules,
                       string_agg(DISTINCT sd.title, '; ' ORDER BY sd.title) AS titles,
                       min(r.quote) AS quote
                FROM rules r
                JOIN source_versions sv ON sv.id = r.source_version_id
                JOIN source_documents sd ON sd.id = sv.source_id
                WHERE r.lifecycle_status = 'approved'
                GROUP BY r.rule_key, r.pathway, COALESCE(r.council_scope, ''),
                         COALESCE(r.applicable_r_codes::text, 'ALL')
            )
            SELECT *
            FROM approved
            WHERE instruments > 1 AND rules > 1
            ORDER BY rules DESC, rule_key
            {_limit_sql(limit)}
            """
        ),
        {"limit": limit},
    ).mappings()
    return [
        finding_for(
            round_number,
            "conflict_prosecutor",
            f"rule_key:{row['rule_key']}:{row['r_codes']}",
            (
                f"Multiple instruments provide approved rules for {row['rule_key']} "
                f"without a demonstrated single winner."
            ),
            f"{row['titles']} :: {row['quote'] or ''}"[:1000],
            "major",
        )
        for row in rows
    ]


ROLE_LOADERS = {
    "gap_hunter": load_gap_hunter_findings,
    "re_extractor": load_re_extractor_findings,
    "prosecutor": load_prosecutor_findings,
    "conflict_prosecutor": load_conflict_prosecutor_findings,
}


def insert_findings(conn: Any, findings: list[Finding]) -> int:
    changed = 0
    for finding in findings:
        result = conn.execute(
            text(
                """
                INSERT INTO adversarial_findings (
                    id, round, agent_role, target, claim, evidence_quote,
                    severity, status, created_at, updated_at
                ) VALUES (
                    CAST(:id AS uuid), :round, :agent_role, :target, :claim,
                    :evidence_quote, :severity, :status, now(), now()
                )
                ON CONFLICT (id) DO UPDATE SET
                    evidence_quote = EXCLUDED.evidence_quote,
                    severity = EXCLUDED.severity,
                    updated_at = now()
                """
            ),
            finding.__dict__,
        )
        changed += result.rowcount or 0
    return changed


def claim_open_findings(conn: Any, worker: str, limit: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            f"""
            UPDATE adversarial_findings
            SET claimed_by = :worker, lease_expires_at = now() + interval '30 minutes', updated_at = now()
            WHERE id IN (
                SELECT id
                FROM adversarial_findings
                WHERE status = 'open'
                  AND (lease_expires_at IS NULL OR lease_expires_at < now())
                ORDER BY severity DESC, created_at
                {_limit_sql(limit)}
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id::text, round, agent_role, target, claim, evidence_quote, severity, status
            """
        ),
        {"worker": worker, "limit": limit},
    ).mappings()
    return [dict(row) for row in rows]


def summarize(conn: Any) -> dict[str, Any]:
    rows = conn.execute(
        text(
            """
            SELECT round, agent_role, status, severity, count(*) AS count
            FROM adversarial_findings
            GROUP BY round, agent_role, status, severity
            ORDER BY round, agent_role, status, severity
            """
        )
    ).mappings()
    rounds: dict[int, dict[str, Any]] = {}
    totals: dict[str, int] = {}
    for row in rows:
        round_entry = rounds.setdefault(int(row["round"]), {"round": int(row["round"]), "counts": {}})
        key = f"{row['agent_role']}:{row['status']}:{row['severity']}"
        round_entry["counts"][key] = int(row["count"])
        totals[str(row["status"])] = totals.get(str(row["status"]), 0) + int(row["count"])

    ordered_rounds = [rounds[key] for key in sorted(rounds)]
    last_two = ordered_rounds[-2:]
    gate_passed = (
        len(last_two) == 2
        and totals.get("open", 0) == 0
        and all(
            sum(count for key, count in item["counts"].items() if ":confirmed:" in key) == 0
            for item in last_two
        )
    )
    return {
        "wp": "WP8",
        "generated_at": now_iso(),
        "rounds_completed": len(ordered_rounds),
        "rounds": ordered_rounds,
        "totals": totals,
        "gate": {
            "passed": gate_passed,
            "rule": "two consecutive full rounds with zero confirmed findings and no open findings",
        },
    }


def run_attack(args: argparse.Namespace) -> int:
    engine = create_engine(database_url())
    with engine.begin() as conn:
        findings = ROLE_LOADERS[args.role](conn, args.round, args.limit)
        changed = insert_findings(conn, findings) if args.apply else 0
    report = {
        "wp": "WP8",
        "mode": "apply" if args.apply else "dry_run",
        "role": args.role,
        "round": args.round,
        "findings": len(findings),
        "changed": changed,
        "items": [finding.__dict__ for finding in findings],
    }
    print(json.dumps(report, indent=2, default=str))
    return 0


def run_defense(args: argparse.Namespace) -> int:
    engine = create_engine(database_url())
    worker = args.worker_id or f"wp8-defense-{socket.gethostname()}"
    with engine.begin() as conn:
        claimed = claim_open_findings(conn, worker, args.limit)
    report = {
        "wp": "WP8",
        "mode": "claim_only",
        "worker": worker,
        "claimed": len(claimed),
        "items": claimed,
        "note": "Frontier defense pass must update each row to fixed or rejected with a quote.",
    }
    print(json.dumps(report, indent=2, default=str))
    return 0


def run_report(args: argparse.Namespace) -> int:
    engine = create_engine(database_url())
    with engine.connect() as conn:
        report = summarize(conn)
    output = json.dumps(report, indent=2, default=str)
    print(output)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(output, encoding="utf-8")
    return 0 if report["gate"]["passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    attack = sub.add_parser("attack")
    attack.add_argument("--round", type=int, required=True)
    attack.add_argument("--role", choices=sorted(ATTACKER_ROLES), required=True)
    attack.add_argument("--limit", type=int, default=100)
    attack.add_argument("--apply", action="store_true")
    attack.set_defaults(func=run_attack)

    defense = sub.add_parser("defense")
    defense.add_argument("--limit", type=int, default=25)
    defense.add_argument("--worker-id", default="")
    defense.set_defaults(func=run_defense)

    report = sub.add_parser("report")
    report.add_argument("--report", default=str(DEFAULT_REPORT))
    report.set_defaults(func=run_report)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
