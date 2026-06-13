"""In-memory V3 spatial/address resolution primitives.

This module models the PR7 spatial spine without introducing schema writes. It
only treats a dataset as authoritative when its licence and source version have
both passed the local approval gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from difflib import SequenceMatcher
from enum import StrEnum
from typing import Any


GDA2020_TARGET_CRS = "EPSG:7844"


class LicenceStatus(StrEnum):
    LICENSED = "licensed"
    RESTRICTED = "restricted"
    UNLICENSED = "unlicensed"
    UNKNOWN = "unknown"


class SourceApprovalStatus(StrEnum):
    APPROVED = "approved"
    PENDING_REVIEW = "pending_review"
    REJECTED = "rejected"


class ResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    MISSING_INFO = "missing_info"
    NEEDS_MORE_INFO = "needs_more_info"
    UNSUPPORTED = "unsupported"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class ProvenanceKind(StrEnum):
    SPATIAL_DATASET = "spatial_dataset"
    MANUAL_OVERRIDE = "manual_override"


FactValue = dict[str, Any] | list[Any] | str | int | float | bool | None
ALLOWED_MANUAL_PROPERTY_FACT_TYPES = frozenset(
    {
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
    }
)
PROHIBITED_MANUAL_FACT_VALUE_KEYS = frozenset(
    {
        "assessment_basis",
        "building_class",
        "dwelling_type",
        "new_or_existing",
        "proposal_type",
        "work_type",
    }
)


def normalize_address(value: str) -> str:
    return " ".join(value.replace(",", " ").casefold().split())


# Common WA street-type abbreviations -> the full words G-NAF stores.
# Only unambiguous expansions belong here; "st" is included because trigram /
# token search still matches "St Georges Terrace" through the unexpanded query.
STREET_TYPE_EXPANSIONS: dict[str, str] = {
    "st": "street",
    "rd": "road",
    "ave": "avenue",
    "av": "avenue",
    "cres": "crescent",
    "ct": "court",
    "pl": "place",
    "dr": "drive",
    "drv": "drive",
    "hwy": "highway",
    "tce": "terrace",
    "pde": "parade",
    "bvd": "boulevard",
    "blvd": "boulevard",
    "cl": "close",
    "gr": "grove",
    "gdns": "gardens",
    "cct": "circuit",
    "esp": "esplanade",
    "prom": "promenade",
    "qy": "quay",
    "ln": "lane",
    "wy": "way",
    "ent": "entrance",
    "bwl": "bowl",
    "rtt": "retreat",
    "hts": "heights",
}

STREET_TYPE_TOKENS = frozenset(
    {
        "st",
        "street",
        "rd",
        "road",
        "ave",
        "av",
        "avenue",
        "ln",
        "lane",
        "way",
        "wy",
        "cres",
        "crescent",
        "ct",
        "court",
        "pl",
        "place",
        "dr",
        "drv",
        "drive",
        "hwy",
        "highway",
        "tce",
        "terrace",
        "pde",
        "parade",
        "bvd",
        "blvd",
        "boulevard",
        "cl",
        "close",
        "gr",
        "grove",
        "gdns",
        "gardens",
        "cct",
        "circuit",
        "esp",
        "esplanade",
        "prom",
        "promenade",
        "qy",
        "quay",
        "rise",
        "loop",
        "mews",
        "gate",
        "vista",
        "heights",
        "hts",
        "entrance",
        "ent",
        "retreat",
        "rtt",
        "square",
        "sq",
        "walk",
        "bend",
    }
)


def expand_street_abbreviations(normalized: str) -> str:
    """Expand street-type abbreviations in an already-normalized address.

    The first token (house/lot number) is never expanded.
    """
    tokens = normalized.split()
    if len(tokens) < 2:
        return normalized
    expanded = [tokens[0]] + [STREET_TYPE_EXPANSIONS.get(token, token) for token in tokens[1:]]
    return " ".join(expanded)


def _is_address_number_token(token: str) -> bool:
    if token == "lot":
        return True
    stripped = token.replace("/", "").replace("-", "")
    return bool(stripped) and stripped.isalnum() and any(ch.isdigit() for ch in stripped)


def query_street_name_tokens(normalized_query: str) -> tuple[str, ...]:
    """Extract query terms that should match the street name."""

    tokens = normalized_query.split()
    while tokens and _is_address_number_token(tokens[0]):
        tokens = tokens[1:]
    if len(tokens) <= 1:
        return ()
    street_type_index = next(
        (i for i, token in enumerate(tokens) if token in STREET_TYPE_TOKENS),
        None,
    )
    if street_type_index is not None:
        candidates = tokens[:street_type_index]
    else:
        candidates = tokens[:1]
    return tuple(token for token in candidates if len(token) >= 2)


def _token_close_enough(query_token: str, candidate_token: str) -> bool:
    if query_token == candidate_token:
        return True
    if len(query_token) >= 3 and candidate_token.startswith(query_token):
        return True
    if len(query_token) >= 4 and query_token.startswith(candidate_token):
        return True
    if len(query_token) >= 5 and len(candidate_token) >= 5:
        return SequenceMatcher(None, query_token, candidate_token).ratio() >= 0.86
    return False


def address_candidate_matches_query_street(query: str, candidate: str) -> bool:
    street_tokens = query_street_name_tokens(normalize_address(query))
    if not street_tokens:
        return True
    candidate_tokens = set(normalize_address(candidate).split())
    return any(
        _token_close_enough(query_token, candidate_token)
        for query_token in street_tokens
        for candidate_token in candidate_tokens
    )


# Shared address-match thresholds (used by both stores): a hit below the
# floor is not a credible match; hits within the gap of the best hit are
# treated as ambiguous and surfaced for disambiguation instead of guessed at.
ADDRESS_MATCH_SCORE_FLOOR = 0.55
ADDRESS_MATCH_AMBIGUITY_GAP = 0.08


def leading_house_number(normalized: str) -> str:
    """Return the leading house number token of a normalized address, or ''.

    Handles plain numbers ("3"), unit/lot composites ("3/42" -> "42" is NOT
    assumed — the whole token must be digits to count), and "lot 5" prefixes.
    """
    tokens = normalized.split()
    if not tokens:
        return ""
    first = tokens[0]
    if first == "lot" and len(tokens) > 1 and tokens[1].isdigit():
        return tokens[1]
    if first.isdigit():
        return first
    return ""


def prohibited_manual_fact_value_keys(value: FactValue) -> frozenset[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = str(key).strip().lower()
            if normalized_key in PROHIBITED_MANUAL_FACT_VALUE_KEYS:
                found.add(normalized_key)
            found.update(prohibited_manual_fact_value_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(prohibited_manual_fact_value_keys(child))
    return frozenset(found)


@dataclass(frozen=True)
class SpatialDatasetMetadata:
    dataset_id: str
    name: str
    provider: str
    version: str
    licence: str
    licence_status: LicenceStatus
    source_crs: str
    source_version_id: str | None = None
    approval_status: SourceApprovalStatus = SourceApprovalStatus.PENDING_REVIEW
    target_crs: str = GDA2020_TARGET_CRS
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    refresh_due: datetime | None = None

    def is_authoritative(self) -> bool:
        return (
            self.licence_status == LicenceStatus.LICENSED
            and self.approval_status == SourceApprovalStatus.APPROVED
            and bool(self.source_version_id)
            and self.target_crs == GDA2020_TARGET_CRS
        )

    def provenance(self, method: str, detail: str | None = None) -> "ResolutionProvenance":
        return ResolutionProvenance(
            kind=ProvenanceKind.SPATIAL_DATASET,
            method=method,
            dataset_id=self.dataset_id,
            source_version_id=self.source_version_id,
            source_crs=self.source_crs,
            target_crs=self.target_crs,
            licence_status=self.licence_status,
            approval_status=self.approval_status,
            detail=detail,
        )


@dataclass(frozen=True)
class DatasetImportResult:
    dataset_id: str
    accepted: bool
    authoritative: bool
    target_crs: str
    reason: str


@dataclass(frozen=True)
class ResolutionProvenance:
    kind: ProvenanceKind
    method: str
    target_crs: str = GDA2020_TARGET_CRS
    dataset_id: str | None = None
    source_version_id: str | None = None
    source_crs: str | None = None
    licence_status: LicenceStatus | None = None
    approval_status: SourceApprovalStatus | None = None
    manual_override_id: str | None = None
    detail: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class AddressPoint:
    address_id: str
    formatted_address: str
    lon: float
    lat: float
    parcel_id: str
    dataset_id: str
    aliases: tuple[str, ...] = ()
    gnaf_pid: str | None = None
    target_crs: str = GDA2020_TARGET_CRS

    def matches_exactly(self, address: str) -> bool:
        normalized = normalize_address(address)
        candidates = (self.formatted_address, *self.aliases)
        return any(normalize_address(candidate) == normalized for candidate in candidates)


@dataclass(frozen=True)
class AddressSearchHit:
    """A ranked G-NAF address candidate.

    Indicative geocode only — never legal proof of title or property identity.
    ``score`` is 0.0-1.0 where 1.0 is an exact normalized match.
    """

    address_id: str
    formatted_address: str
    lat: float
    lon: float
    dataset_id: str
    score: float
    gnaf_pid: str | None = None


@dataclass(frozen=True)
class Parcel:
    parcel_id: str
    lot_plan: str
    local_government: str
    area_m2: float
    dataset_id: str
    target_crs: str = GDA2020_TARGET_CRS
    verification_status: str = "verified"


@dataclass(frozen=True)
class PlanningFeature:
    feature_id: str
    parcel_id: str
    fact_type: str
    value: FactValue
    dataset_id: str
    label: str | None = None
    target_crs: str = GDA2020_TARGET_CRS


@dataclass(frozen=True)
class ManualFact:
    fact_type: str
    value: FactValue
    source_note: str | None = None

    def __post_init__(self) -> None:
        if self.fact_type not in ALLOWED_MANUAL_PROPERTY_FACT_TYPES:
            raise ValueError(f"manual override fact_type is not a property fact: {self.fact_type}")
        prohibited_keys = prohibited_manual_fact_value_keys(self.value)
        if prohibited_keys:
            keys = ", ".join(sorted(prohibited_keys))
            raise ValueError(f"manual override value contains proposal-only keys: {keys}")


@dataclass(frozen=True)
class ManualOverride:
    override_id: str
    project_id: str
    entered_by: str
    reason: str
    address: str | None = None
    facts: tuple[ManualFact, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def provenance(self) -> ResolutionProvenance:
        return ResolutionProvenance(
            kind=ProvenanceKind.MANUAL_OVERRIDE,
            method="manual_override",
            manual_override_id=self.override_id,
            detail=self.reason,
            created_at=self.created_at,
        )


@dataclass(frozen=True)
class PropertyFact:
    fact_id: str
    fact_type: str
    value: FactValue
    provenance: ResolutionProvenance
    confidence: Confidence = Confidence.LOW
    review_status: str = "pending_review"


@dataclass(frozen=True)
class PropertyProfile:
    org_id: str
    project_id: str
    resolution_status: ResolutionStatus
    confidence: Confidence
    address: str | None = None
    address_point_id: str | None = None
    parcel_id: str | None = None
    local_government: str | None = None
    facts: tuple[PropertyFact, ...] = ()
    provenance: tuple[ResolutionProvenance, ...] = ()
    issues: tuple[str, ...] = ()
    target_crs: str = GDA2020_TARGET_CRS


class InMemorySpatialDatasetStore:
    def __init__(self) -> None:
        self.datasets: dict[str, SpatialDatasetMetadata] = {}
        self.address_points: dict[str, AddressPoint] = {}
        self.parcels: dict[str, Parcel] = {}
        self.planning_features: list[PlanningFeature] = []
        self.project_profiles: dict[tuple[str, str], PropertyProfile] = {}

    def import_dataset(
        self,
        metadata: SpatialDatasetMetadata,
        *,
        require_authoritative: bool = True,
    ) -> DatasetImportResult:
        authoritative = metadata.is_authoritative()
        if require_authoritative and not authoritative:
            return DatasetImportResult(
                dataset_id=metadata.dataset_id,
                accepted=False,
                authoritative=False,
                target_crs=metadata.target_crs,
                reason="dataset_not_authoritative_for_spatial_resolution",
            )
        self.datasets[metadata.dataset_id] = metadata
        return DatasetImportResult(
            dataset_id=metadata.dataset_id,
            accepted=True,
            authoritative=authoritative,
            target_crs=metadata.target_crs,
            reason="dataset_registered",
        )

    def add_address_point(self, address_point: AddressPoint) -> None:
        self.address_points[address_point.address_id] = address_point

    def add_parcel(self, parcel: Parcel) -> None:
        self.parcels[parcel.parcel_id] = parcel

    def add_planning_feature(self, feature: PlanningFeature) -> None:
        self.planning_features.append(feature)

    def dataset_for(self, dataset_id: str) -> SpatialDatasetMetadata | None:
        return self.datasets.get(dataset_id)

    def is_authoritative_dataset(self, dataset_id: str) -> bool:
        dataset = self.dataset_for(dataset_id)
        return bool(dataset and dataset.is_authoritative())

    def exact_address_points(self, address: str) -> list[AddressPoint]:
        """Best address-point match(es) — exact first, then ranked search.

        Mirrors ``PostGISSpatialDatasetStore.exact_address_points``: exact
        normalized matches win; otherwise a clear search winner is returned
        alone, near-tied candidates are all returned (reported as ambiguous
        by the resolution service), and weak matches return nothing.
        """
        exact = [point for point in self.address_points.values() if point.matches_exactly(address)]
        if exact:
            return exact
        hits = self.search_address_points(address, limit=5)
        strong = [hit for hit in hits if hit.score >= ADDRESS_MATCH_SCORE_FLOOR]
        if not strong:
            return []
        top = strong[0]
        ties = [hit for hit in strong if (top.score - hit.score) < ADDRESS_MATCH_AMBIGUITY_GAP]
        selected = ties if len(ties) > 1 else [top]
        by_id = {point.address_id: point for point in self.address_points.values()}
        return [by_id[hit.address_id] for hit in selected if hit.address_id in by_id]

    def search_address_points(self, query: str, limit: int = 8) -> list[AddressSearchHit]:
        """Rank address points against a free-text query (typeahead search).

        Token-based scoring: exact normalized match scores 1.0; prefix matches
        0.95; otherwise the fraction of query tokens present in the candidate
        (scaled to 0.9). When the query leads with a house number, candidates
        missing that number are suppressed so "3 X Rise" never outranks the
        right street with the wrong number.
        """
        normalized_query = normalize_address(query)
        if not normalized_query:
            return []
        query_variants = {normalized_query, expand_street_abbreviations(normalized_query)}
        house_number = leading_house_number(normalized_query)

        scored: list[tuple[float, AddressPoint]] = []
        for point in self.address_points.values():
            best = 0.0
            for candidate in (point.formatted_address, *point.aliases):
                if not address_candidate_matches_query_street(normalized_query, candidate):
                    continue
                normalized_candidate = normalize_address(candidate)
                candidate_tokens = set(normalized_candidate.split())
                for variant in query_variants:
                    if normalized_candidate == variant:
                        score = 1.0
                    elif normalized_candidate.startswith(variant):
                        score = 0.95
                    else:
                        variant_tokens = variant.split()
                        matched = sum(1 for token in variant_tokens if token in candidate_tokens)
                        score = (matched / len(variant_tokens)) * 0.9 if variant_tokens else 0.0
                    if house_number and house_number not in candidate_tokens:
                        score = min(score, 0.4)
                    best = max(best, score)
            if best >= 0.5:
                scored.append((best, point))

        scored.sort(key=lambda item: (-item[0], item[1].formatted_address))
        return [
            AddressSearchHit(
                address_id=point.address_id,
                formatted_address=point.formatted_address,
                lat=point.lat,
                lon=point.lon,
                dataset_id=point.dataset_id,
                score=round(score, 4),
                gnaf_pid=point.gnaf_pid,
            )
            for score, point in scored[: max(1, limit)]
        ]

    def parcel_for_address_point(self, point: AddressPoint) -> Parcel | None:
        """Return the parcel an address point belongs to, or None."""
        return self.parcels.get(point.parcel_id)

    def planning_for_parcel(self, parcel_id: str) -> list[PlanningFeature]:
        return [feature for feature in self.planning_features if feature.parcel_id == parcel_id]

    def save_profile(self, profile: PropertyProfile) -> None:
        self.project_profiles[(profile.org_id, profile.project_id)] = profile

    def profile_for_project(self, *, org_id: str, project_id: str) -> PropertyProfile | None:
        return self.project_profiles.get((org_id, project_id))


class AddressResolutionService:
    def __init__(self, store: InMemorySpatialDatasetStore | None = None) -> None:
        self.store = store or create_default_spatial_store()

    def resolve_address(
        self,
        org_id: str,
        project_id: str,
        address: str | None,
        manual_override: ManualOverride | None = None,
    ) -> PropertyProfile:
        if manual_override is not None:
            profile = self._manual_override_profile(org_id, project_id, address, manual_override)
            self.store.save_profile(profile)
            return profile

        if not address or not address.strip():
            profile = self._empty_profile(
                org_id=org_id,
                project_id=project_id,
                address=address,
                status=ResolutionStatus.MISSING_INFO,
                confidence=Confidence.NONE,
                issues=("address_required", "parcel_not_verified"),
            )
            self.store.save_profile(profile)
            return profile

        matches = self.store.exact_address_points(address)
        authoritative_matches = [
            point for point in matches if self.store.is_authoritative_dataset(point.dataset_id)
        ]
        if matches and not authoritative_matches:
            profile = self._empty_profile(
                org_id=org_id,
                project_id=project_id,
                address=address,
                status=ResolutionStatus.UNSUPPORTED,
                confidence=Confidence.NONE,
                issues=(
                    "licensed_authoritative_dataset_not_available",
                    "parcel_not_verified",
                ),
            )
            self.store.save_profile(profile)
            return profile
        if len(authoritative_matches) > 1:
            profile = self._empty_profile(
                org_id=org_id,
                project_id=project_id,
                address=address,
                status=ResolutionStatus.NEEDS_MORE_INFO,
                confidence=Confidence.MEDIUM,
                issues=("multiple_address_points_match", "parcel_not_verified"),
            )
            self.store.save_profile(profile)
            return profile
        if not authoritative_matches:
            profile = self._empty_profile(
                org_id=org_id,
                project_id=project_id,
                address=address,
                status=ResolutionStatus.MISSING_INFO,
                confidence=Confidence.NONE,
                issues=("address_point_not_found", "parcel_not_verified"),
            )
            self.store.save_profile(profile)
            return profile

        point = authoritative_matches[0]
        parcel = self.store.parcel_for_address_point(point)
        if parcel is None or not self.store.is_authoritative_dataset(parcel.dataset_id):
            profile = self._point_only_profile(
                org_id=org_id,
                project_id=project_id,
                point=point,
            )
            self.store.save_profile(profile)
            return profile

        profile = self._resolved_profile(
            org_id=org_id,
            project_id=project_id,
            address=address,
            point=point,
            parcel=parcel,
        )
        self.store.save_profile(profile)
        return profile

    def search_addresses(self, query: str, limit: int = 8) -> list[AddressSearchHit]:
        """Search authoritative address points for typeahead/disambiguation.

        Results are indicative geocodes only — never legal proof of title or
        property identity.
        """
        hits = self.store.search_address_points(query, limit=limit)
        return [hit for hit in hits if self.store.is_authoritative_dataset(hit.dataset_id)]

    def property_for_project(self, *, org_id: str, project_id: str) -> PropertyProfile:
        profile = self.store.profile_for_project(org_id=org_id, project_id=project_id)
        if profile is not None:
            return profile
        return self._empty_profile(
            org_id=org_id,
            project_id=project_id,
            address=None,
            status=ResolutionStatus.MISSING_INFO,
            confidence=Confidence.NONE,
            issues=("address_not_resolved", "parcel_not_verified"),
        )

    def _manual_override_profile(
        self,
        org_id: str,
        project_id: str,
        address: str | None,
        manual_override: ManualOverride,
    ) -> PropertyProfile:
        provenance = manual_override.provenance()
        facts = tuple(
            PropertyFact(
                fact_id=f"manual:{manual_override.override_id}:{index}",
                fact_type=fact.fact_type,
                value=fact.value,
                provenance=provenance,
                confidence=Confidence.LOW,
                review_status="pending_review",
            )
            for index, fact in enumerate(manual_override.facts, start=1)
        )
        return PropertyProfile(
            org_id=org_id,
            project_id=project_id,
            resolution_status=ResolutionStatus.NEEDS_MORE_INFO,
            confidence=Confidence.LOW,
            address=manual_override.address or address,
            facts=facts,
            provenance=(provenance,),
            issues=("manual_override_requires_review",),
        )

    def _resolved_profile(
        self,
        *,
        org_id: str,
        project_id: str,
        address: str,
        point: AddressPoint,
        parcel: Parcel,
    ) -> PropertyProfile:
        point_dataset = self.store.dataset_for(point.dataset_id)
        parcel_dataset = self.store.dataset_for(parcel.dataset_id)
        if point_dataset is None or parcel_dataset is None:
            return self._empty_profile(
                org_id=org_id,
                project_id=project_id,
                address=address,
                status=ResolutionStatus.MISSING_INFO,
                confidence=Confidence.LOW,
                issues=("approved_source_version_not_available", "parcel_not_verified"),
            )

        point_provenance = point_dataset.provenance(
            method="gnaf_exact_match",
            detail="Exact address match against approved/licensed address-point fixture.",
        )
        parcel_provenance = parcel_dataset.provenance(
            method="parcel_link",
            detail="Address point linked to approved/licensed cadastral parcel fixture.",
        )
        parcel_verified = parcel.verification_status == "verified"
        parcel_confidence = Confidence.HIGH if parcel_verified else Confidence.MEDIUM
        parcel_review_status = "accepted" if parcel_verified else "pending_review"
        facts: list[PropertyFact] = [
            PropertyFact(
                fact_id=f"{project_id}:address",
                fact_type="address",
                value={"formatted_address": point.formatted_address, "gnaf_pid": point.gnaf_pid},
                provenance=point_provenance,
                confidence=parcel_confidence,
                review_status=parcel_review_status,
            ),
            PropertyFact(
                fact_id=f"{project_id}:parcel",
                fact_type="parcel",
                value={
                    "parcel_id": parcel.parcel_id,
                    "lot_plan": parcel.lot_plan,
                    "verification_status": parcel.verification_status,
                },
                provenance=parcel_provenance,
                confidence=parcel_confidence,
                review_status=parcel_review_status,
            ),
            PropertyFact(
                fact_id=f"{project_id}:local_government",
                fact_type="local_government",
                value={"name": parcel.local_government},
                provenance=parcel_provenance,
                confidence=parcel_confidence,
                review_status=parcel_review_status,
            ),
        ]
        if parcel_verified and parcel.area_m2 > 0:
            facts.append(
                PropertyFact(
                    fact_id=f"{project_id}:lot_area_m2",
                    fact_type="lot_area_m2",
                    value={"value": parcel.area_m2, "unit": "m2"},
                    provenance=parcel_provenance,
                    confidence=Confidence.HIGH,
                    review_status="accepted",
                )
            )
        provenance = [point_provenance, parcel_provenance]
        for feature in self.store.planning_for_parcel(parcel.parcel_id):
            dataset = self.store.dataset_for(feature.dataset_id)
            if dataset is None or not dataset.is_authoritative():
                continue
            feature_provenance = dataset.provenance(
                method="parcel_planning_feature_intersection",
                detail=feature.label,
            )
            facts.append(
                PropertyFact(
                    fact_id=f"{project_id}:{feature.fact_type}:{feature.feature_id}",
                    fact_type=feature.fact_type,
                    value=feature.value,
                    provenance=feature_provenance,
                    confidence=Confidence.HIGH,
                    review_status="accepted",
                )
            )
            provenance.append(feature_provenance)

        return PropertyProfile(
            org_id=org_id,
            project_id=project_id,
            resolution_status=(
                ResolutionStatus.RESOLVED if parcel_verified else ResolutionStatus.NEEDS_MORE_INFO
            ),
            confidence=Confidence.HIGH if parcel_verified else Confidence.MEDIUM,
            address=point.formatted_address,
            address_point_id=point.address_id,
            parcel_id=parcel.parcel_id,
            local_government=parcel.local_government,
            facts=tuple(facts),
            provenance=tuple(provenance),
            issues=()
            if parcel_verified
            else ("parcel_needs_authoritative_import", "planning_sources_pending_import"),
        )

    def _point_only_profile(
        self,
        *,
        org_id: str,
        project_id: str,
        point: AddressPoint,
    ) -> PropertyProfile:
        """Profile for an address point matched without parcel coverage.

        The canonical G-NAF address and coordinates are still returned so the
        user gets the specific match even where cadastre import is pending.
        """
        point_dataset = self.store.dataset_for(point.dataset_id)
        facts: tuple[PropertyFact, ...] = ()
        provenance: tuple[ResolutionProvenance, ...] = ()
        if point_dataset is not None:
            point_provenance = point_dataset.provenance(
                method="gnaf_address_match",
                detail="Address point matched; cadastral parcel not yet available.",
            )
            facts = (
                PropertyFact(
                    fact_id=f"{project_id}:address",
                    fact_type="address",
                    value={
                        "formatted_address": point.formatted_address,
                        "gnaf_pid": point.gnaf_pid,
                        "lat": point.lat,
                        "lon": point.lon,
                    },
                    provenance=point_provenance,
                    confidence=Confidence.MEDIUM,
                    review_status="pending_review",
                ),
            )
            provenance = (point_provenance,)
        return PropertyProfile(
            org_id=org_id,
            project_id=project_id,
            resolution_status=ResolutionStatus.MISSING_INFO,
            confidence=Confidence.LOW,
            address=point.formatted_address,
            address_point_id=point.address_id,
            facts=facts,
            provenance=provenance,
            issues=("parcel_not_verified",),
        )

    def _empty_profile(
        self,
        *,
        org_id: str,
        project_id: str,
        address: str | None,
        status: ResolutionStatus,
        confidence: Confidence,
        issues: tuple[str, ...],
    ) -> PropertyProfile:
        return PropertyProfile(
            org_id=org_id,
            project_id=project_id,
            resolution_status=status,
            confidence=confidence,
            address=address,
            facts=(),
            provenance=(),
            issues=issues,
        )


def create_default_spatial_store() -> InMemorySpatialDatasetStore:
    store = InMemorySpatialDatasetStore()
    gnaf_dataset = SpatialDatasetMetadata(
        dataset_id="fixture-gnaf-wa-2026-q2",
        name="G-NAF WA address points fixture",
        provider="data.gov.au fixture",
        version="2026-Q2",
        licence="approved fixture licence",
        licence_status=LicenceStatus.LICENSED,
        approval_status=SourceApprovalStatus.APPROVED,
        source_crs=GDA2020_TARGET_CRS,
        target_crs=GDA2020_TARGET_CRS,
        source_version_id="source-version:g-naf-wa:2026-q2",
    )
    cadastre_dataset = SpatialDatasetMetadata(
        dataset_id="fixture-wa-cadastre-2026-06",
        name="WA cadastre fixture",
        provider="Landgate fixture",
        version="2026-06",
        licence="approved fixture licence",
        licence_status=LicenceStatus.LICENSED,
        approval_status=SourceApprovalStatus.APPROVED,
        source_crs="EPSG:4283",
        target_crs=GDA2020_TARGET_CRS,
        source_version_id="source-version:wa-cadastre:2026-06",
    )
    planning_dataset = SpatialDatasetMetadata(
        dataset_id="fixture-cockburn-planning-2026-06",
        name="Cockburn planning features fixture",
        provider="local planning fixture",
        version="2026-06",
        licence="approved fixture licence",
        licence_status=LicenceStatus.LICENSED,
        approval_status=SourceApprovalStatus.APPROVED,
        source_crs=GDA2020_TARGET_CRS,
        target_crs=GDA2020_TARGET_CRS,
        source_version_id="source-version:cockburn-planning:2026-06",
    )
    store.import_dataset(gnaf_dataset)
    store.import_dataset(cadastre_dataset)
    store.import_dataset(planning_dataset)
    store.add_parcel(
        Parcel(
            parcel_id="parcel-cockburn-fixture-1",
            lot_plan="Lot 1 on P12345",
            local_government="City of Cockburn",
            area_m2=500.0,
            dataset_id=cadastre_dataset.dataset_id,
        )
    )
    store.add_parcel(
        Parcel(
            parcel_id="parcel-cockburn-black-swan-rise-canary",
            lot_plan="pending authoritative cadastre import",
            local_government="City of Cockburn",
            area_m2=0.0,
            dataset_id=cadastre_dataset.dataset_id,
            verification_status="canary_pending_authoritative_import",
        )
    )
    store.add_address_point(
        AddressPoint(
            address_id="address-gnaf-fixture-1",
            gnaf_pid="GNAF-WA-FIXTURE-1",
            formatted_address="1 Example Street, Spearwood WA 6163",
            aliases=("1 Example Street, Spearwood WA",),
            lon=115.005,
            lat=-31.995,
            parcel_id="parcel-cockburn-fixture-1",
            dataset_id=gnaf_dataset.dataset_id,
        )
    )
    store.add_address_point(
        AddressPoint(
            address_id="address-gnaf-black-swan-rise-canary",
            gnaf_pid="GNAF-WA-BLACK-SWAN-RISE-CANARY",
            formatted_address="3 Black Swan Rise, Beeliar WA 6164",
            aliases=(
                "3 Black Swan Rise Beeliar WA 6164",
                "3 Black Swan Rise, Beeliar WA",
                "3 Black Swan Rise Beeliar WA",
            ),
            lon=115.82,
            lat=-32.13,
            parcel_id="parcel-cockburn-black-swan-rise-canary",
            dataset_id=gnaf_dataset.dataset_id,
        )
    )
    store.add_planning_feature(
        PlanningFeature(
            feature_id="planning-zone-r40",
            parcel_id="parcel-cockburn-fixture-1",
            fact_type="zone",
            label="Residential R40",
            value={"label": "Residential", "code": "R40"},
            dataset_id=planning_dataset.dataset_id,
        )
    )
    return store
