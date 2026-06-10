"""GOV-EXP-* — export validation checks.

Implements the three export-validators in
docs/process-control/implementation-map.md §6.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from draftcheck.db.models import (
    CheckResult,
    Export,
)
from draftcheck.governance.types import (
    GovernanceFailure,
    GovernanceFailureCode,
    GovernanceSeverity,
)


if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _manifest_validation_passed(manifest: dict | None) -> bool | None:
    """Read the manifest's validation flag.

    Returns True/False if the key exists, None if absent.
    """
    if not isinstance(manifest, dict):
        return None
    if "validation_passed" not in manifest:
        return None
    return bool(manifest["validation_passed"])


def validate(session: "Session") -> list[GovernanceFailure]:
    failures: list[GovernanceFailure] = []

    for exp in session.scalars(select(Export)):
        # Only validate completed exports; pending/in-flight are not in scope.
        if exp.status != "completed":
            continue

        # GOV-EXP-001: completed export must have sha256 + manifest validation flag.
        if exp.sha256 is None:
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.EXP_001_COMPLETED_HAS_VALIDATION,
                    severity=GovernanceSeverity.MAJOR,
                    subject_type="export",
                    subject_id=exp.id,
                    message=(
                        f"Export {exp.id} is completed but has no sha256."
                    ),
                )
            )
        validation = _manifest_validation_passed(exp.manifest_json)
        if validation is None:
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.EXP_001_COMPLETED_HAS_VALIDATION,
                    severity=GovernanceSeverity.MAJOR,
                    subject_type="export",
                    subject_id=exp.id,
                    message=(
                        f"Export {exp.id} manifest_json has no "
                        "'validation_passed' key."
                    ),
                )
            )

        # GOV-EXP-002: validation_passed=false is a hard fail.
        if validation is False:
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.EXP_002_FAILED_VALIDATION_BLOCKED,
                    severity=GovernanceSeverity.CRITICAL,
                    subject_type="export",
                    subject_id=exp.id,
                    message=(
                        f"Export {exp.id} validation_passed=false. "
                        "Per GOV-EXP-002 the export must be blocked from download."
                    ),
                )
            )

        # GOV-EXP-003: every CheckResult in the run must have evidence.
        if exp.check_run_id is None:
            continue
        bad_results = list(
            session.scalars(
                select(CheckResult).where(CheckResult.check_run_id == exp.check_run_id)
            )
        )
        for cr in bad_results:
            if cr.status in ("likely_pass", "likely_fail"):
                if not cr.citations_json or not cr.decision_trace_json or cr.resolved_rule_id is None:
                    failures.append(
                        GovernanceFailure(
                            code=GovernanceFailureCode.EXP_003_CHECK_RUN_RESULTS_VALID,
                            severity=GovernanceSeverity.MAJOR,
                            subject_type="export",
                            subject_id=exp.id,
                            message=(
                                f"Export {exp.id} (check_run {exp.check_run_id}) "
                                f"CheckResult {cr.id} ({cr.check_key!r}) is "
                                f"{cr.status!r} but lacks citations, decision trace, "
                                "or resolved rule."
                            ),
                            evidence_refs=[str(cr.id)],
                        )
                    )

    return failures
