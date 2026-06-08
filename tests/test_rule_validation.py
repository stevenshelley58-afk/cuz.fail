from __future__ import annotations

import pytest

from draftcheck_compliance.rule_validation import (
    has_normative_language,
    normalize_clause_disposition,
    normalize_unit,
    normalized_rule_payload,
    validate_rule_key,
    validate_rule_row_for_status,
)


def test_clause_disposition_deprecated_aliases_and_normative_guard():
    assert has_normative_language("A wall must be set back 1.5 m unless exempt.")
    assert has_normative_language("The standard is deemed-to-comply when the objective is met.")
    assert not has_normative_language("The explanatory numbers are not deemed-to-comply.")
    assert not has_normative_language("Background context only.")
    assert normalize_clause_disposition("definitions") == "definition"
    assert normalize_clause_disposition("fluff", "Background context only.") == "informational"
    assert (
        normalize_clause_disposition("fluff", "The explanatory numbers are not deemed-to-comply.")
        == "informational"
    )
    with pytest.raises(ValueError, match="Normative clauses cannot"):
        normalize_clause_disposition("fluff", "A wall must be set back 1.5 m unless exempt.")


def test_rule_row_cannot_be_approved_without_quote_and_provenance():
    with pytest.raises(ValueError, match="quote anchor"):
        validate_rule_row_for_status(
            lifecycle_status="approved",
            quote="",
            clause_id="cl_1",
            source_version_id="sv_1",
        )
    with pytest.raises(ValueError, match="needs_review"):
        validate_rule_row_for_status(
            lifecycle_status="needs_review",
            quote="quoted text",
            clause_id="cl_1",
            source_version_id="sv_1",
        )
    assert (
        validate_rule_row_for_status(
            lifecycle_status="approved",
            quote="A setback must be at least 1.5 m.",
            clause_id="cl_1",
            source_version_id="sv_1",
        )
        == "approved"
    )


def test_rule_key_and_unit_normalization():
    assert validate_rule_key("front_setback") == "front_setback"
    with pytest.raises(ValueError, match="snake_case"):
        validate_rule_key("Front Setback")
    assert normalize_unit("metres") == "m"
    assert normalize_unit("sqm") == "m2"
    payload = normalized_rule_payload(
        {
            "rule_key": "front_setback",
            "unit": "metres",
            "lifecycle_status": "approved",
            "quote": "A setback must be at least 4.5 m.",
            "clause_id": "cl_1",
            "source_version_id": "sv_1",
        }
    )
    assert payload["unit"] == "m"
