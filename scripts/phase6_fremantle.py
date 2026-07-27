"""Phase 6: City of Fremantle LPP rule candidates.

Sources:
- LPP2.9 Residential Streetscapes (da8dac23-...), D-t-C modifications to
  R-Codes Vol 1 Part B/C: street setbacks, carports, driveways.
- LPP3.20 SCA 5.7 Small Infill Development (c1654799-...), themes 1-8.
- LPP2.2 Split Density Codes & Energy Efficiency Schedule (8d9af7c2-...), Part B.
"""
import sys

sys.path.insert(0, "/app/scripts/phase6")
from lpp_lib import cand, ensure_clause, write_report

COUNCIL = "City of Fremantle"
SV_29 = "da8dac23-f06c-4bb3-bd8a-1def12683fed"
SV_320 = "c1654799-75c6-4dbc-ad09-5a5b6df2f121"
SV_22 = "8d9af7c2-1d93-418a-b98e-545004cff86b"
PDF_29 = "/app/data/raw-sources/councils/fremantle/lpp2_9_residential_streetscapes.pdf"
PDF_320 = "/app/data/raw-sources/councils/fremantle/lpp3_20_sca57_small_infill.pdf"
PDF_22 = "/app/data/raw-sources/councils/fremantle/lpp2_2_split_density_codes.pdf"

R29 = []
R320 = []
R22 = []

def a29(clause_id, section, *a, **k):
    k.setdefault("instrument_section", section)
    R29.append(cand(*a, clause_id=clause_id, sv_id=SV_29, council_scope=COUNCIL, **k))

def a320(clause_id, section, *a, **k):
    k.setdefault("instrument_section", section)
    R320.append(cand(*a, clause_id=clause_id, sv_id=SV_320, council_scope=COUNCIL, **k))

def a22(clause_id, section, *a, **k):
    k.setdefault("instrument_section", section)
    R22.append(cand(*a, clause_id=clause_id, sv_id=SV_22, council_scope=COUNCIL, **k))

HER = {"excluded": "heritage-protected places incl. all heritage areas"}

# ============ LPP2.9 RESIDENTIAL STREETSCAPES ============
c291 = ensure_clause(SV_29, "fremantle_29_s1_street_setback",
                     "LPP2.9 s1 Street setback (Part B cl 5.1.2 / Part C cl 3.3)",
                     "Table 1.1a primary street setbacks by suburb; ground floor = wall "
                     "heights up to 4m on the street elevation; C2.1(iii) 50% reduction "
                     "with open-space compensation (4 suburbs); minor projections 0.75m.")
c292 = ensure_clause(SV_29, "fremantle_29_s2_garage_carport",
                     "LPP2.9 s2 Setback of garages and carports (Part B cl 5.2.1 / Part C cl 3.3)",
                     "Carports in front of dwelling: 1.5m street setback, pillars max "
                     "450x450mm, height max 3m, width 6m (frontage >=12m) / 3m (<12m).")
c294 = ensure_clause(SV_29, "fremantle_29_s4_vehicular_access",
                     "LPP2.9 s4 Vehicular access (Part B cl 5.3.5 C5.2 / Part C cl 3.7 C3.7.3ii)",
                     "Driveways: min 3m (<=4 dwellings), max 4.5m at street boundary, "
                     "aggregate 6m per property. WAPC approved 31 March 2020.")

T11A = "LPP2.9 Table 1.1a Primary Street Setbacks"
a29(c291, "s1 C2.1(i) Table 1.1a", "fremantle.primary_street_setback_ground_min_m.fremantle_north", "gte", 5, "m",
    "Table 1.1a: Primary Street Setbacks — Fremantle 5m 7m; North Fremantle 5m 7m.",
    table_reference=T11A, condition={"suburbs": ["Fremantle", "North Fremantle"], **HER},
    effective_from="2020-03-31")
