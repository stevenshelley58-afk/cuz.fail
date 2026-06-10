"""Shared types for the governance validator package.

These are the only types the audit script and the audit-report
endpoint need to import from the validators package. The validators
themselves return ``list[GovernanceFailure]``; callers group, format,
and present.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID


class GovernanceSeverity(StrEnum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class GovernanceFailureCode(StrEnum):
    # Source / controlled-document checks (GOV-SRC-*)
    SRC_001_OWNER_REQUIRED = "GOV-SRC-001"
    SRC_002_REVIEW_DUE_REQUIRED = "GOV-SRC-002"
    SRC_003_LICENCE_APPROVED = "GOV-SRC-003"
    SRC_004_VERSION_WINDOWS = "GOV-SRC-004"
    SRC_005_CHUNK_FROM_APPROVED_VERSION = "GOV-SRC-005"

    # Rule / extraction traceability (GOV-RULE-*)
    RULE_001_HAS_QUOTE_AND_CLAUSE = "GOV-RULE-001"
    RULE_002_HAS_PRIMARY_LINK = "GOV-RULE-002"
    RULE_003_OPERATOR_VALID = "GOV-RULE-003"
    RULE_004_NO_CONFLICTING_APPROVED_RULES = "GOV-RULE-004"

    # Compliance check evidence (GOV-CHK-*)
    CHK_001_RESOLVED_RULE_AND_CITATIONS = "GOV-CHK-001"
    CHK_002_CITATIONS_FROM_APPROVED_VERSION = "GOV-CHK-002"
    CHK_003_FAILURES_HAVE_RFI = "GOV-CHK-003"
    CHK_004_RUN_WITHIN_CURRENCY_WINDOW = "GOV-CHK-004"

    # Export validation (GOV-EXP-*)
    EXP_001_COMPLETED_HAS_VALIDATION = "GOV-EXP-001"
    EXP_002_FAILED_VALIDATION_BLOCKED = "GOV-EXP-002"
    EXP_003_CHECK_RUN_RESULTS_VALID = "GOV-EXP-003"

    # Eval follow-up (GOV-EVAL-*)
    EVAL_001_FAILED_EVAL_HAS_REVIEW = "GOV-EVAL-001"

    # Control registry (GOV-CTRL-*)
    CTRL_001_TESTED_WITHIN_FREQUENCY = "GOV-CTRL-001"
    CTRL_002_OWNER_ROLE_SET = "GOV-CTRL-002"

    # AI finding / governance finding queue (GOV-FIND-*)
    FIND_001_PROPOSED_NOT_STALE = "GOV-FIND-001"
    FIND_002_ACCEPTED_HAS_DECISION_FIELDS = "GOV-FIND-002"
    FIND_003_CONVERTED_CAPA_LINKED = "GOV-FIND-003"

    # CAPA / ReviewItem checks (GOV-CAPA-*)
    CAPA_001_CLOSED_HAS_EVIDENCE_AND_DATE = "GOV-CAPA-001"
    CAPA_002_EFFECTIVENESS_CHECK_OVERDUE = "GOV-CAPA-002"
    CAPA_003_FINDING_LINK_INTEGRITY = "GOV-CAPA-003"

    # KPI registry (GOV-KPI-*)
    KPI_001_RESULT_FRESH = "GOV-KPI-001"

    # Pipeline step registry (GOV-PIPE-*)
    PIPE_001_CRITICAL_STEP_HAS_CONTROL = "GOV-PIPE-001"


@dataclass(frozen=True)
class GovernanceFailure:
    """A single governance finding produced by a validator function.

    Attributes
    ----------
    code:
        Stable failure code (one of ``GovernanceFailureCode``). Used
        as the primary key for tests and for the audit script's
        deduplication.
    severity:
        ``critical`` failures fail CI; ``major`` and ``minor`` are
        reported but do not fail the default audit run.
    subject_type:
        What the failure refers to (e.g. ``source_version``,
        ``check_result``, ``review_item``). String so the type
        system doesn't bind to a specific ORM class.
    subject_id:
        The row's primary key, or ``None`` for "no specific row".
    message:
        Human-readable summary. May include embedded values.
    evidence_refs:
        Free-form list of related identifiers (e.g. citation ids,
        audit event ids). The audit script prints these.
    detected_at:
        When the validator ran. Set automatically by
        ``run_all_validators``; tests usually freeze via
        ``detected_at=datetime.now(UTC)``.
    """

    code: GovernanceFailureCode
    severity: GovernanceSeverity
    subject_type: str
    subject_id: UUID | None
    message: str
    evidence_refs: list[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))


if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def run_all_validators(session: "Session") -> list[GovernanceFailure]:
    """Run every governance validator and return the union of failures.

    Each validator is a pure function in
    ``draftcheck.governance.validators.*`` that takes a ``Session``
    and returns ``list[GovernanceFailure]``. This orchestrator runs
    them in a stable order (so the audit output is reproducible) and
    returns the concatenation.

    The function does NOT mutate the session.
    """
    # Local imports to avoid a top-level import cycle when
    # validators import from db.models and we want the test
    # harness to monkey-patch models.
    from draftcheck.governance.validators import (
        capa,
        check_results,
        controls,
        eval_followup,
        exports,
        findings,
        kpis,
        pipeline_steps,
        rules,
        sources,
    )

    validators: Iterable[Callable[..., list[GovernanceFailure]]] = (
        sources.validate,
        rules.validate,
        check_results.validate,
        exports.validate,
        eval_followup.validate,
        controls.validate,
        findings.validate,
        capa.validate,
        kpis.validate,
        pipeline_steps.validate,
    )

    failures: list[GovernanceFailure] = []
    for validator in validators:
        failures.extend(validator(session))
    return failures
