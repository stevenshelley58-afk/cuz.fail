"""Server-to-server Property Check endpoint for Blockwise.

This endpoint is intentionally narrow: it converts LotFile's source-backed
property profile into preliminary agent notes. It must refuse when source
coverage or citation provenance is missing.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from datetime import UTC
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from draftcheck.api.address import get_address_service
from draftcheck.domain.address import (
    AddressResolutionService,
    Confidence,
    PropertyFact,
    PropertyProfile,
    ResolutionProvenance,
    ResolutionStatus,
)


LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["blockwise"])

ClientSituation = Literal[
    "seller_appraisal",
    "buyer_question",
    "investor_subdivision",
    "renovation_extension",
    "general",
]

CitationSourceType = Literal[
    "planning_scheme",
    "local_policy",
    "rcode",
    "overlay",
    "council_page",
    "other",
]

ResultStatus = Literal["success", "no_source", "unsupported", "error"]
ResultConfidence = Literal["low", "medium", "high"]
Severity = Literal["info", "watch", "important"]

DISCLAIMER = (
    "Preliminary planning signals only. Review source links and relevant authority "
    "guidance before relying on results."
)


class AgentPropertyCheckRequest(BaseModel):
    workspaceId: str = Field(min_length=1, max_length=160)
    userId: str = Field(min_length=1, max_length=160)
    address: str = Field(min_length=3, max_length=500)
    clientSituation: ClientSituation
    notes: str | None = Field(default=None, max_length=1500)


class CitationResponse(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=240)
    sourceType: CitationSourceType
    url: str | None = None
    excerpt: str | None = Field(default=None, max_length=1000)
    retrievedAt: str | None = Field(default=None, max_length=80)


class PlanningItemResponse(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=240)
    summary: str = Field(min_length=1, max_length=1200)
    citationIds: list[str] = Field(default_factory=list)
    severity: Severity | None = None


class AgentPropertyCheckResponse(BaseModel):
    status: ResultStatus
    normalizedFacts: dict[str, Any] | None = None
    signals: list[PlanningItemResponse] | None = None
    likelyConstraints: list[PlanningItemResponse] | None = None
    talkingPoints: list[str] | None = None
    citations: list[CitationResponse] | None = None
    disclaimer: str
    confidence: ResultConfidence | None = None
    engineRequestId: str | None = None


class _CitedFact(BaseModel):
    fact: PropertyFact
    citation_id: str

    model_config = {"arbitrary_types_allowed": True}


def _configured_tokens() -> tuple[str, ...]:
    tokens: list[str] = []
    for name in ("BLOCKWISE_ENGINE_TOKEN", "DRAFTCHECK_ENGINE_TOKEN"):
        value = os.getenv(name, "").strip()
        if value:
            tokens.append(value)

    for raw in os.getenv("API_AUTH_KEYS", "").split(","):
        item = raw.strip()
        if not item:
            continue
        token = item.split(":", 1)[1].strip() if ":" in item else item
        if token:
            tokens.append(token)

    return tuple(dict.fromkeys(tokens))


def require_blockwise_engine_token(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> None:
    tokens = _configured_tokens()
    if not tokens:
        LOGGER.error("blockwise_property_check.token_not_configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Property Check engine token is not configured.",
        )

    prefix = "Bearer "
    if not authorization or not authorization.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    presented = authorization[len(prefix) :].strip()
    if not presented or not any(hmac.compare_digest(presented, token) for token in tokens):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid bearer token.")


@router.post(
    "/agent-property-check",
    response_model=AgentPropertyCheckResponse,
)
def agent_property_check(
    payload: AgentPropertyCheckRequest,
    service: Annotated[AddressResolutionService, Depends(get_address_service)],
    _token: Annotated[None, Depends(require_blockwise_engine_token)],
) -> AgentPropertyCheckResponse:
    engine_request_id = uuid4().hex
    try:
        _ensure_blockwise_workspace_org(service, payload.workspaceId)
        profile = service.resolve_address(
            org_id=payload.workspaceId,
            project_id=engine_request_id,
            address=payload.address.strip(),
        )
        return _profile_to_response(profile, payload, service, engine_request_id)
    except Exception:
        LOGGER.exception(
            "blockwise_property_check.failed",
            extra={"engine_request_id": engine_request_id},
        )
        return _error_response(engine_request_id)


def _ensure_blockwise_workspace_org(service: AddressResolutionService, workspace_id: str) -> None:
    ensure_org = getattr(service.store, "ensure_org", None)
    if not callable(ensure_org):
        return

    try:
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        return

    ensure_org(
        org_id=str(workspace_uuid),
        slug=f"blockwise-{workspace_uuid.hex}",
        name=f"Blockwise workspace {workspace_uuid}",
    )


def _profile_to_response(
    profile: PropertyProfile,
    payload: AgentPropertyCheckRequest,
    service: AddressResolutionService,
    engine_request_id: str,
) -> AgentPropertyCheckResponse:
    if profile.resolution_status == ResolutionStatus.UNSUPPORTED:
        return _refusal_response("unsupported", engine_request_id)

    if profile.resolution_status != ResolutionStatus.RESOLVED:
        return _refusal_response("no_source", engine_request_id)

    if profile.confidence in {Confidence.LOW, Confidence.NONE}:
        return _refusal_response("no_source", engine_request_id)

    cited_facts = _cited_facts(profile.facts)
    if not cited_facts:
        return _refusal_response("no_source", engine_request_id)

    citations = _citations_for(cited_facts, service)
    if not citations:
        return _refusal_response("no_source", engine_request_id)

    citation_ids = {citation.id for citation in citations}
    if any(cited_fact.citation_id not in citation_ids for cited_fact in cited_facts):
        return _refusal_response("no_source", engine_request_id)

    signals = _signals_for(cited_facts)
    likely_constraints = _constraints_for(cited_facts)
    if any(not item.citationIds for item in [*signals, *likely_constraints]):
        return _refusal_response("no_source", engine_request_id)

    return AgentPropertyCheckResponse(
        status="success",
        normalizedFacts=_normalized_facts(profile, payload, cited_facts),
        signals=signals,
        likelyConstraints=likely_constraints,
        talkingPoints=_talking_points_for(profile, payload, cited_facts),
        citations=citations,
        disclaimer=DISCLAIMER,
        confidence=_confidence_response(profile.confidence),
        engineRequestId=engine_request_id,
    )


def _refusal_response(status_value: Literal["no_source", "unsupported"], engine_request_id: str) -> AgentPropertyCheckResponse:
    return AgentPropertyCheckResponse(
        status=status_value,
        normalizedFacts={},
        signals=[],
        likelyConstraints=[],
        talkingPoints=[],
        citations=[],
        disclaimer=DISCLAIMER,
        engineRequestId=engine_request_id,
    )


def _error_response(engine_request_id: str) -> AgentPropertyCheckResponse:
    return AgentPropertyCheckResponse(
        status="error",
        normalizedFacts={},
        signals=[],
        likelyConstraints=[],
        talkingPoints=[],
        citations=[],
        disclaimer=DISCLAIMER,
        confidence="low",
        engineRequestId=engine_request_id,
    )


def _cited_facts(facts: tuple[PropertyFact, ...]) -> list[_CitedFact]:
    cited: list[_CitedFact] = []
    for fact in facts:
        source_version_id = fact.provenance.source_version_id
        if not source_version_id:
            continue
        if fact.confidence in {Confidence.LOW, Confidence.NONE}:
            continue
        if fact.review_status not in {"accepted", "pending_review"}:
            continue
        cited.append(
            _CitedFact(
                fact=fact,
                citation_id=_citation_id(fact.provenance),
            )
        )
    return cited


def _citation_id(provenance: ResolutionProvenance) -> str:
    raw = provenance.source_version_id or provenance.dataset_id or uuid4().hex
    if 0 < len(raw) <= 160:
        return raw
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _citations_for(
    cited_facts: list[_CitedFact],
    service: AddressResolutionService,
) -> list[CitationResponse]:
    citations: dict[str, CitationResponse] = {}
    for cited_fact in cited_facts:
        provenance = cited_fact.fact.provenance
        if cited_fact.citation_id in citations:
            continue
        title = _citation_title(provenance, service)
        citations[cited_fact.citation_id] = CitationResponse(
            id=cited_fact.citation_id,
            title=title,
            sourceType=_source_type_for_fact(cited_fact.fact.fact_type),
            retrievedAt=_retrieved_at(provenance),
        )
    return list(citations.values())


def _citation_title(provenance: ResolutionProvenance, service: AddressResolutionService) -> str:
    dataset = None
    if provenance.dataset_id:
        dataset = service.store.dataset_for(provenance.dataset_id)
    if dataset is not None:
        return _truncate(f"{dataset.name}, version {dataset.version}", 240)
    if provenance.dataset_id:
        return _truncate(f"{provenance.dataset_id} source dataset", 240)
    return _truncate(f"{provenance.source_version_id} source version", 240)


def _retrieved_at(provenance: ResolutionProvenance) -> str:
    created_at = provenance.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return created_at.isoformat()


def _source_type_for_fact(fact_type: str) -> CitationSourceType:
    normalized = fact_type.strip().lower()
    if normalized == "r_code":
        return "rcode"
    if normalized == "zone":
        return "planning_scheme"
    if normalized in {"overlay", "bushfire", "heritage", "flood", "coastal", "environmental"}:
        return "overlay"
    if normalized in {"council", "local_government"}:
        return "council_page"
    return "other"


def _normalized_facts(
    profile: PropertyProfile,
    payload: AgentPropertyCheckRequest,
    cited_facts: list[_CitedFact],
) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    for cited_fact in cited_facts:
        fact_type = cited_fact.fact.fact_type
        if fact_type not in facts:
            facts[fact_type] = cited_fact.fact.value
            continue
        existing = facts[fact_type]
        if isinstance(existing, list):
            existing.append(cited_fact.fact.value)
        else:
            facts[fact_type] = [existing, cited_fact.fact.value]

    return {
        "address": profile.address,
        "clientSituation": payload.clientSituation,
        "localGovernment": profile.local_government,
        "resolutionStatus": str(profile.resolution_status),
        "sourceCoverage": "source_cited",
        "facts": facts,
    }


def _signals_for(cited_facts: list[_CitedFact]) -> list[PlanningItemResponse]:
    signals: list[PlanningItemResponse] = []
    for cited_fact in cited_facts:
        fact = cited_fact.fact
        summary = _signal_summary(fact)
        if not summary:
            continue
        signals.append(
            PlanningItemResponse(
                id=_item_id("signal", fact),
                title=_signal_title(fact.fact_type),
                summary=summary,
                citationIds=[cited_fact.citation_id],
                severity="info",
            )
        )
    return signals[:8]


def _constraints_for(cited_facts: list[_CitedFact]) -> list[PlanningItemResponse]:
    constraints: list[PlanningItemResponse] = []
    for cited_fact in cited_facts:
        fact = cited_fact.fact
        summary = _constraint_summary(fact)
        if not summary:
            continue
        constraints.append(
            PlanningItemResponse(
                id=_item_id("constraint", fact),
                title=_constraint_title(fact.fact_type),
                summary=summary,
                citationIds=[cited_fact.citation_id],
                severity="watch",
            )
        )
    return constraints[:6]


def _talking_points_for(
    profile: PropertyProfile,
    payload: AgentPropertyCheckRequest,
    cited_facts: list[_CitedFact],
) -> list[str]:
    fact_types = {cited_fact.fact.fact_type for cited_fact in cited_facts}
    points = [
        f"Use this as preliminary conversation prep for {profile.address or payload.address}.",
        "Keep missing property facts as open questions and review the linked source notes before relying on the result.",
    ]
    if "zone" in fact_types or "r_code" in fact_types:
        points.append(
            "Open the conversation around zoning and density signals, then check the relevant policy pathway before discussing development options."
        )
    if "lot_area_m2" in fact_types or "frontage" in fact_types:
        points.append(
            "Treat lot size and frontage as subdivision indicators only; ask for survey, servicing, access, and council policy review before giving stronger guidance."
        )
    if fact_types.intersection({"overlay", "bushfire", "heritage", "flood", "coastal", "environmental"}):
        points.append(
            "Flag overlays as review items early so the client understands extra constraints may affect timing, design, or referral steps."
        )
    return points[:5]


def _signal_title(fact_type: str) -> str:
    labels = {
        "address": "Address match",
        "parcel": "Parcel signal",
        "local_government": "Local government signal",
        "zone": "Zoning signal",
        "r_code": "R-Code density signal",
        "overlay": "Overlay signal",
        "bushfire": "Bushfire signal",
        "heritage": "Heritage signal",
        "lot_area_m2": "Lot size signal",
        "frontage": "Frontage signal",
    }
    return labels.get(fact_type, f"{_humanize(fact_type)} signal")


def _signal_summary(fact: PropertyFact) -> str | None:
    value = _display_value(fact.value)
    if not value:
        return None
    if fact.fact_type == "address":
        return f"Source-cited address match: {value}."
    if fact.fact_type == "parcel":
        return f"Source-cited parcel note: {value}."
    if fact.fact_type in {"zone", "r_code", "overlay", "bushfire", "heritage"}:
        return f"{_humanize(fact.fact_type)} found in source-cited property data: {value}."
    if fact.fact_type in {"lot_area_m2", "frontage"}:
        return f"{_humanize(fact.fact_type)} found in source-cited property data: {value}."
    if fact.fact_type in {"local_government", "council"}:
        return f"Council area signal from source-cited property data: {value}."
    return f"{_humanize(fact.fact_type)} source-cited note: {value}."


def _constraint_title(fact_type: str) -> str:
    labels = {
        "local_government": "Council policy pathway to review",
        "zone": "Zoning pathway to review",
        "r_code": "R-Code density pathway to review",
        "overlay": "Overlay item to review",
        "bushfire": "Bushfire item to review",
        "heritage": "Heritage item to review",
        "lot_area_m2": "Lot size indicator to review",
        "frontage": "Frontage indicator to review",
    }
    return labels.get(fact_type, f"{_humanize(fact_type)} item to review")


def _constraint_summary(fact: PropertyFact) -> str | None:
    if fact.fact_type == "local_government":
        return "Use the local government signal to find the right council policy pathway before giving client notes."
    if fact.fact_type == "zone":
        return "Review zoning controls and local planning policy before discussing development or use options."
    if fact.fact_type == "r_code":
        return "Review density controls before discussing subdivision, extension, or infill potential."
    if fact.fact_type in {"overlay", "bushfire", "heritage", "flood", "coastal", "environmental"}:
        return "Treat this as a likely constraint and review referral, design, timing, or assessment implications before relying on it."
    if fact.fact_type in {"lot_area_m2", "frontage"}:
        return "Compare this indicator with access, servicing, setbacks, policy settings, and survey information before discussing subdivision potential."
    return None


def _item_id(prefix: str, fact: PropertyFact) -> str:
    raw = f"{prefix}:{fact.fact_id}:{fact.fact_type}"
    return _truncate(hashlib.sha256(raw.encode("utf-8")).hexdigest(), 160)


def _display_value(value: Any) -> str:
    if isinstance(value, dict):
        preferred_keys = (
            "formatted_address",
            "name",
            "label",
            "code",
            "value",
            "lot_plan",
            "parcel_id",
        )
        parts: list[str] = []
        for key in preferred_keys:
            raw = value.get(key)
            if raw is not None and str(raw).strip():
                parts.append(str(raw).strip())
        return " / ".join(dict.fromkeys(parts))
    if isinstance(value, list):
        return ", ".join(_display_value(item) for item in value if _display_value(item))
    if value is None:
        return ""
    return str(value).strip()


def _confidence_response(confidence: Confidence) -> ResultConfidence:
    if confidence == Confidence.HIGH:
        return "high"
    if confidence == Confidence.MEDIUM:
        return "medium"
    return "low"


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip().capitalize()


def _truncate(value: str, limit: int) -> str:
    stripped = " ".join(value.split())
    if len(stripped) <= limit:
        return stripped
    return stripped[: max(0, limit - 1)].rstrip() + "..."