a29(c291, "s1 C2.1(i) Table 1.1a", "fremantle.primary_street_setback_upper_min_m.fremantle_north", "gte", 7, "m",
    "Table 1.1a: Primary Street Setbacks — Fremantle 5m 7m; North Fremantle 5m 7m.",
    table_reference=T11A, condition={"suburbs": ["Fremantle", "North Fremantle"], "storey": "upper", **HER},
    effective_from="2020-03-31")
a29(c291, "s1 C2.1(i) Table 1.1a", "fremantle.primary_street_setback_ground_min_m.beaconsfield_wgv", "gte", 7, "m",
    "Table 1.1a: Primary Street Setbacks — Beaconsfield 7m 10m; White Gum Valley 7m 10m.",
    table_reference=T11A, condition={"suburbs": ["Beaconsfield", "White Gum Valley"], **HER},
    effective_from="2020-03-31")
a29(c291, "s1 C2.1(i) Table 1.1a", "fremantle.primary_street_setback_upper_min_m.beaconsfield_wgv", "gte", 10, "m",
    "Table 1.1a: Primary Street Setbacks — Beaconsfield 7m 10m; White Gum Valley 7m 10m.",
    table_reference=T11A, condition={"suburbs": ["Beaconsfield", "White Gum Valley"], "storey": "upper", **HER},
    effective_from="2020-03-31")
a29(c291, "s1 C2.1(i) Table 1.1a note", "fremantle.ground_floor_wall_height_max_m", "lte", 4, "m",
    "For purposes of this clause, ground floor setbacks apply to wall heights up to 4m on the street elevation. Above this height, the upper floor setbacks apply.",
    table_reference=T11A, condition={"defines": "ground floor vs upper floor setback applicability", **HER},
    effective_from="2020-03-31")
a29(c291, "s1 C2.1(iii)", "fremantle.primary_street_setback_reduction_max_pct.south_4", "lte", 50, "%",
    "iii. Within the suburbs of South Fremantle, Samson, O'Connor and Hilton only (excluding Heritage Areas): reduced by up to 50 per cent provided that the area of any building, including a garage encroaching into the setback area, is compensated for by at least an equal area of open space that is located between the street setback line and a line drawn parallel to it at twice the setback distance, with such ground floor area occupied by a minimum 50% soft landscaping.",
    condition={"suburbs": ["South Fremantle", "Samson", "O'Connor", "Hilton"],
               "requires": "equal-area open space compensation + min 50% soft landscaping", **HER},
    evaluable="needs_human_review", effective_from="2020-03-31")
a29(c291, "s1 C3.3.1", "fremantle.minor_projection_into_street_setback_max_m", "lte", 0.75, "m",
    "Minor projections, such as chimneys, eaves, window hoods and other architectural features, are acceptable provided they do not project more than 0.75m into the street setback.",
    condition={"elements": ["chimneys", "eaves", "window hoods", "architectural features"], **HER},
    effective_from="2020-03-31")

C29Q = "Carports may be located in front of the dwelling where:"
a29(c292, "s2 C2.1(i)", "fremantle.carport_street_setback_min_m", "gte", 1.5, "m",
    C29Q + " i. The entire carport (including roof, eaves and pillars/posts) is set back a minimum of 1.5m from primary and secondary street boundaries;",
    condition={"element": "carport in front of dwelling", **HER}, effective_from="2020-03-31")
a29(c292, "s2 C2.1(ii)", "fremantle.carport_pillar_dimension_max_mm", "lte", 450, "mm",
    C29Q + " ii. Pillars and posts have a maximum dimension of 450mm by 450mm;",
    condition={"applies_to": "pillars and posts (both dimensions)", **HER}, effective_from="2020-03-31")
a29(c292, "s2 C2.1(iii)", "fremantle.carport_height_max_m", "lte", 3, "m",
    C29Q + " iii. The carport does not exceed a maximum height of 3 metres above natural ground level as viewed from the street;",
    condition={"measured_from": "natural ground level", **HER}, effective_from="2020-03-31")
