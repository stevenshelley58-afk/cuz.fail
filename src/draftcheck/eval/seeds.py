"""Seed golden eval_cases for the tier1_extraction suite."""
from __future__ import annotations
import uuid
import json
import logging

logger = logging.getLogger(__name__)

TIER1_EXTRACTION_CASES = [
    {
        "case_key": "front_setback_lte_6m",
        "skill_name": "rule_extraction",
        "input_json": {
            "clause_key": "5_3_1_front_setback",
            "clause_text": (
                "5.3.1 Front setback\n"
                "The primary street setback of a dwelling must not be less than 3m "
                "and not more than 6m from the primary street boundary, except where "
                "the setback of the existing dwelling on an adjoining lot facing the "
                "same street is less than 3m."
            ),
        },
        "expected_json": {
            "rule_key": "setback_front_max",
            "operator": "lte",
            "value": 6,
            "unit": "m",
        },
    },
    {
        "case_key": "site_coverage_lte_50pct",
        "skill_name": "rule_extraction",
        "input_json": {
            "clause_key": "5_4_1_site_coverage",
            "clause_text": (
                "5.4.1 Site coverage\n"
                "The site coverage of all buildings and roofed structures on a lot "
                "must not exceed 50% of the lot area."
            ),
        },
        "expected_json": {
            "rule_key": "site_cover_max",
            "operator": "lte",
            "value": 50,
            "unit": "%",
        },
    },
    {
        "case_key": "open_space_gte_45pct",
        "skill_name": "rule_extraction",
        "input_json": {
            "clause_key": "5_5_1_outdoor_living_areas",
            "clause_text": (
                "5.5.1 Outdoor living areas\n"
                "Lots of 350m2 or more must provide a minimum of 45% of the lot "
                "area as outdoor living space, with at least one area of not less "
                "than 16m2 being behind the building line."
            ),
        },
        "expected_json": {
            "rule_key": "open_space_min",
            "operator": "gte",
            "value": 45,
            "unit": "%",
        },
    },
    {
        "case_key": "side_setback_gte_1m",
        "skill_name": "rule_extraction",
        "input_json": {
            "clause_key": "5_3_3_side_setbacks",
            "clause_text": (
                "5.3.3 Side setbacks\n"
                "A wall of a dwelling behind the building line must be set back from "
                "the side boundary at least 1m for a wall height of 3.5m or less, "
                "and at least 1.5m for a wall height between 3.5m and 6m."
            ),
        },
        "expected_json": {
            "rule_key": "setback_side_min",
            "operator": "gte",
            "value": 1,
            "unit": "m",
        },
    },
    {
        "case_key": "boundary_wall_length_lte_9m",
        "skill_name": "rule_extraction",
        "input_json": {
            "clause_key": "5_3_5_boundary_walls",
            "clause_text": (
                "5.3.5 Boundary walls\n"
                "A wall built on or within 0.5m of a side boundary must not exceed "
                "a length of 9m and a height of 3m at the boundary, and may be "
                "permitted on one side boundary only."
            ),
        },
        "expected_json": {
            "rule_key": "boundary_wall_length_max",
            "operator": "lte",
            "value": 9,
            "unit": "m",
        },
    },
]


async def seed_eval_cases(session) -> int:
    """Insert TIER1_EXTRACTION_CASES into eval_cases. Idempotent. Returns rows inserted."""
    from sqlalchemy import text

    inserted = 0
    for case in TIER1_EXTRACTION_CASES:
        r = await session.execute(
            text(
                "INSERT INTO eval_cases "
                "(id, suite_name, case_key, skill_name, input_json, expected_json, "
                "status, created_at, updated_at) "
                "VALUES (:id, 'tier1_extraction', :ck, :sn, :inp::jsonb, :exp::jsonb, "
                "'active', now(), now()) "
                "ON CONFLICT (suite_name, case_key) DO NOTHING "
                "RETURNING id"
            ),
            {
                "id": str(uuid.uuid4()),
                "ck": case["case_key"],
                "sn": case["skill_name"],
                "inp": json.dumps(case["input_json"]),
                "exp": json.dumps(case["expected_json"]),
            },
        )
        if r.fetchone():
            inserted += 1

    await session.commit()
    logger.info("Seeded %d eval_cases (suite=tier1_extraction)", inserted)
    return inserted
