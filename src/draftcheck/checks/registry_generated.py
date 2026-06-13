"""GENERATED check registry — DO NOT EDIT BY HAND.

Produced by scripts/wp6_register_checks_from_clusters.py from
rules.canonical_rule_key clusters with >= 5 approved rules.
Regenerate after clustering; do not hand-edit.  See
docs/OPEN_VOCAB_REBUILD_PLAN.md WP-F.
"""
from __future__ import annotations

from draftcheck.checks.registry import (
    SEED_TIER1_CHECKS,
    SEED_TIER2_CHECKS,
    CheckCategory,
    CheckDefinition,
    CheckTier,
)

GENERATED_FROM = "rules.canonical_rule_key >= 5 approved rules"
DERIVED_COUNT = 10

_DERIVED_TIER1: list[CheckDefinition] = [
    CheckDefinition(
        key='building_storey',
        name='Building Storey',
        tier=CheckTier.TIER1,
        category=CheckCategory.STOREYS,
        fact_keys=('proposed_building_storey_storeys',),
        rule_key_pattern='building_storey',
        unit='storeys',
        description='Advisory check derived from 20 approved WA/Cockburn rules for \'building storey\'. Most-cited source_version 9a909193-662d-4c8d-a595-fa2b25d0dcc4. e.g. "Residential development along Rosalind Way and Benedick Road to be appropriately designed to ensure an integrated streetscape reflective of "',
    ),
    CheckDefinition(
        key='outdoor_living_area',
        name='Outdoor Living Area',
        tier=CheckTier.TIER1,
        category=CheckCategory.LANDSCAPE,
        fact_keys=('proposed_outdoor_living_area_m2', 'site_area_m2'),
        rule_key_pattern='outdoor_living_area',
        unit='m2',
        description='Advisory check derived from 59 approved WA/Cockburn rules for \'outdoor living area\'. Most-cited source_version 9a909193-662d-4c8d-a595-fa2b25d0dcc4. e.g. "an area of 10% of the lot size or 20m2, whichever is greater, directly accessible from a habitable room of the dwelling and located behind t"',
    ),
    CheckDefinition(
        key='parking_bays_per_dwelling',
        name='Parking Bays Per Dwelling',
        tier=CheckTier.TIER1,
        category=CheckCategory.PARKING,
        fact_keys=('proposed_parking_bays_per_dwelling_count',),
        rule_key_pattern='parking_bays_per_dwelling',
        unit='',
        description='Advisory check derived from 47 approved WA/Cockburn rules for \'parking bays per dwelling\'. Most-cited source_version 7e7faf65-fb02-4616-b492-a325bdfed238. e.g. "Visitor car parking is to be a minimum of 10% of the total residential car parking requirement and be provided in addition to the required r"',
    ),
    CheckDefinition(
        key='site_area',
        name='Site Area',
        tier=CheckTier.TIER1,
        category=CheckCategory.SITE,
        fact_keys=('lot_area_m2',),
        rule_key_pattern='site_area',
        unit='m2',
        description='Advisory check derived from 87 approved WA/Cockburn rules for \'site area\'. Most-cited source_version 9a909193-662d-4c8d-a595-fa2b25d0dcc4. e.g. "Consideration shall be given to allowing an ancillary dwelling to have an  internal floor area greater than 70m², up to a maximum of 100m², "',
    ),
]

_DERIVED_TIER2: list[CheckDefinition] = [
    CheckDefinition(
        key='ceiling_height',
        name='Ceiling Height',
        tier=CheckTier.TIER2,
        category=CheckCategory.HEIGHT,
        fact_keys=('proposed_ceiling_height_m',),
        rule_key_pattern='ceiling_height',
        unit='m',
        description='Advisory check derived from 7 approved WA/Cockburn rules for \'ceiling height\'. Most-cited source_version 9a909193-662d-4c8d-a595-fa2b25d0dcc4. e.g. "In relation to ground floor dwellings fronting Cockburn Road and Rockingham \r Road, as a minimum, 3.6m floor to ceiling should be provided."',
    ),
    CheckDefinition(
        key='driveway_width',
        name='Driveway Width',
        tier=CheckTier.TIER2,
        category=CheckCategory.DRIVEWAY,
        fact_keys=('proposed_driveway_width_m',),
        rule_key_pattern='driveway_width',
        unit='m',
        description='Advisory check derived from 12 approved WA/Cockburn rules for \'driveway width\'. Most-cited source_version 9a909193-662d-4c8d-a595-fa2b25d0dcc4. e.g. "Driveways must be minimum 5.5m wide for a minimum 6.3m length (excluding manoeuvring tapers) from the street boundary"',
    ),
    CheckDefinition(
        key='min_frontage',
        name='Min Frontage',
        tier=CheckTier.TIER2,
        category=CheckCategory.LOT,
        fact_keys=('lot_width_m', 'frontage_width_m'),
        rule_key_pattern='min_frontage',
        unit='m',
        description='Advisory check derived from 6 approved WA/Cockburn rules for \'min frontage\'. Most-cited source_version 9a909193-662d-4c8d-a595-fa2b25d0dcc4. e.g. "R5 Single house or \r grouped dwelling Min 2000 - 30"',
    ),
    CheckDefinition(
        key='plot_ratio',
        name='Plot Ratio',
        tier=CheckTier.TIER2,
        category=CheckCategory.SITE,
        fact_keys=('proposed_plot_ratio', 'lot_area_m2'),
        rule_key_pattern='plot_ratio',
        unit='',
        description='Advisory check derived from 6 approved WA/Cockburn rules for \'plot ratio\'. Most-cited source_version 23165d75-774f-498f-b967-c317f63e5412. e.g. "Plot Ratio Abutting Cockburn  & Rockingham  Roads – 2.0"',
    ),
    CheckDefinition(
        key='retaining_wall_height',
        name='Retaining Wall Height',
        tier=CheckTier.TIER2,
        category=CheckCategory.WALL,
        fact_keys=('proposed_retaining_wall_height_m',),
        rule_key_pattern='retaining_wall_height',
        unit='m',
        description='Advisory check derived from 10 approved WA/Cockburn rules for \'retaining wall height\'. Most-cited source_version 269c77a6-7a15-4948-ad47-ae37b8a0db6e. e.g. "Planning approval is required for subdivision retaining walls that exceed 2m in \r height above natural ground level which abut areas of publ"',
    ),
    CheckDefinition(
        key='soft_landscaping',
        name='Soft Landscaping',
        tier=CheckTier.TIER2,
        category=CheckCategory.LANDSCAPE,
        fact_keys=('proposed_soft_landscaping_pct', 'site_area_m2'),
        rule_key_pattern='soft_landscaping',
        unit='%',
        description='Advisory check derived from 16 approved WA/Cockburn rules for \'soft landscaping\'. Most-cited source_version 9a909193-662d-4c8d-a595-fa2b25d0dcc4. e.g. "the local government may reduce the minimum on-site provision to not less than five percent (5%) of the total area of the lot to be set asid"',
    ),
]

TIER1_CHECKS: list[CheckDefinition] = list(SEED_TIER1_CHECKS) + _DERIVED_TIER1
TIER2_CHECKS: list[CheckDefinition] = list(SEED_TIER2_CHECKS) + _DERIVED_TIER2

ALL_CHECKS: list[CheckDefinition] = TIER1_CHECKS + TIER2_CHECKS
CHECK_BY_KEY: dict[str, CheckDefinition] = {c.key: c for c in ALL_CHECKS}