a29(c292, "s2 C2.1(vi)", "fremantle.carport_width_max_m.frontage_12m_plus", "lte", 6, "m",
    C29Q + " vi. The maximum width of the carport is 6 metres on a property with a frontage of 12 metres or greater, and 3 metres on a property with a frontage of less than 12 metres;",
    condition={"frontage_min_m": 12, **HER}, effective_from="2020-03-31")
a29(c292, "s2 C2.1(vi)", "fremantle.carport_width_max_m.frontage_under_12m", "lte", 3, "m",
    C29Q + " vi. The maximum width of the carport is 6 metres on a property with a frontage of 12 metres or greater, and 3 metres on a property with a frontage of less than 12 metres;",
    condition={"frontage_max_m_exclusive": 12, **HER}, effective_from="2020-03-31")

D29Q = "Driveways to primary or secondary street provided as follows:"
a29(c294, "s4 C5.2", "fremantle.driveway_width_min_m", "gte", 3, "m",
    D29Q + " driveways serving four dwellings or less not narrower than 3m at the street boundary;",
    condition={"serves_max_dwellings": 4, "measured_at": "street boundary"}, effective_from="2020-03-31")
a29(c294, "s4 C5.2 / C3.7.3ii", "fremantle.driveway_width_max_m", "lte", 4.5, "m",
    D29Q + " no driveway wider than 4.5m at the street boundary and driveways in aggregate no greater than 6m for any one property. C3.7.3ii Driveways must be a maximum 4.5m wide at the street boundary.",
    condition={"measured_at": "street boundary"}, effective_from="2020-03-31")
a29(c294, "s4 C5.2", "fremantle.driveway_aggregate_width_max_m", "lte", 6, "m",
    D29Q + " no driveway wider than 4.5m at the street boundary and driveways in aggregate no greater than 6m for any one property.",
    condition={"scope": "all driveways on any one property"}, effective_from="2020-03-31")

# ============ LPP3.20 SCA 5.7 SMALL INFILL ============
c320a = ensure_clause(SV_320, "fremantle_320_location_housing",
                      "LPP3.20 s1-2 Location & Housing choice (LPS4 cl 5.7 mandatory)",
                      "Site >=600m2; dwelling max floor area 120m2; max 3 dwellings on "
                      "<=750m2 + 1 per 150m2 over (LPS4 mandatory, no variation).")
c320b = ensure_clause(SV_320, "fremantle_320_built_form",
                      "LPP3.20 s3 Built form",
                      "Rear setback min 5.0m; private outdoor living 30m2 min dim 4.0m, "
                      "20m2 unroofed; upper-floor balcony min 15m2.")
c320c = ensure_clause(SV_320, "fremantle_320_sustainability_open_space",
                      "LPP3.20 s4-5 Sustainability & Open space",
                      "NCC +1 star; two of: 1.5kW PV/dwelling, 1000L rainwater/dwelling, "
                      "greywater, Platinum accessible dwelling. Open space min 70%.")
c320d = ensure_clause(SV_320, "fremantle_320_trees_community",
                      "LPP3.20 s6-7 Trees, landscaping & community",
                      ">=1 tree (3m height / 100mm trunk at 1m / 3m canopy); deep planting "
                      "zone min 25% site, 50% at rear, min dim 3.0m; communal space min "
                      "dim 3.0m where 3+ dwellings.")
c320e = ensure_clause(SV_320, "fremantle_320_vehicle",
                      "LPP3.20 s8 Vehicle movement and parking",
                      "Driveways water-permeable, min 2.75m max 3.0m, crossovers aggregate "
                      "<=6.0m; parking max 1 bay/new dwelling, 2 bays/existing, waiver for "
                      "one dwelling <=60m2, no visitor parking <5 dwellings, max 2 front bays.")

SCA = {"area": "LPS4 Special Control Area 5.7"}
a320(c320a, "s1 Location", "fremantle.sca57_site_area_min_m2", "gte", 600, "m2",
     "As per the requirements of clause 5.7 of LPS4, development of housing under this policy can be considered on properties in areas identified on the scheme map as SCA 5.7, and where the site is 600m2 or over.",
     condition=dict(SCA), effective_from="2019-02-27")
