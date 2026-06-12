"""Compliance API router — Tier-1 deterministic engine endpoints.

Endpoints:

  POST /compliance/projects/{project_id}/run
      Creates a CheckRun, executes the engine, persists results.
      Returns the full advisory result set.

  GET  /compliance/projects/{project_id}/matrix
      Returns the latest CheckRun for the project with all results.

  GET  /compliance/runs/{run_id}
      Returns a specific CheckRun and its results.

Advisory disclaimer: all statuses (likely_pass / likely_fail /
needs_more_info / unsupported) are advisory only and must not be
interpreted as final legal, planning, or certification compliance.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from draftcheck.api.auth import get_current_session
from draftcheck.api.deps import get_db_session
from draftcheck.checks.engine import ComplianceEngine
from draftcheck.db.models import AuditEvent, CheckResult, CheckRun
from draftcheck.domain.identity import ActiveSession, IdentityRole, normalize_role

router = APIRouter(prefix="/compliance", tags=["compliance"])

_engine = ComplianceEngine()


DbSession = Annotated[Session, Depends(get_db_session)]


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class CheckResultItemResponse(BaseModel):
    result_id: str
    check_key: str
    display_name: str
    status: str = Field(
        description="likely_pass | likely_fail | needs_more_info | unsupported"
    )
    threshold_value: float | None
    threshold_unit: str | None
    measured_value: float | None
    rule_id: str | None
    rule_quote: str | None
    citation: str | None
    note: str | None
    missing_info_reason: str | None
    drawing_evidence: dict[str, Any]
    review_reason: str | None
    human_override: dict[str, Any]
    reviewed_by_user_id: str | None
    reviewed_at: datetime | None


class CheckResultOverrideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["record_review", "flag_for_revision", "operator_note"]
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason")
    @classmethod
    def _reason_must_have_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("reason is required")
        return stripped


class ComplianceRunResponse(BaseModel):
    run_id: str
    project_id: str
    org_id: str
    status: str
    as_of_date: datetime
    engine_version: str
    advisory_disclaimer: str
    results: list[CheckResultItemResponse]


class ComplianceMatrixResponse(BaseModel):
    run_id: str
    project_id: str
    org_id: str
    status: str
    as_of_date: datetime
    engine_version: str
    advisory_disclaimer: str
    results: list[CheckResultItemResponse]


_DISCLAIMER = (
    "Results are advisory only (likely_pass / likely_fail / needs_more_info / unsupported). "
    "They are not final legal, planning, building, or certification compliance determinations."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_org_id(active_session: ActiveSession) -> str:
    if active_session.org is not None:
        return str(active_session.org.id)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Cannot determine org_id: no authenticated org.",
    )


def _require_review_actor(active_session: ActiveSession) -> None:
    allowed_roles = {
        IdentityRole.OWNER,
        IdentityRole.OPERATOR,
        IdentityRole.COMPLIANCE_OWNER,
    }
    try:
        role = normalize_role(active_session.user.role)
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compliance result review requires an owner or operator role.",
        ) from exc
    if role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compliance result review requires an owner or operator role.",
        )


def _check_result_response(row: CheckResult) -> CheckResultItemResponse:
    from draftcheck.checks.registry import TIER1_CHECKS, TIER2_CHECKS

    _display_map = {cd.key: cd.name for cd in TIER1_CHECKS + TIER2_CHECKS}

    req = row.requirement_json or {}
    prop = row.proposed_json or {}
    trace = row.decision_trace_json or {}
    citations = row.citations_json or []
    citation = citations[0] if citations else None

    _tv = req.get("threshold_value")
    _tu = req.get("threshold_unit")
    _mv = prop.get("measured_value")
    _ri = req.get("rule_id")
    _note = trace.get("note")
    _missing_info_reason = trace.get("missing_info_reason")
    return CheckResultItemResponse(
        result_id=str(row.id),
        check_key=row.check_key,
        display_name=_display_map.get(row.check_key, row.check_key),
        status=row.status,
        threshold_value=float(str(_tv)) if _tv is not None else None,
        threshold_unit=str(_tu) if _tu is not None else None,
        measured_value=float(str(_mv)) if _mv is not None else None,
        rule_id=str(_ri) if _ri is not None else None,
        rule_quote=row.why_this_applies,
        citation=str(citation) if citation is not None else None,
        note=str(_note) if _note is not None else None,
        missing_info_reason=str(_missing_info_reason) if _missing_info_reason is not None else None,
        drawing_evidence=dict(row.drawing_evidence_json or {}),
        review_reason=row.review_reason,
        human_override=dict(row.human_override_json or {}),
        reviewed_by_user_id=str(row.reviewed_by_user_id) if row.reviewed_by_user_id else None,
        reviewed_at=row.reviewed_at,
    )


def _run_response(run: CheckRun, results: list[CheckResult]) -> ComplianceRunResponse:
    return ComplianceRunResponse(
        run_id=str(run.id),
        project_id=str(run.project_id),
        org_id=str(run.org_id),
        status=run.status,
        as_of_date=run.as_of_date,
        engine_version=run.engine_version,
        advisory_disclaimer=_DISCLAIMER,
        results=[_check_result_response(r) for r in results],
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/projects/{project_id}/run",
    response_model=ComplianceRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run Tier-1 compliance checks for a project",
)
def run_compliance(
    project_id: str,
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
    db: DbSession,
) -> ComplianceRunResponse:
    """Execute the deterministic Tier-1 engine for the project.

    Creates a new CheckRun row, evaluates all Tier-1 check keys against
    approved rules, persists ResolvedRule and CheckResult rows, and returns
    the advisory result set.

    All results are advisory.  Statuses of likely_pass / likely_fail /
    needs_more_info / unsupported are not final compliance determinations.
    """
    org_id = _resolve_org_id(active_session)
    try:
        engine_result = _engine.run_check(
            project_id=project_id,
            org_id=org_id,
            session=db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Load the persisted CheckRun + CheckResult rows to build the response
    run: CheckRun | None = db.get(CheckRun, UUID(engine_result.check_run_id))
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CheckRun was not persisted.",
        )
    results: list[CheckResult] = (
        db.query(CheckResult)
        .filter(CheckResult.check_run_id == run.id)
        .order_by(CheckResult.check_key)
        .all()
    )
    return _run_response(run, results)


@router.get(
    "/projects/{project_id}/matrix",
    response_model=ComplianceMatrixResponse,
    summary="Get the latest compliance matrix for a project",
)
def get_compliance_matrix(
    project_id: str,
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
    db: DbSession,
) -> ComplianceMatrixResponse:
    """Return the most recent completed CheckRun and its results.

    Returns 404 if no compliance run has been executed for this project.
    """
    _resolve_org_id(active_session)

    run: CheckRun | None = (
        db.query(CheckRun)
        .filter(CheckRun.project_id == UUID(project_id))
        .order_by(CheckRun.started_at.desc())
        .first()
    )
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No compliance run found for project {project_id}.",
        )

    results: list[CheckResult] = (
        db.query(CheckResult)
        .filter(CheckResult.check_run_id == run.id)
        .order_by(CheckResult.check_key)
        .all()
    )

    matrix_data = _run_response(run, results)
    return ComplianceMatrixResponse(**matrix_data.model_dump())


@router.post(
    "/results/{result_id}/override",
    response_model=CheckResultItemResponse,
    summary="Record a human review annotation for a compliance result",
)
def record_check_result_override(
    result_id: str,
    payload: CheckResultOverrideRequest,
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
    db: DbSession,
) -> CheckResultItemResponse:
    """Attach a human review note without changing the deterministic verdict."""
    org_id = _resolve_org_id(active_session)
    _require_review_actor(active_session)

    try:
        result_uuid = UUID(result_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance result {result_id} not found.",
        ) from exc

    result: CheckResult | None = db.get(CheckResult, result_uuid)
    if result is None or str(result.org_id) != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance result {result_id} not found.",
        )

    before = {
        "status": result.status,
        "review_reason": result.review_reason,
        "human_override": dict(result.human_override_json or {}),
        "reviewed_by_user_id": str(result.reviewed_by_user_id) if result.reviewed_by_user_id else None,
        "reviewed_at": result.reviewed_at.isoformat() if result.reviewed_at else None,
    }
    now = datetime.now(UTC)
    override = {
        "action": payload.action,
        "reason": payload.reason,
        "recorded_at": now.isoformat(),
        "recorded_by_user_id": str(active_session.user.id),
        "status_unchanged": result.status,
    }

    result.review_reason = payload.reason
    result.human_override_json = override
    result.reviewed_by_user_id = active_session.user.id
    result.reviewed_at = now

    db.add(
        AuditEvent(
            org_id=result.org_id,
            actor_user_id=active_session.user.id,
            event_type="check_result.human_override_recorded",
            action=payload.action,
            subject_type="check_result",
            subject_id=result.id,
            before_json=before,
            after_json={
                "status": result.status,
                "review_reason": result.review_reason,
                "human_override": override,
                "reviewed_by_user_id": str(result.reviewed_by_user_id),
                "reviewed_at": result.reviewed_at.isoformat(),
            },
            metadata_json={
                "project_id": str(result.project_id),
                "check_run_id": str(result.check_run_id),
                "check_key": result.check_key,
                "deterministic_status_preserved": True,
            },
        )
    )
    db.flush()
    return _check_result_response(result)


@router.get(
    "/runs/{run_id}",
    response_model=ComplianceRunResponse,
    summary="Get a specific compliance run and its results",
)
def get_compliance_run(
    run_id: str,
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
    db: DbSession,
) -> ComplianceRunResponse:
    """Return a specific CheckRun by id with all its check results."""
    _resolve_org_id(active_session)

    run: CheckRun | None = db.get(CheckRun, UUID(run_id))
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance run {run_id} not found.",
        )

    results: list[CheckResult] = (
        db.query(CheckResult)
        .filter(CheckResult.check_run_id == run.id)
        .order_by(CheckResult.check_key)
        .all()
    )
    return _run_response(run, results)
