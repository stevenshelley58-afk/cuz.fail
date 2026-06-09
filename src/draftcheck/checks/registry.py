# Check registry — all check definitions in code, not DB rows.
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class CheckTier(StrEnum):
    TIER1 = "tier1"
    TIER2 = "tier2"


class CheckCategory(StrEnum):
    SETBACK = "setback"
    SITE_COVER = "site_cover"
    OPEN_SPACE = "open_space"
    GARAGE = "garage"
    BOUNDARY_WALL = "boundary_wall"
    HEIGHT = "height"


@dataclass(frozen=True)
class CheckDefinition:
    key: str                   # e.g. "setback_front"
    name: str                  # human display
    tier: CheckTier
    category: CheckCategory
    fact_keys: tuple[str, ...]  # PropertyFact keys to look up
    rule_key_pattern: str      # pattern to match rule_key in rules table
    unit: str
    description: str


TIER1_CHECKS: list[CheckDefinition] = [
    CheckDefinition(
        key="setback_front",
        name="Front setback",
        tier=CheckTier.TIER1,
        category=CheckCategory.SETBACK,
        fact_keys=("proposed_setback_front_m",),
        rule_key_pattern="setback.front",
        unit="m",
        description="Minimum distance from the front boundary to the primary structure.",
    ),
    CheckDefinition(
        key="setback_rear",
        name="Rear setback",
        tier=CheckTier.TIER1,
        category=CheckCategory.SETBACK,
        fact_keys=("proposed_setback_rear_m",),
        rule_key_pattern="setback.rear",
        unit="m",
        description="Minimum distance from the rear boundary to the primary structure.",
    ),
    CheckDefinition(
        key="setback_side_primary",
        name="Primary side setback",
        tier=CheckTier.TIER1,
        category=CheckCategory.SETBACK,
        fact_keys=("proposed_setback_side_primary_m",),
        rule_key_pattern="setback.side.primary",
        unit="m",
        description="Minimum distance from the primary (larger) side boundary to the structure.",
    ),
    CheckDefinition(
        key="setback_side_secondary",
        name="Secondary side setback",
        tier=CheckTier.TIER1,
        category=CheckCategory.SETBACK,
        fact_keys=("proposed_setback_side_secondary_m",),
        rule_key_pattern="setback.side.secondary",
        unit="m",
        description="Minimum distance from the secondary (smaller) side boundary to the structure.",
    ),
    CheckDefinition(
        key="site_cover",
        name="Site coverage",
        tier=CheckTier.TIER1,
        category=CheckCategory.SITE_COVER,
        fact_keys=("proposed_site_cover_pct", "site_area_m2", "proposed_covered_area_m2"),
        rule_key_pattern="site_cover.max",
        unit="%",
        description="Maximum percentage of the site area that may be covered by roofed structures.",
    ),
    CheckDefinition(
        key="open_space",
        name="Open space",
        tier=CheckTier.TIER1,
        category=CheckCategory.OPEN_SPACE,
        fact_keys=("proposed_open_space_pct", "site_area_m2", "proposed_open_space_m2"),
        rule_key_pattern="open_space.min",
        unit="%",
        description="Minimum percentage of the site area that must remain as usable open space.",
    ),
    CheckDefinition(
        key="garage_width",
        name="Garage width",
        tier=CheckTier.TIER1,
        category=CheckCategory.GARAGE,
        fact_keys=("proposed_garage_width_m", "frontage_width_m"),
        rule_key_pattern="garage.width.max",
        unit="m",
        description="Maximum width of garage or carport opening facing the primary street.",
    ),
    CheckDefinition(
        key="garage_dominance",
        name="Garage dominance",
        tier=CheckTier.TIER1,
        category=CheckCategory.GARAGE,
        fact_keys=("proposed_garage_width_m", "dwelling_facade_width_m"),
        rule_key_pattern="garage.dominance.max",
        unit="%",
        description=(
            "Maximum proportion of the street-facing facade that may be occupied by"
            " garage or carport openings."
        ),
    ),
    CheckDefinition(
        key="boundary_wall_length",
        name="Boundary wall length",
        tier=CheckTier.TIER1,
        category=CheckCategory.BOUNDARY_WALL,
        fact_keys=(
            "proposed_boundary_wall_length_m",
            "proposed_boundary_wall_height_m",
            "lot_depth_m",
        ),
        rule_key_pattern="boundary_wall.length.max",
        unit="m",
        description=(
            "Maximum length of a wall built on or within 150 mm of a side or rear boundary,"
            " subject to height limits."
        ),
    ),
]

TIER2_CHECKS: list[CheckDefinition] = [
    CheckDefinition(
        key="height_overall",
        name="Overall building height",
        tier=CheckTier.TIER2,
        category=CheckCategory.HEIGHT,
        fact_keys=("proposed_height_overall_m", "natural_ground_level_m"),
        rule_key_pattern="height.overall.max",
        unit="m",
        description=(
            "Maximum overall building height measured from natural ground level."
            " Returns needs_more_info unless calibrated survey levels are provided."
        ),
    ),
    CheckDefinition(
        key="height_wall",
        name="External wall height",
        tier=CheckTier.TIER2,
        category=CheckCategory.HEIGHT,
        fact_keys=("proposed_wall_height_m", "natural_ground_level_m"),
        rule_key_pattern="height.wall.max",
        unit="m",
        description=(
            "Maximum external wall height measured from natural ground level."
            " Returns needs_more_info unless calibrated survey levels are provided."
        ),
    ),
]

ALL_CHECKS: list[CheckDefinition] = TIER1_CHECKS + TIER2_CHECKS
CHECK_BY_KEY: dict[str, CheckDefinition] = {c.key: c for c in ALL_CHECKS}
