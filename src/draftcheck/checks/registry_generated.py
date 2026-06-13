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
DERIVED_COUNT = 20

_DERIVED_TIER1: list[CheckDefinition] = [
    CheckDefinition(
        key='building_storey',
        name='Building Storey',
        tier=CheckTier.TIER1,
        category=CheckCategory.STOREYS,
        fact_keys=('proposed_building_storey_storeys',),
        rule_key_pattern='building_storey',
        unit='storeys',
        description='Advisory check derived from 54 approved WA/Cockburn rules for \'building storey\'. Most-cited source_version 9a909193-662d-4c8d-a595-fa2b25d0dcc4. e.g. "Residential development along Rosalind Way and Benedick Road to be appropriately designed to ensure an integrated streetscape reflective of "',
    ),
    CheckDefinition(
        key='driveway_width',
        name='Driveway Width',
        tier=CheckTier.TIER1,
        category=CheckCategory.DRIVEWAY,
        fact_keys=('proposed_driveway_width_m',),
        rule_key_pattern='driveway_width',
        unit='m',
        description='Advisory check derived from 26 approved WA/Cockburn rules for \'driveway width\'. Most-cited source_version 9a909193-662d-4c8d-a595-fa2b25d0dcc4. e.g. "Driveways must be minimum 5.5m wide for a minimum 6.3m length (excluding manoeuvring tapers) from the street boundary"',
    ),
    CheckDefinition(
        key='outdoor_living_area',
        name='Outdoor Living Area',
        tier=CheckTier.TIER1,
        category=CheckCategory.LANDSCAPE,
        fact_keys=('proposed_outdoor_living_area_m2',),
        rule_key_pattern='outdoor_living_area',
        unit='m2',
        description='Advisory check derived from 91 approved WA/Cockburn rules for \'outdoor living area\'. Most-cited source_version 9a909193-662d-4c8d-a595-fa2b25d0dcc4. e.g. "an area of 10% of the lot size or 20m2, whichever is greater, directly accessible from a habitable room of the dwelling and located behind t"',
    ),
    CheckDefinition(
        key='parking_bays_per_dwelling',
        name='Parking Bays Per Dwelling',
        tier=CheckTier.TIER1,
        category=CheckCategory.PARKING,
        fact_keys=('proposed_parking_bays_per_dwelling_count',),
        rule_key_pattern='parking_bays_per_dwelling',
        unit='',
        description='Advisory check derived from 71 approved WA/Cockburn rules for \'parking bays per dwelling\'. Most-cited source_version 7e7faf65-fb02-4616-b492-a325bdfed238. e.g. "Visitor car parking is to be a minimum of 10% of the total residential car parking requirement and be provided in addition to the required r"',
    ),
    CheckDefinition(
        key='retaining_wall_height',
        name='Retaining Wall Height',
        tier=CheckTier.TIER1,
        category=CheckCategory.WALL,
        fact_keys=('proposed_retaining_wall_height_m',),
        rule_key_pattern='retaining_wall_height',
        unit='m',
        description='Advisory check derived from 22 approved WA/Cockburn rules for \'retaining wall height\'. Most-cited source_version 9a909193-662d-4c8d-a595-fa2b25d0dcc4. e.g. "Planning approval is required for subdivision retaining walls that exceed 2m in \r height above natural ground level which abut areas of publ"',
    ),
    CheckDefinition(
        key='site_area',
        name='Site Area',
        tier=CheckTier.TIER1,
        category=CheckCategory.SITE,
        fact_keys=('lot_area_m2',),
        rule_key_pattern='site_area',
        unit='m2',
        description='Advisory check derived from 227 approved WA/Cockburn rules for \'site area\'. Most-cited source_version 9a909193-662d-4c8d-a595-fa2b25d0dcc4. e.g. "Consideration shall be given to allowing an ancillary dwelling to have an  internal floor area greater than 70m², up to a maximum of 100m², "',
    ),
    CheckDefinition(
        key='soft_landscaping',
        name='Soft Landscaping',
        tier=CheckTier.TIER1,
        category=CheckCategory.LANDSCAPE,
        fact_keys=('proposed_soft_landscaping_pct',),
        rule_key_pattern='soft_landscaping',
        unit='%',
        description='Advisory check derived from 32 approved WA/Cockburn rules for \'soft landscaping\'. Most-cited source_version 9a909193-662d-4c8d-a595-fa2b25d0dcc4. e.g. "the local government may reduce the minimum on-site provision to not less than five percent (5%) of the total area of the lot to be set asid"',
    ),
]

