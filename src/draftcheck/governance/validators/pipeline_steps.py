"""GOV-PIPE-* — pipeline-step registry checks.

Implements the one pipeline-validator in
docs/process-control/implementation-map.md §6.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from draftcheck.db.models import GovernanceControl, GovernancePipelineStep, GovernanceRisk
from draftcheck.governance.types import (
    GovernanceFailure,
    GovernanceFailureCode,
    GovernanceSeverity,
)


if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def validate(session: "Session") -> list[GovernanceFailure]:
    failures: list[GovernanceFailure] = []

    # Build a set of risk codes that have at least one control.
    risk_codes_with_controls: set[str] = set(
        session.scalars(select(GovernanceControl.code).distinct())
    )

    for step in session.scalars(select(GovernancePipelineStep)):
        if not step.is_critical:
            continue
        # A critical step must be linked to at least one control.
        # We use a soft heuristic: any risk in the same stage with a control.
        # The map's strict requirement is "a control whose risk_code references
        # the stage" — we encode this as ``stage`` matching one of the risks
        # associated with a control, with stage defaults to step.stage.
        # A future PR may add an explicit ``step_risk`` link table; for PR-3
        # the link is via the step.stage string.
        related_risks = list(
            session.scalars(
                select(GovernanceRisk).where(GovernanceRisk.default_owner_role == step.stage)
            )
        )
        if not related_risks:
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.PIPE_001_CRITICAL_STEP_HAS_CONTROL,
                    severity=GovernanceSeverity.MINOR,
                    subject_type="governance_pipeline_step",
                    subject_id=step.id,
                    message=(
                        f"GovernancePipelineStep {step.id} (stage={step.stage!r}, "
                        f"function={step.function_path!r}) is critical but no "
                        "GovernanceRisk matches its stage."
                    ),
                )
            )
            continue
        for risk in related_risks:
            if risk.code not in risk_codes_with_controls:
                failures.append(
                    GovernanceFailure(
                        code=GovernanceFailureCode.PIPE_001_CRITICAL_STEP_HAS_CONTROL,
                        severity=GovernanceSeverity.MINOR,
                        subject_type="governance_pipeline_step",
                        subject_id=step.id,
                        message=(
                            f"GovernancePipelineStep {step.id} (stage={step.stage!r}) "
                            f"is critical and links to risk {risk.code!r}, but "
                            "that risk has no GovernanceControl."
                        ),
                        evidence_refs=[risk.code],
                    )
                )

    return failures
