"""V3 Projects API router — Stage 2.

Implements the four frozen-contract endpoints:

  POST /projects               → 201 ProjectResponse
  GET  /projects               → 200 list[ProjectResponse]
  POST /projects/{id}/property/override  → 200 PropertyFactResponse  [authenticated]
  POST /projects/{id}/proposal  → 200 ProposalResponse  [idempotent upsert]

Stage 3 additions:
  GET    /projects/{id}        → 200 ProjectResponse
  PATCH  /projects/{id}        → 200 ProjectResponse
  DELETE /projects/{id}        → 204 No Content  (hard delete)

HARD STOPS — intentionally not implemented here:
  POST /projects/{id}/resolve-address  — owned by api/address.py
  GET  /projects/{id}/property         — owned by api/address.py

Stage 2 safety invariants (must all hold):
  1. dwelling_type is a PROPOSAL FACT.  It MUST NOT appear in PropertyFact.
     override_fact() raises ValueError if fact_type == "dwelling_type";
     this endpoint maps that to 422.
  2. Every PropertyFact override must record provenance (entered_by + reason).
     Missing/empty reason → 422.
  3. POST /projects/{id}/property/override REQUIRES authentication (any session).
     Uses get_current_session — pipeline is fully AI, no special reviewer role.
  4. resolution_status values are advisory — "resolved" is NOT legal proof.
  5. No direct table creation.  Alembic is the sole schema authority.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from draftcheck.api.auth import get_current_session
from draftcheck.api.deps import get_db_session
from draftcheck.api.guest_quota import guest_quota
from draftcheck.db.models import Project, PropertyFact, Proposal
from draftcheck.domain.identity import ActiveSession
from draftcheck.domain.projects.service import (
    ProjectService,
    ProposalService,
    PropertyService,
)


router = APIRouter(prefix="/projects", tags=["projects"])

_project_svc = ProjectService()
_property_svc = PropertyService()
_proposal_svc = ProposalService()




DbSession = Annotated[Session, Depends(get_db_session)]


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    council_scope: str | None = Field(default=None, max_length=200)


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=240)
    council_scope: str | None = Field(default=None, max_length=200)
    proposal_type: str | None = Field(default=None, max_length=80)
    dwelling_type: str | None = Field(default=None, max_length=80)
    building_class: str | None = Field(default=None, max_length=40)
    work_type: str | None = Field(default=None, max_length=80)
    new_or_existing: str | None = Field(default=None, max_length=40)
    lot_type: str | None = Field(default=None, max_length=80)


class ProjectResponse(BaseModel):
    id: str
    org_id: str
    name: str
    status: str
    council_scope: str | None
    created_at: datetime
    updated_at: datetime


class FactOverrideRequest(BaseModel):
    fact_type: str = Field(min_length=1, max_length=80)
    value: Any = Field(default=None)
    reason: str = Field(min_length=1, max_length=500)
    entered_by: str | None = Field(default=None, max_length=120)


class ProvenanceResponse(BaseModel):
    entered_by: str | None
    reason: str | None
    method: str


class PropertyFactResponse(BaseModel):
    fact_id: str
    fact_type: str
    value: Any
    confidence: str | None
    review_status: str
    provenance: ProvenanceResponse


class ProposalRequest(BaseModel):
    proposal_type: str | None = Field(default=None, max_length=80)
    dwelling_type: str | None = Field(default=None, max_length=80)
    building_class: str | None = Field(default=None, max_length=40)
    work_type: str | None = Field(default=None, max_length=80)
    new_or_existing: str | None = Field(default=None, max_length=40)
    lot_type: str | None = Field(default=None, max_length=80)
    primary_street_confirmed: bool = False
    secondary_street_confirmed: bool = False
    source: str | None = Field(default=None, max_length=80)
    confidence: float | None = None


class ProposalResponse(BaseModel):
    id: str
    org_id: str
    project_id: str
    proposal_type: str | None
    dwelling_type: str | None
    building_class: str | None
    work_type: str | None
    new_or_existing: str | None
    lot_type: str | None
    primary_street_confirmed: bool
    secondary_street_confirmed: bool
    source: str | None
    confidence: float | None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _project_response(project: Project) -> ProjectResponse:
    council_scope: str | None = None
    if isinstance(project.metadata_json, dict):
        raw = project.metadata_json.get("council_scope")
        council_scope = str(raw) if raw is not None else None
    return ProjectResponse(
        id=str(project.id),
        org_id=str(project.org_id),
        name=project.name,
        status=project.status,
        council_scope=council_scope,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _fact_response(fact: PropertyFact) -> PropertyFactResponse:
    prov = fact.provenance_json or {}
    value = fact.value_json.get("value") if isinstance(fact.value_json, dict) else fact.value_json
    return PropertyFactResponse(
        fact_id=str(fact.id),
        fact_type=fact.fact_type,
        value=value,
        confidence=str(fact.confidence) if fact.confidence is not None else None,
        review_status=fact.review_status,
        provenance=ProvenanceResponse(
            entered_by=str(prov["entered_by"]) if prov.get("entered_by") is not None else None,
            reason=str(prov["reason"]) if prov.get("reason") is not None else None,
            method=str(prov.get("method") or "manual_override"),
        ),
    )


def _proposal_response(proposal: Proposal) -> ProposalResponse:
    return ProposalResponse(
        id=str(proposal.id),
        org_id=str(proposal.org_id),
        project_id=str(proposal.project_id),
        proposal_type=proposal.proposal_type,
        dwelling_type=proposal.dwelling_type,
        building_class=proposal.building_class,
        work_type=proposal.work_type,
        new_or_existing=proposal.new_or_existing,
        lot_type=proposal.lot_type,
        primary_street_confirmed=proposal.primary_street_confirmed,
        secondary_street_confirmed=proposal.secondary_street_confirmed,
        source=proposal.source,
        confidence=proposal.confidence,
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
    )


def _resolve_org_id(active_session: ActiveSession, project: Project | None) -> str:
    """Return the org_id to use for this request.

    Priority:
      1. Authenticated user's org_id (non-guest session)
      2. Project's own org_id (guest with project context)
      3. 401 if neither is available
    """
    if active_session.org is not None:
        if project is not None and str(project.org_id) != str(active_session.org.id):
            # 404 (not 403) so callers cannot probe for other orgs' project ids.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {str(project.id)!r} not found.",
            )
        return str(active_session.org.id)
    if project is not None:
        return str(project.org_id)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Cannot determine org_id: no authenticated org and no project context.",
    )


def _get_project_or_404(project_id: str, db: Session) -> Project:
    """Fetch a project by id or raise 404."""
    project = _project_svc.get_project(project_id=project_id, session=db)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id!r} not found.",
        )
    return project


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
)
def create_project(
    payload: CreateProjectRequest,
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
    db: DbSession,
    _quota: Annotated[None, Depends(guest_quota("address"))],
) -> ProjectResponse:
    org_id = _resolve_org_id(active_session, None)
    try:
        project = _project_svc.create_project(
            org_id=org_id,
            name=payload.name,
            council_scope=payload.council_scope,
            session=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return _project_response(project)


@router.get(
    "",
    response_model=list[ProjectResponse],
    summary="List projects for the authenticated org",
)
def list_projects(
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
    db: DbSession,
) -> list[ProjectResponse]:
    org_id = _resolve_org_id(active_session, None)
    projects = _project_svc.list_projects(org_id=org_id, session=db)
    return [_project_response(p) for p in projects]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get a project by id",
)
def get_project(
    project_id: str,
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
    db: DbSession,
) -> ProjectResponse:
    project = _get_project_or_404(project_id, db)
    # Ensure the caller belongs to this project's org (or is a guest with org resolved from project).
    _resolve_org_id(active_session, project)
    return _project_response(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update a project's name or metadata fields",
)
def update_project(
    project_id: str,
    payload: UpdateProjectRequest,
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
    db: DbSession,
) -> ProjectResponse:
    """Partial update — only supplied (non-None) fields are written.

    Updatable fields:
      name           — project display name
      council_scope  — stored in metadata_json["council_scope"]

    Proposal-level fields (proposal_type, dwelling_type, building_class,
    work_type, new_or_existing, lot_type) are accepted here for convenience
    but are written via ProposalService.upsert_proposal so the Proposal
    invariants (dwelling_type lives in Proposal, not PropertyFact) are
    always respected.
    """
    project = _get_project_or_404(project_id, db)
    _resolve_org_id(active_session, project)

    # Update core project fields.
    if payload.name is not None:
        project.name = payload.name

    if payload.council_scope is not None:
        meta = dict(project.metadata_json) if isinstance(project.metadata_json, dict) else {}
        meta["council_scope"] = payload.council_scope
        project.metadata_json = meta

    # Update proposal-level fields if any were supplied.
    proposal_fields = {
        k: v
        for k, v in {
            "proposal_type": payload.proposal_type,
            "dwelling_type": payload.dwelling_type,
            "building_class": payload.building_class,
            "work_type": payload.work_type,
            "new_or_existing": payload.new_or_existing,
            "lot_type": payload.lot_type,
        }.items()
        if v is not None
    }
    if proposal_fields:
        try:
            _proposal_svc.upsert_proposal(
                project_id=project_id,
                data=proposal_fields,
                session=db,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    db.flush()
    return _project_response(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project (hard delete)",
)
def delete_project(
    project_id: str,
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
    db: DbSession,
) -> None:
    """Hard-delete a project and all child rows (cascaded by FK constraints).

    Returns 204 No Content on success, 404 if the project does not exist.
    """
    project = _get_project_or_404(project_id, db)
    _resolve_org_id(active_session, project)
    db.delete(project)
    db.flush()


@router.post(
    "/{project_id}/property/override",
    response_model=PropertyFactResponse,
    summary="Override a property fact",
)
def override_property_fact(
    project_id: str,
    payload: FactOverrideRequest,
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
    db: DbSession,
) -> PropertyFactResponse:
    """Override a property fact with manual data.

    INVARIANT 1: dwelling_type is a proposal fact — supplying
    fact_type="dwelling_type" returns 422.

    INVARIANT 2: reason is required and must not be empty.
    """
    if not payload.reason or not payload.reason.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="reason must not be empty for a manual fact override.",
        )
    try:
        fact = _property_svc.override_fact(
            project_id=project_id,
            fact_type=payload.fact_type,
            value=payload.value,
            reason=payload.reason,
            entered_by=payload.entered_by,
            session=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return _fact_response(fact)


@router.post(
    "/{project_id}/proposal",
    response_model=ProposalResponse,
    summary="Upsert the proposal for a project (idempotent)",
)
def upsert_proposal(
    project_id: str,
    payload: ProposalRequest,
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
    db: DbSession,
) -> ProposalResponse:
    """Idempotent upsert — repeated calls with identical data return the same id."""
    try:
        proposal = _proposal_svc.upsert_proposal(
            project_id=project_id,
            data=payload.model_dump(exclude_none=False),
            session=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return _proposal_response(proposal)
