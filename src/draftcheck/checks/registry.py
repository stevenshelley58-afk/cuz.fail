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
    # Rule coverage expansion categories (2026-07-26, §2.3).
    AMENITY = "amenity"
    SUBDIVISION = "subdivision"
    BUILDING_SAFETY = "building_safety"
    ENVIRONMENTAL = "environmental"


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

# ---------------------------------------------------------------------------
# Rule coverage expansion checks (§2.3, 2026-07-26).
# These extend the registry to cover the full WA rule universe.
# ---------------------------------------------------------------------------
COVERAGE_TIER1_CHECKS: list[CheckDefinition] = [
    CheckDefinition(
        key="setback_front_secondary",
        name="Secondary street setback",
        tier=CheckTier.TIER1,
        category=CheckCategory.SETBACK,
        fact_keys=("proposed_setback_front_secondary_m",),
        rule_key_pattern="setback.front.secondary",
        unit="m",
        description="Minimum setback from the secondary street boundary.",
    ),
    CheckDefinition(
        key="deep_soil_area",
        name="Deep soil area",
        tier=CheckTier.TIER1,
        category=CheckCategory.LANDSCAPE,
        fact_keys=("proposed_deep_soil_area_m2", "site_area_m2"),
        rule_key_pattern="deep_soil",
        unit="m2",
        description="Minimum deep soil area for landscaping and tree growth.",
    ),
    CheckDefinition(
        key="tree_planting",
        name="Tree planting requirement",
        tier=CheckTier.TIER1,
        category=CheckCategory.LANDSCAPE,
        fact_keys=("proposed_tree_count",),
        rule_key_pattern="tree_planting",
        unit="count",
        description="Minimum number of trees to be planted.",
    ),
    CheckDefinition(
        key="outdoor_living_dimension",
        name="Outdoor living min dimension",
        tier=CheckTier.TIER1,
        category=CheckCategory.OPEN_SPACE,
        fact_keys=("proposed_outdoor_living_min_dimension_m",),
        rule_key_pattern="outdoor_living.dimension",
        unit="m",
        description="Minimum dimension of the outdoor living area.",
    ),
    CheckDefinition(
        key="pool_barrier_height",
        name="Pool barrier height",
        tier=CheckTier.TIER1,
        category=CheckCategory.BUILDING_SAFETY,
        fact_keys=("proposed_pool_barrier_height_mm",),
        rule_key_pattern="pool_barrier.height",
        unit="mm",
        description="Minimum pool barrier height (Building Regulations 2012).",
    ),
    CheckDefinition(
        key="smoke_alarm",
        name="Smoke alarm compliance",
        tier=CheckTier.TIER1,
        category=CheckCategory.BUILDING_SAFETY,
        fact_keys=("smoke_alarm_compliant",),
        rule_key_pattern="smoke_alarm",
        unit="boolean",
        description="Smoke alarm compliance (photoelectric, interconnected).",
    ),
    CheckDefinition(
        key="min_lot_size",
        name="Minimum lot size",
        tier=CheckTier.TIER1,
        category=CheckCategory.SUBDIVISION,
        fact_keys=("site_area_m2",),
        rule_key_pattern="min_lot_size",
        unit="m2",
        description="Minimum lot size per R-Code (DCP 2.2).",
    ),
]

