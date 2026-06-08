from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_core.audit import record_audit
from draftcheck_core.json_utils import from_json, to_json
from draftcheck_core.models import (
    AddressFact,
    AddressPoint,
    AddressProfile,
    LocalGovernmentBoundary,
    LocalGovernmentFact,
    Parcel,
    PlanningLayerFeature,
    Project,
    ProjectProposal,
    Property,
    SpatialDataset,
)
from draftcheck_core.project_service import property_to_dict
from draftcheck_core.review_queue import ReviewQueueService
from draftcheck_shared.schemas import (
    AddressFactInput,
    AddressFactRead,
    AddressProfileRead,
    AddressResolveRequest,
    AddressSuggestionRead,
    ProjectProposalRead,
    PropertyProfileRead,
    PropertyResolveRequest,
    PropertyRead,
    ReviewQueueItemCreate,
)

Point = tuple[float, float]


class AddressResolutionService:
    def __init__(self, db: Session):
        self.db = db

    def suggest_addresses(self, query: str, limit: int = 8) -> list[AddressSuggestionRead]:
        target = _normalize_address(query)
        if len(target) < 3:
            return []

        suggestions: list[tuple[int, AddressSuggestionRead]] = []
        seen: set[str] = set()
        for point in self.db.scalars(select(AddressPoint).order_by(AddressPoint.created_at.desc())):
            score = _address_match_score(target, point.address)
            if not score:
                continue
            parcel = self.db.get(Parcel, point.parcel_id) if point.parcel_id else None
            suggestion = AddressSuggestionRead(
                address=point.address,
                formatted_address=point.address,
                local_government=parcel.local_government if parcel else None,
                lot_plan=parcel.lot_plan if parcel else None,
                parcel_id=parcel.id if parcel else point.parcel_id,
                confidence=_suggestion_confidence(score),
                source="address_point",
            )
            key = _normalize_address(suggestion.formatted_address)
            if key in seen:
                continue
            seen.add(key)
            suggestions.append((score, suggestion))

        for project in self.db.scalars(select(Project).order_by(Project.created_at.desc())):
            score = _address_match_score(target, project.address)
            if not score:
                continue
            key = _normalize_address(project.address)
            if key in seen:
                continue
            seen.add(key)
            suggestions.append(
                (
                    min(score, 50),
                    AddressSuggestionRead(
                        address=project.address,
                        formatted_address=project.address,
                        local_government=project.local_government,
                        lot_plan=project.lot_plan,
                        parcel_id=None,
                        confidence="low",
                        source="project_history",
                    ),
                )
            )

        suggestions.sort(key=lambda item: item[0], reverse=True)
        return [suggestion for _score, suggestion in suggestions[:limit]]

    def resolve_address(
        self,
        payload: AddressResolveRequest,
        *,
        project_id: str | None = None,
    ) -> AddressProfileRead:
        as_of_date = payload.as_of_date or _default_as_of_date()
        spatial = self._resolve_spatial_context(payload.address, as_of_date)
        issues = spatial["issues"]
        resolution_status = _resolution_status_for_issues(issues)
        confidence = _confidence_for_resolution(resolution_status)

        profile = AddressProfile(
            project_id=project_id,
            input_address=payload.address,
            formatted_address=spatial["formatted_address"] or payload.address,
            resolution_status=resolution_status,
            confidence=confidence,
            parcel_id=spatial["parcel_id"],
            local_government=spatial["local_government"],
            lot_plan=spatial["lot_plan"],
            resolver_sources_json=to_json(spatial["resolver_sources"]),
            dataset_version_ids_json=to_json(spatial["dataset_version_ids"]),
            issues_json=to_json(issues),
            as_of_date=as_of_date,
            assessment_basis=payload.assessment_basis,
        )
        self.db.add(profile)
        self.db.flush()
        for fact in spatial["facts"]:
            self._add_fact_row(profile.id, fact)
        if spatial["local_government"]:
            self._add_local_government_fact(profile.id, spatial)
        for fact_payload in payload.facts:
            self._add_fact(profile.id, fact_payload)
        self.db.flush()
        self._enqueue_spatial_review_if_required(profile, issues, payload.address)
        record_audit(
            self.db,
            action="address.resolve",
            target_type="address_profile",
            target_id=profile.id,
            project_id=project_id,
            metadata={
                "resolution_status": profile.resolution_status,
                "confidence": profile.confidence,
                "issues": issues,
                "as_of_date": as_of_date,
            },
        )
        return self.profile_to_read(profile)

    def resolve_project_property(
        self,
        project_id: str,
        payload: PropertyResolveRequest,
    ) -> PropertyProfileRead:
        project = self._get_project(project_id)
        request = AddressResolveRequest(
            address=payload.address or project.address,
            as_of_date=payload.as_of_date or project.as_of_date,
            assessment_basis=payload.assessment_basis or project.assessment_basis,  # type: ignore[arg-type]
            facts=payload.facts,
        )
        profile_read = self.resolve_address(request, project_id=project_id)
        prop = self.db.scalar(select(Property).where(Property.project_id == project_id))
        if not prop:
            prop = Property(project_id=project_id, address=profile_read.formatted_address)
            self.db.add(prop)
        prop.address_profile_id = profile_read.id
        prop.address = profile_read.formatted_address
        self._sync_property_from_facts(prop, profile_read.facts)
        self.db.flush()
        record_audit(
            self.db,
            action="property.resolved",
            target_type="property",
            target_id=prop.id,
            project_id=project_id,
            metadata={
                "address_profile_id": profile_read.id,
                "resolution_status": profile_read.resolution_status,
            },
        )
        return self.property_profile(project_id)

    def property_profile(self, project_id: str) -> PropertyProfileRead:
        self._get_project(project_id)
        prop = self.db.scalar(select(Property).where(Property.project_id == project_id))
        profile = None
        if prop and prop.address_profile_id:
            address_profile = self.db.get(AddressProfile, prop.address_profile_id)
            profile = self.profile_to_read(address_profile) if address_profile else None
        if not profile:
            address_profile = self.db.scalar(
                select(AddressProfile)
                .where(AddressProfile.project_id == project_id)
                .order_by(AddressProfile.created_at.desc())
            )
            profile = self.profile_to_read(address_profile) if address_profile else None
        proposal = self.db.scalar(select(ProjectProposal).where(ProjectProposal.project_id == project_id))
        issues = profile.issues if profile else ["address_not_resolved"]
        return PropertyProfileRead(
            project_id=project_id,
            property=PropertyRead(**property_to_dict(prop)) if prop else None,
            address_profile=profile,
            proposal=_proposal_read(proposal) if proposal else None,
            issues=issues,
        )

    def profile_to_read(self, profile: AddressProfile) -> AddressProfileRead:
        facts = [
            self.fact_to_read(fact)
            for fact in self.db.scalars(
                select(AddressFact)
                .where(AddressFact.address_profile_id == profile.id)
                .order_by(AddressFact.created_at)
            )
        ]
        return AddressProfileRead(
            id=profile.id,
            project_id=profile.project_id,
            input_address=profile.input_address,
            formatted_address=profile.formatted_address,
            resolution_status=profile.resolution_status,  # type: ignore[arg-type]
            confidence=profile.confidence,  # type: ignore[arg-type]
            parcel_id=profile.parcel_id,
            local_government=profile.local_government,
            lot_plan=profile.lot_plan,
            resolver_sources=from_json(profile.resolver_sources_json, []),
            dataset_version_ids=from_json(profile.dataset_version_ids_json, []),
            issues=from_json(profile.issues_json, []),
            as_of_date=profile.as_of_date,
            assessment_basis=profile.assessment_basis,  # type: ignore[arg-type]
            facts=facts,
            planning=_planning_summary(facts),
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    def fact_to_read(self, fact: AddressFact) -> AddressFactRead:
        return AddressFactRead(
            id=fact.id,
            address_profile_id=fact.address_profile_id,
            fact_type=fact.fact_type,
            value_json=from_json(fact.value_json, {}),
            confidence=fact.confidence,  # type: ignore[arg-type]
            method=fact.method,
            spatial_dataset_id=fact.spatial_dataset_id,
            source_version_id=fact.source_version_id,
            planning_layer_feature_id=fact.planning_layer_feature_id,
            effective_from=fact.effective_from,
            effective_to=fact.effective_to,
            stale_at=fact.stale_at,
            review_status=fact.review_status,
            created_at=fact.created_at,
        )

    def _add_fact(self, address_profile_id: str, payload: AddressFactInput) -> AddressFact:
        fact = AddressFact(
            address_profile_id=address_profile_id,
            fact_type=payload.fact_type,
            value_json=to_json(payload.value_json),
            confidence=payload.confidence,
            method=payload.method,
            spatial_dataset_id=payload.spatial_dataset_id,
            source_version_id=payload.source_version_id,
            planning_layer_feature_id=payload.planning_layer_feature_id,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            review_status=payload.review_status,
        )
        self.db.add(fact)
        return fact

    def _add_fact_row(self, address_profile_id: str, payload: dict[str, Any]) -> AddressFact:
        fact = AddressFact(
            address_profile_id=address_profile_id,
            fact_type=payload["fact_type"],
            value_json=to_json(payload["value_json"]),
            confidence=payload.get("confidence", "high"),
            method=payload["method"],
            spatial_dataset_id=payload.get("spatial_dataset_id"),
            source_version_id=payload.get("source_version_id"),
            planning_layer_feature_id=payload.get("planning_layer_feature_id"),
            effective_from=payload.get("effective_from"),
            effective_to=payload.get("effective_to"),
            review_status=payload.get("review_status", "verified"),
        )
        self.db.add(fact)
        return fact

    def _add_local_government_fact(self, address_profile_id: str, spatial: dict[str, Any]) -> LocalGovernmentFact:
        fact = LocalGovernmentFact(
            address_profile_id=address_profile_id,
            local_government=spatial["local_government"],
            method=spatial.get("local_government_method", "cadastre_attribute"),
            confidence=spatial.get("local_government_confidence", "high"),
            spatial_dataset_id=spatial.get("local_government_spatial_dataset_id"),
            source_version_id=spatial.get("local_government_source_version_id"),
            review_status="verified",
        )
        self.db.add(fact)
        return fact

    def _resolve_spatial_context(self, address: str, as_of_date: str) -> dict[str, Any]:
        issues: list[str] = []
        resolver_sources: set[str] = set()
        dataset_version_ids: set[str] = set()
        facts: list[dict[str, Any]] = []

        point_row, address_issues = self._find_address_point(address)
        issues.extend(address_issues)
        if not point_row:
            return {
                "formatted_address": address,
                "parcel_id": None,
                "local_government": None,
                "lot_plan": None,
                "resolver_sources": [],
                "dataset_version_ids": [],
                "facts": [],
                "issues": _dedupe(issues),
            }

        _collect_provenance(point_row.source_version_id, point_row.spatial_dataset_id, resolver_sources, dataset_version_ids)
        point = _point_for_address_point(point_row)
        if point is None:
            issues.append("address_point_geometry_missing")

        parcel = self.db.get(Parcel, point_row.parcel_id) if point_row.parcel_id else None
        if not parcel and point:
            parcel, parcel_issues = self._parcel_containing_point(point)
            issues.extend(parcel_issues)
        if not parcel:
            if "multiple_parcels_match" not in issues:
                issues.append("parcel_not_verified")
        else:
            _collect_provenance(parcel.source_version_id, parcel.spatial_dataset_id, resolver_sources, dataset_version_ids)
            if point and parcel.geom_wkt:
                parcel_polygon = _parse_polygon_wkt(parcel.geom_wkt)
                if not parcel_polygon or not _point_in_polygon(point, parcel_polygon):
                    issues.append("parcel_geometry_conflict")
            else:
                issues.append("parcel_geometry_missing")
            if not parcel.source_version_id:
                dataset_source_version_id = self._dataset_source_version_id(parcel.spatial_dataset_id)
                if not dataset_source_version_id:
                    issues.append("parcel_source_version_required")

            facts.extend(self._parcel_facts(parcel))

        local_government = parcel.local_government if parcel else None
        local_government_spatial_dataset_id = parcel.spatial_dataset_id if parcel else None
        local_government_source_version_id = parcel.source_version_id if parcel else None
        local_government_method = "cadastre_attribute"
        if point:
            boundaries = self._local_government_boundaries_containing_point(point)
            if len(boundaries) > 1:
                issues.append("multiple_local_government_boundaries_match")
            elif boundaries:
                boundary = boundaries[0]
                _collect_provenance(
                    boundary.source_version_id,
                    boundary.spatial_dataset_id,
                    resolver_sources,
                    dataset_version_ids,
                )
                if local_government and _normalize_label(local_government) != _normalize_label(boundary.name):
                    issues.append("local_government_boundary_conflict")
                local_government = boundary.name
                local_government_spatial_dataset_id = boundary.spatial_dataset_id
                local_government_source_version_id = boundary.source_version_id
                local_government_method = "point_in_polygon"
        if not local_government:
            issues.append("local_government_not_verified")
        elif parcel:
            facts.append(
                {
                    "fact_type": "local_government",
                    "value_json": {"label": local_government},
                    "method": local_government_method,
                    "spatial_dataset_id": local_government_spatial_dataset_id,
                    "source_version_id": local_government_source_version_id,
                }
            )

        planning_features: list[tuple[PlanningLayerFeature, str]] = []
        if point and parcel:
            planning_features = self._planning_features_for(point, parcel.id, as_of_date)
            for feature, method in planning_features:
                _collect_provenance(
                    feature.source_version_id,
                    feature.spatial_dataset_id,
                    resolver_sources,
                    dataset_version_ids,
                )
                facts.append(_feature_fact(feature, method))
        if parcel and not planning_features:
            issues.append("planning_layers_not_found")

        return {
            "formatted_address": point_row.address,
            "parcel_id": parcel.id if parcel else None,
            "local_government": local_government,
            "lot_plan": parcel.lot_plan if parcel else None,
            "resolver_sources": sorted(resolver_sources),
            "dataset_version_ids": sorted(dataset_version_ids),
            "facts": facts,
            "issues": _dedupe(issues),
            "local_government_method": local_government_method,
            "local_government_spatial_dataset_id": local_government_spatial_dataset_id,
            "local_government_source_version_id": local_government_source_version_id,
            "local_government_confidence": "high" if local_government else "low",
        }

    def _find_address_point(self, address: str) -> tuple[AddressPoint | None, list[str]]:
        target = _normalize_address(address)
        scored: list[tuple[int, AddressPoint]] = []
        for point in self.db.scalars(select(AddressPoint).order_by(AddressPoint.created_at.desc())):
            score = _address_match_score(target, point.address)
            if score:
                scored.append((score, point))
        if not scored:
            return None, ["address_point_not_found", "parcel_not_verified"]
        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best_point = scored[0]
        if best_score >= 100:
            tied = [point for score, point in scored if score == best_score]
            if len(tied) > 1:
                return None, ["multiple_address_points_match"]
            return best_point, []
        tied = [point for score, point in scored if score == best_score]
        if len(tied) > 1:
            return None, ["multiple_address_points_match"]
        if best_score >= 60:
            return None, ["address_match_requires_human_review"]
        return None, ["address_point_not_found", "parcel_not_verified"]

    def _parcel_containing_point(self, point: Point) -> tuple[Parcel | None, list[str]]:
        matches = [
            parcel
            for parcel in self.db.scalars(select(Parcel))
            if parcel.geom_wkt and _point_in_polygon(point, _parse_polygon_wkt(parcel.geom_wkt) or [])
        ]
        if len(matches) > 1:
            return None, ["multiple_parcels_match"]
        return (matches[0], []) if matches else (None, [])

    def _local_government_boundaries_containing_point(self, point: Point) -> list[LocalGovernmentBoundary]:
        return [
            boundary
            for boundary in self.db.scalars(select(LocalGovernmentBoundary))
            if boundary.geom_wkt and _point_in_polygon(point, _parse_polygon_wkt(boundary.geom_wkt) or [])
        ]

    def _planning_features_for(
        self,
        point: Point,
        parcel_id: str,
        as_of_date: str,
    ) -> list[tuple[PlanningLayerFeature, str]]:
        matches: list[tuple[PlanningLayerFeature, str]] = []
        for feature in self.db.scalars(select(PlanningLayerFeature).order_by(PlanningLayerFeature.layer_type)):
            metadata: Any = from_json(feature.metadata_json, {})
            if not _effective_on(metadata, as_of_date):
                continue
            parcel_ids = metadata.get("parcel_ids", [])
            if isinstance(parcel_ids, list) and parcel_id in parcel_ids:
                matches.append((feature, "parcel_id_match"))
                continue
            if feature.geom_wkt and _point_in_polygon(point, _parse_polygon_wkt(feature.geom_wkt) or []):
                matches.append((feature, "point_in_polygon"))
        return matches

    def _parcel_facts(self, parcel: Parcel) -> list[dict[str, Any]]:
        facts: list[dict[str, Any]] = [
            {
                "fact_type": "parcel",
                "value_json": {
                    "parcel_id": parcel.id,
                    "lot_plan": parcel.lot_plan,
                    "local_government": parcel.local_government,
                },
                "method": "address_point_parcel_match",
                "spatial_dataset_id": parcel.spatial_dataset_id,
                "source_version_id": parcel.source_version_id or self._dataset_source_version_id(parcel.spatial_dataset_id),
            }
        ]
        if parcel.area_m2 is not None:
            facts.append(
                {
                    "fact_type": "lot_area_m2",
                    "value_json": {"value": parcel.area_m2, "unit": "m2"},
                    "method": "cadastre_attribute",
                    "spatial_dataset_id": parcel.spatial_dataset_id,
                    "source_version_id": parcel.source_version_id
                    or self._dataset_source_version_id(parcel.spatial_dataset_id),
                }
            )
        return facts

    def _dataset_source_version_id(self, spatial_dataset_id: str | None) -> str | None:
        if not spatial_dataset_id:
            return None
        dataset = self.db.get(SpatialDataset, spatial_dataset_id)
        return dataset.source_version_id if dataset else None

    def _sync_property_from_facts(self, prop: Property, facts: list[AddressFactRead]) -> None:
        overlays: list[dict[str, Any]] = []
        for fact in facts:
            if fact.fact_type == "zone":
                prop.zoning = _fact_label(fact.value_json)
            elif fact.fact_type == "lot_area_m2":
                value = fact.value_json.get("value")
                if isinstance(value, int | float):
                    prop.lot_area_m2 = float(value)
            elif fact.fact_type.endswith("_overlay") or fact.fact_type == "overlay":
                overlays.append({"label": str(_fact_label(fact.value_json))})
        if overlays:
            prop.overlays_json = to_json([overlay["label"] for overlay in overlays if overlay.get("label")])

    def _get_project(self, project_id: str) -> Project:
        project = self.db.get(Project, project_id)
        if not project:
            raise KeyError("Project not found")
        return project

    def _enqueue_spatial_review_if_required(
        self,
        profile: AddressProfile,
        issues: list[str],
        input_address: str,
    ) -> None:
        if profile.resolution_status != "needs_human_review":
            return
        ReviewQueueService(self.db).enqueue(
            ReviewQueueItemCreate(
                queue="spatial_ambiguity_review",
                project_id=profile.project_id,
                target_type="address_profile",
                target_id=profile.id,
                reason=f"Address resolution requires human review: {profile.resolution_status}",
                blocking_level="blocking",
                evidence={
                    "address_profile_id": profile.id,
                    "input_address": input_address,
                    "formatted_address": profile.formatted_address,
                    "resolution_status": profile.resolution_status,
                    "confidence": profile.confidence,
                    "issues": issues,
                    "resolver_sources": from_json(profile.resolver_sources_json, []),
                    "dataset_version_ids": from_json(profile.dataset_version_ids_json, []),
                },
                suggested_action=(
                    "Review candidate address, parcel, local government, zoning, and overlay evidence "
                    "before this profile is used for rule resolution or compliance checks."
                ),
                priority="high",
            )
        )


def _default_as_of_date() -> str:
    return date.today().isoformat()


_HUMAN_REVIEW_ADDRESS_ISSUES = {
    "address_match_requires_human_review",
    "multiple_address_points_match",
    "multiple_parcels_match",
    "multiple_local_government_boundaries_match",
    "local_government_boundary_conflict",
}


def _resolution_status_for_issues(issues: list[str]) -> str:
    if not issues:
        return "resolved"
    if all(issue in _HUMAN_REVIEW_ADDRESS_ISSUES for issue in issues):
        return "needs_human_review"
    return "missing_info"


def _confidence_for_resolution(resolution_status: str) -> str:
    if resolution_status == "resolved":
        return "high"
    if resolution_status == "needs_human_review":
        return "medium"
    return "low"


def _normalize_address(value: str) -> str:
    return " ".join(value.lower().replace(",", " ").split())


def _address_match_score(normalized_query: str, address: str) -> int:
    normalized_address = _normalize_address(address)
    if not normalized_query or not normalized_address:
        return 0
    if normalized_address == normalized_query:
        return 100
    if normalized_address.startswith(normalized_query):
        return 90
    query_tokens = normalized_query.split()
    address_tokens = normalized_address.split()
    if all(token in address_tokens for token in query_tokens):
        return 75
    if normalized_query in normalized_address:
        return 65
    return 0


def _suggestion_confidence(score: int) -> str:
    if score >= 100:
        return "high"
    if score >= 65:
        return "medium"
    return "low"


def _normalize_label(value: str) -> str:
    return " ".join(value.lower().split())


def _collect_provenance(
    source_version_id: str | None,
    spatial_dataset_id: str | None,
    resolver_sources: set[str],
    dataset_version_ids: set[str],
) -> None:
    if source_version_id:
        resolver_sources.add(f"source_version:{source_version_id}")
    if spatial_dataset_id:
        resolver_sources.add(f"spatial_dataset:{spatial_dataset_id}")
        dataset_version_ids.add(spatial_dataset_id)


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _point_for_address_point(point: AddressPoint) -> Point | None:
    if point.lon is not None and point.lat is not None:
        return (point.lon, point.lat)
    if point.geom_wkt:
        return _parse_point_wkt(point.geom_wkt)
    return None


def _parse_point_wkt(value: str) -> Point | None:
    stripped = value.strip()
    if not stripped.upper().startswith("POINT"):
        return None
    body = stripped[stripped.find("(") + 1 : stripped.rfind(")")]
    parts = body.replace(",", " ").split()
    if len(parts) < 2:
        return None
    try:
        return (float(parts[0]), float(parts[1]))
    except ValueError:
        return None


def _parse_polygon_wkt(value: str) -> list[Point] | None:
    stripped = value.strip()
    if not stripped.upper().startswith("POLYGON"):
        return None
    start = stripped.find("((")
    end = stripped.rfind("))")
    if start == -1 or end == -1:
        return None
    ring_text = stripped[start + 2 : end].split("),", 1)[0]
    points: list[Point] = []
    for pair in ring_text.split(","):
        parts = pair.split()
        if len(parts) < 2:
            return None
        try:
            points.append((float(parts[0]), float(parts[1])))
        except ValueError:
            return None
    return points if len(points) >= 4 else None


def _point_in_polygon(point: Point, polygon: list[Point]) -> bool:
    if len(polygon) < 3:
        return False
    x, y = point
    inside = False
    previous_x, previous_y = polygon[-1]
    for current_x, current_y in polygon:
        if _point_on_segment(point, (previous_x, previous_y), (current_x, current_y)):
            return True
        crosses_y = (current_y > y) != (previous_y > y)
        if crosses_y:
            slope_x = (previous_x - current_x) * (y - current_y) / (previous_y - current_y) + current_x
            if x < slope_x:
                inside = not inside
        previous_x, previous_y = current_x, current_y
    return inside


def _point_on_segment(point: Point, start: Point, end: Point) -> bool:
    x, y = point
    x1, y1 = start
    x2, y2 = end
    cross = (y - y1) * (x2 - x1) - (x - x1) * (y2 - y1)
    if abs(cross) > 1e-9:
        return False
    return min(x1, x2) - 1e-9 <= x <= max(x1, x2) + 1e-9 and min(y1, y2) - 1e-9 <= y <= max(y1, y2) + 1e-9


def _effective_on(metadata: dict[str, Any], as_of_date: str) -> bool:
    effective_from = metadata.get("effective_from")
    effective_to = metadata.get("effective_to")
    if isinstance(effective_from, str) and effective_from and effective_from > as_of_date:
        return False
    if isinstance(effective_to, str) and effective_to and effective_to < as_of_date:
        return False
    return True


def _feature_fact(feature: PlanningLayerFeature, method: str) -> dict[str, Any]:
    fact_type = _feature_fact_type(feature.layer_type)
    metadata: Any = from_json(feature.metadata_json, {})
    value: dict[str, Any] = {
        "label": feature.label,
        "layer_type": feature.layer_type,
    }
    if feature.code:
        value["code"] = feature.code
    if fact_type in {"bushfire_prone", "heritage_overlay"} or fact_type.endswith("_overlay"):
        value.setdefault("value", True)
    return {
        "fact_type": fact_type,
        "value_json": value,
        "method": method,
        "spatial_dataset_id": feature.spatial_dataset_id,
        "source_version_id": feature.source_version_id,
        "planning_layer_feature_id": feature.id,
        "effective_from": metadata.get("effective_from") if isinstance(metadata, dict) else None,
        "effective_to": metadata.get("effective_to") if isinstance(metadata, dict) else None,
    }


def _feature_fact_type(layer_type: str) -> str:
    normalized = layer_type.lower().strip().replace("-", "_").replace(" ", "_")
    if normalized in {"zone", "r_code_density"}:
        return normalized
    if normalized in {"bushfire", "bushfire_prone", "bushfire_prone_area"}:
        return "bushfire_prone"
    if normalized in {"heritage", "heritage_area"}:
        return "heritage_overlay"
    if "overlay" in normalized:
        return normalized if normalized.endswith("_overlay") else f"{normalized}_overlay"
    return normalized


def _planning_summary(facts: list[AddressFactRead]) -> dict[str, Any] | None:
    if not facts:
        return None
    summary: dict[str, Any] = {}
    overlays: list[dict[str, Any]] = []
    for fact in facts:
        if fact.fact_type == "zone":
            summary["zone"] = _fact_label(fact.value_json)
        elif fact.fact_type == "r_code_density":
            summary["r_code_density"] = _fact_label(fact.value_json)
        elif fact.fact_type == "bushfire_prone":
            summary["bushfire_prone"] = fact.value_json.get("value")
        elif fact.fact_type == "heritage_overlay":
            summary["heritage"] = fact.value_json.get("value", True)
            overlays.append(fact.value_json)
        elif fact.fact_type.endswith("_overlay") or fact.fact_type == "overlay":
            overlays.append(fact.value_json)
    if overlays:
        summary["overlays"] = overlays
    return summary or None


def _fact_label(value: dict[str, Any]) -> Any:
    if "label" in value and "code" in value:
        return f"{value['label']} {value['code']}".strip()
    return value.get("label", value.get("code", value.get("value")))


def _proposal_read(proposal: ProjectProposal) -> ProjectProposalRead:
    return ProjectProposalRead(
        id=proposal.id,
        project_id=proposal.project_id,
        proposal_type=proposal.proposal_type,
        dwelling_type=proposal.dwelling_type,
        building_class=proposal.building_class,
        work_type=proposal.work_type,
        occupancy_class=proposal.occupancy_class,
        new_or_existing=proposal.new_or_existing,
        lot_type=proposal.lot_type,
        primary_street_confirmed=proposal.primary_street_confirmed,
        secondary_street_confirmed=proposal.secondary_street_confirmed,
        source=proposal.source,  # type: ignore[arg-type]
        confidence=proposal.confidence,
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
    )
