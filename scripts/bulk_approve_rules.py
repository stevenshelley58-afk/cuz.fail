"""Batch approval of rule candidates with governance trace.

Approves a batch of rule candidates that have passed validation, promoting
them to the rules table with full governance metadata.

Usage:
    python scripts/bulk_approve_rules.py \
        --from-report reports/rcodes_table_extraction.json \
        --approver-user-id <uuid> \
        --source-version-id <uuid> \
        --require-governance-pass \
        --dry-run

Governance pre-checks (GOV-RULE-*):
    GOV-RULE-001: has quote and clause_id
    GOV-RULE-002: has primary source_version link
    GOV-RULE-003: approver user has operator role
    GOV-RULE-004: no conflicting approved rule (same key + r_code + dwelling_type + different value)

Safety:
    --require-governance-pass is mandatory in production (env-gated).
    Idempotent: re-running with the same report does not create duplicates
    (unique constraint on source_version_id + rule_key).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

try:
    import psycopg
except ImportError:
    print("ERROR: psycopg not installed. Run: pip install psycopg[binary]", file=sys.stderr)
    sys.exit(1)


class GovernanceFailure(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def gov_rule_001(candidate: dict[str, Any]) -> None:
    """Has quote and clause_id."""
    if not candidate.get("quote"):
        raise GovernanceFailure("GOV-RULE-001", "missing quote")
    if not candidate.get("clause_id"):
        raise GovernanceFailure("GOV-RULE-001", "missing clause_id")


def gov_rule_002(candidate: dict[str, Any]) -> None:
    """Has primary source_version link."""
    if not candidate.get("source_version_id"):
        raise GovernanceFailure("GOV-RULE-002", "missing source_version_id")


def gov_rule_003(conn: Any, approver_user_id: str) -> None:
    """Approver user has operator role."""
    cur = conn.cursor()
    cur.execute(
        "SELECT role FROM users WHERE id = %s",
        (approver_user_id,),
    )
    row = cur.fetchone()
    if not row:
        raise GovernanceFailure("GOV-RULE-003", f"approver user {approver_user_id} not found")
    if row[0] not in ("operator", "admin", "superadmin"):
        raise GovernanceFailure(
            "GOV-RULE-003",
            f"approver role '{row[0]}' lacks operator permission",
        )


def gov_rule_004(conn: Any, candidate: dict[str, Any]) -> None:
    """No conflicting approved rule."""
    cur = conn.cursor()
    rule_key = candidate.get("rule_key", "")
    r_codes = candidate.get("applicable_r_codes", [])
    dwelling_type = candidate.get("dwelling_type")
    new_value = candidate.get("value_json", {}).get("value")

    if new_value is None:
        return  # Skip non-numeric

    for rc in r_codes:
        cur.execute(
            """SELECT id, value_json FROM rules
               WHERE rule_key = %s
                 AND lifecycle_status = 'approved'
                 AND applicable_r_codes @> %s::jsonb
                 AND (dwelling_type = %s::varchar OR (dwelling_type IS NULL AND %s::varchar IS NULL))""",
            (rule_key, json.dumps([rc]), dwelling_type, dwelling_type),
        )
        existing = cur.fetchone()
        if existing:
            existing_val = (existing[1] or {}).get("value")
            if existing_val is not None and existing_val != new_value:
                raise GovernanceFailure(
                    "GOV-RULE-004",
                    f"conflict: {rule_key} [{rc}] existing={existing_val} vs new={new_value}",
                )


def run_governance_checks(
    conn: Any,
    candidate: dict[str, Any],
    approver_user_id: str,
) -> list[str]:
    """Run all governance checks, return list of failure codes."""
    failures: list[str] = []
    for check in (
        lambda: gov_rule_001(candidate),
        lambda: gov_rule_002(candidate),
        lambda: gov_rule_003(conn, approver_user_id),
        lambda: gov_rule_004(conn, candidate),
    ):
        try:
            check()
        except GovernanceFailure as e:
            failures.append(f"{e.code}: {e.message}")
    return failures


def approve_candidate(
    conn: Any,
    candidate: dict[str, Any],
    approver_user_id: str,
    report_file: str,
) -> str | None:
    """Promote a candidate to the rules table. Returns rule_id or None."""
    cur = conn.cursor()
    rule_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    try:
        cur.execute(
            """INSERT INTO rules
               (id, source_version_id, clause_id, rule_key, canonical_rule_key,
                rule_type, pathway, lifecycle_status, operator, value_json, unit,
                condition_json, quote, extractor_model, check_type, evaluable,
                applicable_r_codes, applicable_zones, council_scope,
                dwelling_type, effective_from, effective_to,
                instrument_section, table_reference,
                approved_by_user_id, approved_at, approval_metadata_json,
                metadata_json, rule_logic_json, created_at, updated_at)
               VALUES (
                   %s, %s, %s, %s, %s,
                   %s, %s, 'approved', %s, %s, %s,
                   %s, %s, %s, %s, %s,
                   %s, %s, %s,
                   %s, %s, %s,
                   %s, %s,
                   %s, %s, %s,
                   '{}', '{}', now(), now()
               )
               ON CONFLICT ON CONSTRAINT uq_rules_version_key DO NOTHING
               RETURNING id""",
            (
                rule_id,
                candidate["source_version_id"],
                candidate["clause_id"],
                candidate["rule_key"],
                candidate.get("canonical_rule_key"),
                candidate.get("rule_type", "standard"),
                candidate.get("pathway", "deemed_to_comply"),
                candidate.get("operator"),
                json.dumps(candidate.get("value_json", {})),
                candidate.get("unit"),
                json.dumps(candidate.get("condition_json", {})),
                candidate.get("quote", ""),
                candidate.get("extractor_model"),
                candidate.get("check_type"),
                candidate.get("evaluable"),
                json.dumps(candidate.get("applicable_r_codes")),
                json.dumps(candidate.get("applicable_zones")) if candidate.get("applicable_zones") else None,
                candidate.get("council_scope"),
                candidate.get("dwelling_type"),
                candidate.get("effective_from"),
                candidate.get("effective_to"),
                candidate.get("instrument_section"),
                candidate.get("table_reference"),
                approver_user_id,
                now,
                json.dumps({"batch": report_file, "governance_pass": True}),
            ),
        )
        result = cur.fetchone()
        return str(result[0]) if result else None
    except Exception as e:
        print(f"  ERROR approving {candidate.get('rule_key')}: {e}", file=sys.stderr)
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Bulk approve rule candidates.")
    parser.add_argument("--from-report", required=True, help="Path to extraction report JSON")
    parser.add_argument("--approver-user-id", required=True, help="Approver user UUID")
    parser.add_argument("--source-version-id", help="Override source version UUID")
    parser.add_argument(
        "--require-governance-pass", action="store_true",
        help="Mandatory in production: block approval on any governance failure",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions without DB writes")
    args = parser.parse_args()

    # Production safety: require governance pass
    env = os.getenv("DRAFTCHECK_ENV", "local")
    if env == "production" and not args.require_governance_pass:
        print("ERROR: --require-governance-pass is mandatory in production", file=sys.stderr)
        return 1

    report_path = Path(args.from_report)
    if not report_path.exists():
        print(f"ERROR: Report not found: {report_path}", file=sys.stderr)
        return 1

    with open(report_path) as f:
        report = json.load(f)

    candidates = report.get("candidates", [])
    source_version_id = args.source_version_id or report.get("source_version_id")

    # Filter to evaluable candidates only
    eligible = [c for c in candidates if c.get("evaluable") == "yes"]
    skipped = len(candidates) - len(eligible)

    print(f"Report: {report_path.name}")
    print(f"Total candidates: {len(candidates)}")
    print(f"Eligible for approval: {len(eligible)}")
    print(f"Skipped (needs review): {skipped}")
    print(f"Approver: {args.approver_user_id}")
    print(f"Source version: {source_version_id}")

    if args.dry_run:
        print("\n[DRY RUN] Would approve the following:")
        for c in eligible[:10]:
            print(f"  {c['rule_key']} [{','.join(c.get('applicable_r_codes', []))}] "
                  f"{c.get('operator')} {c.get('value_json', {}).get('value')} {c.get('unit', '')}")
        if len(eligible) > 10:
            print(f"  ... and {len(eligible) - 10} more")
        return 0

    db_url = os.environ["DATABASE_URL"].replace(
        "postgresql+asyncpg://", "postgresql://"
    ).replace("postgresql+psycopg://", "postgresql://")

    approved_count = 0
    failed_count = 0
    failure_log: list[dict[str, Any]] = []

    with psycopg.connect(db_url) as conn:
        # Verify source version is approved
        cur = conn.cursor()
        cur.execute(
            "SELECT review_status FROM source_versions WHERE id = %s",
            (source_version_id,),
        )
        sv_row = cur.fetchone()
        if not sv_row:
            print(f"ERROR: Source version {source_version_id} not found", file=sys.stderr)
            return 1
        if sv_row[0] != "approved":
            print(
                f"WARNING: Source version review_status is '{sv_row[0]}' (not 'approved'). "
                f"Rules may not be citable until source is approved.",
                file=sys.stderr,
            )

        for candidate in eligible:
            # Override source_version_id if specified
            if source_version_id:
                candidate["source_version_id"] = source_version_id

            # Run governance checks
            failures = run_governance_checks(conn, candidate, args.approver_user_id)

            if failures and args.require_governance_pass:
                failed_count += 1
                failure_log.append({
                    "rule_key": candidate.get("rule_key"),
                    "failures": failures,
                })
                continue

            # Approve
            rule_id = approve_candidate(conn, candidate, args.approver_user_id, report_path.name)
            if rule_id:
                approved_count += 1

        conn.commit()

    # Write approval report
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    approval_report_path = _ROOT / "reports" / f"rule_approval_{timestamp}.json"
    approval_report = {
        "source_report": str(report_path),
        "source_version_id": source_version_id,
        "approver_user_id": args.approver_user_id,
        "approved_count": approved_count,
        "failed_count": failed_count,
        "skipped_needs_review": skipped,
        "failures": failure_log,
        "timestamp": timestamp,
    }
    approval_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(approval_report_path, "w") as f:
        json.dump(approval_report, f, indent=2)

    print(f"\n--- Approval Summary ---")
    print(f"Approved: {approved_count}")
    print(f"Failed governance: {failed_count}")
    print(f"Skipped (needs review): {skipped}")
    print(f"Report: {approval_report_path}")

    if failed_count > 0:
        print(f"\nGovernance failures:")
        for fl in failure_log[:10]:
            print(f"  {fl['rule_key']}: {', '.join(fl['failures'])}")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
