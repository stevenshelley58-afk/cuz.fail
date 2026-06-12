"""WP7 - deterministic legal graph conflict sweep.

Populates missing ``exception_to`` edges only when clause context names a base
rule deterministically. Potential cross-instrument conflicts are reported, and
same-instrument same-applicability value disagreements become review_items.
No precedence winner is selected here.

Run inside the api container:
    python /app/scripts/wp7_conflict_sweep.py --report /app/reports/conflict_sweep.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import Connection  # noqa: E402

ORG_ID = "1d31c315-5087-47df-a8d4-ebfd08efad5d"
NS = uuid.UUID("8102b72a-c708-40fa-8293-afd061e7894c")
DEFAULT_REPORT = Path(__file__).resolve().parent.parent / "reports" / "conflict_sweep.json"


@dataclass(frozen=True)
class RuleRow:
    id: str
    org_id: str | None
    source_version_id: str
    source_id: str
    instrument_name: str
    authority: str
    clause_id: str
    clause_path: str | None
    section_ref: str | None
    clause_text: str
    rule_key: str
    rule_type: str
    pathway: str
    operator: str | None
    value_json: dict[str, Any]
    unit: str | None
    condition_json: dict[str, Any]
    applicable_r_codes: Any
    applicable_zones: Any
    council_scope: str | None
    quote: str


def deterministic_id(kind: str, *parts: object) -> str:
    return str(uuid.uuid5(NS, "|".join([kind, *(str(p) for p in parts)])))


def norm_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip().casefold()


def as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [value]
        except json.JSONDecodeError:
            return [value]
    return []


def base_rule_key(rule: RuleRow) -> str:
    return str(rule.value_json.get("base_rule_key") or rule.rule_key)


def density_codes(rule: RuleRow) -> tuple[str, ...]:
    codes = as_list(rule.applicable_r_codes)
    if not codes:
        codes = as_list(rule.condition_json.get("density_codes"))
    if not codes:
        applicability = as_dict(rule.value_json.get("applicability"))
        codes = as_list(applicability.get("density_codes"))
    return tuple(sorted({str(code) for code in codes if str(code).strip()}))


def density_buckets(rule: RuleRow) -> tuple[str, ...]:
    codes = density_codes(rule)
    return codes or ("ALL",)


def value_signature(rule: RuleRow) -> tuple[Any, ...]:
    value = rule.value_json.get("value")
    if isinstance(value, float):
        value = round(value, 6)
    return (rule.operator, value, rule.unit)


def applicability_signature(rule: RuleRow) -> tuple[str, str, str, str]:
    condition = {
        k: v
        for k, v in sorted(rule.condition_json.items())
        if k not in {"confidence", "base_rule_key"}
    }
    return (
        json.dumps(condition, sort_keys=True, default=str),
        json.dumps(density_codes(rule), sort_keys=True),
        json.dumps(as_list(rule.applicable_zones), sort_keys=True, default=str),
        rule.council_scope or "",
    )


def quote_names_base_rule(exception_rule: RuleRow, candidate_base: RuleRow) -> bool:
    haystack = norm_text(f"{exception_rule.quote} {exception_rule.clause_text}")
    needles = [
        candidate_base.rule_key,
        candidate_base.clause_path,
        candidate_base.section_ref,
    ]
    return any(norm_text(needle) and norm_text(needle) in haystack for needle in needles)


def select_exception_base(exception_rule: RuleRow, rules: list[RuleRow]) -> RuleRow | None:
    key = base_rule_key(exception_rule)
    candidates = [
        rule
        for rule in rules
        if rule.id != exception_rule.id
        and rule.rule_type != "exception"
        and rule.source_version_id == exception_rule.source_version_id
        and base_rule_key(rule) == key
    ]
    named = [rule for rule in candidates if quote_names_base_rule(exception_rule, rule)]
    if len(named) == 1:
        return named[0]
    return None


def cross_instrument_conflicts(rules: list[RuleRow]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[RuleRow]] = {}
    for rule in rules:
        for code in density_buckets(rule):
            grouped.setdefault((rule.rule_key, code, rule.pathway), []).append(rule)

    conflicts: list[dict[str, Any]] = []
    for (rule_key, density_code, pathway), rows in sorted(grouped.items(), key=lambda item: item[0]):
        instruments = {row.source_id for row in rows}
        if len(rows) <= 1 or len(instruments) <= 1:
            continue
        conflicts.append(
            {
                "rule_key": rule_key,
                "density_code": density_code,
                "pathway": pathway,
                "instrument_count": len(instruments),
                "rule_count": len(rows),
                "rules": [
                    {
                        "rule_id": row.id,
                        "instrument": row.instrument_name,
                        "authority": row.authority,
                        "value": value_signature(row),
                        "quote": row.quote,
                    }
                    for row in rows
                ],
            }
        )
    return conflicts


def extraction_bug_groups(rules: list[RuleRow]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, tuple[str, str, str, str]], list[RuleRow]] = {}
    for rule in rules:
        key = (rule.source_id, rule.rule_key, rule.pathway, applicability_signature(rule))
        grouped.setdefault(key, []).append(rule)

    bugs: list[dict[str, Any]] = []
    for (_source_id, rule_key, pathway, _app), rows in sorted(grouped.items(), key=lambda item: str(item[0])):
        value_sigs = {value_signature(row) for row in rows}
        if len(rows) > 1 and len(value_sigs) > 1:
            bugs.append(
                {
                    "instrument": rows[0].instrument_name,
                    "rule_key": rule_key,
                    "pathway": pathway,
                    "rule_ids": [row.id for row in rows],
                    "values": [list(sig) for sig in sorted(value_sigs, key=str)],
                }
            )
    return bugs


def database_url() -> str:
    url = os.environ["DATABASE_URL"]
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")


def load_rules(conn: Connection) -> list[RuleRow]:
    rows = conn.execute(
        text(
            """
            SELECT r.id::text AS id, r.org_id::text AS org_id,
                   r.source_version_id::text AS source_version_id,
                   sv.source_id::text AS source_id,
                   sd.title AS instrument_name, sd.authority,
                   r.clause_id::text AS clause_id, c.clause_path, c.section_ref,
                   c.text AS clause_text, r.rule_key, r.rule_type, r.pathway,
                   r.operator, r.value_json, r.unit, r.condition_json,
                   r.applicable_r_codes, r.applicable_zones, r.council_scope,
                   r.quote
            FROM rules r
            JOIN clauses c ON c.id = r.clause_id
            JOIN source_versions sv ON sv.id = r.source_version_id
            JOIN source_documents sd ON sd.id = sv.source_id
            WHERE r.lifecycle_status = 'approved'
            ORDER BY sd.title, r.rule_key, r.id
            """
        )
    ).mappings()
    return [
        RuleRow(
            id=str(row["id"]),
            org_id=row["org_id"],
            source_version_id=str(row["source_version_id"]),
            source_id=str(row["source_id"]),
            instrument_name=str(row["instrument_name"]),
            authority=str(row["authority"] or ""),
            clause_id=str(row["clause_id"]),
            clause_path=row["clause_path"],
            section_ref=row["section_ref"],
            clause_text=str(row["clause_text"] or ""),
            rule_key=str(row["rule_key"]),
            rule_type=str(row["rule_type"]),
            pathway=str(row["pathway"]),
            operator=row["operator"],
            value_json=as_dict(row["value_json"]),
            unit=row["unit"],
            condition_json=as_dict(row["condition_json"]),
            applicable_r_codes=row["applicable_r_codes"],
            applicable_zones=row["applicable_zones"],
            council_scope=row["council_scope"],
            quote=str(row["quote"] or ""),
        )
        for row in rows
    ]


def existing_exception_edges(conn: Connection) -> set[str]:
    rows = conn.execute(
        text("SELECT from_ref FROM legal_edges WHERE from_type = 'rule' AND relation = 'exception_to'")
    )
    return {str(row[0]) for row in rows}


def insert_exception_edge(conn: Connection, exception_rule: RuleRow, base_rule: RuleRow, dry_run: bool) -> str:
    edge_id = deterministic_id("edge", "rule", exception_rule.id, "rule", base_rule.id, "exception_to")
    if dry_run:
        return edge_id
    metadata = json.dumps({"wp7": True, "deterministic_reason": "exception_quote_named_base_rule"})
    conn.execute(
        text(
            """
            INSERT INTO legal_edges (id, from_type, from_ref, to_type, to_ref, relation,
                evidence_quote, confidence, review_status, metadata_json, created_at, updated_at)
            VALUES (CAST(:id AS uuid), 'rule', :from_ref, 'rule', :to_ref, 'exception_to',
                :quote, 0.85, 'pending_review', CAST(:metadata AS jsonb), now(), now())
            ON CONFLICT (from_type, from_ref, to_type, to_ref, relation) DO UPDATE
                SET evidence_quote = EXCLUDED.evidence_quote,
                    metadata_json = legal_edges.metadata_json || EXCLUDED.metadata_json,
                    updated_at = now()
            """
        ),
        {
            "id": edge_id,
            "from_ref": exception_rule.id,
            "to_ref": base_rule.id,
            "quote": exception_rule.quote,
            "metadata": metadata,
        },
    )
    return edge_id


def insert_review_item(
    conn: Connection,
    *,
    subject_type: str,
    subject_id: str,
    reason: str,
    source: dict[str, Any],
    dry_run: bool,
) -> str:
    review_id = deterministic_id("review", subject_type, subject_id, reason)
    if dry_run:
        return review_id
    conn.execute(
        text(
            """
            INSERT INTO review_items (id, org_id, subject_type, subject_id, reason, status,
                priority, source_json, metadata_json, severity, created_at, updated_at)
            VALUES (CAST(:id AS uuid), CAST(:org_id AS uuid), :subject_type,
                CAST(:subject_id AS uuid), :reason, 'open', 1,
                CAST(:source AS jsonb), CAST(:metadata AS jsonb), 'medium', now(), now())
            ON CONFLICT (id) DO UPDATE
                SET reason = EXCLUDED.reason,
                    source_json = EXCLUDED.source_json,
                    metadata_json = review_items.metadata_json || EXCLUDED.metadata_json,
                    updated_at = now()
            """
        ),
        {
            "id": review_id,
            "org_id": ORG_ID,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "reason": reason,
            "source": json.dumps(source),
            "metadata": json.dumps({"wp7": True}),
        },
    )
    return review_id


def close_exception_edges(conn: Connection, rules: list[RuleRow], dry_run: bool) -> dict[str, Any]:
    existing = existing_exception_edges(conn)
    exceptions = [rule for rule in rules if rule.rule_type == "exception" and rule.id not in existing]
    created: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    for exception_rule in exceptions:
        base = select_exception_base(exception_rule, rules)
        if base is not None:
            edge_id = insert_exception_edge(conn, exception_rule, base, dry_run=dry_run)
            created.append({"edge_id": edge_id, "exception_rule_id": exception_rule.id, "base_rule_id": base.id})
            continue
        reason = (
            "WP7 exception rule lacks exception_to edge and deterministic clause context "
            "does not name exactly one approved base rule."
        )
        review_id = insert_review_item(
            conn,
            subject_type="rule",
            subject_id=exception_rule.id,
            reason=reason,
            source={
                "rule_id": exception_rule.id,
                "rule_key": exception_rule.rule_key,
                "quote": exception_rule.quote,
                "clause_path": exception_rule.clause_path,
            },
            dry_run=dry_run,
        )
        reviews.append({"review_item_id": review_id, "rule_id": exception_rule.id, "reason": reason})
    return {"created_edges": created, "review_items": reviews}


def write_extraction_bug_reviews(
    conn: Connection,
    bugs: list[dict[str, Any]],
    rules_by_id: dict[str, RuleRow],
    dry_run: bool,
) -> list[dict[str, Any]]:
    reviews: list[dict[str, Any]] = []
    for bug in bugs:
        subject_id = bug["rule_ids"][0]
        reason = (
            "WP7 extraction bug: same instrument and same applicability have approved "
            "rules with different values."
        )
        review_id = insert_review_item(
            conn,
            subject_type="rule",
            subject_id=subject_id,
            reason=reason,
            source={**bug, "quotes": [rules_by_id[rid].quote for rid in bug["rule_ids"]]},
            dry_run=dry_run,
        )
        reviews.append({"review_item_id": review_id, **bug})
    return reviews


def quoteless_legal_edges(conn: Connection) -> int:
    row = conn.execute(
        text("SELECT count(*) FROM legal_edges WHERE evidence_quote IS NULL OR btrim(evidence_quote) = ''")
    ).first()
    return int(row[0]) if row else 0


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="report without DB writes")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    engine = create_engine(database_url())
    with engine.begin() as conn:
        rules = load_rules(conn)
        exception_result = close_exception_edges(conn, rules, dry_run=args.dry_run)
        conflicts = cross_instrument_conflicts(rules)
        bugs = extraction_bug_groups(rules)
        bug_reviews = write_extraction_bug_reviews(
            conn,
            bugs,
            {rule.id: rule for rule in rules},
            dry_run=args.dry_run,
        )
        quoteless = quoteless_legal_edges(conn) if not args.dry_run else None

    report = {
        "wp": "WP7",
        "dry_run": args.dry_run,
        "summary": {
            "approved_rules_scanned": len(rules),
            "exception_edges_created": len(exception_result["created_edges"]),
            "exception_review_items": len(exception_result["review_items"]),
            "cross_instrument_conflicts": len(conflicts),
            "extraction_bug_review_items": len(bug_reviews),
            "quoteless_legal_edges": quoteless,
        },
        "exception_edges_created": exception_result["created_edges"],
        "exception_review_items": exception_result["review_items"],
        "cross_instrument_conflicts": conflicts,
        "extraction_bug_review_items": bug_reviews,
        "notes": ["No AI-decided precedence changes were made."],
    }
    report["gate_passed"] = args.dry_run or quoteless == 0
    write_report(Path(args.report), report)
    print(json.dumps(report, indent=2, default=str))
    return 0 if report["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
