"""V3 address/property router.

The coordinator mounts this router later. Routes here are intentionally relative
to the `/api/v1` contract paths from the master rebuild plan.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from draftcheck.api.auth import get_current_session, require_allowed_origin
from draftcheck.domain.address import (
    GDA2020_TARGET_CRS,
    AddressResolutionService,
    AddressSearchHit,
    ManualFact,
    ManualOverride,
    PropertyFact,
    PropertyProfile,
    ResolutionProvenance,
)
from draftcheck.domain.identity import ActiveSession


router = APIRouter(tags=["projects"])

_address_service: AddressResolutionService | None = None

ManualAddressFactType = Literal[
    "address",
    "parcel",
    "council",
    "local_government",
    "zone",
    "r_code",
    "overlay",
    "bushfire",
    "heritage",
    "lot_area",
    "lot_area_m2",
    "frontage",
    "corner_lot",
    "primary_street",
    "secondary_street",
]


class ManualOverrideFactRequest(BaseModel):
    fact_type: ManualAddressFactType
    value: Any = Field(default_factory=dict)
    source_note: str | None = Field(default=None, max_length=500)


class ManualOverrideRequest(BaseModel):
    override_id: str | None = Field(default=None, max_length=120)
    entered_by: str = Field(default="unknown", max_length=120)
    reason: str = Field(min_length=1, max_length=500)
    address: str | None = Field(default=None, max_length=500)
    facts: list[ManualOverrideFactRequest] = Field(default_factory=list)


class ResolveAddressRequest(BaseModel):
    address: str | None = Field(default=None, max_length=500)
    manual_override: ManualOverrideRequest | None = None


class ProvenanceResponse(BaseModel):
    kind: str
    method: str
    target_crs: str
    dataset_id: str | None
    source_version_id: str | None
    source_crs: str | None
    licence_status: str | None
    approval_status: str | None
    manual_override_id: str | None
    detail: str | None
    created_at: datetime


class PropertyFactResponse(BaseModel):
    fact_id: str
    fact_type: str
    value: Any
    confidence: str
    review_status: str
    provenance: ProvenanceResponse


class PropertyProfileResponse(BaseModel):
    org_id: str
    project_id: str
    resolution_status: str
    confidence: str
    address: str | None
    address_point_id: str | None
    parcel_id: str | None
    local_government: str | None
    target_crs: str
    issues: list[str]
    provenance: list[ProvenanceResponse]
    facts: list[PropertyFactResponse]
    property_facts: list[PropertyFactResponse]


def get_address_service() -> AddressResolutionService:
    global _address_service
    if _address_service is None:
        import os

        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            try:
                from sqlalchemy import create_engine

                from draftcheck.domain.address.postgis_store import PostGISSpatialDatasetStore

                engine = create_engine(database_url)
                postgis_store = PostGISSpatialDatasetStore(engine)
                _address_service = AddressResolutionService(store=postgis_store)  # type: ignore[arg-type]
            except Exception:  # pragma: no cover – PostGIS not available in all envs
                import logging

                logging.getLogger(__name__).warning(
                    "get_address_service: DATABASE_URL is set but PostGIS store failed to "
                    "initialise; falling back to in-memory store",
                    exc_info=True,
                )
                _address_service = AddressResolutionService()
        else:
            _address_service = AddressResolutionService()
    return _address_service


def _manual_override(project_id: str, payload: ManualOverrideRequest | None) -> ManualOverride | None:
    if payload is None:
        return None
    try:
        return ManualOverride(
            override_id=payload.override_id or f"manual-{uuid4().hex}",
            project_id=project_id,
            entered_by=payload.entered_by,
            reason=payload.reason,
            address=payload.address,
            facts=tuple(
                ManualFact(
                    fact_type=fact.fact_type,
                    value=fact.value,
                    source_note=fact.source_note,
                )
                for fact in payload.facts
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


def _provenance_response(provenance: ResolutionProvenance) -> ProvenanceResponse:
    return ProvenanceResponse(
        kind=str(provenance.kind),
        method=provenance.method,
        target_crs=provenance.target_crs or GDA2020_TARGET_CRS,
        dataset_id=provenance.dataset_id,
        source_version_id=provenance.source_version_id,
        source_crs=provenance.source_crs,
        licence_status=str(provenance.licence_status) if provenance.licence_status else None,
        approval_status=str(provenance.approval_status) if provenance.approval_status else None,
        manual_override_id=provenance.manual_override_id,
        detail=provenance.detail,
        created_at=provenance.created_at,
    )


def _fact_response(fact: PropertyFact) -> PropertyFactResponse:
    return PropertyFactResponse(
        fact_id=fact.fact_id,
        fact_type=fact.fact_type,
        value=fact.value,
        confidence=str(fact.confidence),
        review_status=fact.review_status,
        provenance=_provenance_response(fact.provenance),
    )


def _profile_response(profile: PropertyProfile) -> PropertyProfileResponse:
    facts = [_fact_response(fact) for fact in profile.facts]
    return PropertyProfileResponse(
        org_id=profile.org_id,
        project_id=profile.project_id,
        resolution_status=str(profile.resolution_status),
        confidence=str(profile.confidence),
        address=profile.address,
        address_point_id=profile.address_point_id,
        parcel_id=profile.parcel_id,
        local_government=profile.local_government,
        target_crs=profile.target_crs,
        issues=list(profile.issues),
        provenance=[_provenance_response(provenance) for provenance in profile.provenance],
        facts=facts,
        property_facts=facts,
    )


class AddressSearchItem(BaseModel):
    address: str
    address_point_id: str
    gnaf_pid: str | None
    lat: float
    lon: float
    score: float


class AddressSearchResponse(BaseModel):
    items: list[AddressSearchItem]
    count: int
    disclaimer: str = (
        "Indicative geocode matches from the approved address library — "
        "not legal proof of title or property identity."
    )


def _search_item(hit: AddressSearchHit) -> AddressSearchItem:
    return AddressSearchItem(
        address=hit.formatted_address,
        address_point_id=hit.address_id,
        gnaf_pid=hit.gnaf_pid,
        lat=hit.lat,
        lon=hit.lon,
        score=hit.score,
    )


@router.get("/address/search", response_model=AddressSearchResponse)
def search_addresses(
    service: Annotated[AddressResolutionService, Depends(get_address_service)],
    _active_session: Annotated[ActiveSession, Depends(get_current_session)],
    q: str = Query(min_length=3, max_length=200),
    limit: int = Query(default=8, ge=1, le=20),
) -> AddressSearchResponse:
    hits = service.search_addresses(q, limit=limit)
    return AddressSearchResponse(items=[_search_item(hit) for hit in hits], count=len(hits))


@router.post(
    "/projects/{project_id}/resolve-address",
    response_model=PropertyProfileResponse,
)
def resolve_project_address(
    project_id: str,
    payload: ResolveAddressRequest,
    service: Annotated[AddressResolutionService, Depends(get_address_service)],
    _allowed_origin: Annotated[None, Depends(require_allowed_origin)],
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
) -> PropertyProfileResponse:
    profile = service.resolve_address(
        org_id=str(active_session.org.id),
        project_id=project_id,
        address=payload.address,
        manual_override=_manual_override(project_id, payload.manual_override),
    )
    return _profile_response(profile)


@router.get(
    "/projects/{project_id}/property",
    response_model=PropertyProfileResponse,
)
def get_project_property(
    project_id: str,
    service: Annotated[AddressResolutionService, Depends(get_address_service)],
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
) -> PropertyProfileResponse:
    return _profile_response(service.property_for_project(org_id=str(active_session.org.id), project_id=project_id))
