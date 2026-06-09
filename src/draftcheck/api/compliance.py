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

import os
from collections.abc import Generator
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from draftcheck.api.auth import get_current_session
from draftcheck.checks.engine import ComplianceEngine
from draftcheck.db.engine import create_session_factory
from draftcheck.db.models import CheckResult, CheckRun
from draftcheck.domain.identity import ActiveSession

router = APIRouter(prefix="/compliance", tags=["compliance"])

_engine = ComplianceEngine()


# ---------------------------------------------------------------------------
# DB session dependency (mirrors projects.py)
# ---------------------------------------------------------------------------


def get_db_session() -> Generator[Session, None, None]:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URL is not configured; durable storage unavailable.",
        )
    factory = create_session_factory(database_url)
    db: Session = factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db_session)]


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class CheckResultItemResponse(BaseModel):
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
    return CheckResultItemResponse(
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
