"""Golden eval_case seeds for suite 'tier1_extraction'.

Seed data uses realistic WA R-codes clause text.
Run seed_eval_cases(session) once per environment to populate eval_cases.
"""

from __future__ import annotations

from uuid import uuid4

TIER1_SEEDS = [
    {
        "case_key": "front_setback_r20",
        "skill_name": "rule_extraction",
        "input_json": {
            "clause_text": (
                "Clause 5.3.1 — Front setback: Buildings or structures shall not be erected "
                "closer than 6 metres to the front boundary of the lot, as measured from the "
                "primary street alignment, in accordance with the Residential Design Codes of "
                "Western Australia (R20 coding)."
            ),
            "clause_ref": "5.3.1",
        },
        "expected_json": {
            "rule_key": "front_setback",
            "operator": "lte",
            "value": 6,
            "unit": "m",
        },
        "metadata_json": {"source": "WA R-Codes Table 1", "coding": "R20"},
    },
    {
        "case_key": "site_coverage_r20",
        "skill_name": "rule_extraction",
        "input_json": {
            "clause_text": (
                "Clause 5.3.4 — Site coverage: The total area of all buildings and roofed "
                "structures on the lot, including outbuildings, shall not exceed 50 per cent "
                "of the total lot area (R20 coding). Uncovered pools, patios and paved areas "
                "are excluded from this calculation."
            ),
            "clause_ref": "5.3.4",
        },
        "expected_json": {
            "rule_key": "site_coverage",
            "operator": "lte",
            "value": 50,
            "unit": "%",
        },
        "metadata_json": {"source": "WA R-Codes Table 1", "coding": "R20"},
    },
    {
        "case_key": "open_space_r20",
        "skill_name": "rule_extraction",
        "input_json": {
            "clause_text": (
                "Clause 5.3.5 — Open space: A minimum of 45 per cent of the total lot area "
                "shall be maintained as open space, comprising landscaping, lawn, garden areas "
                "and other unpaved surfaces permeable to rain water (R20 coding). Impermeable "
                "paving counts against this requirement."
            ),
            "clause_ref": "5.3.5",
        },
        "expected_json": {
            "rule_key": "open_space",
            "operator": "gte",
            "value": 45,
            "unit": "%",
        },
        "metadata_json": {"source": "WA R-Codes Table 1", "coding": "R20"},
    },
    {
        "case_key": "side_setback_r20",
        "skill_name": "rule_extraction",
        "input_json": {
            "clause_text": (
                "Clause 5.3.2 — Side setbacks: Where a wall is not built to the boundary, "
                "the minimum side setback shall be 1 metre from each side lot boundary. "
                "This requirement applies to all habitable rooms and garages (R20 coding)."
            ),
            "clause_ref": "5.3.2",
        },
        "expected_json": {
            "rule_key": "side_setback",
            "operator": "gte",
            "value": 1,
            "unit": "m",
        },
        "metadata_json": {"source": "WA R-Codes Table 1", "coding": "R20"},
    },
    {
        "case_key": "boundary_wall_length_r20",
        "skill_name": "rule_extraction",
        "input_json": {
            "clause_text": (
                "Clause 5.3.3 — Boundary walls: Where a wall is built on or within 0.5 metres "
                "of a side boundary, the aggregate length of all such walls on that boundary "
                "shall not exceed 9 metres. Wall height shall not exceed 3.5 metres above "
                "natural ground level (R20 coding)."
            ),
            "clause_ref": "5.3.3",
        },
        "expected_json": {
            "rule_key": "boundary_wall_length",
            "operator": "lte",
            "value": 9,
            "unit": "m",
        },
        "metadata_json": {"source": "WA R-Codes Table 1", "coding": "R20"},
    },
]


def seed_eval_cases(session: object, suite_name: str = "tier1_extraction") -> int:
    """Insert golden eval_cases for the given suite if they do not already exist.

    Returns the number of rows inserted (skips existing case_keys).
    """
    from draftcheck.db.models import EvalCase

    existing_keys: set[str] = {
        row.case_key
        for row in session.query(EvalCase.case_key)  # type: ignore[attr-defined]
        .filter(EvalCase.suite_name == suite_name)
        .all()
    }

    inserted = 0
    for seed in TIER1_SEEDS:
        if seed["case_key"] in existing_keys:
            continue
        case = EvalCase(
            id=uuid4(),
            suite_name=suite_name,
            case_key=seed["case_key"],
            skill_name=seed["skill_name"],
            input_json=seed["input_json"],
            expected_json=seed["expected_json"],
            status="active",
            metadata_json=seed.get("metadata_json", {}),
        )
        session.add(case)  # type: ignore[attr-defined]
        inserted += 1

    session.commit()  # type: ignore[attr-defined]
    return inserted
