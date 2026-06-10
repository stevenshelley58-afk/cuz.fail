"""GOV-EVAL-* — eval follow-up checks.

Implements the one eval-validator in
docs/process-control/implementation-map.md §6.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from draftcheck.db.models import (
    EvalRun,
    GovernanceFinding,
    SkillVersion,
)
from draftcheck.governance.types import (
    GovernanceFailure,
    GovernanceFailureCode,
    GovernanceSeverity,
)


if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _active_skill_version_ids(session: "Session") -> set[str]:
    """Return the set of skill_version_ids currently flagged as 'active'."""
    rows = list(
        session.scalars(
            select(SkillVersion).where(SkillVersion.status == "active")
        )
    )
    return {sv.id for sv in rows}


def validate(session: "Session") -> list[GovernanceFailure]:
    failures: list[GovernanceFailure] = []

    active_skill_versions = _active_skill_version_ids(session)
    if not active_skill_versions:
        return failures

    for ev in session.scalars(select(EvalRun)):
        if ev.skill_version_id not in active_skill_versions:
            continue
        if ev.status != "failed":
            continue
        # Find a GovernanceFinding whose proposed remediation links to this
        # EvalRun, OR a ReviewItem linked to the eval case. We use
        # GovernanceFinding for PR-6's wiring; for PR-3 we accept either.
        finding = session.scalar(
            select(GovernanceFinding.id)
            .where(
                GovernanceFinding.proposed_by_job_trace_id == ev.job_trace_id,
            )
            .limit(1)
        ) if ev.job_trace_id else None
        if finding is None:
            # Fallback: any review_item whose source_json mentions this eval_run.
            from draftcheck.db.models import ReviewItem
            review = session.scalar(
                select(ReviewItem.id)
                .where(
                    ReviewItem.subject_type == "eval_run",
                    ReviewItem.subject_id == ev.id,
                )
                .limit(1)
            )
            if review is None:
                failures.append(
                    GovernanceFailure(
                        code=GovernanceFailureCode.EVAL_001_FAILED_EVAL_HAS_REVIEW,
                        severity=GovernanceSeverity.MAJOR,
                        subject_type="eval_run",
                        subject_id=ev.id,
                        message=(
                            f"EvalRun {ev.id} (skill_version {ev.skill_version_id}) "
                            "is 'failed' for an active skill but has no "
                            "GovernanceFinding or ReviewItem follow-up."
                        ),
                    )
                )

    return failures