a320(c320a, "s2 Housing choice", "fremantle.sca57_dwelling_floor_area_max_m2", "lte", 120, "m2",
     "As per the requirements of the clause 5.7 of LPS4 the following applies to development under this policy: Any new dwelling shall have a maximum floor area of 120m2.",
     condition={**SCA, "source": "LPS4 cl 5.7", "variation": "none permitted"}, effective_from="2019-02-27")
a320(c320a, "s2 Housing choice", "fremantle.sca57_dwellings_max_count.lot_750_or_less", "lte", 3, "dwellings",
     "A maximum of three dwellings, including existing dwellings, on lots 750m2 or less. On lots over 750m2 an additional dwelling for every 150m2 in excess of 750m2.",
     condition={**SCA, "lot_area_max_m2": 750, "includes_existing": True, "variation": "none permitted"},
     check_type="max_count", effective_from="2019-02-27")
a320(c320a, "s2 Housing choice", "fremantle.sca57_additional_dwelling_per_m2_over_750", "eq", 150, "m2 per additional dwelling",
     "On lots over 750m2 an additional dwelling for every 150m2 in excess of 750m2.",
     condition={**SCA, "lot_area_gt_m2": 750, "variation": "none permitted"}, effective_from="2019-02-27")
a320(c320b, "s3.2 Rear setback", "fremantle.sca57_rear_setback_min_m", "gte", 5.0, "m",
     "DEEMED-TO-COMPLY All buildings shall be set back a minimum 5.0m from the rear boundary of the development site.",
     condition=dict(SCA), effective_from="2019-02-27")
a320(c320b, "s3.3 Private outdoor living", "fremantle.sca57_outdoor_living_area_min_m2", "gte", 30, "m2",
     "A minimum 30m2 of outdoor living area shall be provided per dwelling, with minimum length and width dimension of 4.0m, directly accessible from a habitable room. 20m2 of this area is to be without a permanent roof cover.",
     condition={**SCA, "per": "dwelling", "access": "directly accessible from a habitable room"}, effective_from="2019-02-27")
a320(c320b, "s3.3 Private outdoor living", "fremantle.sca57_outdoor_living_min_dimension_m", "gte", 4.0, "m",
     "A minimum 30m2 of outdoor living area shall be provided per dwelling, with minimum length and width dimension of 4.0m, directly accessible from a habitable room.",
     condition={**SCA, "applies_to": "length and width"}, effective_from="2019-02-27")
a320(c320b, "s3.3 Private outdoor living", "fremantle.sca57_outdoor_living_unroofed_min_m2", "gte", 20, "m2",
     "20m2 of this area is to be without a permanent roof cover.",
     condition=dict(SCA), effective_from="2019-02-27")
a320(c320b, "s3.3 Private outdoor living", "fremantle.sca57_upper_floor_balcony_min_m2", "gte", 15, "m2",
     "The outdoor living area (balcony) may be reduced to a minimum 15m2 where the outdoor living area is to an upper floor dwelling only.",
     condition={**SCA, "storey": "upper floor dwelling only"}, effective_from="2019-02-27")
a320(c320c, "s4.1 D-t-C 1", "fremantle.sca57_nathers_stars_above_ncc_min", "gte", 1, "stars above NCC requirement",
     "1. The development achieves a star rating of one star in excess of the current energy efficiency requirement of the National Construction Code. The star rating shall be certified by an accredited energy assessor.",
     condition={**SCA, "certification": "accredited energy assessor"}, effective_from="2019-02-27")
a320(c320c, "s4.1 D-t-C 2", "fremantle.sca57_pv_system_min_kw_per_dwelling", "gte", 1.5, "kW",
     "The development includes at least two of the following: The provision of a minimum 1.5kw photovoltaic solar panel system per dwelling.",
     condition={**SCA, "option_of": "at least two of four sustainability options", "per": "dwelling"}, effective_from="2019-02-27")
