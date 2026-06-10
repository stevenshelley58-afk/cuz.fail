"""Conflict sweep — deterministic CI defect query for the legal graph.

Implements docs/CORPUS_COMPLETENESS_PLAN.md Phase 4b items 4 and 5:

1. Conflict detection: two ``approved`` rules with the same rule_key,
   satisfiable joint applicability, different values, and NO precedence path
   between them (walking the code-owned WA ruleset in
   ``draftcheck.checks.precedence`` over ``legal_edges``) → finding.  Every
   hit is a defect: missing edge, wrong applicability, or genuine legal
   ambiguity (which the engine must answer ``needs_more_info`` with both
   citations — never silently pick one).
2. Dependency closure: an ``approved`` rule whose ``condition_json``
   references another rule/definition (``depends_on``/``defines`` edges, or
   explicit ``depends_on``/``definition_refs`` keys in condition_json) must
   resolve to an approved atom; otherwise → finding.

Runs INSIDE the api container (psycopg3 via DATABASE_URL):

    docker exec draftcheck-wa-v3-api-1 python /app/scripts/conflict_sweep.py \
        --report /app/reports/conflict_sweep.json [--strict]

``--strict`` exits 1 when any finding exists — wire this into CI so the
report must be empty for green (Phase 4b exit gate).

No LLM is used anywhere in this script — it is purely deterministic.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from draftcheck.checks.precedence import (  # noqa: E402
    CandidateRule,
    Edge,
    instrument_level_for,
    resolve_precedence,
)

#: rules.lifecycle_status values treated as approved for sweep purposes.
APPROVED_RULE_STATUSES = ("approved", "auto_accepted")


# ---------------------------------------------------------------------------
# Pure functions (no DB) — unit-tested in tests/test_precedence.py
# ---------------------------------------------------------------------------


def value_identity(rule: dict) -> str:
    """Opaque identity for a rule's value: operator + value_json.value + unit."""
    value = None
    vj = rule.get("value_json")
    if isinstance(vj, dict):
        value = vj.get("value")
    return f"{rule.get('operator')}|{value}|{rule.get('unit')}"


def _as_set(value: Any) -> set[str] | None:
    """JSONB list → set of normalised strings; None/empty → None (= applies to all)."""
    if not value:
        return None
    if isinstance(value, list | tuple | set):
        out = {str(v).strip().upper() for v in value if str(v).strip()}
        return out or None
    return {str(value).strip().upper()}


def joint_applicability_satisfiable(a: dict, b: dict) -> bool:
    """Conservative satisfiability of joint applicability.

    Two rules are jointly applicable unless they are PROVABLY disjoint:
    - both pin density codes and the sets do not intersect, or
    - both pin zones and the sets do not intersect, or
    - both pin a dwelling_type in condition_json and the types differ.
    NULL/empty always means "applies to all" (matches engine semantics).
    """
    r_a, r_b = _as_set(a.get("applicable_r_codes")), _as_set(b.get("applicable_r_codes"))
    if r_a is not None and r_b is not None and not (r_a & r_b):
        return False
    z_a, z_b = _as_set(a.get("applicable_zones")), _as_set(b.get("applicable_zones"))
    if z_a is not None and z_b is not None and not (z_a & z_b):
        return False
    c_a = a.get("condition_json") if isinstance(a.get("condition_json"), dict) else {}
    c_b = b.get("condition_json") if isinstance(b.get("condition_json"), dict) else {}
    dw_a = str(c_a.get("dwelling_type") or "").strip().lower()
    dw_b = str(c_b.get("dwelling_type") or "").strip().lower()
    if dw_a and dw_b and dw_a not in ("any",) and dw_b not in ("any",) and dw_a != dw_b:
        return False
    return True


