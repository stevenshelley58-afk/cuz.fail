from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_core.audit import record_audit
from draftcheck_core.json_utils import from_json, to_json
from draftcheck_core.models import GoldenEvalCase, GoldenEvalRun, ReviewQueueItem
from draftcheck_core.review_queue import OPEN_REVIEW_STATUSES, ReviewQueueService
from draftcheck_shared.schemas import (
    AddressResolveRequest,
    GoldenEvalCaseCreate,
    GoldenEvalCaseRead,
    GoldenEvalRunRead,
    GoldenEvalRunRequest,
    ReviewQueueItemCreate,
)


class GoldenEvalService:
    def __init__(self, db: Session):
        self.db = db

    def create_case(self, payload: GoldenEvalCaseCreate) -> GoldenEvalCaseRead:
        case = GoldenEvalCase(
            track=payload.track,
            name=payload.name,
            input_json=to_json(payload.input),
            expected_json=to_json(payload.expected),
            source_version_ids_json=to_json(payload.source_version_ids),
            is_active=payload.is_active,
            created_by=payload.created_by,
            notes=payload.notes,
        )
        self.db.add(case)
        self.db.flush()
        record_audit(
            self.db,
            action="golden_eval.case_created",
            target_type="golden_eval_case",
            target_id=case.id,
            metadata={"track": case.track, "name": case.name, "is_active": case.is_active},
        )
        self.db.flush()
        return _golden_eval_case_read(case)

    def list_cases(self, *, track: str | None = None, active_only: bool = True) -> list[GoldenEvalCaseRead]:
        stmt = select(GoldenEvalCase).order_by(GoldenEvalCase.track, GoldenEvalCase.name)
        if track:
            stmt = stmt.where(GoldenEvalCase.track == track)
        if active_only:
            stmt = stmt.where(GoldenEvalCase.is_active.is_(True))
        return [_golden_eval_case_read(case) for case in self.db.scalars(stmt)]

    def run(self, payload: GoldenEvalRunRequest) -> GoldenEvalRunRead:
        now = datetime.now(UTC).replace(tzinfo=None)
        cases = self._active_cases(payload.track)
        case_results = [self._evaluate_case(case) for case in cases]
        case_count = len(cases)
        passed_count = sum(1 for result in case_results if result["status"] == "passed")
        failed_count = case_count - passed_count
        false_likely_pass_count = sum(_false_likely_pass_count(result) for result in case_results)
        passed = case_count > 0 and failed_count == 0
        metrics: dict[str, Any] = {
            "case_count": case_count,
            "passed_count": passed_count,
            "failed_count": failed_count,
            "false_likely_pass_count": false_likely_pass_count,
            "release_gate_satisfied": passed,
        }
        status = "no_cases" if case_count == 0 else "passed" if passed else "failed"
        run = GoldenEvalRun(
            track=payload.track,
            status=status,
            passed=passed,
            case_count=case_count,
            passed_count=passed_count,
            failed_count=failed_count,
            metrics_json=to_json(metrics),
            case_results_json=to_json(case_results),
            commit_sha=payload.commit_sha,
            model_version=payload.model_version,
            run_by=payload.run_by,
            started_at=now,
            finished_at=now,
        )
        self.db.add(run)
        self.db.flush()
        if failed_count > 0:
            ReviewQueueService(self.db).enqueue(
                ReviewQueueItemCreate(
                    queue="eval_failure_review",
                    target_type="golden_eval_run",
                    target_id=run.id,
                    reason="Golden eval release gate is not satisfied",
                    blocking_level="blocking",
                    evidence={
                        "track": payload.track,
                        "case_count": case_count,
                        "passed_count": passed_count,
                        "failed_count": failed_count,
                        "failed_case_ids": [
                            result["case_id"] for result in case_results if result["status"] == "failed"
                        ],
                    },
                    suggested_action="Fix failed golden eval cases and rerun before release.",
                    priority="critical",
                )
            )
        elif case_count > 0:
            self._resolve_open_eval_failures(payload.track)
        record_audit(
            self.db,
            action="golden_eval.run_created",
            target_type="golden_eval_run",
            target_id=run.id,
            metadata={
                "track": payload.track,
                "status": run.status,
                "case_count": case_count,
                "passed": run.passed,
            },
        )
        self.db.flush()
        return _golden_eval_run_read(run)

    def _evaluate_case(self, case: GoldenEvalCase) -> dict[str, Any]:
        case_input: dict[str, Any] = from_json(case.input_json, {})
        expected: dict[str, Any] = from_json(case.expected_json, {})
        source_version_ids: list[str] = from_json(case.source_version_ids_json, [])
        try:
            actual = self._actual_for_case(case.track, case_input)
            if case.track == "retrieval":
                matched, mismatches = _matches_retrieval_expected(actual, expected)
            else:
                matched, mismatches = _matches_expected(actual, expected)
            return {
                "case_id": case.id,
                "track": case.track,
                "name": case.name,
                "status": "passed" if matched else "failed",
                "reason": "Expected output matched." if matched else "Expected output did not match actual output.",
                "source_version_ids": source_version_ids,
                "input": case_input,
                "expected": expected,
                "actual": actual,
                "mismatches": mismatches,
            }
        except Exception as exc:
            return {
                "case_id": case.id,
                "track": case.track,
                "name": case.name,
                "status": "failed",
                "reason": f"Eval case execution failed: {exc}",
                "source_version_ids": source_version_ids,
                "input": case_input,
                "expected": expected,
                "actual": {},
                "mismatches": [{"path": "$", "expected": expected, "actual": str(exc)}],
            }

    def _actual_for_case(self, track: str, case_input: dict[str, Any]) -> dict[str, Any]:
        if track == "retrieval":
            from draftcheck_retrieval.service import RetrievalService

            question = _required_text(case_input, "question", "q", "query")
            answer = RetrievalService(self.db).ask(question, case_input.get("source_filters") or case_input.get("filters"))
            actual = answer.model_dump(mode="json")
            actual["citation_count"] = len(answer.citations)
            actual["citation_titles"] = [citation.source_title for citation in answer.citations]
            return actual

        if track == "rule_extraction":
            from draftcheck_compliance.rule_audits import RuleAuditService
            from draftcheck_compliance.rules import RuleGovernanceService
            from draftcheck_core.models import Clause, RuleRow

            source_version_id = case_input.get("source_version_id")
            coverage = RuleGovernanceService(self.db).coverage_audit(source_version_id=source_version_id)
            no_orphan = RuleAuditService(self.db).no_orphan_audit(source_version_id=source_version_id)
            rule_stmt = select(RuleRow).order_by(RuleRow.rule_key, RuleRow.created_at)
            if source_version_id:
                rule_stmt = rule_stmt.where(RuleRow.source_version_id == source_version_id)
            rules: list[dict[str, Any]] = []
            for rule in self.db.scalars(rule_stmt):
                clause = self.db.get(Clause, rule.clause_id)
                quote_anchor_valid = bool(
                    clause
                    and clause.source_version_id == rule.source_version_id
                    and " ".join(rule.quote.split()) in " ".join(clause.text.split())
                )
                rules.append(
                    {
                        "id": rule.id,
                        "rule_key": rule.rule_key,
                        "operator": rule.operator,
                        "value": from_json(rule.value_json, {}),
                        "unit": rule.unit,
                        "condition_text": rule.condition_text,
                        "quote": rule.quote,
                        "clause_id": rule.clause_id,
                        "source_version_id": rule.source_version_id,
                        "lifecycle_status": rule.lifecycle_status,
                        "quote_anchor_valid": quote_anchor_valid,
                    }
                )
            return {
                "source_version_id": source_version_id,
                "rules": rules,
                "coverage": coverage.model_dump(mode="json"),
                "coverage_gap_count": coverage.gap_count,
                "coverage_summary": coverage.summary,
                "no_orphan": no_orphan.model_dump(mode="json"),
                "no_orphan_blocking_count": no_orphan.blocking_count,
                "no_orphan_summary": no_orphan.summary,
            }

        if track == "spatial_resolution":
            from draftcheck_core.address_service import AddressResolutionService

            payload = AddressResolveRequest(
                address=_required_text(case_input, "address"),
                as_of_date=case_input.get("as_of_date"),
                assessment_basis=case_input.get("assessment_basis", "current_rules"),
                facts=case_input.get("facts", []),
            )
            profile = AddressResolutionService(self.db).resolve_address(
                payload,
                project_id=case_input.get("project_id"),
            )
            actual = profile.model_dump(mode="json")
            actual["fact_types"] = [fact.fact_type for fact in profile.facts]
            return actual

        if track == "drawing_extraction":
            from draftcheck_document_ai.service import DocumentAnalysisService

            project_id = _required_text(case_input, "project_id")
            document_id = _required_text(case_input, "document_id")
            service = DocumentAnalysisService(self.db)
            if case_input.get("analyze", True):
                results = service.analyze_document(project_id, document_id)
            else:
                results = []
                service.extract_facts_for_document(project_id, document_id)
            facts = service.list_facts(project_id, document_id)
            return {
                "project_id": project_id,
                "document_id": document_id,
                "result_count": len(results),
                "statuses": [result.status for result in results],
                "facts": facts,
                "fact_count": len(facts),
                "fact_labels": [fact.get("label") for fact in facts],
                "measurement_ready_fact_labels": [
                    fact.get("label")
                    for fact in facts
                    if fact.get("metadata", {}).get("measurement_compliance_ready") is True
                ],
            }

        if track == "compliance":
            from draftcheck_compliance.service import ComplianceService

            project_id = _required_text(case_input, "project_id")
            matrix = ComplianceService(self.db).run_checks(project_id)
            actual = matrix.model_dump(mode="json")
            actual["result_count"] = len(matrix.results)
            actual["statuses_by_check"] = {result.check_key: result.status for result in matrix.results}
            actual["missing_information_by_check"] = {
                result.check_key: result.missing_information for result in matrix.results
            }
            return actual

        raise ValueError(f"Unsupported eval track: {track}")

    def _resolve_open_eval_failures(self, track: str | None) -> None:
        for item in self.db.scalars(
            select(ReviewQueueItem).where(
                ReviewQueueItem.queue == "eval_failure_review",
                ReviewQueueItem.status.in_(OPEN_REVIEW_STATUSES),
            )
        ):
            evidence: dict[str, Any] = from_json(item.evidence_json, {})
            if evidence.get("track") == track:
                item.status = "resolved"

    def get_run(self, run_id: str) -> GoldenEvalRunRead:
        run = self.db.get(GoldenEvalRun, run_id)
        if not run:
            raise KeyError("Golden eval run not found")
        return _golden_eval_run_read(run)

    def _active_cases(self, track: str | None) -> list[GoldenEvalCase]:
        stmt = select(GoldenEvalCase).where(GoldenEvalCase.is_active.is_(True)).order_by(GoldenEvalCase.name)
        if track:
            stmt = stmt.where(GoldenEvalCase.track == track)
        return list(self.db.scalars(stmt))


