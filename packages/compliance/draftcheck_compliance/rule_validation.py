from __future__ import annotations

import re
from typing import Any


CANONICAL_CLAUSE_DISPOSITIONS = {
    "rule_bearing",
    "definition",
    "procedural",
    "informational",
    "manual_review",
}
DEPRECATED_CLAUSE_DISPOSITIONS = {
    "definitions": "definition",
    "fluff": "informational",
}
RULE_CANDIDATE_STATUSES = {"candidate", "pending_review", "rejected"}
RULE_LIFECYCLE_STATUSES = {
    "auto_accepted",
    "approved",
    "pending_review",
    "rejected",
    "stale",
    "superseded",
}
APPROVED_RULE_STATUSES = {"auto_accepted", "approved"}

_RULE_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_NORMATIVE_PATTERN = re.compile(
    r"\b(must|shall|required|not permitted|unless|except|deemed-to-comply|"
    r"deemed to comply|may be approved|performance criteria|acceptable outcome|"
    r"notwithstanding|despite|does not apply)\b",
    re.IGNORECASE,
)


def validate_rule_key(rule_key: str) -> str:
    normalized = rule_key.strip()
    if not _RULE_KEY_PATTERN.fullmatch(normalized):
        raise ValueError("Rule key must be lowercase snake_case and use the closed vocabulary shape")
    return normalized


def has_normative_language(value: str) -> bool:
    return any(not _is_negated_deemed_to_comply(value, match) for match in _NORMATIVE_PATTERN.finditer(value))


def normalize_clause_disposition(value: str, clause_text: str = "") -> str:
    normalized = value.strip().lower()
    normalized = DEPRECATED_CLAUSE_DISPOSITIONS.get(normalized, normalized)
    if normalized not in CANONICAL_CLAUSE_DISPOSITIONS:
        raise ValueError(f"Unsupported ClauseDisposition: {value}")
    if normalized == "informational" and has_normative_language(clause_text):
        raise ValueError("Normative clauses cannot be classified as informational")
    return normalized


def validate_rule_candidate_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized not in RULE_CANDIDATE_STATUSES:
        raise ValueError(f"Unsupported RuleExtractionCandidate.status: {status}")
    return normalized


def validate_rule_lifecycle_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized == "needs_review":
        raise ValueError("Deprecated RuleRow status: needs_review; use pending_review")
    if normalized not in RULE_LIFECYCLE_STATUSES:
        raise ValueError(f"Unsupported RuleRow.lifecycle_status: {status}")
    return normalized


def validate_rule_row_for_status(
    *,
    lifecycle_status: str,
    quote: str,
    clause_id: str | None,
    source_version_id: str | None,
) -> str:
    normalized_status = validate_rule_lifecycle_status(lifecycle_status)
    if normalized_status in APPROVED_RULE_STATUSES:
        if not quote.strip():
            raise ValueError("Approved RuleRow requires a quote anchor")
        if not clause_id:
            raise ValueError("Approved RuleRow requires clause_id provenance")
        if not source_version_id:
            raise ValueError("Approved RuleRow requires source_version_id provenance")
    return normalized_status


def normalize_unit(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower().replace("metres", "m").replace("meters", "m")
    aliases: dict[str, str] = {
        "meter": "m",
        "metre": "m",
        "millimetre": "mm",
        "millimeter": "mm",
        "square metres": "m2",
        "square meters": "m2",
        "sqm": "m2",
        "m^2": "m2",
        "%": "percent",
    }
    return aliases.get(normalized, normalized)


def _is_negated_deemed_to_comply(value: str, match: re.Match[str]) -> bool:
    term = match.group(0).lower().replace(" ", "-")
    if term != "deemed-to-comply":
        return False
    prefix = value[max(0, match.start() - 24) : match.start()].lower()
    return bool(re.search(r"\bnot\s+(?:a\s+|an\s+|the\s+)?$", prefix))


def normalized_rule_payload(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    if "rule_key" in result:
        result["rule_key"] = validate_rule_key(str(result["rule_key"]))
    if "unit" in result:
        result["unit"] = normalize_unit(result["unit"])
    if "status" in result:
        result["status"] = validate_rule_candidate_status(str(result["status"]))
    if "lifecycle_status" in result:
        result["lifecycle_status"] = validate_rule_row_for_status(
            lifecycle_status=str(result["lifecycle_status"]),
            quote=str(result.get("quote") or ""),
            clause_id=result.get("clause_id"),
            source_version_id=result.get("source_version_id"),
        )
    return result