def to_candidate(rule: dict) -> CandidateRule:
    return CandidateRule(
        rule_id=str(rule["id"]),
        rule_key=str(rule.get("rule_key") or ""),
        instrument_level=instrument_level_for(rule.get("source_type")),
        rule_type=str(rule.get("rule_type") or "requirement"),
        pathway=str(rule.get("pathway") or "none"),
        value_repr=value_identity(rule),
        citation=rule.get("citation"),
        clause_ref=str(rule["clause_id"]) if rule.get("clause_id") else None,
        source_version_id=str(rule["source_version_id"])
        if rule.get("source_version_id") else None,
    )


def to_edges(edge_rows: list[dict]) -> list[Edge]:
    return [
        Edge(
            from_ref=str(e.get("from_ref") or ""),
            to_ref=str(e.get("to_ref") or ""),
            relation=str(e.get("relation") or ""),
            review_status=str(e.get("review_status") or "pending_review"),
            from_type=str(e.get("from_type") or ""),
            to_type=str(e.get("to_type") or ""),
        )
        for e in edge_rows
    ]


def find_conflicts(rules: list[dict], edge_rows: list[dict]) -> list[dict]:
    """Phase 4b item 4 defect query over plain dict rows (no DB).

    A finding = two approved rules, same rule_key, satisfiable joint
    applicability, different values, and ``resolve_precedence`` cannot pick a
    winner between them from the edges.
    """
    edges = to_edges(edge_rows)
    by_key: dict[str, list[dict]] = {}
    for r in rules:
        if str(r.get("lifecycle_status")) not in APPROVED_RULE_STATUSES:
            continue
        key = str(r.get("rule_key") or "")
        if key:
            by_key.setdefault(key, []).append(r)

    findings: list[dict] = []
    for key, group in sorted(by_key.items()):
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if value_identity(a) == value_identity(b):
                    continue
                if not joint_applicability_satisfiable(a, b):
                    continue
                resolution = resolve_precedence([to_candidate(a), to_candidate(b)], edges)
                if resolution.status == "winner":
                    continue
                findings.append({
                    "kind": "rule_conflict",
                    "rule_key": key,
                    "rule_ids": sorted([str(a["id"]), str(b["id"])]),
                    "values": sorted([value_identity(a), value_identity(b)]),
                    "citations": [c for c in (a.get("citation"), b.get("citation")) if c],
                    "detail": (
                        "approved rules with satisfiable joint applicability, different "
                        "values, and no precedence path — missing edge, wrong "
                        "applicability, or genuine ambiguity (engine must answer "
                        "needs_more_info with both citations)"
                    ),
                })
    return findings


