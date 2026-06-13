# Check registry — check definitions in code, not DB rows.
#
# Open-vocab pipeline (2026-06-14): the authoritative check list now comes from
# ``registry_generated.py`` (seed checks + checks DERIVED from rule clusters by
# ``scripts/wp6_register_checks_from_clusters.py``).  The hand-written checks below
# are retained as ``SEED_*`` — they seed the generator and act as a safe fallback
# if the generated module is ever missing or broken.  See
# ``docs/OPEN_VOCAB_REBUILD_PLAN.md`` WP-F.
from dataclasses import dataclass
from enum import StrEnum

class CheckTier(StrEnum):
    TIER1 = "tier1"
    TIER2 = "tier2"


class CheckCategory(StrEnum):
    # Original hand-list categories (2026-06-10).
    SETBACK = "setback"
    SITE_COVER = "site_cover"
    OPEN_SPACE = "open_space"
    GARAGE = "garage"
    BOUNDARY_WALL = "boundary_wall"
    HEIGHT = "height"
    # Open-vocab derived categories (2026-06-14). New cluster-derived checks map
    # into these so the compliance panel can group them (WP-H groupings:
    # Boundary setbacks / Building envelope / Site & landscape /
    # Garages & parking / Walls & fences / Lot shape).
    STOREYS = "storeys"
    SITE = "site"
    LANDSCAPE = "landscape"
    PARKING = "parking"
    DRIVEWAY = "driveway"
    FENCE = "fence"
    WALL = "wall"
    LOT = "lot"
    OTHER = "other"


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


SEED_TIER1_CHECKS: list[CheckDefinition] = [
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

SEED_TIER2_CHECKS: list[CheckDefinition] = [
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

SEED_ALL_CHECKS: list[CheckDefinition] = SEED_TIER1_CHECKS + SEED_TIER2_CHECKS

# Maps a seed check key -> the canonical_rule_key (open-vocab cluster label) that
# covers the same regulated thing.  The check derivation skips generating a
# duplicate check for these canonical keys, so the seed checks keep their stable
# keys (and the golden fixture stays green) while the derivation adds only NEW
# categories on top.  Consumed by scripts/wp6_register_checks_from_clusters.py.
SEED_CANONICAL_RULE_KEYS: dict[str, str] = {
    "setback_front": "primary_street_setback",
    "setback_rear": "rear_setback",
    "setback_side_primary": "side_setback",
    "setback_side_secondary": "secondary_street_setback",
    "site_cover": "site_cover",
    "open_space": "open_space",
    "garage_width": "garage_width",
    "garage_dominance": "garage_dominance",
    "boundary_wall_length": "boundary_wall_length",
    "height_overall": "building_height",
    "height_wall": "wall_height",
}

# ---------------------------------------------------------------------------
# Public surface.
#
# Prefer the generated registry (seed + cluster-derived checks).  Fall back to
# the seed checks if the generated module is missing or fails to import, so the
# engine never loses the core checks.  The import sits at the BOTTOM of this
# module on purpose: registry_generated imports CheckTier/CheckCategory/
# CheckDefinition back from here, and those names are already defined above.
# ---------------------------------------------------------------------------
try:
    from draftcheck.checks.registry_generated import (  # noqa: E402
        TIER1_CHECKS as _GEN_TIER1,
        TIER2_CHECKS as _GEN_TIER2,
    )

    TIER1_CHECKS: list[CheckDefinition] = list(_GEN_TIER1)
    TIER2_CHECKS: list[CheckDefinition] = list(_GEN_TIER2)
    REGISTRY_SOURCE = "generated"
except Exception:  # pragma: no cover - defensive fallback
    TIER1_CHECKS = list(SEED_TIER1_CHECKS)
    TIER2_CHECKS = list(SEED_TIER2_CHECKS)
    REGISTRY_SOURCE = "seed_fallback"

ALL_CHECKS: list[CheckDefinition] = TIER1_CHECKS + TIER2_CHECKS
CHECK_BY_KEY: dict[str, CheckDefinition] = {c.key: c for c in ALL_CHECKS}