def _golden_eval_case_read(case: GoldenEvalCase) -> GoldenEvalCaseRead:
    return GoldenEvalCaseRead(
        id=case.id,
        track=case.track,  # type: ignore[arg-type]
        name=case.name,
        input=from_json(case.input_json, {}),
        expected=from_json(case.expected_json, {}),
        source_version_ids=from_json(case.source_version_ids_json, []),
        is_active=case.is_active,
        created_by=case.created_by,
        notes=case.notes,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


def _golden_eval_run_read(run: GoldenEvalRun) -> GoldenEvalRunRead:
    return GoldenEvalRunRead(
        id=run.id,
        track=run.track,  # type: ignore[arg-type]
        status=run.status,
        passed=run.passed,
        case_count=run.case_count,
        passed_count=run.passed_count,
        failed_count=run.failed_count,
        metrics=from_json(run.metrics_json, {}),
        case_results=from_json(run.case_results_json, []),
        commit_sha=run.commit_sha,
        model_version=run.model_version,
        engine_version=run.engine_version,
        run_by=run.run_by,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _required_text(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise ValueError(f"Missing required text field: {'/'.join(keys)}")


def _matches_expected(actual: Any, expected: Any, path: str = "$") -> tuple[bool, list[dict[str, Any]]]:
    mismatches: list[dict[str, Any]] = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False, [{"path": path, "expected": expected, "actual": actual}]
        for key, expected_value in expected.items():
            if key not in actual:
                mismatches.append({"path": f"{path}.{key}", "expected": expected_value, "actual": "<missing>"})
                continue
            matched, nested = _matches_expected(actual[key], expected_value, f"{path}.{key}")
            if not matched:
                mismatches.extend(nested)
        return not mismatches, mismatches
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False, [{"path": path, "expected": expected, "actual": actual}]
        for index, expected_item in enumerate(expected):
            if not any(_matches_expected(actual_item, expected_item, f"{path}[{index}]")[0] for actual_item in actual):
                mismatches.append({"path": f"{path}[{index}]", "expected": expected_item, "actual": actual})
        return not mismatches, mismatches
    if actual != expected:
        return False, [{"path": path, "expected": expected, "actual": actual}]
    return True, []


_RETRIEVAL_EXPECTATION_KEYS = {
    "answer_contains",
    "answer_not_contains",
    "citation_titles_include",
    "citation_titles_include_any",
    "citation_titles_exclude",
    "min_citation_count",
    "max_citation_count",
    "source_version_ids_include",
    "source_version_ids_include_any",
}


def _matches_retrieval_expected(actual: dict[str, Any], expected: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    generic_expected = {
        key: value for key, value in expected.items() if key not in _RETRIEVAL_EXPECTATION_KEYS
    }
    matched, mismatches = _matches_expected(actual, generic_expected)
    mismatches.extend(_retrieval_quality_mismatches(actual, expected))
    return matched and not mismatches, mismatches


def _retrieval_quality_mismatches(actual: dict[str, Any], expected: dict[str, Any]) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    answer = str(actual.get("answer") or "")
    citation_titles = [str(title) for title in actual.get("citation_titles") or []]
    source_version_ids = [str(source_version_id) for source_version_id in actual.get("source_version_ids") or []]
    citation_count = int(actual.get("citation_count") or 0)

    for index, required_text in enumerate(_expected_string_list(expected, "answer_contains")):
        if required_text.casefold() not in answer.casefold():
            mismatches.append(
                {
                    "path": f"$.answer_contains[{index}]",
                    "expected": required_text,
                    "actual": answer,
                }
            )

    for index, forbidden_text in enumerate(_expected_string_list(expected, "answer_not_contains")):
        if forbidden_text.casefold() in answer.casefold():
            mismatches.append(
                {
                    "path": f"$.answer_not_contains[{index}]",
                    "expected": f"not present: {forbidden_text}",
                    "actual": answer,
                }
            )

    for index, required_title in enumerate(_expected_string_list(expected, "citation_titles_include")):
        if not any(required_title.casefold() == title.casefold() for title in citation_titles):
            mismatches.append(
                {
                    "path": f"$.citation_titles_include[{index}]",
                    "expected": required_title,
                    "actual": citation_titles,
                }
            )

    for index, allowed_titles in enumerate(_expected_string_groups(expected, "citation_titles_include_any")):
        if not any(
            allowed_title.casefold() == title.casefold()
            for allowed_title in allowed_titles
            for title in citation_titles
        ):
            mismatches.append(
                {
                    "path": f"$.citation_titles_include_any[{index}]",
                    "expected": allowed_titles,
                    "actual": citation_titles,
                }
            )

    for index, forbidden_title in enumerate(_expected_string_list(expected, "citation_titles_exclude")):
        if any(forbidden_title.casefold() == title.casefold() for title in citation_titles):
            mismatches.append(
                {
                    "path": f"$.citation_titles_exclude[{index}]",
                    "expected": f"not present: {forbidden_title}",
                    "actual": citation_titles,
                }
            )

    for index, required_version_id in enumerate(_expected_string_list(expected, "source_version_ids_include")):
        if required_version_id not in source_version_ids:
            mismatches.append(
                {
                    "path": f"$.source_version_ids_include[{index}]",
                    "expected": required_version_id,
                    "actual": source_version_ids,
                }
            )

    for index, allowed_version_ids in enumerate(_expected_string_groups(expected, "source_version_ids_include_any")):
        if not any(allowed_version_id in source_version_ids for allowed_version_id in allowed_version_ids):
            mismatches.append(
                {
                    "path": f"$.source_version_ids_include_any[{index}]",
                    "expected": allowed_version_ids,
                    "actual": source_version_ids,
                }
            )

    min_citation_count = expected.get("min_citation_count")
    if isinstance(min_citation_count, int) and citation_count < min_citation_count:
        mismatches.append(
            {
                "path": "$.min_citation_count",
                "expected": min_citation_count,
                "actual": citation_count,
            }
        )

    max_citation_count = expected.get("max_citation_count")
    if isinstance(max_citation_count, int) and citation_count > max_citation_count:
        mismatches.append(
            {
                "path": "$.max_citation_count",
                "expected": max_citation_count,
                "actual": citation_count,
            }
        )

    return mismatches


def _expected_string_list(expected: dict[str, Any], key: str) -> list[str]:
    value = expected.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _expected_string_groups(expected: dict[str, Any], key: str) -> list[list[str]]:
    value = expected.get(key, [])
    if not isinstance(value, list):
        return []
    groups: list[list[str]] = []
    for item in value:
        if isinstance(item, list):
            group = [nested for nested in item if isinstance(nested, str)]
            if group:
                groups.append(group)
        elif isinstance(item, str):
            groups.append([item])
    return groups


def _false_likely_pass_count(case_result: dict[str, Any]) -> int:
    if case_result.get("track") != "compliance":
        return 0
    actual_statuses = case_result.get("actual", {}).get("statuses_by_check", {})
    expected_statuses = case_result.get("expected", {}).get("statuses_by_check", {})
    if not isinstance(actual_statuses, dict) or not isinstance(expected_statuses, dict):
        return 0
    return sum(
        1
        for check_key, expected_status in expected_statuses.items()
        if actual_statuses.get(check_key) == "likely_pass" and expected_status != "likely_pass"
    )
