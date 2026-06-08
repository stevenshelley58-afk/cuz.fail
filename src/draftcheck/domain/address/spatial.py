"""In-memory V3 spatial/address resolution primitives.

This module models the PR7 spatial spine without introducing schema writes. It
only treats a dataset as authoritative when its licence and source version have
both passed the local approval gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
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
    NEEDS_HUMAN_REVIEW = "needs_human_review"
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
class Parcel:
    parcel_id: str
    lot_plan: str
    local_government: str
    area_m2: float
    dataset_id: str
    target_crs: str = GDA2020_TARGET_CRS


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
        return [point for point in self.address_points.values() if point.matches_exactly(address)]

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
                status=ResolutionStatus.NEEDS_HUMAN_REVIEW,
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
        parcel = self.store.parcels.get(point.parcel_id)
        if parcel is None or not self.store.is_authoritative_dataset(parcel.dataset_id):
            profile = self._empty_profile(
                org_id=org_id,
                project_id=project_id,
                address=address,
                status=ResolutionStatus.MISSING_INFO,
                confidence=Confidence.LOW,
                issues=("parcel_not_verified",),
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
            resolution_status=ResolutionStatus.NEEDS_HUMAN_REVIEW,
            confidence=Confidence.LOW,
            address=manual_override.address or address,
            facts=facts,
            provenance=(provenance,),
            issues=("manual_override_requires_human_review",),
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
        facts: list[PropertyFact] = [
            PropertyFact(
                fact_id=f"{project_id}:address",
                fact_type="address",
                value={"formatted_address": point.formatted_address, "gnaf_pid": point.gnaf_pid},
                provenance=point_provenance,
                confidence=Confidence.HIGH,
                review_status="accepted",
            ),
            PropertyFact(
                fact_id=f"{project_id}:parcel",
                fact_type="parcel",
                value={"parcel_id": parcel.parcel_id, "lot_plan": parcel.lot_plan},
                provenance=parcel_provenance,
                confidence=Confidence.HIGH,
                review_status="accepted",
            ),
            PropertyFact(
                fact_id=f"{project_id}:local_government",
                fact_type="local_government",
                value={"name": parcel.local_government},
                provenance=parcel_provenance,
                confidence=Confidence.HIGH,
                review_status="accepted",
            ),
            PropertyFact(
                fact_id=f"{project_id}:lot_area_m2",
                fact_type="lot_area_m2",
                value={"value": parcel.area_m2, "unit": "m2"},
                provenance=parcel_provenance,
                confidence=Confidence.HIGH,
                review_status="accepted",
            ),
        ]
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
            resolution_status=ResolutionStatus.RESOLVED,
            confidence=Confidence.HIGH,
            address=point.formatted_address,
            address_point_id=point.address_id,
            parcel_id=parcel.parcel_id,
            local_government=parcel.local_government,
            facts=tuple(facts),
            provenance=tuple(provenance),
            issues=(),
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
