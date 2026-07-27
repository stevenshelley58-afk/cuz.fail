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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

try:
    import psycopg
except ImportError:
    print("ERROR: psycopg not installed. Run: pip install psycopg[binary]", file=sys.stderr)
    sys.exit(1)

from draftcheck.extraction.validators import run_all_validators  # noqa: E402


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


def validate_candidate(
    candidate: dict[str, Any],
    clause_text: str,
    disposition: str,
) -> tuple[dict[str, dict[str, object]], list[str]]:
    """Run the universal extraction validators required before promotion."""
    results = run_all_validators(
        quote=str(candidate.get("quote") or ""),
        clause_text=clause_text,
        disposition=disposition,
        value_json=candidate.get("value_json") or {},
        unit=candidate.get("unit"),
        rule_key=candidate.get("rule_key"),
    )
    failures = [
        f"VALIDATOR-{name}: {result.get('detail', 'failed')}"
        for name, result in results.items()
        if not result.get("pass")
    ]
    return results, failures


def _candidate_id(candidate: dict[str, Any]) -> str:
    identity = f"{candidate.get('source_version_id')}:{candidate.get('rule_key')}"
    return str(uuid5(NAMESPACE_URL, f"draftcheck:bulk-rule-candidate:{identity}"))


def upsert_rule_candidate(
    conn: Any,
    candidate: dict[str, Any],
    *,
    approver_user_id: str,
    org_id: str,
    report_file: str,
    validator_results: dict[str, dict[str, object]],
    validator_failures: list[str],
) -> str:
    """Persist the candidate and its validator trace before any promotion."""
    candidate_id = _candidate_id(candidate)
    review_status = "pending_review" if validator_failures else "validators_passed"
    conn.execute(
        """
        INSERT INTO rule_candidates (
            id, org_id, source_version_id, clause_id, rule_key, canonical_rule_key,
            rule_type, pathway, check_type, evaluable, rule_logic_json, operator,
            value_json, unit, condition_json, quote, extractor_model, confidence,
            review_status, reviewed_by_user_id, reviewed_at, metadata_json,
            validator_results_json, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, now(), %s,
            %s, now(), now()
        )
        ON CONFLICT (id) DO UPDATE SET
            canonical_rule_key = EXCLUDED.canonical_rule_key,
            check_type = EXCLUDED.check_type,
            evaluable = EXCLUDED.evaluable,
            rule_logic_json = EXCLUDED.rule_logic_json,
            operator = EXCLUDED.operator,
            value_json = EXCLUDED.value_json,
            unit = EXCLUDED.unit,
            condition_json = EXCLUDED.condition_json,
            quote = EXCLUDED.quote,
            extractor_model = EXCLUDED.extractor_model,
            confidence = EXCLUDED.confidence,
            review_status = EXCLUDED.review_status,
            reviewed_by_user_id = EXCLUDED.reviewed_by_user_id,
            reviewed_at = now(),
            metadata_json = EXCLUDED.metadata_json,
            validator_results_json = EXCLUDED.validator_results_json,
            updated_at = now()
        """,
        (
            candidate_id,
            org_id,
            candidate["source_version_id"],
            candidate["clause_id"],
            candidate["rule_key"],
            candidate.get("canonical_rule_key"),
            candidate.get("rule_type") or "requirement",
            candidate.get("pathway") or "none",
            "numeric_threshold"
            if candidate.get("evaluable") == "yes"
            else candidate.get("check_type"),
            "auto_numeric" if candidate.get("evaluable") == "yes" else candidate.get("evaluable"),
            json.dumps(candidate.get("rule_logic_json") or {}),
            candidate.get("operator"),
            json.dumps(candidate.get("value_json") or {}),
            candidate.get("unit"),
            json.dumps(candidate.get("condition_json") or {}),
            candidate.get("quote") or "",
            candidate.get("extractor_model"),
            candidate.get("confidence"),
            review_status,
            approver_user_id,
            json.dumps(
                {
                    "batch": report_file,
                    "bulk_import": True,
                    "validator_failures": validator_failures,
                }
            ),
            json.dumps(validator_results),
        ),
    )
    return candidate_id


