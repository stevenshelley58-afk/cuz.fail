"""Evaluation framework — runs skill_versions against eval_cases, records eval_runs."""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4


@dataclass
class EvalSuiteResult:
    suite_name: str
    skill_version_id: str | None
    pass_count: int = 0
    fail_count: int = 0
    error_count: int = 0
    mean_score: float = 0.0
    run_ids: list[str] = field(default_factory=list)


class EvalRunner:
    """Runs eval_cases for a suite and persists eval_runs rows."""

    def __init__(self, adapter: Any, session_factory: Any) -> None:
        self.adapter = adapter
        self.session_factory = session_factory

    async def run_suite(
        self, suite_name: str, skill_version_id: str | None = None
    ) -> EvalSuiteResult:
        from draftcheck.db.models import EvalCase

        result = EvalSuiteResult(suite_name=suite_name, skill_version_id=skill_version_id)
        scores: list[float] = []

        with self.session_factory() as session:
            cases = (
                session.query(EvalCase)
                .filter(
                    EvalCase.suite_name == suite_name,
                    EvalCase.status == "active",
                )
                .all()
            )

        for case in cases:
            run = await self.run_case(case, skill_version_id)
            result.run_ids.append(str(run["id"]))
            status = run["status"]
            if status == "pass":
                result.pass_count += 1
            elif status == "error":
                result.error_count += 1
            else:
                result.fail_count += 1
            if run.get("score") is not None:
                scores.append(float(run["score"]))

        if scores:
            result.mean_score = sum(scores) / len(scores)

        return result

    async def run_case(
        self, case: Any, skill_version_id: str | None
    ) -> dict[str, Any]:
        from draftcheck.ai.substrate import ModelRequest
        from draftcheck.db.models import EvalRun

        run_id = uuid4()
        started_at = datetime.now(tz=UTC)
        effective_skill_version = skill_version_id or case.skill_name

        try:
            prompt = self._build_prompt(case)
            request = ModelRequest(
                job_id=str(run_id),
                job_type=f"eval_{case.skill_name}",
                skill_version_id=effective_skill_version,
                prompt=prompt,
                max_output_tokens=512,
            )
            response = self.adapter.complete(request)

            output: dict[str, Any] = {}
            if response.status == "succeeded" and response.text:
                try:
                    output = json.loads(response.text)
                except json.JSONDecodeError:
                    output = {"raw_text": response.text}

            score = self.score_output(output, case.expected_json, case.skill_name)
            status = "pass" if score >= 1.0 else "fail"

        except Exception as exc:
            output = {"error": str(exc), "traceback": traceback.format_exc()}
            score = 0.0
            status = "error"
            response = None

        finished_at = datetime.now(tz=UTC)

        run_row = EvalRun(
            id=run_id,
            eval_case_id=case.id,
            skill_version_id=effective_skill_version if effective_skill_version else None,
            status=status,
            score=Decimal(str(round(score, 4))),
            output_json=output,
            metrics_json={
                "input_tokens": getattr(response, "input_tokens", None),
                "output_tokens": getattr(response, "output_tokens", None),
                "cost_cents": getattr(response, "cost_cents", None),
            }
            if response
            else {},
            started_at=started_at,
            finished_at=finished_at,
            error=output.get("error") if status == "error" else None,
        )

        with self.session_factory() as session:
            session.add(run_row)
            session.commit()

        return {
            "id": run_id,
            "status": status,
            "score": score,
            "output": output,
        }

    def _build_prompt(self, case: Any) -> str:
        input_data = case.input_json
        if isinstance(input_data, dict):
            text = input_data.get("clause_text") or input_data.get("text") or json.dumps(input_data)
        else:
            text = str(input_data)
        return (
            f"Skill: {case.skill_name}\n"
            f"Input: {text}\n"
            f"Respond with JSON matching the expected output schema."
        )

    def score_output(self, output: dict[str, Any], expected: dict[str, Any], skill_name: str) -> float:
        if not isinstance(output, dict) or not isinstance(expected, dict):
            return 0.0

        if skill_name == "rule_extraction":
            return self._score_rule_extraction(output, expected)
        elif skill_name == "compliance_check":
            return self._score_compliance_check(output, expected)
        elif skill_name == "search_ask":
            return self._score_search_ask(output, expected)
        else:
            return 1.0 if output == expected else 0.0

    def _score_rule_extraction(self, output: dict[str, Any], expected: dict[str, Any]) -> float:
        """Score: rule_key matches, operator matches, value within 5% tolerance."""
        if output.get("rule_key") != expected.get("rule_key"):
            return 0.0
        if output.get("operator") != expected.get("operator"):
            return 0.0

        expected_value = expected.get("value")
        output_value = output.get("value")
        if expected_value is None and output_value is None:
            return 1.0
        if expected_value is None or output_value is None:
            return 0.0

        try:
            exp_f = float(expected_value)
            out_f = float(output_value)
            if exp_f == 0:
                within_tolerance = out_f == 0
            else:
                within_tolerance = abs(out_f - exp_f) / abs(exp_f) <= 0.05
        except (TypeError, ValueError):
            within_tolerance = str(output_value) == str(expected_value)

        return 1.0 if within_tolerance else 0.0

    def _score_compliance_check(self, output: dict[str, Any], expected: dict[str, Any]) -> float:
        """Score: status matches exactly."""
        return 1.0 if output.get("status") == expected.get("status") else 0.0

    def _score_search_ask(self, output: dict[str, Any], expected: dict[str, Any]) -> float:
        """Score: fraction of expected citation IDs found in output."""
        expected_ids: list[str] = expected.get("citation_ids", [])
        if not expected_ids:
            return 1.0
        output_ids: set[str] = set(output.get("citation_ids", []))
        found = sum(1 for eid in expected_ids if eid in output_ids)
        return found / len(expected_ids)
