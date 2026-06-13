"""Validate sanitized parser real-sample evidence without DB persistence.

This checker gives operators a bounded offline place to record reviewed parser
sample outcomes. It intentionally does not write artifact rows, source-library
rows, or any other database-backed persistence.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any


SCHEMA_VERSION = "parser_real_sample_evidence_v1"
SAFE_SAMPLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,79}$")
SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")
FORBIDDEN_KEY_FRAGMENTS = (
    "raw_text",
    "raw_content",
    "raw_document",
    "source_text",
    "full_text",
    "extracted_text",
    "ocr_text",
    "content_bytes",
    "original_filename",
    "client_name",
    "address",
)
SUPPORTED_FORMATS = {
    "application/pdf",
    "application/dxf",
    "application/x-dxf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "model/ifc",
    "application/ifc",
    "text/plain",
    "text/csv",
}
REVIEWED_STATUSES = {"human_confirmed", "operator_reviewed"}


@dataclass(frozen=True)
class EvidenceCheck:
    status: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    report: dict[str, Any]


def load_evidence(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("evidence file must contain a JSON object")
    return data


def check_evidence(data: dict[str, Any], *, min_samples: int = 1) -> EvidenceCheck:
    errors: list[str] = []
    warnings: list[str] = []

    _check_forbidden_content(data, path="$", errors=errors)

    schema_version = data.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        errors.append(f"$.schema_version must be {SCHEMA_VERSION!r}")

    samples = data.get("samples")
    if not isinstance(samples, list):
        errors.append("$.samples must be a list")
        samples = []
    if len(samples) < min_samples:
        errors.append(f"$.samples must contain at least {min_samples} reviewed sample(s)")

    sample_reports: list[dict[str, Any]] = []
    valid_sample_count = 0
    total_expected = 0
    total_matched = 0
    total_mismatched = 0
    total_false_positive = 0

    for index, sample in enumerate(samples):
        sample_path = f"$.samples[{index}]"
        if not isinstance(sample, dict):
            errors.append(f"{sample_path} must be an object")
            continue

        sample_errors: list[str] = []
        sample_warnings: list[str] = []
        sample_report = _check_sample(sample, sample_path, sample_errors, sample_warnings)
        errors.extend(sample_errors)
        warnings.extend(sample_warnings)
        sample_reports.append(sample_report)
        if sample_report["status"] == "passed":
            valid_sample_count += 1
        total_expected += sample_report["expected_fact_count"]
        total_matched += sample_report["matched_fact_count"]
        total_mismatched += sample_report["mismatched_fact_count"]
        total_false_positive += sample_report["false_positive_count"]

    if valid_sample_count < min_samples:
        errors.append(f"valid reviewed sample count {valid_sample_count} is below required {min_samples}")

    status = "passed" if not errors else "blocked"
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "valid_sample_count": valid_sample_count,
        "required_sample_count": min_samples,
        "sample_count": len(samples),
        "expected_fact_count": total_expected,
        "matched_fact_count": total_matched,
        "mismatched_fact_count": total_mismatched,
        "false_positive_count": total_false_positive,
        "beta_status": "not_beta_ready",
        "beta_blockers_remaining": [
            "persistence-connected validation is DB-owned and not checked here",
            "real-sample evidence must remain operator-reviewed and sanitized",
            "parser evidence here is advisory and does not certify compliance",
        ],
        "samples": sample_reports,
        "errors": errors,
        "warnings": warnings,
    }
    return EvidenceCheck(
        status=status,
        errors=tuple(errors),
        warnings=tuple(warnings),
        report=report,
    )


def _check_sample(
    sample: dict[str, Any],
    sample_path: str,
    errors: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    sample_id = _string(sample.get("sample_id"))
    if sample_id is None or not SAFE_SAMPLE_ID.match(sample_id):
        errors.append(f"{sample_path}.sample_id must be 3-80 safe filename characters")
        sample_id = f"sample_{sample_path}"

    reviewed_by = _string(sample.get("reviewed_by"))
    if reviewed_by is None:
        errors.append(f"{sample_path}.reviewed_by is required")

    reviewed_at = _string(sample.get("reviewed_at"))
    if reviewed_at is None or not _is_timezone_datetime(reviewed_at):
        errors.append(f"{sample_path}.reviewed_at must be an ISO-8601 datetime with timezone")

    sanitization = sample.get("sanitization")
    if not isinstance(sanitization, dict):
        errors.append(f"{sample_path}.sanitization must be an object")
        sanitization = {}
    if sanitization.get("operator_reviewed") is not True:
        errors.append(f"{sample_path}.sanitization.operator_reviewed must be true")
    if sanitization.get("raw_source_retained") is not False:
        errors.append(f"{sample_path}.sanitization.raw_source_retained must be false")
    if sanitization.get("contains_personal_info") is not False:
        errors.append(f"{sample_path}.sanitization.contains_personal_info must be false")
    if sanitization.get("contains_client_identifiers") is not False:
        errors.append(f"{sample_path}.sanitization.contains_client_identifiers must be false")

    document = sample.get("document")
    if not isinstance(document, dict):
        errors.append(f"{sample_path}.document must be an object")
        document = {}
    media_type = _string(document.get("media_type"))
    if media_type not in SUPPORTED_FORMATS:
        errors.append(f"{sample_path}.document.media_type must be a supported parser media type")
    if _string(document.get("parser_name")) is None:
        errors.append(f"{sample_path}.document.parser_name is required")
    if _string(document.get("parser_version")) is None:
        errors.append(f"{sample_path}.document.parser_version is required")
    source_hash = _string(document.get("source_hash_sha256"))
    if source_hash is None or not SHA256.match(source_hash):
        errors.append(f"{sample_path}.document.source_hash_sha256 must be a SHA-256 hex digest")
    page_count = document.get("page_count")
    if not isinstance(page_count, int) or page_count < 1:
        errors.append(f"{sample_path}.document.page_count must be a positive integer")

    expected = sample.get("expected_facts")
    extracted = sample.get("extracted_facts")
    if not isinstance(expected, list) or not expected:
        errors.append(f"{sample_path}.expected_facts must be a non-empty list")
        expected = []
    if not isinstance(extracted, list):
        errors.append(f"{sample_path}.extracted_facts must be a list")
        extracted = []

    expected_by_key = _facts_by_key(expected, f"{sample_path}.expected_facts", errors)
    extracted_by_key = _facts_by_key(extracted, f"{sample_path}.extracted_facts", errors)
    matches, mismatches, missing = _compare_expected_facts(expected_by_key, extracted_by_key)
    false_positives = sorted(set(extracted_by_key) - set(expected_by_key))

    for key, reason in mismatches.items():
        errors.append(f"{sample_path}.facts[{key}] mismatch: {reason}")
    for key in missing:
        errors.append(f"{sample_path}.expected_facts[{key}] was not extracted")
    for key in false_positives:
        errors.append(f"{sample_path}.extracted_facts[{key}] has no expected counterpart")

    for fact_index, fact in enumerate(extracted):
        fact_path = f"{sample_path}.extracted_facts[{fact_index}]"
        if not isinstance(fact, dict):
            continue
        if _string(fact.get("review_status")) not in REVIEWED_STATUSES:
            errors.append(f"{fact_path}.review_status must be operator-reviewed")
        confidence = fact.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
            errors.append(f"{fact_path}.confidence must be a number from 0 to 1")
        if fact.get("measurement_compliance_ready") is not False:
            errors.append(f"{fact_path}.measurement_compliance_ready must be false")

    status = "passed" if not (mismatches or missing or errors) else "blocked"
    return {
        "sample_id": sample_id,
        "status": status,
        "media_type": media_type,
        "expected_fact_count": len(expected_by_key),
        "extracted_fact_count": len(extracted_by_key),
        "matched_fact_count": len(matches),
        "mismatched_fact_count": len(mismatches),
        "missing_fact_count": len(missing),
        "false_positive_count": len(false_positives),
        "matched_facts": sorted(matches),
        "mismatched_facts": mismatches,
        "missing_facts": sorted(missing),
        "false_positives": false_positives,
    }


def _facts_by_key(
    facts: list[Any],
    facts_path: str,
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    facts_by_key: dict[str, dict[str, Any]] = {}
    for index, fact in enumerate(facts):
        fact_path = f"{facts_path}[{index}]"
        if not isinstance(fact, dict):
            errors.append(f"{fact_path} must be an object")
            continue
        key = _string(fact.get("fact_key"))
        if key is None:
            errors.append(f"{fact_path}.fact_key is required")
            continue
        if key in facts_by_key:
            errors.append(f"{fact_path}.fact_key duplicates {key!r}")
            continue
        if _string(fact.get("fact_type")) is None:
            errors.append(f"{fact_path}.fact_type is required")
        if "numeric_value" not in fact and "text_value" not in fact:
            errors.append(f"{fact_path} must include numeric_value or text_value")
        if "numeric_value" in fact and not isinstance(fact.get("numeric_value"), (int, float)):
            errors.append(f"{fact_path}.numeric_value must be numeric")
        facts_by_key[key] = fact
    return facts_by_key


def _compare_expected_facts(
    expected_by_key: dict[str, dict[str, Any]],
    extracted_by_key: dict[str, dict[str, Any]],
) -> tuple[set[str], dict[str, str], set[str]]:
    matches: set[str] = set()
    mismatches: dict[str, str] = {}
    missing = set(expected_by_key) - set(extracted_by_key)
    for key, expected in expected_by_key.items():
        extracted = extracted_by_key.get(key)
        if extracted is None:
            continue
        reason = _fact_mismatch_reason(expected, extracted)
        if reason is None:
            matches.add(key)
        else:
            mismatches[key] = reason
    return matches, mismatches, missing


def _fact_mismatch_reason(expected: dict[str, Any], extracted: dict[str, Any]) -> str | None:
    expected_type = expected.get("fact_type")
    if expected_type != extracted.get("fact_type"):
        return f"fact_type {extracted.get('fact_type')!r} != expected {expected_type!r}"

    expected_unit = expected.get("unit")
    if expected_unit != extracted.get("unit"):
        return f"unit {extracted.get('unit')!r} != expected {expected_unit!r}"

    if "numeric_value" in expected:
        tolerance = float(expected.get("tolerance") or 0.001)
        extracted_value = extracted.get("numeric_value")
        if not isinstance(extracted_value, (int, float)):
            return "numeric_value is missing or non-numeric"
        delta = abs(float(expected["numeric_value"]) - float(extracted_value))
        if delta > tolerance:
            return f"numeric_value delta {delta} exceeds tolerance {tolerance}"
    elif expected.get("text_value") != extracted.get("text_value"):
        return "text_value differs from expected"
    return None


def _check_forbidden_content(value: Any, *, path: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            normalized = key_text.lower()
            if any(fragment in normalized for fragment in FORBIDDEN_KEY_FRAGMENTS):
                errors.append(f"{path}.{key_text} is not allowed in sanitized evidence")
            _check_forbidden_content(child, path=f"{path}.{key_text}", errors=errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_forbidden_content(child, path=f"{path}[{index}]", errors=errors)
    elif isinstance(value, str) and len(value) > 500:
        errors.append(f"{path} string exceeds 500 characters; store only bounded sanitized evidence")


def _string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _is_timezone_datetime(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_json", type=Path, help="Sanitized parser sample evidence JSON")
    parser.add_argument("--min-samples", type=int, default=1)
    parser.add_argument("--output", type=Path, help="Optional path for the JSON check report")
    args = parser.parse_args(argv)

    if args.min_samples < 1:
        parser.error("--min-samples must be at least 1")

    check = check_evidence(load_evidence(args.evidence_json), min_samples=args.min_samples)
    output = json.dumps(check.report, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0 if check.status == "passed" else 2


if __name__ == "__main__":
    sys.exit(main())
