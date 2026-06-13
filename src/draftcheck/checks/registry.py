# Check registry — all check definitions in code, not DB rows.
from dataclasses import dataclass
from enum import StrEnum

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
    LOT = "lot"
    LANDSCAPING = "landscaping"
    SURVEILLANCE = "surveillance"
    OUTDOOR_LIVING = "outdoor_living"
    AMENITY = "amenity"
    ACCESS = "access"
    STORAGE = "storage"
    TRIGGER = "trigger"
    DRAWING_QA = "drawing_qa"


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
    CheckDefinition(
        key="site_area",
        name="Site area",
        tier=CheckTier.TIER1,
        category=CheckCategory.LOT,
        fact_keys=("lot_area_m2", "site_area_m2"),
        rule_key_pattern="site_area.min",
        unit="m2",
        description="Minimum site area for the applicable density code and dwelling type.",
    ),
    CheckDefinition(
        key="minimum_frontage",
        name="Minimum frontage",
        tier=CheckTier.TIER1,
        category=CheckCategory.LOT,
        fact_keys=("frontage", "frontage_width_m"),
        rule_key_pattern="minimum_frontage.min",
        unit="m",
        description="Minimum lot frontage for the applicable density code or dwelling type.",
    ),
    CheckDefinition(
        key="outdoor_living_area",
        name="Outdoor living area",
        tier=CheckTier.TIER1,
        category=CheckCategory.OUTDOOR_LIVING,
        fact_keys=("outdoor_living_area_m2", "outdoor_living_min_dimension_m"),
        rule_key_pattern="outdoor_living_area.min",
        unit="m2",
        description="Minimum outdoor living area and minimum dimension.",
    ),
    CheckDefinition(
        key="private_open_space",
        name="Private open space",
        tier=CheckTier.TIER1,
        category=CheckCategory.OUTDOOR_LIVING,
        fact_keys=("private_open_space_m2", "private_open_space_pct"),
        rule_key_pattern="private_open_space.min",
        unit="m2",
        description="Minimum private open space area where applicable.",
    ),
    CheckDefinition(
        key="soft_landscaping",
        name="Soft landscaping",
        tier=CheckTier.TIER1,
        category=CheckCategory.LANDSCAPING,
        fact_keys=("soft_landscaping_pct", "deep_soil_area_m2", "tree_count"),
        rule_key_pattern="soft_landscaping.min",
        unit="%",
        description="Minimum soft landscaping, deep soil, or tree planting requirement.",
    ),
    CheckDefinition(
        key="street_surveillance",
        name="Street surveillance",
        tier=CheckTier.TIER1,
        category=CheckCategory.SURVEILLANCE,
        fact_keys=("street_surveillance_opening_present",),
        rule_key_pattern="street_surveillance.required",
        unit="bool",
        description="Required street-facing surveillance opening or equivalent passive surveillance.",
    ),
    CheckDefinition(
        key="solar_access",
        name="Solar access",
        tier=CheckTier.TIER1,
        category=CheckCategory.AMENITY,
        fact_keys=("solar_access_hours",),
        rule_key_pattern="solar_access.min",
        unit="hours",
        description="Minimum solar access to major openings or outdoor living areas.",
    ),
    CheckDefinition(
        key="privacy",
        name="Visual privacy",
        tier=CheckTier.TIER1,
        category=CheckCategory.AMENITY,
        fact_keys=("privacy_overlooking_risk_count", "privacy_screening_provided"),
        rule_key_pattern="privacy.max",
        unit="count",
        description="Visual privacy overlooking risk count or required screening.",
    ),
    CheckDefinition(
        key="overshadowing",
        name="Overshadowing",
        tier=CheckTier.TIER1,
        category=CheckCategory.AMENITY,
        fact_keys=("overshadowing_pct", "overshadowed_neighbour_site_area_m2", "neighbour_site_area_m2"),
        rule_key_pattern="overshadowing.max",
        unit="%",
        description="Maximum overshadowing impact on adjoining residential property.",
    ),
    CheckDefinition(
        key="vehicle_access",
        name="Vehicle access",
        tier=CheckTier.TIER1,
        category=CheckCategory.ACCESS,
        fact_keys=("vehicle_access_shown", "driveway_width_m", "parking_bay_count"),
        rule_key_pattern="vehicle_access.required",
        unit="bool",
        description="Vehicle access, driveway, and parking facts required by planning controls.",
    ),
    CheckDefinition(
        key="parking_bays_per_dwelling",
        name="Parking bays per dwelling",
        tier=CheckTier.TIER1,
        category=CheckCategory.ACCESS,
        fact_keys=("parking_bays_per_dwelling", "parking_bay_count"),
        rule_key_pattern="parking_bays_per_dwelling.min",
        unit="count",
        description="Minimum resident parking bays per dwelling.",
    ),
    CheckDefinition(
        key="visitor_parking_per_dwelling",
        name="Visitor parking",
        tier=CheckTier.TIER1,
        category=CheckCategory.ACCESS,
        fact_keys=("visitor_parking_per_dwelling", "visitor_parking_bay_count"),
        rule_key_pattern="visitor_parking_per_dwelling.min",
        unit="count",
        description="Minimum visitor parking bays per dwelling where applicable.",
    ),
    CheckDefinition(
        key="driveway_width",
        name="Driveway width",
        tier=CheckTier.TIER1,
        category=CheckCategory.ACCESS,
        fact_keys=("driveway_width_m",),
        rule_key_pattern="driveway_width.min",
        unit="m",
        description="Minimum or maximum driveway width requirement.",
    ),
    CheckDefinition(
        key="bin_storage",
        name="Bin storage",
        tier=CheckTier.TIER1,
        category=CheckCategory.STORAGE,
        fact_keys=("bin_storage_shown",),
        rule_key_pattern="bin_storage.required",
        unit="bool",
        description="Bin storage area shown where required by local planning policy.",
    ),
    CheckDefinition(
        key="retaining_fill_trigger",
        name="Retaining and fill",
        tier=CheckTier.TIER1,
        category=CheckCategory.TRIGGER,
        fact_keys=("retaining_fill_height_m", "retaining_wall_height_m", "fill_height_m"),
        rule_key_pattern="retaining_fill.max",
        unit="m",
        description="Retaining wall or fill height trigger for additional review.",
    ),
    CheckDefinition(
        key="retaining_wall_height",
        name="Retaining wall height",
        tier=CheckTier.TIER1,
        category=CheckCategory.TRIGGER,
        fact_keys=("retaining_wall_height_m", "retaining_fill_height_m"),
        rule_key_pattern="retaining_wall_height.max",
        unit="m",
        description="Maximum retaining wall height before additional assessment is required.",
    ),
    CheckDefinition(
        key="fence_height_front",
        name="Front fence height",
        tier=CheckTier.TIER1,
        category=CheckCategory.AMENITY,
        fact_keys=("front_fence_height_m", "fence_height_front_m"),
        rule_key_pattern="fence_height_front.max",
        unit="m",
        description="Maximum front fence height.",
    ),
    CheckDefinition(
        key="fence_height_side",
        name="Side fence height",
        tier=CheckTier.TIER1,
        category=CheckCategory.AMENITY,
        fact_keys=("side_fence_height_m", "fence_height_side_m"),
        rule_key_pattern="fence_height_side.max",
        unit="m",
        description="Maximum side or secondary street fence height.",
    ),
    CheckDefinition(
        key="ancillary_dwelling_trigger",
        name="Ancillary dwelling",
        tier=CheckTier.TIER1,
        category=CheckCategory.TRIGGER,
        fact_keys=("ancillary_dwelling_proposed",),
        rule_key_pattern="ancillary_dwelling.trigger",
        unit="bool",
        description="Ancillary dwelling proposal trigger.",
    ),
    CheckDefinition(
        key="bal_bushfire_trigger",
        name="BAL and bushfire",
        tier=CheckTier.TIER1,
        category=CheckCategory.TRIGGER,
        fact_keys=("bushfire_prone_area_flag", "bal_rating"),
        rule_key_pattern="bal_bushfire.trigger",
        unit="bool",
        description="Bushfire-prone area or BAL assessment trigger.",
    ),
    CheckDefinition(
        key="heritage_overlay_trigger",
        name="Heritage overlay",
        tier=CheckTier.TIER1,
        category=CheckCategory.TRIGGER,
        fact_keys=("heritage_overlay_flag", "heritage"),
        rule_key_pattern="heritage_overlay.trigger",
        unit="bool",
        description="Heritage overlay or listing trigger.",
    ),
    CheckDefinition(
        key="plot_ratio",
        name="Plot ratio",
        tier=CheckTier.TIER1,
        category=CheckCategory.LOT,
        fact_keys=("plot_ratio", "proposed_plot_ratio"),
        rule_key_pattern="plot_ratio.max",
        unit="ratio",
        description="Maximum plot ratio where applicable.",
    ),
    CheckDefinition(
        key="title_block_completeness",
        name="Title block completeness",
        tier=CheckTier.TIER1,
        category=CheckCategory.DRAWING_QA,
        fact_keys=("title_block_present",),
        rule_key_pattern="title_block_completeness.required",
        unit="bool",
        description="Title block present in drawing set.",
    ),
    CheckDefinition(
        key="revision_completeness",
        name="Revision completeness",
        tier=CheckTier.TIER1,
        category=CheckCategory.DRAWING_QA,
        fact_keys=("revision_present",),
        rule_key_pattern="revision_completeness.required",
        unit="bool",
        description="Drawing revision information present.",
    ),
    CheckDefinition(
        key="north_point_completeness",
        name="North point completeness",
        tier=CheckTier.TIER1,
        category=CheckCategory.DRAWING_QA,
        fact_keys=("north_point_present",),
        rule_key_pattern="north_point_completeness.required",
        unit="bool",
        description="North point present in drawing set.",
    ),
    CheckDefinition(
        key="scale_completeness",
        name="Scale completeness",
        tier=CheckTier.TIER1,
        category=CheckCategory.DRAWING_QA,
        fact_keys=("scale_present",),
        rule_key_pattern="scale_completeness.required",
        unit="bool",
        description="Drawing scale present.",
    ),
    CheckDefinition(
        key="dimension_completeness",
        name="Dimension completeness",
        tier=CheckTier.TIER1,
        category=CheckCategory.DRAWING_QA,
        fact_keys=("dimensions_present",),
        rule_key_pattern="dimension_completeness.required",
        unit="bool",
        description="Dimension annotations present in drawing set.",
    ),
    CheckDefinition(
        key="building_storeys",
        name="Building storeys",
        tier=CheckTier.TIER1,
        category=CheckCategory.HEIGHT,
        fact_keys=("building_storeys", "proposed_storeys"),
        rule_key_pattern="building_storeys.max",
        unit="storeys",
        description="Maximum number of storeys.",
    ),
    CheckDefinition(
        key="wall_height",
        name="Wall height",
        tier=CheckTier.TIER1,
        category=CheckCategory.HEIGHT,
        fact_keys=("wall_height_m", "proposed_wall_height_m"),
        rule_key_pattern="wall_height.max",
        unit="m",
        description="Maximum wall height.",
    ),
    CheckDefinition(
        key="ceiling_height",
        name="Ceiling height",
        tier=CheckTier.TIER1,
        category=CheckCategory.HEIGHT,
        fact_keys=("ceiling_height_m",),
        rule_key_pattern="ceiling_height.min",
        unit="m",
        description="Minimum ceiling height where a planning or building rule applies.",
    ),
    CheckDefinition(
        key="ground_floor_height",
        name="Ground floor height",
        tier=CheckTier.TIER1,
        category=CheckCategory.HEIGHT,
        fact_keys=("ground_floor_height_m",),
        rule_key_pattern="ground_floor_height.min",
        unit="m",
        description="Minimum ground floor height where applicable.",
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
