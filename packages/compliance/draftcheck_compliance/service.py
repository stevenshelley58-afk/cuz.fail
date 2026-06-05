from __future__ import annotations

from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_compliance.calculators import (
    area_percentage,
    boundary_wall_length_percentage,
    compare_maximum,
    compare_minimum,
    garage_width_ratio,
)
from draftcheck_core.audit import record_audit
from draftcheck_core.json_utils import from_json, to_json
from draftcheck_core.models import CheckDefinition, CheckResult, CheckRun, ExtractedMeasurement
from draftcheck_retrieval.service import RetrievalService
from draftcheck_shared.schemas import CheckResultRead, ComplianceMatrix


LIABILITY_NOTICE = (
    "Assistive drafting review only. This is not legal advice, planning approval, "
    "building certification, or a compliance certificate. Human review is required before submission."
)

DEFAULT_CHECKS = [
    {
        "key": "site_cover",
        "label": "Site cover",
        "category": "planning",
        "method": "max_percentage",
        "requirement": {"max_percent": 55, "part_key": "building_footprint_m2", "whole_key": "site_area_m2"},
        "source_query": "site cover R-Codes open space",
    },
    {
        "key": "open_space",
        "label": "Open space",
        "category": "planning",
        "method": "min_percentage",
        "requirement": {"min_percent": 45, "part_key": "open_space_m2", "whole_key": "site_area_m2"},
        "source_query": "open space R-Codes residential design",
    },
    {
        "key": "front_setback",
        "label": "Front setback",
        "category": "planning",
        "method": "min_value",
        "requirement": {"min_value": 4.0, "value_key": "front_setback_m", "unit": "m"},
        "source_query": "front setback primary street R-Codes",
    },
    {
        "key": "side_setback",
        "label": "Side setback",
        "category": "planning",
        "method": "min_value",
        "requirement": {"min_value": 1.0, "value_key": "side_setback_m", "unit": "m"},
        "source_query": "side setback lot boundary R-Codes",
    },
    {
        "key": "rear_setback",
        "label": "Rear setback",
        "category": "planning",
        "method": "min_value",
        "requirement": {"min_value": 1.5, "value_key": "rear_setback_m", "unit": "m"},
        "source_query": "rear setback lot boundary R-Codes",
    },
    {
        "key": "deep_soil_tree_planting",
        "label": "Deep soil and tree planting",
        "category": "planning",
        "method": "all_min_values",
        "requirement": {
            "values": [
                {"key": "deep_soil_area_m2", "min_value": 12.0, "unit": "m2"},
                {"key": "tree_count", "min_value": 1.0, "unit": "count"},
            ]
        },
        "source_query": "deep soil tree planting landscaping R-Codes",
    },
    {
        "key": "garage_dominance",
        "label": "Garage dominance",
        "category": "planning",
        "method": "garage_ratio",
        "requirement": {"max_percent": 50, "garage_key": "garage_width_m", "frontage_key": "frontage_width_m"},
        "source_query": "garage width dominance street surveillance",
    },
    {
        "key": "street_surveillance",
        "label": "Street surveillance",
        "category": "planning",
        "method": "boolean_required",
        "requirement": {"value_key": "street_surveillance_opening_present", "expected": 1},
        "source_query": "street surveillance habitable opening R-Codes",
    },
    {
        "key": "outdoor_living_area",
        "label": "Outdoor living area",
        "category": "planning",
        "method": "all_min_values",
        "requirement": {
            "values": [
                {"key": "outdoor_living_area_m2", "min_value": 24.0, "unit": "m2"},
                {"key": "outdoor_living_min_dimension_m", "min_value": 4.0, "unit": "m"},
            ]
        },
        "source_query": "outdoor living area minimum dimension R-Codes",
    },
    {
        "key": "solar_access",
        "label": "Solar access",
        "category": "planning",
        "method": "min_value",
        "requirement": {"min_value": 2.0, "value_key": "solar_access_hours", "unit": "hours"},
        "source_query": "solar access north facing major openings R-Codes",
    },
    {
        "key": "privacy",
        "label": "Privacy",
        "category": "planning",
        "method": "max_value",
        "requirement": {"max_value": 0.0, "value_key": "privacy_overlooking_risk_count", "unit": "count"},
        "source_query": "visual privacy overlooking R-Codes",
    },
    {
        "key": "overshadowing",
        "label": "Overshadowing",
        "category": "planning",
        "method": "max_percentage",
        "requirement": {
            "max_percent": 25,
            "part_key": "overshadowed_neighbour_site_area_m2",
            "whole_key": "neighbour_site_area_m2",
        },
        "source_query": "overshadowing adjoining property R-Codes",
    },
    {
        "key": "vehicle_access",
        "label": "Vehicle access",
        "category": "planning",
        "method": "boolean_required",
        "requirement": {"value_key": "vehicle_access_shown", "expected": 1},
        "source_query": "vehicle access driveway parking R-Codes local policy",
    },
    {
        "key": "bin_storage",
        "label": "Bin storage",
        "category": "planning",
        "method": "boolean_required",
        "requirement": {"value_key": "bin_storage_shown", "expected": 1},
        "source_query": "bin storage waste collection local planning policy",
    },
    {
        "key": "ancillary_dwelling_trigger",
        "label": "Ancillary dwelling trigger",
        "category": "planning",
        "method": "trigger_flag",
        "requirement": {"value_key": "ancillary_dwelling_proposed", "trigger_value": 1},
        "source_query": "ancillary dwelling R-Codes additional dwelling",
    },
    {
        "key": "retaining_fill_trigger",
        "label": "Retaining and fill trigger",
        "category": "planning",
        "method": "max_value",
        "requirement": {"max_value": 0.5, "value_key": "retaining_fill_height_m", "unit": "m"},
        "source_query": "retaining wall fill site works local planning policy",
    },
    {
        "key": "bal_bushfire_trigger",
        "label": "BAL and bushfire trigger",
        "category": "building",
        "method": "trigger_flag",
        "requirement": {"value_key": "bushfire_prone_area_flag", "trigger_value": 1},
        "source_query": "bushfire prone area BAL planning building requirements",
    },
    {
        "key": "heritage_overlay_trigger",
        "label": "Heritage and planning overlay trigger",
        "category": "planning",
        "method": "trigger_flag",
        "requirement": {"value_key": "heritage_overlay_flag", "trigger_value": 1},
        "source_query": "heritage overlay local planning scheme",
    },
    {
        "key": "boundary_wall",
        "label": "Boundary wall length",
        "category": "planning",
        "method": "boundary_wall_ratio",
        "requirement": {
            "max_percent": 45,
            "boundary_wall_key": "boundary_wall_length_m",
            "lot_boundary_key": "lot_boundary_length_m",
        },
        "source_query": "boundary wall length height R-Codes",
    },
    {
        "key": "title_block_completeness",
        "label": "Title block completeness",
        "category": "drawing_qa",
        "method": "boolean_required",
        "requirement": {"value_key": "title_block_present", "expected": 1},
        "source_query": "lodgement checklist title block drawing",
    },
    {
        "key": "revision_completeness",
        "label": "Revision completeness",
        "category": "drawing_qa",
        "method": "boolean_required",
        "requirement": {"value_key": "revision_present", "expected": 1},
        "source_query": "lodgement checklist revision drawing",
    },
    {
        "key": "north_point_completeness",
        "label": "North point completeness",
        "category": "drawing_qa",
        "method": "boolean_required",
        "requirement": {"value_key": "north_point_present", "expected": 1},
        "source_query": "lodgement checklist north point drawing",
    },
    {
        "key": "scale_completeness",
        "label": "Scale completeness",
        "category": "drawing_qa",
        "method": "boolean_required",
        "requirement": {"value_key": "scale_present", "expected": 1},
        "source_query": "lodgement checklist scale drawing",
    },
    {
        "key": "dimension_completeness",
        "label": "Dimension completeness",
        "category": "drawing_qa",
        "method": "boolean_required",
        "requirement": {"value_key": "dimensions_present", "expected": 1},
        "source_query": "lodgement checklist dimensions drawing",
    },
    {
        "key": "drawing_qa_completeness",
        "label": "Drawing QA completeness",
        "category": "drawing_qa",
        "method": "human_review",
        "requirement": {"required": ["north point", "scale", "revision", "dimensions"]},
        "source_query": "council lodgement checklist drawing north point scale",
    },
]