a320(c320c, "s4.1 D-t-C 2", "fremantle.sca57_rainwater_storage_min_l_per_dwelling", "gte", 1000, "L",
     "The provision of holding at least 1000 litres of rainwater per dwelling. The rainwater is to be connected to water use in a dwelling(s), e.g. toilet or washing machine, and/or used for irrigation on private or communal outdoor areas.",
     condition={**SCA, "option_of": "at least two of four sustainability options", "per": "dwelling"}, effective_from="2019-02-27")
a320(c320c, "s5.1 Open space", "fremantle.sca57_open_space_min_pct", "gte", 70, "%",
     "DEEMED-TO-COMPLY A minimum 70% of the entire development site shall be open space.",
     condition={**SCA, "of": "entire development site"}, effective_from="2019-02-27")
a320(c320c, "s5.1 Design principles", "fremantle.sca57_open_space_reduced_min_pct", "gte", 60, "%",
     "Council may consider a reduction in open space to a minimum of 60% open space where - an existing dwelling is retained or adapted with no significant enlargement ... or a building assessed as having 'some' or more cultural heritage significance is retained; or a building with a high degree of embedded energy is retained; or a minimum of 50% of the available open space includes areas that are developed as water permeable uncovered: outdoor living areas, communal areas and/or deep planting zones.",
     condition={**SCA, "pathway": "design principles (discretionary reduction)"},
     evaluable="needs_human_review", effective_from="2019-02-27")
a320(c320d, "s6.1 Canopy cover", "fremantle.sca57_trees_min_count", "gte", 1, "trees",
     "DEEMED-TO-COMPLY Retain or plant at least one tree on site that meets the following requirements - Healthy specimen with ongoing viability as identified by a suitably qualified arborist. At least 3m in height and/or have a trunk with a diameter of at least 100mm, one metre from the ground and/or has a canopy of 3.0m or more or the potential to reach these measurements.",
     condition=dict(SCA), check_type="min_count", effective_from="2019-02-27")
a320(c320d, "s6.1 Canopy cover", "fremantle.sca57_tree_height_min_m", "gte", 3, "m",
     "At least 3m in height and/or have a trunk with a diameter of at least 100mm, one metre from the ground and/or has a canopy of 3.0m or more or the potential to reach these measurements.",
     condition={**SCA, "alternatives": "trunk diameter >=100mm at 1m from ground, or canopy >=3.0m, or potential to reach these"},
     effective_from="2019-02-27")
a320(c320d, "s6.2 Deep planting zone", "fremantle.sca57_deep_planting_zone_min_pct", "gte", 25, "%",
     "A minimum 25% of the development site area shall be provided as deep planting zone.",
     condition={**SCA, "of": "development site area", "source": "LPS4 mandatory"}, effective_from="2019-02-27")
a320(c320d, "s6.2 Deep planting zone", "fremantle.sca57_deep_planting_zone_rear_min_pct", "gte", 50, "%",
     "50% of the deep planting zone must be provided on the rear portion of the site.",
     condition={**SCA, "of": "deep planting zone"}, effective_from="2019-02-27")
a320(c320d, "s6.2 Deep planting zone", "fremantle.sca57_deep_planting_zone_min_dimension_m", "gte", 3.0, "m",
     "The deep planting zone shall: Be landscaped, water permeable, unpaved and uncovered; Be a minimum length and width dimension of 3.0 metres; Not be used for vehicle parking or access; Contain no buildings, patios, pergolas, swimming pools or external fixtures.",
     condition={**SCA, "applies_to": "length and width"}, effective_from="2019-02-27")
a320(c320d, "s7.1 Communal space", "fremantle.sca57_communal_space_min_dimension_m", "gte", 3.0, "m",
     "Where three or more dwellings are proposed, usable and effective communal space shall be provided that is accessible to all residents of a development site, with a minimum dimension of 3.0m.",
     condition={**SCA, "trigger": "three or more dwellings proposed"}, effective_from="2019-02-27")