def approve_candidate(
    conn: Any,
    candidate: dict[str, Any],
    approver_user_id: str,
    report_file: str,
    *,
    candidate_id: str,
    org_id: str,
    validator_results: dict[str, dict[str, object]],
) -> tuple[str, bool]:
    """Promote a validated candidate and create its evidence and audit links."""
    rule_id = str(uuid4())
    now = datetime.now(UTC).isoformat()
    result = conn.execute(
        """INSERT INTO rules
           (id, org_id, source_version_id, clause_id, candidate_id,
            rule_key, canonical_rule_key, rule_type, pathway, lifecycle_status,
            operator, value_json, unit, condition_json, quote, extractor_model,
            check_type, evaluable, applicable_r_codes, applicable_zones,
            council_scope, dwelling_type, effective_from, effective_to,
            instrument_section, table_reference, approved_by_user_id, approved_at,
            approval_metadata_json, metadata_json, rule_logic_json, created_at, updated_at)
           VALUES (
               %s, %s, %s, %s, %s,
               %s, %s, %s, %s, 'approved',
               %s, %s, %s, %s, %s, %s,
               %s, %s, %s, %s,
               %s, %s, %s, %s,
               %s, %s, %s, %s,
               %s, '{}', %s, now(), now()
           )
           ON CONFLICT ON CONSTRAINT uq_rules_version_key DO NOTHING
           RETURNING id""",
        (
            rule_id,
            org_id,
            candidate["source_version_id"],
            candidate["clause_id"],
            candidate_id,
            candidate["rule_key"],
            candidate.get("canonical_rule_key"),
            candidate.get("rule_type") or "requirement",
            candidate.get("pathway") or "none",
            candidate.get("operator"),
            json.dumps(candidate.get("value_json") or {}),
            candidate.get("unit"),
            json.dumps(candidate.get("condition_json") or {}),
            candidate.get("quote") or "",
            candidate.get("extractor_model"),
            "numeric_threshold"
            if candidate.get("evaluable") == "yes"
            else candidate.get("check_type"),
            "auto_numeric" if candidate.get("evaluable") == "yes" else candidate.get("evaluable"),
            json.dumps(candidate.get("applicable_r_codes"))
            if candidate.get("applicable_r_codes")
            else None,
            json.dumps(candidate.get("applicable_zones"))
            if candidate.get("applicable_zones")
            else None,
            candidate.get("council_scope"),
            candidate.get("dwelling_type"),
            candidate.get("effective_from"),
            candidate.get("effective_to"),
            candidate.get("instrument_section"),
            candidate.get("table_reference"),
            approver_user_id,
            now,
            json.dumps(
                {
                    "batch": report_file,
                    "governance_pass": True,
                    "universal_validators_pass": True,
                    "validator_results": validator_results,
                }
            ),
            json.dumps(candidate.get("rule_logic_json") or {}),
        ),
    ).fetchone()
    created = result is not None
    if result is None:
        result = conn.execute(
            "SELECT id FROM rules WHERE source_version_id = %s AND rule_key = %s",
            (candidate["source_version_id"], candidate["rule_key"]),
        ).fetchone()
        if result is None:
            raise RuntimeError("rule insert conflicted but the existing rule could not be loaded")
        rule_id = str(result[0])
        conn.execute(
            "UPDATE rules SET candidate_id = COALESCE(candidate_id, %s), updated_at = now() WHERE id = %s",
            (candidate_id, rule_id),
        )
    else:
        rule_id = str(result[0])

    conn.execute(
        """INSERT INTO rule_clause_links
           (id, rule_id, clause_id, source_version_id, link_type, quote,
            confidence, metadata_json, created_at, updated_at)
           VALUES (%s, %s, %s, %s, 'primary', %s, %s, %s, now(), now())
           ON CONFLICT (rule_id, clause_id, link_type) DO NOTHING""",
        (
            str(uuid4()),
            rule_id,
            candidate["clause_id"],
            candidate["source_version_id"],
            candidate.get("quote") or "",
            candidate.get("confidence"),
            json.dumps({"batch": report_file, "candidate_id": candidate_id}),
        ),
    )
    conn.execute(
        """UPDATE rule_candidates
           SET review_status = 'auto_promoted', reviewed_by_user_id = %s,
               reviewed_at = now(), auto_promoted_at = now(),
               metadata_json = metadata_json || %s::jsonb, updated_at = now()
           WHERE id = %s""",
        (
            approver_user_id,
            json.dumps({"promoted_rule_id": rule_id}),
            candidate_id,
        ),
    )
    if created:
        conn.execute(
            """INSERT INTO audit_events
               (id, org_id, actor_user_id, event_type, action, subject_type,
                subject_id, before_json, after_json, metadata_json, created_at)
               VALUES (%s, %s, %s, 'rule_governance', 'promote',
                       'rule', %s, %s, %s, %s, now())""",
            (
                str(uuid4()),
                org_id,
                approver_user_id,
                rule_id,
                json.dumps({"lifecycle_status": "candidate"}),
                json.dumps({"lifecycle_status": "approved"}),
                json.dumps(
                    {
                        "batch": report_file,
                        "candidate_id": candidate_id,
                        "validator_results": validator_results,
                    }
                ),
            ),
        )
    return rule_id, created