class ComplianceService:
    def __init__(self, db: Session):
        self.db = db
        self.retrieval = RetrievalService(db)

    def ensure_default_check_definitions(self) -> None:
        for item in DEFAULT_CHECKS:
            self.upsert_check_definition(item)
        self.db.flush()

    def load_check_definitions_yaml(self, yaml_text: str) -> list[CheckDefinition]:
        parsed = yaml.safe_load(yaml_text) or {}
        entries = parsed.get("checks", parsed if isinstance(parsed, list) else [])
        if not isinstance(entries, list):
            raise ValueError("Check definition YAML must contain a checks list")
        definitions = [self.upsert_check_definition(entry) for entry in entries]
        self.db.flush()
        return definitions

    def upsert_check_definition(self, item: dict[str, Any]) -> CheckDefinition:
        existing = self.db.scalar(select(CheckDefinition).where(CheckDefinition.key == item["key"]))
        if existing:
            existing.label = item["label"]
            existing.category = item["category"]
            existing.method = item["method"]
            existing.requirement_json = to_json(item.get("requirement", {}))
            existing.source_query = item.get("source_query", "")
            existing.is_active = item.get("is_active", True)
            return existing
        definition = CheckDefinition(
            key=item["key"],
            label=item["label"],
            category=item["category"],
            method=item["method"],
            requirement_json=to_json(item.get("requirement", {})),
            source_query=item.get("source_query", ""),
            is_active=item.get("is_active", True),
        )
        self.db.add(definition)
        return definition

    def run_checks(self, project_id: str) -> ComplianceMatrix:
        self.ensure_default_check_definitions()
        measurements = {
            m.key: m
            for m in self.db.scalars(
                select(ExtractedMeasurement).where(ExtractedMeasurement.project_id == project_id)
            )
        }
        check_run = CheckRun(project_id=project_id, status="completed")
        self.db.add(check_run)
        self.db.flush()

        definitions = self.db.scalars(
            select(CheckDefinition).where(CheckDefinition.is_active.is_(True)).order_by(CheckDefinition.key)
        ).all()
        results: list[CheckResultRead] = []
        source_version_ids: set[str] = set()
        for definition in definitions:
            result = self._evaluate_definition(project_id, check_run.id, definition, measurements)
            self.db.add(result)
            self.db.flush()
            result_read = self._result_to_schema(result)
            results.append(result_read)
            source_version_ids.update(citation.source_version_id for citation in result_read.citations)

        check_run.source_version_ids_json = to_json(sorted(source_version_ids))
        record_audit(
            self.db,
            action="checks.run",
            target_type="check_run",
            target_id=check_run.id,
            project_id=project_id,
            metadata={"result_count": len(results), "source_version_ids": sorted(source_version_ids)},
        )
        return ComplianceMatrix(
            project_id=project_id,
            check_run_id=check_run.id,
            status="completed",
            source_version_ids=sorted(source_version_ids),
            results=results,
            liability_notice=LIABILITY_NOTICE,
        )

    def list_results(self, project_id: str) -> list[CheckResultRead]:
        rows = self.db.scalars(
            select(CheckResult).where(CheckResult.project_id == project_id).order_by(CheckResult.created_at.desc())
        ).all()
        return [self._result_to_schema(row) for row in rows]

    def _evaluate_definition(
        self,
        project_id: str,
        check_run_id: str,
        definition: CheckDefinition,
        measurements: dict[str, ExtractedMeasurement],
    ) -> CheckResult:
        requirement: dict[str, Any] = from_json(definition.requirement_json, {})
        citations = self.retrieval.citation_for_check(definition.source_query)
        missing: list[str] = []
        data_missing: list[str] = []
        assumptions = ["Thresholds are default seed values and must be confirmed against cited current sources."]
        status = "needs_human_review"
        proposed = "No deterministic measurement available."
        confidence = 0.35 if citations else 0.2

        def need(key: str) -> ExtractedMeasurement | None:
            measurement = measurements.get(key)
            if not measurement:
                data_missing.append(key)
                missing.append(key)
            return measurement

        if definition.method == "max_percentage":
            part = need(requirement["part_key"])
            whole = need(requirement["whole_key"])
            if part and whole:
                pct = area_percentage(part.value, whole.value)
                proposed = f"{pct}% from {part.value}{part.unit} / {whole.value}{whole.unit}"
                status = "likely_pass" if pct <= requirement["max_percent"] else "likely_fail"
                confidence = min(part.confidence, whole.confidence, 0.8)
        elif definition.method == "min_percentage":
            part = need(requirement["part_key"])
            whole = need(requirement["whole_key"])
            if part and whole:
                pct = area_percentage(part.value, whole.value)
                proposed = f"{pct}% from {part.value}{part.unit} / {whole.value}{whole.unit}"
                status = "likely_pass" if pct >= requirement["min_percent"] else "likely_fail"
                confidence = min(part.confidence, whole.confidence, 0.8)
        elif definition.method == "min_value":
            measurement = need(requirement["value_key"])
            if measurement:
                proposed = f"{measurement.value}{measurement.unit}"
                status = (
                    "likely_pass"
                    if compare_minimum(measurement.value, requirement["min_value"])
                    else "likely_fail"
                )
                confidence = min(measurement.confidence, 0.8)
        elif definition.method == "max_value":
            measurement = need(requirement["value_key"])
            if measurement:
                proposed = f"{measurement.value}{measurement.unit}"
                status = (
                    "likely_pass"
                    if compare_maximum(measurement.value, requirement["max_value"])
                    else "likely_fail"
                )
                confidence = min(measurement.confidence, 0.8)
        elif definition.method == "all_min_values":
            evaluations: list[str] = []
            all_pass = True
            confidence_values: list[float] = []
            for value_requirement in requirement.get("values", []):
                measurement = need(value_requirement["key"])
                if not measurement:
                    all_pass = False
                    continue
                passed = compare_minimum(measurement.value, value_requirement["min_value"])
                all_pass = all_pass and passed
                confidence_values.append(measurement.confidence)
                evaluations.append(
                    f"{value_requirement['key']}={measurement.value}{measurement.unit} "
                    f"(minimum {value_requirement['min_value']}{value_requirement.get('unit', measurement.unit)})"
                )
            if evaluations:
                proposed = "; ".join(evaluations)
                status = "likely_pass" if all_pass else "likely_fail"
                confidence = min([0.8, *confidence_values])
        elif definition.method == "garage_ratio":
            garage = need(requirement["garage_key"])
            frontage = need(requirement["frontage_key"])
            if garage and frontage:
                ratio = garage_width_ratio(garage.value, frontage.value)
                proposed = f"{ratio}% garage/frontage width ratio"
                status = "likely_pass" if ratio <= requirement["max_percent"] else "likely_fail"
                confidence = min(garage.confidence, frontage.confidence, 0.75)
        elif definition.method == "boundary_wall_ratio":
            wall = need(requirement["boundary_wall_key"])
            boundary = need(requirement["lot_boundary_key"])
            if wall and boundary:
                ratio = boundary_wall_length_percentage(wall.value, boundary.value)
                proposed = f"{ratio}% boundary wall/lot boundary length ratio"
                status = "likely_pass" if ratio <= requirement["max_percent"] else "likely_fail"
                confidence = min(wall.confidence, boundary.confidence, 0.75)
        elif definition.method == "boolean_required":
            measurement = need(requirement["value_key"])
            if measurement:
                expected = float(requirement.get("expected", 1))
                proposed = f"{requirement['value_key']}={measurement.value:g}"
                status = "likely_pass" if measurement.value == expected else "likely_fail"
                confidence = min(measurement.confidence, 0.65)
        elif definition.method == "trigger_flag":
            measurement = need(requirement["value_key"])
            if measurement:
                trigger_value = float(requirement.get("trigger_value", 1))
                proposed = f"{requirement['value_key']}={measurement.value:g}"
                if measurement.value == trigger_value:
                    status = "needs_human_review"
                    missing.append("trigger-specific source interpretation and supporting evidence")
                else:
                    status = "not_applicable"
                confidence = min(measurement.confidence, 0.65)
        else:
            missing.append("manual drawing QA review")

        if data_missing:
            status = "missing_info"
            confidence = min(confidence, 0.3)

        if not citations:
            missing.append("approved source citation")
            if not data_missing and status != "not_applicable":
                status = "needs_human_review"
                confidence = min(confidence, 0.35)

        return CheckResult(
            check_run_id=check_run_id,
            project_id=project_id,
            check_key=definition.key,
            label=definition.label,
            category=definition.category,
            status=status,
            requirement=to_json(requirement),
            proposed=proposed,
            evidence_refs_json=to_json([]),
            citations_json=to_json([citation.model_dump(mode="json") for citation in citations]),
            assumptions_json=to_json(assumptions),
            missing_information_json=to_json(missing),
            confidence=confidence,
            requires_human_review=True,
            created_by_model="deterministic",
            prompt_version="none",
        )

    def _result_to_schema(self, row: CheckResult) -> CheckResultRead:
        return CheckResultRead(
            id=row.id,
            check_key=row.check_key,
            label=row.label,
            category=row.category,
            status=row.status,  # type: ignore[arg-type]
            requirement=row.requirement,
            proposed=row.proposed,
            evidence_refs=from_json(row.evidence_refs_json, []),
            citations=from_json(row.citations_json, []),
            assumptions=from_json(row.assumptions_json, []),
            missing_information=from_json(row.missing_information_json, []),
            confidence=row.confidence,
            requires_human_review=row.requires_human_review,
            created_at=row.created_at,
        )
