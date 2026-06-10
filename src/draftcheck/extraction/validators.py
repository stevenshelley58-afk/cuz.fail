"""Deterministic validators for LLM-extracted rule candidates.

Each validator returns a ValidatorResult(passed, detail).
No DB access — these are pure functions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from draftcheck.extraction.normalize import whitespace_normalize
from draftcheck.extraction.vocabulary import NORMATIVE_WORDS, RULE_KEYS

# Minimum quote length that makes sense as an anchor.
_MIN_QUOTE_LEN = 5

# Canonical unit set that the pipeline must produce.
_CANONICAL_UNITS: frozenset[str | None] = frozenset({"m", "m2", "%", "storeys", None})

# Aliases that should have been normalized away before reaching validators.
_UNIT_ALIASES: frozenset[str] = frozenset({
    "mm", "millimetre", "millimeter",
    "cm", "centimetre", "centimeter",
    "metre", "meter",
    "percent", "per cent",
    "sqm", "square metres", "square meters",
    "storey", "stories",
})


@dataclass
class ValidatorResult:
    passed: bool
    detail: str


# ---------------------------------------------------------------------------
# Individual validators
# ---------------------------------------------------------------------------


def validate_quote_anchor(quote: str, clause_text: str) -> ValidatorResult:
    """Quote must appear verbatim (after whitespace-normalization) in clause_text.

    FAIL conditions:
    - quote is empty
    - quote is shorter than _MIN_QUOTE_LEN characters
    - normalized quote not found in normalized clause_text
    """
    if not quote or not quote.strip():
        return ValidatorResult(passed=False, detail="quote is empty")

    norm_quote = whitespace_normalize(quote)
    if len(norm_quote) < _MIN_QUOTE_LEN:
        return ValidatorResult(
            passed=False,
            detail=f"quote is too short ({len(norm_quote)} chars, minimum {_MIN_QUOTE_LEN})",
        )

    norm_text = whitespace_normalize(clause_text)
    if norm_quote not in norm_text:
        return ValidatorResult(
            passed=False,
            detail=f"quote not found verbatim in clause text: {norm_quote!r}",
        )

    return ValidatorResult(passed=True, detail="quote found in clause text")


def validate_normative_language(clause_text: str, disposition: str) -> ValidatorResult:
    """If disposition is 'rule_bearing', clause_text must contain a NORMATIVE_WORD.

    For non-rule-bearing dispositions the check is skipped (pass).
    FAIL when rule_bearing but no normative word is found.
    """
    if disposition != "rule_bearing":
        return ValidatorResult(
            passed=True,
            detail=f"disposition is {disposition!r} — normative language check skipped",
        )

    norm_text = whitespace_normalize(clause_text).lower()
    found = [w for w in NORMATIVE_WORDS if w in norm_text]
    if not found:
        searched = ", ".join(sorted(NORMATIVE_WORDS))
        return ValidatorResult(
            passed=False,
            detail=f"no normative word found in clause text; searched for: {searched}",
        )

    return ValidatorResult(
        passed=True,
        detail=f"normative language found: {found[0]!r}",
    )


def validate_no_orphan_numbers(quote: str, value_json: Any) -> ValidatorResult:
    """Any numeric value in value_json must appear as a number in the quote.

    Extracts all numeric strings from value_json (supports scalar, list, dict).
    For each, checks that the string form appears in the quote.
    FAIL if any extracted value is absent.
    """
    extracted_values = _extract_numbers(value_json)
    if not extracted_values:
        return ValidatorResult(passed=True, detail="no numeric values in extraction")

    norm_quote = whitespace_normalize(quote)
    missing = []
    for num_str in extracted_values:
        # Match the number as it would appear in text (not as a substring of a larger number).
        pattern = r"(?<!\d)" + re.escape(num_str) + r"(?!\d)"
        if not re.search(pattern, norm_quote):
            missing.append(num_str)

    if missing:
        return ValidatorResult(
            passed=False,
            detail=f"numeric value(s) {missing!r} from extraction not found in quote",
        )

    return ValidatorResult(passed=True, detail="all numeric values present in quote")


def validate_unit_normalization(value_json: Any, unit: str | None) -> ValidatorResult:
    """Unit must be from the canonical set (m, %, None).

    FAIL if unit is a known alias that should have been normalized away.
    FAIL if unit is not canonical and not an alias (unknown unit is also a failure
    because the pipeline should produce known units only).
    """
    if unit is None:
        return ValidatorResult(passed=True, detail="unit is None (dimensionless)")

    unit_lower = unit.strip().lower()

    if unit_lower in _UNIT_ALIASES:
        return ValidatorResult(
            passed=False,
            detail=f"unit {unit!r} is an alias that should have been normalized before validation",
        )

    if unit in _CANONICAL_UNITS:
        return ValidatorResult(passed=True, detail=f"unit {unit!r} is canonical")

    return ValidatorResult(
        passed=False,
        detail=f"unit {unit!r} is not in the canonical set (m, %, None)",
    )


def validate_rule_key(rule_key: str) -> ValidatorResult:
    """rule_key must be in RULE_KEYS vocabulary.

    FAIL if not present (hallucinated or misspelled key).
    """
    if rule_key in RULE_KEYS:
        return ValidatorResult(passed=True, detail=f"rule_key {rule_key!r} is valid")

    return ValidatorResult(
        passed=False,
        detail=f"rule_key {rule_key!r} is not in the approved vocabulary: {sorted(RULE_KEYS)!r}",
    )


# ---------------------------------------------------------------------------
# Aggregate runner
# ---------------------------------------------------------------------------


def run_all_validators(
    quote: str,
    clause_text: str,
    disposition: str,
    value_json: Any,
    unit: str | None,
    rule_key: str,
) -> dict[str, dict]:
    """Run all 5 validators and return results keyed by validator name.

    Return format: {validator_name: {"pass": bool, "detail": str}}
    Does NOT write to DB.
    """
    results: dict[str, dict] = {}

    for name, result in [
        ("quote_anchor", validate_quote_anchor(quote, clause_text)),
        ("normative_language", validate_normative_language(clause_text, disposition)),
        ("no_orphan_numbers", validate_no_orphan_numbers(quote, value_json)),
        ("unit_normalization", validate_unit_normalization(value_json, unit)),
        ("rule_key", validate_rule_key(rule_key)),
    ]:
        results[name] = {"pass": result.passed, "detail": result.detail}

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_numbers(value_json: Any) -> list[str]:
    """Recursively extract all numeric values from value_json as strings."""
    numbers: list[str] = []
    if isinstance(value_json, (int, float)):
        numbers.append(_num_to_str(value_json))
    elif isinstance(value_json, list):
        for item in value_json:
            numbers.extend(_extract_numbers(item))
    elif isinstance(value_json, dict):
        for v in value_json.values():
            numbers.extend(_extract_numbers(v))
    return numbers


def _num_to_str(n: int | float) -> str:
    """Convert a number to the string form most likely to appear in source text."""
    if isinstance(n, int):
        return str(n)
    # Drop trailing zeros so "50.0" matches "50" in the source.
    s = f"{n:g}"
    return s