_DERIVED_TIER2: list[CheckDefinition] = [
    CheckDefinition(
        key='average_lot_size',
        name='Average Lot Size',
        tier=CheckTier.TIER2,
        category=CheckCategory.OTHER,
        fact_keys=('proposed_average_lot_size_m2',),
        rule_key_pattern='average_lot_size',
        unit='m2',
        description='Advisory check derived from 6 approved WA/Cockburn rules for \'average lot size\'. Most-cited source_version 53d1da5b-3393-4146-8f39-b3e90b5a8023. e.g. "R160 = 62.5m2"',
    ),
    CheckDefinition(
        key='car_parking_ratio_per_gla',
        name='Car Parking Ratio Per Gla',
        tier=CheckTier.TIER2,
        category=CheckCategory.PARKING,
        fact_keys=('proposed_car_parking_ratio_per_gla_m2',),
        rule_key_pattern='car_parking_ratio_per_gla',
        unit='m2',
        description='Advisory check derived from 9 approved WA/Cockburn rules for \'car parking ratio per gla\'. Most-cited source_version 53d1da5b-3393-4146-8f39-b3e90b5a8023. e.g. "- General/  General  (Licensed)  1 : 50m2 gla"',
    ),
    CheckDefinition(
        key='ceiling_height',
        name='Ceiling Height',
        tier=CheckTier.TIER2,
        category=CheckCategory.HEIGHT,
        fact_keys=('proposed_ceiling_height_m',),
        rule_key_pattern='ceiling_height',
        unit='m',
        description='Advisory check derived from 9 approved WA/Cockburn rules for \'ceiling height\'. Most-cited source_version 9554ea37-dd7d-47ad-833b-ebec2e99fcac. e.g. "In relation to ground floor dwellings fronting Cockburn Road and Rockingham \r Road, as a minimum, 3.6m floor to ceiling should be provided."',
    ),
    CheckDefinition(
        key='exempted_sign_max_size',
        name='Exempted Sign Max Size',
        tier=CheckTier.TIER2,
        category=CheckCategory.OTHER,
        fact_keys=('proposed_exempted_sign_max_size_m2',),
        rule_key_pattern='exempted_sign_max_size',
        unit='m2',
        description='Advisory check derived from 6 approved WA/Cockburn rules for \'exempted sign max size\'. Most-cited source_version 53d1da5b-3393-4146-8f39-b3e90b5a8023. e.g. "Advertising. Relating directly  to advising the name,  address, telephone number  and purpose of the service  provided on the property on  w"',
    ),
    CheckDefinition(
        key='facility_structure_spacing',
        name='Facility Structure Spacing',
        tier=CheckTier.TIER2,
        category=CheckCategory.OTHER,
        fact_keys=('proposed_facility_structure_spacing_m',),
        rule_key_pattern='facility_structure_spacing',
        unit='m',
        description='Advisory check derived from 7 approved WA/Cockburn rules for \'facility structure spacing\'. Most-cited source_version 2064086b-a51d-47ed-8475-a5f2dd45c572. e.g. "There is to be at least 6 m between a caravan, camp, annexe or other structure or building on a facility and any land reserved or set aside "',
    ),
    CheckDefinition(
        key='fence_height_side',
        name='Fence Height Side',
        tier=CheckTier.TIER2,
        category=CheckCategory.FENCE,
        fact_keys=('proposed_fence_height_side_m',),
        rule_key_pattern='fence_height_side',
        unit='m',
        description='Advisory check derived from 6 approved WA/Cockburn rules for \'fence height side\'. Most-cited source_version 9554ea37-dd7d-47ad-833b-ebec2e99fcac. e.g. "The interface between residential development and the public open space may be fenced to a maximum height of 1.2m from natural ground level,"',
    ),
    CheckDefinition(
        key='min_frontage',
        name='Min Frontage',
        tier=CheckTier.TIER2,
        category=CheckCategory.LOT,
        fact_keys=('lot_width_m', 'frontage_width_m'),
        rule_key_pattern='min_frontage',
        unit='m',
        description='Advisory check derived from 10 approved WA/Cockburn rules for \'min frontage\'. Most-cited source_version 9a909193-662d-4c8d-a595-fa2b25d0dcc4. e.g. "Where reticulated sewerage is available, the minimum recommended lot size is 1000m2, with a minimum frontage width of 25m."',
    ),
    CheckDefinition(
        key='min_lot_area_per_dwelling',
        name='Min Lot Area Per Dwelling',
        tier=CheckTier.TIER2,
        category=CheckCategory.OTHER,
        fact_keys=('proposed_min_lot_area_per_dwelling_m2',),
        rule_key_pattern='min_lot_area_per_dwelling',
        unit='m2',
        description='Advisory check derived from 6 approved WA/Cockburn rules for \'min lot area per dwelling\'. Most-cited source_version 53d1da5b-3393-4146-8f39-b3e90b5a8023. e.g. "R160 lots – calculated by dividing the lot area (m2) by 62.5 to give the number of dwellings."',
    ),
    CheckDefinition(
        key='parking_ratio_hotel_tavern',
        name='Parking Ratio Hotel Tavern',
        tier=CheckTier.TIER2,
        category=CheckCategory.PARKING,
        fact_keys=('proposed_parking_ratio_hotel_tavern_m2',),
        rule_key_pattern='parking_ratio_hotel_tavern',
        unit='m2',
        description='Advisory check derived from 5 approved WA/Cockburn rules for \'parking ratio hotel tavern\'. Most-cited source_version 53d1da5b-3393-4146-8f39-b3e90b5a8023. e.g. "1 : 2m2 nla of Drinking Area"',
    ),
    CheckDefinition(
        key='parking_ratio_medical_centre',
        name='Parking Ratio Medical Centre',
        tier=CheckTier.TIER2,
        category=CheckCategory.PARKING,
        fact_keys=('proposed_parking_ratio_medical_centre_m2',),
        rule_key_pattern='parking_ratio_medical_centre',
        unit='m2',
        description='Advisory check derived from 5 approved WA/Cockburn rules for \'parking ratio medical centre\'. Most-cited source_version 53d1da5b-3393-4146-8f39-b3e90b5a8023. e.g. "5 : 1 Practitioner OR* 5 : 1 Consulting Room"',
    ),
    CheckDefinition(
        key='parking_ratio_per_gla',
        name='Parking Ratio Per Gla',
        tier=CheckTier.TIER2,
        category=CheckCategory.PARKING,
        fact_keys=('proposed_parking_ratio_per_gla_m2',),
        rule_key_pattern='parking_ratio_per_gla',
        unit='m2',
        description='Advisory check derived from 5 approved WA/Cockburn rules for \'parking ratio per gla\'. Most-cited source_version 53d1da5b-3393-4146-8f39-b3e90b5a8023. e.g. "1 : 200m2 gla"',
    ),
    CheckDefinition(
        key='plot_ratio',
        name='Plot Ratio',
        tier=CheckTier.TIER2,
        category=CheckCategory.SITE,
        fact_keys=('proposed_plot_ratio',),
        rule_key_pattern='plot_ratio',
        unit='',
        description='Advisory check derived from 8 approved WA/Cockburn rules for \'plot ratio\'. Most-cited source_version 23165d75-774f-498f-b967-c317f63e5412. e.g. "Plot Ratio Abutting Cockburn  & Rockingham  Roads – 2.0"',
    ),
    CheckDefinition(
        key='vertical_distance_above_water_table',
        name='Vertical Distance Above Water Table',
        tier=CheckTier.TIER2,
        category=CheckCategory.OTHER,
        fact_keys=('proposed_vertical_distance_above_water_table_m',),
        rule_key_pattern='vertical_distance_above_water_table',
        unit='m',
        description='Advisory check derived from 5 approved WA/Cockburn rules for \'vertical distance above water table\'. Most-cited source_version 53d1da5b-3393-4146-8f39-b3e90b5a8023. e.g. "the vertical distance between the bottom of the domestic waste effluent  disposal system is greater than 2 metres above the highest known wa"',
    ),
]

TIER1_CHECKS: list[CheckDefinition] = list(SEED_TIER1_CHECKS) + _DERIVED_TIER1
TIER2_CHECKS: list[CheckDefinition] = list(SEED_TIER2_CHECKS) + _DERIVED_TIER2

ALL_CHECKS: list[CheckDefinition] = TIER1_CHECKS + TIER2_CHECKS
CHECK_BY_KEY: dict[str, CheckDefinition] = {c.key: c for c in ALL_CHECKS}