COVERAGE_TIER2_CHECKS: list[CheckDefinition] = [
    CheckDefinition(
        key="solar_access",
        name="Solar access",
        tier=CheckTier.TIER2,
        category=CheckCategory.AMENITY,
        fact_keys=("proposed_solar_access_hours",),
        rule_key_pattern="solar_access",
        unit="hours",
        description="Minimum solar access to north-facing major openings.",
    ),
    CheckDefinition(
        key="visual_privacy",
        name="Visual privacy setback",
        tier=CheckTier.TIER2,
        category=CheckCategory.AMENITY,
        fact_keys=("proposed_privacy_setback_m",),
        rule_key_pattern="visual_privacy",
        unit="m",
        description="Minimum setback for major openings to prevent overlooking.",
    ),
    CheckDefinition(
        key="overshadowing",
        name="Overshadowing limit",
        tier=CheckTier.TIER2,
        category=CheckCategory.AMENITY,
        fact_keys=("proposed_overshadowing_pct",),
        rule_key_pattern="overshadowing",
        unit="%",
        description="Maximum overshadowing of adjoining properties.",
    ),
    CheckDefinition(
        key="vehicle_access",
        name="Vehicle access provision",
        tier=CheckTier.TIER2,
        category=CheckCategory.PARKING,
        fact_keys=("vehicle_access_provided",),
        rule_key_pattern="vehicle_access",
        unit="boolean",
        description="Vehicle access provision compliance.",
    ),
    CheckDefinition(
        key="car_parking_spaces",
        name="Car parking spaces",
        tier=CheckTier.TIER2,
        category=CheckCategory.PARKING,
        fact_keys=("proposed_parking_spaces",),
        rule_key_pattern="car_parking",
        unit="count",
        description="Minimum car parking spaces required.",
    ),
    CheckDefinition(
        key="street_surveillance",
        name="Street surveillance",
        tier=CheckTier.TIER2,
        category=CheckCategory.SITE,
        fact_keys=("street_surveillance_provided",),
        rule_key_pattern="street_surveillance",
        unit="boolean",
        description="Street surveillance via habitable room openings.",
    ),
    CheckDefinition(
        key="building_height_partc",
        name="Building height (Part C)",
        tier=CheckTier.TIER2,
        category=CheckCategory.HEIGHT,
        fact_keys=("proposed_height_overall_m",),
        rule_key_pattern="building_height.partc",
        unit="m",
        description="Maximum building height under Part C (medium density).",
    ),
    CheckDefinition(
        key="building_separation",
        name="Building separation",
        tier=CheckTier.TIER2,
        category=CheckCategory.SETBACK,
        fact_keys=("proposed_building_separation_m",),
        rule_key_pattern="building_separation",
        unit="m",
        description="Minimum separation between buildings on same lot.",
    ),
    CheckDefinition(
        key="communal_open_space",
        name="Communal open space",
        tier=CheckTier.TIER2,
        category=CheckCategory.OPEN_SPACE,
        fact_keys=("proposed_communal_open_space_m2",),
        rule_key_pattern="communal_open_space",
        unit="m2",
        description="Minimum communal open space for grouped/multiple dwellings.",
    ),
    CheckDefinition(
        key="bal_construction",
        name="BAL construction level",
        tier=CheckTier.TIER2,
        category=CheckCategory.ENVIRONMENTAL,
        fact_keys=("bal_construction_level",),
        rule_key_pattern="bal_construction",
        unit="category",
        description="Bushfire Attack Level construction requirement.",
    ),
]

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
    # Coverage expansion canonical keys (§2.3).
    "setback_front_secondary": "secondary_street_setback",
    "deep_soil_area": "deep_soil_area",
    "tree_planting": "tree_planting",
    "outdoor_living_area": "outdoor_living_area",
    "outdoor_living_dimension": "outdoor_living_dimension",
    "solar_access": "solar_access",
    "visual_privacy": "visual_privacy",
    "overshadowing": "overshadowing",
    "vehicle_access": "vehicle_access",
    "car_parking_spaces": "car_parking_spaces",
    "street_surveillance": "street_surveillance",
    "building_height_partc": "building_height_partc",
    "plot_ratio": "plot_ratio",
    "building_separation": "building_separation",
    "communal_open_space": "communal_open_space",
    "bal_construction": "bal_construction",
    "pool_barrier_height": "pool_barrier_height",
    "smoke_alarm": "smoke_alarm",
    "min_lot_size": "min_lot_size",
    "min_frontage": "min_frontage",
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

    TIER1_CHECKS: list[CheckDefinition] = list(_GEN_TIER1) + COVERAGE_TIER1_CHECKS
    TIER2_CHECKS: list[CheckDefinition] = list(_GEN_TIER2) + COVERAGE_TIER2_CHECKS
    REGISTRY_SOURCE = "generated"
except Exception:  # pragma: no cover - defensive fallback
    TIER1_CHECKS = list(SEED_TIER1_CHECKS) + COVERAGE_TIER1_CHECKS
    TIER2_CHECKS = list(SEED_TIER2_CHECKS) + COVERAGE_TIER2_CHECKS
    REGISTRY_SOURCE = "seed_fallback"

ALL_CHECKS: list[CheckDefinition] = TIER1_CHECKS + TIER2_CHECKS
CHECK_BY_KEY: dict[str, CheckDefinition] = {c.key: c for c in ALL_CHECKS}