def main() -> int:
    parser = argparse.ArgumentParser(description="Bulk approve rule candidates.")
    parser.add_argument("--from-report", required=True, help="Path to extraction report JSON")
    parser.add_argument("--approver-user-id", required=True, help="Approver user UUID")
    parser.add_argument("--source-version-id", help="Override source version UUID")
    parser.add_argument(
        "--require-governance-pass",
        action="store_true",
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
        print("\n[DRY RUN] Running all checks without database writes.")

    db_url = (
        os.environ["DATABASE_URL"]
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
    )

    approved_count = 0
    existing_count = 0
    failed_count = 0
    failure_log: list[dict[str, Any]] = []

    with psycopg.connect(db_url) as conn:
        # Verify source version is approved
        cur = conn.cursor()
        cur.execute(
            "SELECT org_id FROM users WHERE id = %s",
            (args.approver_user_id,),
        )
        approver_row = cur.fetchone()
        if not approver_row:
            print(f"ERROR: Approver user {args.approver_user_id} not found", file=sys.stderr)
            return 1
        org_id = str(approver_row[0])

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

        for candidate in candidates:
            # Override source_version_id if specified
            if source_version_id:
                candidate["source_version_id"] = source_version_id

            clause_row = conn.execute(
                "SELECT text, disposition, source_version_id FROM clauses WHERE id = %s",
                (candidate.get("clause_id"),),
            ).fetchone()
            if clause_row is None:
                failed_count += 1
                failure_log.append(
                    {
                        "rule_key": candidate.get("rule_key"),
                        "failures": ["GOV-RULE-001: clause_id does not resolve to a clause"],
                    }
                )
                continue

            validator_results, validator_failures = validate_candidate(
                candidate,
                str(clause_row[0]),
                str(clause_row[1]),
            )
            failures = list(validator_failures)
            if str(clause_row[2]) != str(candidate.get("source_version_id")):
                failures.append("GOV-RULE-002: clause source_version_id does not match candidate")
            failures.extend(run_governance_checks(conn, candidate, args.approver_user_id))
            if candidate.get("evaluable") != "yes":
                failures.append("GOV-RULE-005: candidate is not auto-evaluable")

            if not args.dry_run:
                candidate_id = upsert_rule_candidate(
                    conn,
                    candidate,
                    approver_user_id=args.approver_user_id,
                    org_id=org_id,
                    report_file=report_path.name,
                    validator_results=validator_results,
                    validator_failures=failures,
                )
            else:
                candidate_id = _candidate_id(candidate)

            # No rule is promoted unless every universal validator and every
            # governance check passes.
            must_block = bool(failures)
            if must_block or candidate.get("evaluable") != "yes":
                failed_count += 1
                failure_log.append(
                    {
                        "rule_key": candidate.get("rule_key"),
                        "failures": failures,
                    }
                )
                continue

            if args.dry_run:
                approved_count += 1
                continue

            _rule_id, created = approve_candidate(
                conn,
                candidate,
                args.approver_user_id,
                report_path.name,
                candidate_id=candidate_id,
                org_id=org_id,
                validator_results=validator_results,
            )
            if created:
                approved_count += 1
            else:
                existing_count += 1

        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()

    # Write approval report
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    approval_report_path = _ROOT / "reports" / f"rule_approval_{timestamp}.json"
    approval_report = {
        "source_report": str(report_path),
        "source_version_id": source_version_id,
        "approver_user_id": args.approver_user_id,
        "approved_count": approved_count,
        "existing_count": existing_count,
        "failed_count": failed_count,
        "skipped_needs_review": skipped,
        "failures": failure_log,
        "timestamp": timestamp,
    }
    approval_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(approval_report_path, "w") as f:
        json.dump(approval_report, f, indent=2)

    print("\n--- Approval Summary ---")
    print(f"Approved: {approved_count}")
    print(f"Already approved: {existing_count}")
    print(f"Failed governance: {failed_count}")
    print(f"Skipped (needs review): {skipped}")
    print(f"Report: {approval_report_path}")

    if failed_count > 0:
        print("\nGovernance failures:")
        for fl in failure_log[:10]:
            print(f"  {fl['rule_key']}: {', '.join(fl['failures'])}")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
