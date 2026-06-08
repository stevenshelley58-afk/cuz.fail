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
from draftcheck_core.json_utils import from_json, hash_text, to_json
from draftcheck_core.models import (
    CheckDefinition,
    CheckResult,
    CheckRun,
    DecisionTrace,
    ExtractedMeasurement,
    Project,
    ResolvedRule,
    RuleRow,
    SourceCitation,
    SourceDocument,
    SourceLicenceReview,
    SourceVersion,
)
from draftcheck_core.review_queue import ReviewQueueService
from draftcheck_core.source_support import (
    source_version_can_support_regulatory_output,
    source_version_runtime_support_conditions,
)
from draftcheck_shared.schemas import CheckResultRead, ComplianceMatrix, ReviewQueueItemCreate


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
        project = self.db.get(Project, project_id)
        if not project:
            raise KeyError("Project not found")
        as_of_date = project.as_of_date or project.lodgement_date or "unknown"
        assessment_basis = project.assessment_basis
        measurements = {
            m.key: m
            for m in self.db.scalars(
                select(ExtractedMeasurement).where(ExtractedMeasurement.project_id == project_id)
            )
        }
        check_run = CheckRun(
            project_id=project_id,
            status="completed",
            as_of_date=as_of_date,
            assessment_basis=assessment_basis,
        )
        self.db.add(check_run)
        self.db.flush()

        definitions = self.db.scalars(
            select(CheckDefinition).where(CheckDefinition.is_active.is_(True)).order_by(CheckDefinition.key)
        ).all()
        results: list[CheckResultRead] = []
        source_version_ids: set[str] = set()
        for definition in definitions:
            result, trace_payload = self._evaluate_definition(
                project_id,
                check_run.id,
                definition,
                measurements,
                as_of_date=as_of_date,
                assessment_basis=assessment_basis,
            )
            self.db.add(result)
            self.db.flush()
            trace = self._create_decision_trace(project_id, result, trace_payload)
            self.db.add(trace)
            self.db.flush()
            result_read = self._result_to_schema(result, decision_trace=trace)
            self._enqueue_review_item_for_result(project_id, result_read)
            results.append(result_read)
            source_version_ids.update(citation.source_version_id for citation in result_read.citations)

        check_run.source_version_ids_json = to_json(sorted(source_version_ids))
        record_audit(
            self.db,
            action="checks.run",
            target_type="check_run",
            target_id=check_run.id,
            project_id=project_id,
            metadata={
                "result_count": len(results),
                "source_version_ids": sorted(source_version_ids),
                "as_of_date": as_of_date,
                "assessment_basis": assessment_basis,
            },
        )
        return ComplianceMatrix(
            project_id=project_id,
            check_run_id=check_run.id,
            status="completed",
            as_of_date=as_of_date,
            assessment_basis=assessment_basis,  # type: ignore[arg-type]
            source_version_ids=sorted(source_version_ids),
            results=results,
            liability_notice=LIABILITY_NOTICE,
        )

    def list_results(self, project_id: str) -> list[CheckResultRead]:
        rows = self.db.scalars(
            select(CheckResult).where(CheckResult.project_id == project_id).order_by(CheckResult.created_at.desc())
        ).all()
        return [self._result_to_schema(row) for row in rows]

    def list_results_for_run(self, project_id: str, check_run_id: str) -> list[CheckResultRead]:
        rows = self.db.scalars(
            select(CheckResult)
            .where(CheckResult.project_id == project_id, CheckResult.check_run_id == check_run_id)
            .order_by(CheckResult.created_at)
        ).all()
        return [self._result_to_schema(row) for row in rows]

    def list_latest_run_results(self, project_id: str) -> list[CheckResultRead]:
        check_run = self.db.scalar(
            select(CheckRun)
            .where(CheckRun.project_id == project_id)
            .order_by(CheckRun.created_at.desc())
        )
        if not check_run:
            return []
        return self.list_results_for_run(project_id, check_run.id)

    def get_decision_trace(self, project_id: str, check_result_id: str) -> DecisionTrace | None:
        return self.db.scalar(
            select(DecisionTrace)
            .where(
                DecisionTrace.project_id == project_id,
                DecisionTrace.check_result_id == check_result_id,
            )
            .order_by(DecisionTrace.created_at.desc())
        )

    def _evaluate_definition(
        self,
        project_id: str,
        check_run_id: str,
        definition: CheckDefinition,
        measurements: dict[str, ExtractedMeasurement],
        *,
        as_of_date: str,
        assessment_basis: str,
    ) -> tuple[CheckResult, dict[str, Any]]:
        seed_requirement: dict[str, Any] = from_json(definition.requirement_json, {})
        approved_rule_rows, approved_resolved_rules = self._approved_rule_support(
            project_id,
            definition.key,
            as_of_date=as_of_date,
            assessment_basis=assessment_basis,
        )
        resolved_rule_citations = _resolved_rule_citation_payloads(approved_resolved_rules)
        citation_payloads = resolved_rule_citations or _rule_row_citation_payloads(self.db, approved_rule_rows)
        requirement, rule_support_issues = self._requirement_for_evaluation(
            definition.method,
            seed_requirement,
            approved_rule_rows,
        )
        missing: list[str] = []
        data_missing: list[str] = []
        used_measurements: list[ExtractedMeasurement] = []
        used_measurement_ids: set[str] = set()
        assumptions = (
            ["Approved rule rows supply deterministic thresholds; human review remains required before submission."]
            if approved_rule_rows and not rule_support_issues
            else ["Thresholds are default seed values and must be confirmed against cited current sources."]
        )
        status = "needs_human_review"
        proposed = "No deterministic measurement available."
        comparison = "not evaluated"
        confidence = 0.35 if citation_payloads else 0.2

        def need(key: str) -> ExtractedMeasurement | None:
            measurement = measurements.get(key)
            if not measurement:
                data_missing.append(key)
                missing.append(key)
            elif measurement.id not in used_measurement_ids:
                used_measurements.append(measurement)
                used_measurement_ids.add(measurement.id)
            return measurement

        if definition.method == "max_percentage":
            part = need(requirement["part_key"])
            whole = need(requirement["whole_key"])
            if part and whole:
                pct = area_percentage(part.value, whole.value)
                proposed = f"{pct}% from {part.value}{part.unit} / {whole.value}{whole.unit}"
                comparison = f"{pct} <= {requirement['max_percent']}"
                status = "likely_pass" if pct <= requirement["max_percent"] else "likely_fail"
                confidence = min(part.confidence, whole.confidence, 0.8)
        elif definition.method == "min_percentage":
            part = need(requirement["part_key"])
            whole = need(requirement["whole_key"])
            if part and whole:
                pct = area_percentage(part.value, whole.value)
                proposed = f"{pct}% from {part.value}{part.unit} / {whole.value}{whole.unit}"
                comparison = f"{pct} >= {requirement['min_percent']}"
                status = "likely_pass" if pct >= requirement["min_percent"] else "likely_fail"
                confidence = min(part.confidence, whole.confidence, 0.8)
        elif definition.method == "min_value":
            measurement = need(requirement["value_key"])
            if measurement:
                proposed = f"{measurement.value}{measurement.unit}"
                comparison = f"{measurement.value} >= {requirement['min_value']}"
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
                comparison = f"{measurement.value} <= {requirement['max_value']}"
                status = (
                    "likely_pass"
                    if compare_maximum(measurement.value, requirement["max_value"])
                    else "likely_fail"
                )
                confidence = min(measurement.confidence, 0.8)
        elif definition.method == "all_min_values":
            evaluations: list[str] = []
            comparisons: list[str] = []
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
                comparisons.append(f"{measurement.value} >= {value_requirement['min_value']}")
                evaluations.append(
                    f"{value_requirement['key']}={measurement.value}{measurement.unit} "
                    f"(minimum {value_requirement['min_value']}{value_requirement.get('unit', measurement.unit)})"
                )
            if evaluations:
                proposed = "; ".join(evaluations)
                comparison = "; ".join(comparisons)
                status = "likely_pass" if all_pass else "likely_fail"
                confidence = min([0.8, *confidence_values])
        elif definition.method == "garage_ratio":
            garage = need(requirement["garage_key"])
            frontage = need(requirement["frontage_key"])
            if garage and frontage:
                ratio = garage_width_ratio(garage.value, frontage.value)
                proposed = f"{ratio}% garage/frontage width ratio"
                comparison = f"{ratio} <= {requirement['max_percent']}"
                status = "likely_pass" if ratio <= requirement["max_percent"] else "likely_fail"
                confidence = min(garage.confidence, frontage.confidence, 0.75)
        elif definition.method == "boundary_wall_ratio":
            wall = need(requirement["boundary_wall_key"])
            boundary = need(requirement["lot_boundary_key"])
            if wall and boundary:
                ratio = boundary_wall_length_percentage(wall.value, boundary.value)
                proposed = f"{ratio}% boundary wall/lot boundary length ratio"
                comparison = f"{ratio} <= {requirement['max_percent']}"
                status = "likely_pass" if ratio <= requirement["max_percent"] else "likely_fail"
                confidence = min(wall.confidence, boundary.confidence, 0.75)
        elif definition.method == "boolean_required":
            measurement = need(requirement["value_key"])
            if measurement:
                expected = float(requirement.get("expected", 1))
                proposed = f"{requirement['value_key']}={measurement.value:g}"
                comparison = f"{measurement.value:g} == {expected:g}"
                status = "likely_pass" if measurement.value == expected else "likely_fail"
                confidence = min(measurement.confidence, 0.65)
        elif definition.method == "trigger_flag":
            measurement = need(requirement["value_key"])
            if measurement:
                trigger_value = float(requirement.get("trigger_value", 1))
                proposed = f"{requirement['value_key']}={measurement.value:g}"
                comparison = f"{measurement.value:g} == trigger {trigger_value:g}"
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

        if status in {"likely_pass", "likely_fail", "not_applicable"}:
            if not approved_rule_rows:
                missing.append(f"approved rule row for {definition.key}")
            elif not approved_resolved_rules:
                missing.append(f"approved resolved rule for {definition.key}")
            elif rule_support_issues:
                missing.extend(rule_support_issues)
            if (not approved_rule_rows or not approved_resolved_rules or rule_support_issues) and not data_missing:
                status = "needs_human_review"
                confidence = min(confidence, 0.35)

        if not citation_payloads:
            missing.append("approved source citation")
            if not data_missing:
                status = "unsupported"
                confidence = min(confidence, 0.35)

        evidence_refs = _measurement_evidence_refs(used_measurements)
        result = CheckResult(
            check_run_id=check_run_id,
            project_id=project_id,
            check_key=definition.key,
            label=definition.label,
            category=definition.category,
            status=status,
            as_of_date=as_of_date,
            assessment_basis=assessment_basis,
            requirement=to_json(requirement),
            proposed=proposed,
            evidence_refs_json=to_json(evidence_refs),
            citations_json=to_json(citation_payloads),
            assumptions_json=to_json(assumptions),
            missing_information_json=to_json(missing),
            confidence=confidence,
            requires_human_review=True,
            created_by_model="deterministic",
            prompt_version="none",
        )
        return result, self._decision_trace_payload(
            definition=definition,
            requirement=requirement,
            proposed=proposed,
            comparison=comparison,
            status=status,
            missing=missing,
            data_missing=data_missing,
            measurements=used_measurements,
            citations=citation_payloads,
            approved_rule_rows=approved_rule_rows,
            approved_resolved_rules=approved_resolved_rules,
            as_of_date=as_of_date,
            assessment_basis=assessment_basis,
        )

    def _enqueue_review_item_for_result(self, project_id: str, result: CheckResultRead) -> None:
        if result.status not in {"missing_info", "needs_human_review", "unsupported"}:
            return
        source_version_id = result.citations[0].source_version_id if result.citations else None
        reason = f"Compliance check {result.check_key} requires review: {result.status}"
        ReviewQueueService(self.db).enqueue(
            ReviewQueueItemCreate(
                queue="conflict_review",
                project_id=project_id,
                source_version_id=source_version_id,
                target_type="compliance_check",
                target_id=f"{project_id}:{result.check_key}",
                reason=reason,
                blocking_level="blocking",
                evidence={
                    "check_result_id": result.id,
                    "decision_trace_id": result.decision_trace_id,
                    "check_key": result.check_key,
                    "status": result.status,
                    "as_of_date": result.as_of_date,
                    "assessment_basis": result.assessment_basis,
                    "missing_information": result.missing_information,
                    "citation_count": len(result.citations),
                },
                suggested_action=(
                    "Resolve missing information, source support, rule resolution, or discretionary conflict "
                    "before treating this check as confident."
                ),
                priority="high" if result.status == "unsupported" else "medium",
            )
        )

    def _approved_rule_support(
        self,
        project_id: str,
        rule_key: str,
        *,
        as_of_date: str,
        assessment_basis: str,
    ) -> tuple[list[RuleRow], list[ResolvedRule]]:
        rule_rows = _filter_rule_rows_by_regulatory_source_support(
            self.db,
            list(
                self.db.scalars(
                    select(RuleRow)
                    .join(
                        SourceLicenceReview,
                        SourceLicenceReview.source_version_id == RuleRow.source_version_id,
                    )
                    .join(
                        SourceVersion,
                        SourceVersion.id == RuleRow.source_version_id,
                    )
                    .join(
                        SourceDocument,
                        SourceDocument.id == SourceVersion.source_document_id,
                    )
                    .where(
                        RuleRow.rule_key == rule_key,
                        RuleRow.lifecycle_status.in_(("approved", "auto_accepted")),
                        *source_version_runtime_support_conditions(),
                        SourceDocument.is_active.is_(True),
                    )
                ).all()
            ),
        )
        if not rule_rows:
            return [], []

        resolved_rules = list(
            self.db.scalars(
                select(ResolvedRule).where(
                    ResolvedRule.project_id == project_id,
                    ResolvedRule.rule_row_id.in_([row.id for row in rule_rows]),
                    ResolvedRule.as_of_date == as_of_date,
                    ResolvedRule.assessment_basis == assessment_basis,
                    ResolvedRule.status.in_(("needs_human_review", "likely_pass", "likely_fail")),
                    ResolvedRule.citations_json != "[]",
                )
            ).all()
        )
        if resolved_rules:
            resolved_rule_row_ids = {row.rule_row_id for row in resolved_rules}
            rule_rows = [row for row in rule_rows if row.id in resolved_rule_row_ids]
        return rule_rows, resolved_rules

    def _requirement_for_evaluation(
        self,
        method: str,
        seed_requirement: dict[str, Any],
        approved_rule_rows: list[RuleRow],
    ) -> tuple[dict[str, Any], list[str]]:
        requirement = dict(seed_requirement)
        if not approved_rule_rows:
            return requirement, []

        issues: list[str] = []
        if method in {"max_percentage", "garage_ratio", "boundary_wall_ratio"}:
            value = self._first_rule_number(approved_rule_rows, ("max_percent", "maximum_percent", "percent", "value"))
            if value is None:
                issues.append("approved rule row maximum percentage threshold")
            else:
                requirement["max_percent"] = value
        elif method == "min_percentage":
            value = self._first_rule_number(approved_rule_rows, ("min_percent", "minimum_percent", "percent", "value"))
            if value is None:
                issues.append("approved rule row minimum percentage threshold")
            else:
                requirement["min_percent"] = value
        elif method == "min_value":
            value = self._first_rule_number(approved_rule_rows, ("min_value", "minimum", "value"))
            if value is None:
                issues.append("approved rule row minimum threshold")
            else:
                requirement["min_value"] = value
        elif method == "max_value":
            value = self._first_rule_number(approved_rule_rows, ("max_value", "maximum", "value"))
            if value is None:
                issues.append("approved rule row maximum threshold")
            else:
                requirement["max_value"] = value
        elif method == "boolean_required":
            value = self._first_rule_number(approved_rule_rows, ("expected", "required_value", "value"))
            if value is None:
                issues.append("approved rule row expected value")
            else:
                requirement["expected"] = value
        elif method == "trigger_flag":
            value = self._first_rule_number(approved_rule_rows, ("trigger_value", "value"))
            if value is None:
                issues.append("approved rule row trigger value")
            else:
                requirement["trigger_value"] = value
        elif method == "all_min_values":
            values = self._approved_all_min_values(seed_requirement, approved_rule_rows)
            if values is None:
                issues.append("approved rule row minimum values")
            else:
                requirement["values"] = values
        return requirement, issues

    def _first_rule_number(self, rule_rows: list[RuleRow], keys: tuple[str, ...]) -> float | None:
        for row in rule_rows:
            payload: Any = from_json(row.value_json, {})
            if not isinstance(payload, dict):
                continue
            for key in keys:
                value = payload.get(key)
                if isinstance(value, int | float):
                    return float(value)
                if isinstance(value, str):
                    try:
                        return float(value)
                    except ValueError:
                        continue
        return None

    def _approved_all_min_values(
        self,
        seed_requirement: dict[str, Any],
        rule_rows: list[RuleRow],
    ) -> list[dict[str, Any]] | None:
        for row in rule_rows:
            payload: Any = from_json(row.value_json, {})
            if not isinstance(payload, dict):
                continue
            values = payload.get("values")
            if isinstance(values, list) and values:
                return [dict(value) for value in values if isinstance(value, dict)]
            min_values = payload.get("min_values")
            if isinstance(min_values, dict):
                approved_values: list[dict[str, Any]] = []
                for seed_value in seed_requirement.get("values", []):
                    if not isinstance(seed_value, dict):
                        continue
                    key = seed_value.get("key")
                    if key not in min_values:
                        return None
                    value = min_values[key]
                    if not isinstance(value, int | float):
                        return None
                    next_value = dict(seed_value)
                    next_value["min_value"] = float(value)
                    approved_values.append(next_value)
                if approved_values:
                    return approved_values
        return None

    def _create_decision_trace(
        self,
        project_id: str,
        result: CheckResult,
        payload: dict[str, Any],
    ) -> DecisionTrace:
        return DecisionTrace(
            project_id=project_id,
            check_result_id=result.id,
            inputs_json=to_json(payload["inputs"]),
            formula=payload["formula"],
            comparison=payload["comparison"],
            result=result.status,
            rule_ids_json=to_json(payload["rule_ids"]),
            resolved_rule_ids_json=to_json(payload["resolved_rule_ids"]),
            measurement_ids_json=to_json(payload["measurement_ids"]),
            citation_ids_json=to_json(payload["citation_refs"]),
            unit_conversions_json=to_json(payload["unit_conversions"]),
            rounding_policy=payload["rounding_policy"],
            tolerance=payload["tolerance"],
            input_sources_json=to_json(payload["input_sources"]),
            applicability_trace_json=to_json(payload["applicability_trace"]),
            precedence_trace_json=to_json(payload["precedence_trace"]),
            engine_version="draftcheck-compliance-v0.1",
            rule_snapshot_hash=payload["rule_snapshot_hash"],
            measurement_snapshot_hash=payload["measurement_snapshot_hash"],
        )

    def _decision_trace_payload(
        self,
        *,
        definition: CheckDefinition,
        requirement: dict[str, Any],
        proposed: str,
        comparison: str,
        status: str,
        missing: list[str],
        data_missing: list[str],
        measurements: list[ExtractedMeasurement],
        citations: list[dict[str, Any]],
        approved_rule_rows: list[RuleRow],
        approved_resolved_rules: list[ResolvedRule],
        as_of_date: str,
        assessment_basis: str,
    ) -> dict[str, Any]:
        measurement_inputs = [
            {
                "id": measurement.id,
                "key": measurement.key,
                "value": measurement.value,
                "unit": measurement.unit,
                "source": measurement.source,
                "confidence": measurement.confidence,
                "evidence_ref": measurement.evidence_ref,
            }
            for measurement in measurements
        ]
        citation_refs = [
            {
                "source_version_id": citation.get("source_version_id"),
                "clause_id": citation.get("clause_id"),
                "page_number": citation.get("page_number"),
            }
            for citation in citations
        ]
        inputs = {
            "check_definition_id": definition.id,
            "check_key": definition.key,
            "method": definition.method,
            "source_query": definition.source_query,
            "as_of_date": as_of_date,
            "assessment_basis": assessment_basis,
            "requirement": requirement,
            "measurements": measurement_inputs,
        }
        input_sources = [
            {
                "type": "measurement",
                "id": measurement["id"],
                "key": measurement["key"],
                "source": measurement["source"],
                "evidence_ref": measurement["evidence_ref"],
            }
            for measurement in measurement_inputs
        ] + [
            {
                "type": "approved_source_citation",
                "source_version_id": citation.get("source_version_id"),
                "clause_id": citation.get("clause_id"),
            }
            for citation in citations
        ]
        rule_rows: list[dict[str, Any]] = [
            {
                "id": row.id,
                "rule_key": row.rule_key,
                "operator": row.operator,
                "value_json": from_json(row.value_json, {}),
                "unit": row.unit,
                "clause_id": row.clause_id,
                "source_version_id": row.source_version_id,
                "lifecycle_status": row.lifecycle_status,
            }
            for row in approved_rule_rows
        ]
        resolved_rules: list[dict[str, Any]] = [
            {
                "id": row.id,
                "rule_row_id": row.rule_row_id,
                "status": row.status,
                "as_of_date": row.as_of_date,
                "assessment_basis": row.assessment_basis,
                "applies_reason": row.applies_reason,
                "overridden_rule_ids": from_json(row.overridden_rule_ids_json, []),
            }
            for row in approved_resolved_rules
        ]
        overridden_rule_ids_set: set[str] = set()
        for row in approved_resolved_rules:
            row_overridden_rule_ids: list[str] = from_json(row.overridden_rule_ids_json, [])
            overridden_rule_ids_set.update(row_overridden_rule_ids)
        overridden_rule_ids = sorted(overridden_rule_ids_set)
        rule_snapshot = {
            "requirement": requirement,
            "citation_refs": citation_refs,
            "rule_rows": rule_rows,
            "resolved_rules": resolved_rules,
        }
        measurement_snapshot = {"measurements": measurement_inputs}
        return {
            "inputs": inputs,
            "formula": self._formula_for(definition.method, requirement),
            "comparison": comparison or proposed,
            "rule_ids": [row.id for row in approved_rule_rows],
            "resolved_rule_ids": [row.id for row in approved_resolved_rules],
            "measurement_ids": [measurement.id for measurement in measurements],
            "citation_refs": citation_refs,
            "unit_conversions": [],
            "rounding_policy": self._rounding_policy_for(definition.method),
            "tolerance": None,
            "input_sources": input_sources,
            "applicability_trace": {
                "status": status,
                "data_missing": data_missing,
                "missing_information": missing,
                "approved_source_citations_found": bool(citations),
                "as_of_date": as_of_date,
                "assessment_basis": assessment_basis,
            },
            "precedence_trace": {
                "resolved_rule_support": "resolved_rule_found" if approved_resolved_rules else "not_available",
                "overrides_evaluated": bool(approved_resolved_rules),
                "overridden_rule_ids": overridden_rule_ids,
                "note": "Seed thresholds are not treated as final compliance without approved resolved rules.",
            },
            "rule_snapshot_hash": hash_text(to_json(rule_snapshot)),
            "measurement_snapshot_hash": hash_text(to_json(measurement_snapshot)),
        }

    def _formula_for(self, method: str, requirement: dict[str, Any]) -> str:
        if method == "max_percentage":
            return f"round(({requirement['part_key']} / {requirement['whole_key']}) * 100, 2) <= max_percent"
        if method == "min_percentage":
            return f"round(({requirement['part_key']} / {requirement['whole_key']}) * 100, 2) >= min_percent"
        if method == "min_value":
            return f"{requirement['value_key']} >= min_value"
        if method == "max_value":
            return f"{requirement['value_key']} <= max_value"
        if method == "all_min_values":
            return "all configured measurements >= their minimum values"
        if method == "garage_ratio":
            return f"round(({requirement['garage_key']} / {requirement['frontage_key']}) * 100, 2) <= max_percent"
        if method == "boundary_wall_ratio":
            return (
                f"round(({requirement['boundary_wall_key']} / {requirement['lot_boundary_key']}) * 100, 2) "
                "<= max_percent"
            )
        if method == "boolean_required":
            return f"{requirement['value_key']} == expected"
        if method == "trigger_flag":
            return f"{requirement['value_key']} == trigger_value"
        return "manual review"

    def _rounding_policy_for(self, method: str) -> str:
        if method in {"max_percentage", "min_percentage", "garage_ratio", "boundary_wall_ratio"}:
            return "round percentage/ratio calculation to 2 decimals before comparison"
        return "no rounding before comparison"

    def _result_to_schema(self, row: CheckResult, decision_trace: DecisionTrace | None = None) -> CheckResultRead:
        if decision_trace is None:
            decision_trace = self.db.scalar(
                select(DecisionTrace)
                .where(DecisionTrace.check_result_id == row.id)
                .order_by(DecisionTrace.created_at.desc())
            )
        return CheckResultRead(
            id=row.id,
            decision_trace_id=decision_trace.id if decision_trace else None,
            rule_ids=from_json(decision_trace.rule_ids_json, []) if decision_trace else [],
            resolved_rule_ids=from_json(decision_trace.resolved_rule_ids_json, []) if decision_trace else [],
            measurement_ids=from_json(decision_trace.measurement_ids_json, []) if decision_trace else [],
            check_key=row.check_key,
            label=row.label,
            category=row.category,
            status=row.status,  # type: ignore[arg-type]
            as_of_date=row.as_of_date,
            assessment_basis=row.assessment_basis,  # type: ignore[arg-type]
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


def _resolved_rule_citation_payloads(resolved_rules: list[ResolvedRule]) -> list[dict[str, Any]]:
    required_fields = {"source_document_id", "source_title", "source_version_id", "retrieved_at"}
    payloads: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for resolved_rule in resolved_rules:
        parsed: Any = from_json(resolved_rule.citations_json, [])
        if not isinstance(parsed, list):
            continue
        for item in parsed:
            if not isinstance(item, dict) or not required_fields.issubset(item):
                continue
            key = (
                item.get("source_version_id"),
                item.get("clause_id"),
                item.get("page_number"),
                item.get("quote"),
            )
            if key in seen:
                continue
            seen.add(key)
            payloads.append(item)
    return payloads


def _filter_rule_rows_by_regulatory_source_support(db: Session, rule_rows: list[RuleRow]) -> list[RuleRow]:
    support_cache: dict[str, bool] = {}
    supported: list[RuleRow] = []
    for row in rule_rows:
        if row.source_version_id not in support_cache:
            support_cache[row.source_version_id] = source_version_can_support_regulatory_output(
                db,
                row.source_version_id,
            )
        if support_cache[row.source_version_id]:
            supported.append(row)
    return supported


def _rule_row_citation_payloads(db: Session, rule_rows: list[RuleRow]) -> list[dict[str, Any]]:
    if not rule_rows:
        return []
    payloads: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for rule_row in rule_rows:
        citation_rows = db.scalars(
            select(SourceCitation)
            .where(
                SourceCitation.source_version_id == rule_row.source_version_id,
                SourceCitation.clause_id == rule_row.clause_id,
            )
            .order_by(SourceCitation.created_at)
        ).all()
        for citation in citation_rows:
            parsed: Any = from_json(citation.citation_json, {})
            if not isinstance(parsed, dict):
                continue
            key = (
                parsed.get("source_version_id"),
                parsed.get("clause_id"),
                parsed.get("heading"),
                parsed.get("page_number"),
            )
            if key in seen:
                continue
            seen.add(key)
            payloads.append(parsed)
    return payloads


def _measurement_evidence_refs(measurements: list[ExtractedMeasurement]) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for measurement in measurements:
        ref = measurement.evidence_ref or f"measurement:{measurement.id}:source:{measurement.source}"
        if ref in seen:
            continue
        seen.add(ref)
        refs.append(ref)
    return refs