a320(c320e, "s8.1 Vehicle access", "fremantle.sca57_driveway_width_min_m", "gte", 2.75, "m",
     "The minimum width of a driveway shall be 2.75m.",
     condition={**SCA, "amends": "R-Codes cl 5.3.5", "surface": "water permeable construction required"}, effective_from="2019-02-27")
a320(c320e, "s8.1 Vehicle access", "fremantle.sca57_driveway_width_max_m", "lte", 3.0, "m",
     "The maximum width of a driveway shall be 3.0m.",
     condition={**SCA, "amends": "R-Codes cl 5.3.5"}, effective_from="2019-02-27")
a320(c320e, "s8.1 Vehicle access", "fremantle.sca57_crossover_aggregate_width_max_m", "lte", 6.0, "m",
     "If the existing driveway/crossover doesn't allow access to the rear of the site, then an additional crossover is permitted subject to a 3.0m maximum width and in aggregate width of crossovers on a development site to not be over 6.0m.",
     condition={**SCA, "per_crossover_max_m": 3.0}, effective_from="2019-02-27")
a320(c320e, "s8.1 Vehicle access", "fremantle.sca57_driveway_water_permeable", "eq", True, None,
     "Driveways shall be water permeable in construction; no hardstand or impermeable paved driveways will be approved on site.",
     condition=dict(SCA), check_type="boolean", evaluable="needs_human_review", effective_from="2019-02-27")
a320(c320e, "s8.2 Vehicle parking", "fremantle.sca57_parking_max_bays_per_new_dwelling", "lte", 1, "bays",
     "A maximum of 1 vehicle parking bay shall be provided for each new dwelling and a maximum of two car bays for any existing dwelling on the development site.",
     condition={**SCA, "dwelling": "new", "source": "LPS4 mandatory"}, check_type="max_count", effective_from="2019-02-27")
a320(c320e, "s8.2 Vehicle parking", "fremantle.sca57_parking_max_bays_per_existing_dwelling", "lte", 2, "bays",
     "A maximum of 1 vehicle parking bay shall be provided for each new dwelling and a maximum of two car bays for any existing dwelling on the development site.",
     condition={**SCA, "dwelling": "existing", "source": "LPS4 mandatory"}, check_type="max_count", effective_from="2019-02-27")
a320(c320e, "s8.2 Vehicle parking", "fremantle.sca57_parking_waiver_dwelling_floor_area_max_m2", "lte", 60, "m2",
     "The vehicle parking bay requirement above, can be waived where one small dwelling within a development achieves a floor area of 60m2 or less.",
     condition={**SCA, "waives": "1 bay requirement for that dwelling"}, effective_from="2019-02-27")
a320(c320e, "s8.2 Vehicle parking", "fremantle.sca57_visitor_parking_max_bays.under_5_dwellings", "lte", 0, "bays",
     "Visitor parking shall not be provided for development less than 5 dwellings.",
     condition={**SCA, "development_max_dwellings": 4}, check_type="max_count", effective_from="2019-02-27")
a320(c320e, "s8.2 Vehicle parking", "fremantle.sca57_front_parking_max_bays", "lte", 2, "bays",
     "A maximum of two car bays shall be provided to the front of the development.",
     condition={**SCA, "location": "front of the development"}, check_type="max_count", effective_from="2019-02-27")

# ============ LPP2.2 SPLIT DENSITY / ENERGY EFFICIENCY ============
c22b = ensure_clause(SV_22, "fremantle_22_partb_schedule",
                     "LPP2.2 Part B Energy Efficiency and Sustainability Schedule",
                     "NatHERS +1 star above BCA; min 3kW PV; 3000L rainwater tank plumbed "
                     "to toilet/laundry OR greywater reuse OR significant tree retention; "
                     "solar/heat-pump/PV electric hot water and electric cooking. 0.5 star "
                     "alternative for clauses 1.2/1.3.")