def _condition_refs(condition_json: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(condition_json, dict):
        for key in ("depends_on", "definition_refs", "defined_terms"):
            value = condition_json.get(key)
            if isinstance(value, str) and value.strip():
                refs.append(value.strip())
            elif isinstance(value, list | tuple):
                refs.extend(str(v).strip() for v in value if str(v).strip())
    return refs


def check_dependency_closure(rules: list[dict], edge_rows: list[dict]) -> list[dict]:
    """Phase 4b item 5: approved rules must depend only on approved atoms.

    Checks two reference mechanisms:
    - outgoing ``depends_on``/``defines`` legal edges from an approved rule's
      lineage (rule id / clause id) must land on an approved rule's lineage;
    - explicit ``depends_on`` / ``definition_refs`` / ``defined_terms`` keys in
      condition_json must match an approved rule's rule_key or id.
    """
    approved = [r for r in rules if str(r.get("lifecycle_status")) in APPROVED_RULE_STATUSES]
    approved_refs: set[str] = set()
    approved_keys: set[str] = set()
    for r in approved:
        approved_refs.add(str(r["id"]))
        if r.get("clause_id"):
            approved_refs.add(str(r["clause_id"]))
        if r.get("rule_key"):
            approved_keys.add(str(r["rule_key"]))

    findings: list[dict] = []
    dep_edges = [
        e for e in edge_rows if str(e.get("relation")) in ("depends_on", "defines")
    ]
    for r in approved:
        own_refs = {str(r["id"])}
        if r.get("clause_id"):
            own_refs.add(str(r["clause_id"]))
        for e in dep_edges:
            if str(e.get("from_ref")) not in own_refs:
                continue
            to_ref = str(e.get("to_ref") or "")
            if str(e.get("to_type")) == "external_reference" or to_ref not in approved_refs:
                findings.append({
                    "kind": "dependency_unresolved",
                    "rule_id": str(r["id"]),
                    "rule_key": r.get("rule_key"),
                    "edge_relation": e.get("relation"),
                    "missing_target": {"to_type": e.get("to_type"), "to_ref": to_ref},
                    "detail": (
                        "approved rule depends on a target that is not an approved "
                        "atom — the rule cannot stay approved (Phase 4b item 5)"
                    ),
                })
        for ref in _condition_refs(r.get("condition_json")):
            if ref not in approved_keys and ref not in approved_refs:
                findings.append({
                    "kind": "dependency_unresolved",
                    "rule_id": str(r["id"]),
                    "rule_key": r.get("rule_key"),
                    "edge_relation": "condition_json",
                    "missing_target": {"to_type": "condition_ref", "to_ref": ref},
                    "detail": (
                        "condition_json references a definition/rule that does not "
                        "resolve to an approved atom"
                    ),
                })
    return findings


# ---------------------------------------------------------------------------
# DB loading + main
# ---------------------------------------------------------------------------


def load_rows(dsn: str) -> tuple[list[dict], list[dict]]:
    import psycopg

    with psycopg.connect(dsn) as conn:
        rule_rows = conn.execute(
            """
            SELECT r.id, r.rule_key, r.rule_type, r.pathway, r.lifecycle_status,
                   r.operator, r.value_json, r.unit, r.condition_json,
                   r.applicable_r_codes, r.applicable_zones, r.clause_id,
                   r.source_version_id, sd.source_type, sd.title, c.clause_path
            FROM rules r
            JOIN source_versions sv ON sv.id = r.source_version_id
            JOIN source_documents sd ON sd.id = sv.source_id
            LEFT JOIN clauses c ON c.id = r.clause_id
            WHERE r.lifecycle_status = ANY(%s)
            """,
            (list(APPROVED_RULE_STATUSES),),
        ).fetchall()
        rules = [
            {
                "id": str(row[0]),
                "rule_key": row[1],
                "rule_type": row[2],
                "pathway": row[3],
                "lifecycle_status": row[4],
                "operator": row[5],
                "value_json": row[6],
                "unit": row[7],
                "condition_json": row[8],
                "applicable_r_codes": row[9],
                "applicable_zones": row[10],
                "clause_id": str(row[11]) if row[11] else None,
                "source_version_id": str(row[12]) if row[12] else None,
                "source_type": row[13],
                "citation": f"{row[14]} cl {row[15]}" if row[15] else row[14],
            }
            for row in rule_rows
        ]
        edge_rows = conn.execute(
            "SELECT from_type, from_ref, to_type, to_ref, relation, review_status "
            "FROM legal_edges"
        ).fetchall()
        edges = [
            {
                "from_type": row[0],
                "from_ref": row[1],
                "to_type": row[2],
                "to_ref": row[3],
                "relation": row[4],
                "review_status": row[5],
            }
            for row in edge_rows
        ]
    return rules, edges


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", default="reports/conflict_sweep.json")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any finding exists (CI gate)")
    args = ap.parse_args()

    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    rules, edges = load_rows(dsn)

    conflicts = find_conflicts(rules, edges)
    dependency_findings = check_dependency_closure(rules, edges)
    findings = conflicts + dependency_findings

    report: dict[str, Any] = {
        "approved_rules_checked": len(rules),
        "legal_edges_loaded": len(edges),
        "conflict_findings": len(conflicts),
        "dependency_findings": len(dependency_findings),
        "findings": findings,
        "green": not findings,
    }
    out = json.dumps(report, indent=2, default=str)
    if args.report:
        os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(out)
    print(out)

    if args.strict and findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
