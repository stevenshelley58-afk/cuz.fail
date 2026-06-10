"""GOV-SRC-* — controlled-document (source) governance checks.

Implements the five source-validators in
docs/process-control/implementation-map.md §6.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from draftcheck.db.models import (
    CheckResult,
    ResolvedRule,
    Source,
    SourceReviewRecord,
    SourceVersion,
)
from draftcheck.governance.types import (
    GovernanceFailure,
    GovernanceFailureCode,
    GovernanceSeverity,
)


if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# Lifecycle states for an active, non-superseded source version. The
# check is "this is the version we trust to answer questions."
_ACTIVE_STATUSES = ("active",)
_NOT_SUPERSEDED = (False,)


def _is_active_version(version: SourceVersion) -> bool:
    """An active source version is non-superseded and not explicitly retired.

    The current model uses ``superseded_by_version_id`` to mark
    supersession; we treat any non-null value as superseded.
    ``metadata_json.retired_at`` is the de-facto retirement signal in
    absence of a dedicated column.
    """
    if version.superseded_by_version_id is not None:
        return False
    retired_at = (version.metadata_json or {}).get("retired_at")
    if retired_at:
        return False
    return True


def _latest_review(session: "Session", version_id: object) -> SourceReviewRecord | None:
    return session.scalars(
        select(SourceReviewRecord)
        .where(SourceReviewRecord.source_version_id == version_id)
        .order_by(SourceReviewRecord.reviewed_at.desc())
        .limit(1)
    ).first()


def validate(session: "Session") -> list[GovernanceFailure]:
    failures: list[GovernanceFailure] = []

    # GOV-SRC-001: active source version must have an owner.
    active_versions = list(
        session.scalars(
            select(SourceVersion).where(SourceVersion.superseded_by_version_id.is_(None))
        )
    )
    for v in active_versions:
        if v.owner_user_id is None:
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.SRC_001_OWNER_REQUIRED,
                    severity=GovernanceSeverity.CRITICAL,
                    subject_type="source_version",
                    subject_id=v.id,
                    message=(
                        f"SourceVersion {v.id} has no owner_user_id. "
                        "Per GOV-SRC-001 every active source must have an owner."
                    ),
                )
            )

        # GOV-SRC-002: review_due_date set and not in the past.
        if v.review_due_date is None:
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.SRC_002_REVIEW_DUE_REQUIRED,
                    severity=GovernanceSeverity.MAJOR,
                    subject_type="source_version",
                    subject_id=v.id,
                    message=(
                        f"SourceVersion {v.id} has no review_due_date. "
                        "Per GOV-SRC-002 every active source must have a review date."
                    ),
                )
            )
        elif isinstance(v.review_due_date, date) and v.review_due_date < datetime.now(UTC).date():
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.SRC_002_REVIEW_DUE_REQUIRED,
                    severity=GovernanceSeverity.MAJOR,
                    subject_type="source_version",
                    subject_id=v.id,
                    message=(
                        f"SourceVersion {v.id} review_due_date {v.review_due_date} "
                        "is in the past. Per GOV-SRC-002 the review is overdue."
                    ),
                )
            )

        # GOV-SRC-003: latest review record approves + license cleared.
        latest = _latest_review(session, v.id)
        if latest is None:
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.SRC_003_LICENCE_APPROVED,
                    severity=GovernanceSeverity.MAJOR,
                    subject_type="source_version",
                    subject_id=v.id,
                    message=(
                        f"SourceVersion {v.id} has no SourceReviewRecord. "
                        "Per GOV-SRC-003 every active source needs an approved review."
                    ),
                )
            )
        else:
            if latest.review_status != "approved":
                failures.append(
                    GovernanceFailure(
                        code=GovernanceFailureCode.SRC_003_LICENCE_APPROVED,
                        severity=GovernanceSeverity.MAJOR,
                        subject_type="source_version",
                        subject_id=v.id,
                        message=(
                            f"SourceVersion {v.id} latest review status is "
                            f"{latest.review_status!r}; expected 'approved'."
                        ),
                    )
                )
            if latest.licence_status not in ("approved", "public", "cc-by"):
                failures.append(
                    GovernanceFailure(
                        code=GovernanceFailureCode.SRC_003_LICENCE_APPROVED,
                        severity=GovernanceSeverity.MAJOR,
                        subject_type="source_version",
                        subject_id=v.id,
                        message=(
                            f"SourceVersion {v.id} licence_status is "
                            f"{latest.licence_status!r}; expected one of "
                            "'approved', 'public', 'cc-by'."
                        ),
                    )
                )

    # GOV-SRC-004: a single Source should not have overlapping effective windows.
    # We only flag versions that are simultaneously non-superseded AND have
    # overlapping effective_from/effective_to ranges.
    sources = list(session.scalars(select(Source)))
    for src in sources:
        versions = list(
            session.scalars(
                select(SourceVersion).where(
                    SourceVersion.source_id == src.id,
                    SourceVersion.superseded_by_version_id.is_(None),
                )
            )
        )
        for i, a in enumerate(versions):
            for b in versions[i + 1 :]:
                if a.effective_from is None or a.effective_to is None:
                    continue
                if b.effective_from is None or b.effective_to is None:
                    continue
                if a.effective_from <= b.effective_to and b.effective_from <= a.effective_to:
                    failures.append(
                        GovernanceFailure(
                            code=GovernanceFailureCode.SRC_004_VERSION_WINDOWS,
                            severity=GovernanceSeverity.MINOR,
                            subject_type="source_version",
                            subject_id=a.id,
                            message=(
                                f"SourceVersion {a.id} and {b.id} for source "
                                f"{src.id} have overlapping effective windows."
                            ),
                            evidence_refs=[str(b.id)],
                        )
                    )

    # GOV-SRC-005: chunks cited from ResolvedRule/CheckResult must come from
    # a source_version whose latest review is approved.
    cited_versions: set[object] = set()
    for rr in session.scalars(select(ResolvedRule)):
        for c in (rr.citations_json or []):
            if isinstance(c, dict) and c.get("source_version_id"):
                cited_versions.add(c["source_version_id"])
    for cr in session.scalars(select(CheckResult)):
        for c in (cr.citations_json or []):
            if isinstance(c, dict) and c.get("source_version_id"):
                cited_versions.add(c["source_version_id"])
    for v_id in cited_versions:
        target: SourceVersion | None = session.get(SourceVersion, v_id)
        if target is None:
            continue
        if not _is_active_version(target):
            continue
        latest = _latest_review(session, v_id)
        if latest is None or latest.review_status != "approved":
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.SRC_005_CHUNK_FROM_APPROVED_VERSION,
                    severity=GovernanceSeverity.MAJOR,
                    subject_type="source_version",
                    subject_id=v.id,
                    message=(
                        f"SourceVersion {v.id} is cited by ResolvedRule/CheckResult "
                        "but its latest review is not 'approved'."
                    ),
                )
            )

    return failures