SPLIT = {"applies_to": "new dwelling development on split-coded land connected to reticulated sewer",
         "pathway": "LPS4 cl 4.3.4 higher density code via Energy Efficiency Schedule"}
a22(c22b, "Part B cl 1.1", "fremantle.splitcode_nathers_stars_above_bca_min", "gte", 1, "stars above BCA requirement",
    "1.1 The dwelling shall be designed and constructed to a Nationwide House Energy Rating Scheme (NatHERS) star rating a minimum of one star in excess of the current energy efficiency requirement of the Building Codes of Australia for class 1A buildings, or an equivalent demonstrating comparable energy efficiency.",
    condition={**SPLIT, "certification": "suitably qualified and accredited energy assessor at DA stage"},
    effective_from="2022-01-19")
a22(c22b, "Part B cl 1.2", "fremantle.splitcode_pv_system_min_kw", "gte", 3, "kW",
    "1.2 Provision of a minimum 3kW photovoltaic solar panel system;",
    condition=SPLIT, effective_from="2022-01-19")
a22(c22b, "Part B cl 1.3(a)", "fremantle.splitcode_rainwater_tank_min_l", "gte", 3000, "L",
    "1.3 Provision of: (a) a minimum 3000L capacity rainwater tank plumbed to either a toilet or laundry within the dwelling; or (b) an approved greywater reuse system ...; or (c) successful registration of an existing tree on the City's Significant Tree and Vegetation Areas Register and its subsequent retention;",
    condition={**SPLIT, "alternatives": ["approved greywater reuse system", "registered significant tree retention"],
               "plumbed_to": "toilet or laundry"}, effective_from="2022-01-19")
a22(c22b, "Part B alternative", "fremantle.splitcode_alternative_nathers_stars_min", "gte", 0.5, "additional stars per substituted item",
    "In cases where an applicant demonstrates that the requirements of clause 1.2 and/or 1.3 of Part B cannot reasonably be met, Council may accept the achievement of an additional half (0.5) star NatHERS star rating in lieu of each of the items at clause 1.2 and/or 1.3 as an alternative means of complying with this policy.",
    condition={**SPLIT, "substitutes": "clause 1.2 (PV) and/or 1.3 (water/tree) items"},
    evaluable="needs_human_review", effective_from="2022-01-19")

write_report("/app/reports/phase6_fremantle_lpp29_streetscape_extraction.json",
             SV_29, PDF_29, "LPP2.9 Residential Streetscapes",
             ["Table 1.1a Primary Street Setbacks"], R29,
             [("Heritage areas excluded from all provisions; South Fremantle/Samson/O'Connor/Hilton "
              "ground+upper setbacks revert to R-Codes (no LPP override)."),
              "s3 Building height modifies no D-t-C criteria (design principles only) — not extracted.",
              "LPP2.8 Fences cross-referenced for carport doors/gates — separate instrument."])
write_report("/app/reports/phase6_fremantle_lpp320_sca57_extraction.json",
             SV_320, PDF_320, "LPP3.20 SCA 5.7 Small Infill Development",
             [], R320,
             ["Dwelling count and floor area limits are LPS4 cl 5.7 mandatory with no variation.",
              "Visual appearance (s3.1) relies on Design Advisory Committee — qualitative, not extracted.",
              "s7.2 street interface D-t-C criteria qualitative — not extracted."])
write_report("/app/reports/phase6_fremantle_lpp22_split_density_extraction.json",
             SV_22, PDF_22, "LPP2.2 Part B Energy Efficiency and Sustainability Schedule",
             [], R22,
             [("Part A pathways (heritage retention, low income housing, non-conforming use removal) "
              "are qualitative eligibility routes under LPS4 cl 4.3.4 — not extracted."),
              ("Part B cl 1.4 (electric hot water/cooking) is a specification requirement — "
              "qualitative, not extracted.")])
