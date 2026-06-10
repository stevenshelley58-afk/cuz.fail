"""V3 address/property router.

The coordinator mounts this router later. Routes here are intentionally relative
to the `/api/v1` contract paths from the master rebuild plan.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from draftcheck.api.auth import get_current_session, require_allowed_origin
from draftcheck.domain.address import (
    GDA2020_TARGET_CRS,
    AddressResolutionService,
    ManualFact,
    ManualOverride,
    PropertyFact,
    PropertyProfile,
    ResolutionProvenance,
)
from draftcheck.domain.identity import ActiveSession


router = APIRouter(tags=["projects"])

_address_service: AddressResolutionService | None = None
_suggest_engine: Any | None = None
_suggest_engine_checked = False

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


class AddressSuggestion(BaseModel):
    address: str
    gnaf_pid: str | None = None


class AddressSuggestResponse(BaseModel):
    query: str
    suggestions: list[AddressSuggestion]


def _get_suggest_engine() -> Any | None:
    global _suggest_engine, _suggest_engine_checked
    if not _suggest_engine_checked:
        _suggest_engine_checked = True
        import os

        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            try:
                from sqlalchemy import create_engine

                _suggest_engine = create_engine(database_url, pool_pre_ping=True)
            except Exception:  # pragma: no cover – DB not available in all envs
                import logging

                logging.getLogger(__name__).warning(
                    "suggest_addresses: failed to create engine from DATABASE_URL",
                    exc_info=True,
                )
    return _suggest_engine


@router.get("/addresses/suggest", response_model=AddressSuggestResponse)
def suggest_addresses(
    q: str,
    _allowed_origin: Annotated[None, Depends(require_allowed_origin)],
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
    limit: int = 8,
) -> AddressSuggestResponse:
    """Predictive G-NAF address suggestions for the chat one-box.

    Indicative geocode candidates only — never legal proof of title or
    property identity. Returns an empty list when no spatial DB is configured.
    """
    query = q.strip()
    limit = max(1, min(limit, 15))
    if len(query) < 3:
        return AddressSuggestResponse(query=query, suggestions=[])

    engine = _get_suggest_engine()
    if engine is None:
        return AddressSuggestResponse(query=query, suggestions=[])

    from sqlalchemy import text as sql_text

    # Both predicates are served by the gin_trgm_ops index on address_text
    # (migration 0014): ILIKE via trigram extraction, `%` via the similarity
    # threshold. similarity() appears only in ORDER BY, computed on the few
    # index-matched rows — never as a table-scan filter.
    trigram_sql = sql_text(
        """
        SELECT address_text, gnaf_pid
        FROM address_points
        WHERE address_text ILIKE :prefix
           OR address_text % :q
        ORDER BY (address_text ILIKE :prefix) DESC,
                 similarity(address_text, :q) DESC,
                 address_text
        LIMIT :limit
        """
    )
    ilike_sql = sql_text(
        """
        SELECT address_text, gnaf_pid
        FROM address_points
        WHERE address_text ILIKE :contains
        ORDER BY (address_text ILIKE :prefix) DESC, address_text
        LIMIT :limit
        """
    )
    params = {
        "q": query,
        "prefix": f"{query}%",
        "contains": f"%{query}%",
        "limit": limit,
    }
    rows: list[Any] = []
    try:
        with engine.connect() as conn:
            rows = list(conn.execute(trigram_sql, params))
    except Exception:
        # pg_trgm unavailable or query failed — fall back to plain ILIKE
        try:
            with engine.connect() as conn:
                rows = list(conn.execute(ilike_sql, params))
        except Exception:  # pragma: no cover – table absent / DB down
            import logging

            logging.getLogger(__name__).warning(
                "suggest_addresses: lookup failed", exc_info=True
            )
            rows = []

    seen: set[str] = set()
    suggestions: list[AddressSuggestion] = []
    for row in rows:
        addr = (row[0] or "").strip()
        if not addr or addr.lower() in seen:
            continue
        seen.add(addr.lower())
        suggestions.append(AddressSuggestion(address=addr, gnaf_pid=row[1]))
    return AddressSuggestResponse(query=query, suggestions=suggestions)


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
