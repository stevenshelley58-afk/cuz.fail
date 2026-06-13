"""Deterministic validators for LLM-extracted rule candidates.

Each validator returns a ValidatorResult(passed, detail).
No DB access; these are pure functions.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from draftcheck.extraction.normalize import unit_category_for_unit, whitespace_normalize
from draftcheck.extraction.vocabulary import NORMATIVE_WORDS, is_hinted_key

# Minimum quote length that makes sense as an anchor.
_MIN_QUOTE_LEN = 5

# Canonical unit set that the pipeline must produce.
_CANONICAL_UNITS: frozenset[str | None] = frozenset({
    "m",
    "m2",
    "%",
    "storeys",
    "count",
    "ratio",
    "degrees",
    "dB",
    "lx",
    None,
})

# Aliases that should have been normalized away before reaching validators.
_UNIT_ALIASES: frozenset[str] = frozenset({
    "mm", "millimetre", "millimeter",
    "cm", "centimetre", "centimeter",
    "km",
    "metre", "meter",
    "percent", "per cent",
    "sqm", "sq m", "sq.m", "square metres", "square meters", "metres squared", "ha",
    "storey", "stories",
    "degree", "degrees",
    "db", "decibels",
    "lux",
    "bay", "bays", "dwelling", "dwellings",
    "per dwelling",
})


@dataclass
class ValidatorResult:
    passed: bool
    detail: str


# ---------------------------------------------------------------------------
# Individual validators
# ---------------------------------------------------------------------------


def validate_quote_anchor(quote: str, clause_text: str) -> ValidatorResult:
    """Quote must appear verbatim after whitespace-normalization in clause_text."""
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
    """Rule-bearing clauses must contain normative language."""
    if disposition != "rule_bearing":
        return ValidatorResult(
            passed=True,
            detail=f"disposition is {disposition!r}; normative language check skipped",
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
    """Any numeric value in value_json must appear as a number in the quote."""
    extracted_values = _extract_numbers(value_json)
    if not extracted_values:
        return ValidatorResult(passed=True, detail="no numeric values in extraction")

    norm_quote = whitespace_normalize(quote)
    missing = []
    for num_str in extracted_values:
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
    """Unit must be canonical, not a known alias."""
    if unit is None:
        return ValidatorResult(passed=True, detail="unit is None (dimensionless)")

    if unit in _CANONICAL_UNITS:
        return ValidatorResult(passed=True, detail=f"unit {unit!r} is canonical")

    unit_lower = unit.strip().lower()

    if unit_lower in _UNIT_ALIASES:
        return ValidatorResult(
            passed=False,
            detail=f"unit {unit!r} is an alias that should have been normalized before validation",
        )

    return ValidatorResult(
        passed=False,
        detail=f"unit {unit!r} is not in the canonical set",
    )


def validate_rule_key(rule_key: str) -> ValidatorResult:
    """rule_key must be a usable open-vocabulary snake_case key."""
    if not rule_key or not re.fullmatch(r"[a-z][a-z0-9_]{2,60}", rule_key):
        return ValidatorResult(
            passed=False,
            detail="rule_key must be snake_case 3-60 chars",
        )

    return ValidatorResult(
        passed=True,
        detail=f"rule_key {rule_key!r}; hinted={is_hinted_key(rule_key)}",
    )


def validate_value_finite(value: Any) -> ValidatorResult:
    """Every numeric value must be finite and within universal magnitude bounds."""
    numbers = _extract_numbers(value)
    if not numbers:
        return ValidatorResult(passed=True, detail="no numeric values in extraction")

    bad: list[str] = []
    for raw in numbers:
        num = float(raw)
        if not math.isfinite(num) or abs(num) > 1_000_000:
            bad.append(raw)

    if bad:
        return ValidatorResult(
            passed=False,
            detail=f"non-finite or out-of-bounds numeric value(s): {bad!r}",
        )

    return ValidatorResult(passed=True, detail="all numeric values finite")


def validate_unit_category_sanity(value: Any, unit_category: str | None) -> ValidatorResult:
    """Universal hard sanity bounds for canonical unit categories."""
    numbers = [float(raw) for raw in _extract_numbers(value)]
    if not numbers:
        return ValidatorResult(passed=True, detail="no numeric values in extraction")

    bounds: dict[str, tuple[float, float]] = {
        "length": (0.0, 1000.0),
        "area": (0.0, 1_000_000.0),
        "percent": (0.0, 100.0),
        "count_storeys": (1.0, 60.0),
        "count": (0.0, 1000.0),
        "ratio": (0.0, 1000.0),
        "angle": (0.0, 360.0),
        "decibel": (0.0, 200.0),
        "illuminance": (0.0, 1_000_000.0),
    }
    if unit_category not in bounds:
        return ValidatorResult(
            passed=False,
            detail=f"unknown unit category {unit_category!r}",
        )

    lo, hi = bounds[unit_category]
    bad = [n for n in numbers if n < lo or n > hi]
    if bad:
        return ValidatorResult(
            passed=False,
            detail=f"value(s) {bad!r} outside {unit_category} bounds [{lo}, {hi}]",
        )

    return ValidatorResult(
        passed=True,
        detail=f"all numeric values within {unit_category} bounds [{lo}, {hi}]",
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
    """Run all universal validators and return results keyed by validator name.

    Return format: {validator_name: {"pass": bool, "detail": str}}
    Does NOT write to DB.
    """
    results: dict[str, dict] = {}

    for name, result in [
        ("quote_anchor", validate_quote_anchor(quote, clause_text)),
        ("normative_language", validate_normative_language(clause_text, disposition)),
        ("no_orphan_numbers", validate_no_orphan_numbers(quote, value_json)),
        ("unit_normalization", validate_unit_normalization(value_json, unit)),
        ("value_finite", validate_value_finite(value_json)),
        ("unit_category_sanity", validate_unit_category_sanity(value_json, unit_category_for_unit(unit))),
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
    return f"{n:g}"
