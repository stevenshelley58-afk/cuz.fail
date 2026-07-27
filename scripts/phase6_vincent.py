"""Phase 6: City of Vincent LPP 7.1.1 Built Form Policy rule candidates.

Source version f3da5cec-aac6-4b5e-ab62-a0eee334bd48.
All values transcribed verbatim from the policy text/tables (pdfplumber dump).
Sections: Volume 1 s1 Town Centre, s2 Activity Corridor, s3 Mixed Use,
s4 Transit Corridor, s5 Residential; Volume 2 s1 Town Centre (multiple
dwellings / mixed use acceptable outcomes).
"""
import sys

sys.path.insert(0, "/app/scripts/phase6")
from lpp_lib import cand, ensure_clause, write_report

COUNCIL = "City of Vincent"
SV = "f3da5cec-aac6-4b5e-ab62-a0eee334bd48"
PDF = "/app/data/raw-sources/councils/vincent/lpp_7_1_1_built_form_policy.pdf"

C = []
WARN = []

def clause(key, title, text):
    return ensure_clause(SV, key, title, text)

def add(clause_id, section, *a, **k):
    k.setdefault("instrument_section", section)
    C.append(cand(*a, clause_id=clause_id, sv_id=SV, council_scope=COUNCIL, **k))

RES_AREA = ["Residential Built Form Area"]
TC_AREA = ["Town Centre Built Form Area"]
AC_AREA = ["Activity Corridor Built Form Area"]
MU_AREA = ["Mixed Use Built Form Area"]
TR_AREA = ["Transit Corridor Built Form Area"]

# ============ VOLUME 1 SECTION 5 - RESIDENTIAL ============
c5 = clause("lpp711_v1_s5_residential",
            "LPP7.1.1 Volume 1 Section 5 Residential",
            "Deemed-to-comply provisions replacing/amending R-Codes Vol 1 clauses "
            "5.1.2, 5.1.3, 5.1.6, 5.2.1, 5.2.2, 5.2.4, 5.2.5, 5.3.2, 5.4.4.")
S5 = "Volume 1 Section 5 (Residential)"

add(c5, S5, "vincent.upper_floor_wall_stepback_min_m.residential", "gte", 2, "m",
    "C5.1.4 Walls on upper floors setback a minimum of 2 metres behind the ground floor predominant building line (excluding any porch or verandah), as determined by the City.",
    zones=RES_AREA, table_reference="Clause 5.1 C5.1.4",
    canonical_rule_key="vincent.upper_floor_wall_stepback_min_m")
add(c5, S5, "vincent.upper_floor_balcony_stepback_min_m.residential", "gte", 1, "m",
    "C5.1.5 Balconies on upper floors setback a minimum of 1 metre behind the ground floor predominant building line (excluding any porch or verandah), as determined by the City.",
    zones=RES_AREA, table_reference="Clause 5.1 C5.1.5")
add(c5, S5, "vincent.secondary_street_upper_floor_stepback_min_m.residential", "gte", 1.5, "m",
    "C5.1.7 Secondary street setbacks for upper floors is to be 1.5 metres behind each portion of the ground floor setback.",
    zones=RES_AREA, table_reference="Clause 5.1 C5.1.7")
add(c5, S5, "vincent.porch_projection_into_street_setback_max_pct.residential", "lte", 50, "%",
    "C5.1.3 An unenclosed porch, verandah or the equivalent may (subject to the Building Codes of Australia) project into the primary street setback area to a maximum of half the required primary street setback area.",
    zones=RES_AREA, table_reference="Clause 5.1 C5.1.3",
    condition={"of": "required primary street setback area"})

# Lot boundary setback tables 1-5.2b / 1-5.2c (category from Table 1-5.2a matrix)
for cat, low, up in (("B", 4.5, 6.5), ("C", 6.5, 12.5)):
    add(c5, S5, f"vincent.lot_boundary_setback_min_m.residential.cat_{cat.lower()}_storeys_1_3",
        "gte", low, "m",
        f"Table 1 – 5.2b: category {cat} — setback for ground floor, second storey and third storey {low}m (category per Table 1 – 5.2a subject/neighbouring Built Form Area matrix).",
        zones=RES_AREA, table_reference="Table 1-5.2b",
        condition={"category": cat, "storeys": "ground floor to third storey",
                   "category_source": "Table 1-5.2a adjoining-property matrix"})
    add(c5, S5, f"vincent.lot_boundary_setback_min_m.residential.cat_{cat.lower()}_storeys_4_plus",
        "gte", up, "m",
        f"Table 1 – 5.2b: category {cat} — setback for the fourth storey and above {up}m (category per Table 1 – 5.2a subject/neighbouring Built Form Area matrix).",
        zones=RES_AREA, table_reference="Table 1-5.2b",
        condition={"category": cat, "storeys": "fourth storey and above",
                   "category_source": "Table 1-5.2a adjoining-property matrix"})
for wcond, wkey, val in (("\u226414", "lte14", 3), (">14", "gt14", 4)):
    add(c5, S5, f"vincent.lot_boundary_setback_min_m.residential.cat_d_lot_width_{wkey}",
        "gte", val, "m",
        f"Table 1 – 5.2c: width of lot {wcond} metres — setback {val}m (category D per Table 1 – 5.2a).",
        zones=RES_AREA, table_reference="Table 1-5.2c",
        condition={"category": "D", "lot_width_condition": wcond})

# Table 1-5.3 Building Height - Residential Area
METRICS = [
    ("top_external_wall_roof_above", "Top of external wall (roof above)"),
    ("top_external_wall_concealed_roof", "Top of external wall (concealed roof)"),
    ("bottom_skillion_roof", "Bottom of skillion roof"),
    ("top_skillion_roof", "Top of skillion roof"),
    ("top_pitched_roof", "Top of pitched roof"),
]
RES_HEIGHTS = {  # storeys: [wall above, concealed, skillion bottom, skillion top, pitched]
    1: [3.5, 5, 3.5, 5, 7],
    2: [7, 8, 7, 8, 10],
    3: [9, 10, 9, 10, 12],
    4: [12, 13, 12, 13, 15],
    5: [16, 17, 16, 17, 18],
}
for storeys, vals in RES_HEIGHTS.items():
    add(c5, S5, f"vincent.building_height_max_storeys.residential.s{storeys}", "lte", storeys, "storeys",
        f"TABLE 1 – 5.3: Building Height – Residential Area — maximum {storeys} storeys as per Figure 2 (height limits: top of external wall (roof above) {vals[0]}m, concealed roof {vals[1]}m, skillion {vals[2]}-{vals[3]}m, pitched {vals[4]}m).",
        zones=RES_AREA, table_reference="Table 1-5.3",
        condition={"storey_band": storeys, "location_source": "Figure 2 Building Heights map"},
        check_type="max_storeys")
    for (mkey, mlabel), v in zip(METRICS, vals):
        add(c5, S5, f"vincent.building_height_max_m.residential.s{storeys}.{mkey}", "lte", v, "m",
            f"TABLE 1 – 5.3: Building Height – Residential Area — {storeys} storeys: {mlabel} {v}m.",
            zones=RES_AREA, table_reference="Table 1-5.3",
            condition={"storey_band": storeys, "measurement_point": mlabel})

# Garages / carports
add(c5, S5, "vincent.garage_setback_behind_dwelling_alignment_min_m.residential", "gte", 0.5, "m",
    "C5.4.2 Garages are to be setback a minimum of 500mm behind the dwelling alignment (excluding any porch portico verandah or balcony or the like).",
    zones=RES_AREA, table_reference="Clause 5.4 C5.4.2")
add(c5, S5, "vincent.carport_width_max_pct_frontage.residential", "lte", 50, "%",
    "C5.4.7 The total width of any carport within the street setback area is not to exceed 50 per cent of the frontage (including strata lots) of the lot or six metres whichever is the lesser.",
    zones=RES_AREA, table_reference="Clause 5.4 C5.4.7",
    condition={"location": "within street setback area", "lesser_of": ["50% of frontage", "6m"]})
add(c5, S5, "vincent.carport_width_max_m.residential", "lte", 6, "m",
    "C5.4.7 The total width of any carport within the street setback area is not to exceed 50 per cent of the frontage (including strata lots) of the lot or six metres whichever is the lesser.",
    zones=RES_AREA, table_reference="Clause 5.4 C5.4.7",
    condition={"location": "within street setback area", "lesser_of": ["50% of frontage", "6m"]})
add(c5, S5, "vincent.garage_width_max_pct_lot.residential", "lte", 50, "%",
    "C5.5.1 Garages which are 50% or less than the width of the lot.",
    zones=RES_AREA, table_reference="Clause 5.5 C5.5.1")
add(c5, S5, "vincent.garage_width_max_m.narrow_lot", "lte", 4, "m",
    "C5.5.2 For lots less than 10 metres wide, garages which are a maximum of 4 metres wide.",
    zones=RES_AREA, table_reference="Clause 5.5 C5.5.2",
    condition={"lot_width_lt_m": 10})

# Street walls and fences (C5.7.2)
FENCE_QUOTE = ("C5.7.2 Street walls, fences and gates within the primary street setback area, including along "
               "the side boundaries, and front walls and fences to new dwellings fronting a right of way or dedicated road")
add(c5, S5, "vincent.fence_height_max_m.primary_street", "lte", 1.8, "m",
    FENCE_QUOTE + ": 1. Maximum height of 1.8 metres above the natural ground level.",
    zones=RES_AREA, table_reference="Clause 5.7 C5.7.2",
    condition={"measured_from": "natural ground level"})
add(c5, S5, "vincent.fence_pier_height_max_m.primary_street", "lte", 2, "m",
    FENCE_QUOTE + ": 2. Maximum height of piers with decorative capping to be 2 metres above the natural ground level.",
    zones=RES_AREA, table_reference="Clause 5.7 C5.7.2")
add(c5, S5, "vincent.fence_solid_portion_height_max_m.primary_street", "lte", 1.2, "m",
    FENCE_QUOTE + ": 3. Maximum height of solid portion of wall to be 1.2 metres above adjacent footpath level and are to be visually permeable above 1.2 metres.",
    zones=RES_AREA, table_reference="Clause 5.7 C5.7.2",
    condition={"measured_from": "adjacent footpath level", "visual_permeability_above_m": 1.2})
add(c5, S5, "vincent.fence_pier_width_max_mm", "lte", 400, "mm",
    FENCE_QUOTE + ": 4. Posts and piers are to have a maximum width 400 millimetres and a maximum diameter of 500 millimetres.",
    zones=RES_AREA, table_reference="Clause 5.7 C5.7.2")
add(c5, S5, "vincent.fence_pier_diameter_max_mm", "lte", 500, "mm",
    FENCE_QUOTE + ": 4. Posts and piers are to have a maximum width 400 millimetres and a maximum diameter of 500 millimetres.",
    zones=RES_AREA, table_reference="Clause 5.7 C5.7.2")
add(c5, S5, "vincent.fence_solid_portion_height_max_m.secondary_street", "lte", 1.8, "m",
    "C5.7.3 ... Solid portion of wall may increase to a maximum height of 1.8 metres above adjacent footpath level provided that the wall or fence has at least two significant appropriate design features (to the satisfaction of the City of Vincent).",
    zones=RES_AREA, table_reference="Clause 5.7 C5.7.3",
    condition={"location": "secondary streets / behind primary street setback line / district distributor roads",
               "requires": "two significant design features"})

# Sight lines (C5.8.1)
add(c5, S5, "vincent.sightline_structure_height_max_m.driveway", "lte", 0.75, "m",
    "C5.8.1 Walls, fences and other structures truncated or reduced to no higher than 0.75m within 1.5m where walls, fences, or other structures adjoin a driveway that intersects a street, right-of-way, communal street.",
    zones=RES_AREA, table_reference="Clause 5.8 C5.8.1",
    condition={"within_m_of_intersection": 1.5})
add(c5, S5, "vincent.sightline_gate_unobstructed_view_min_pct", "gte", 50, "%",
    "C5.8.1 ... If a gate is proposed across a vehicle access point where a driveway meets a public street and where two streets intersect, the gate must provide: When Closed: a minimum of 50 per cent unobstructed view.",
    zones=RES_AREA, table_reference="Clause 5.8 C5.8.1")
add(c5, S5, "vincent.sightline_clear_gap_min_mm", "gte", 40, "mm",
    "C5.8.1 ... a Clear Sight Line means: Continuous horizontal or vertical gaps that constitute a minimum of 50% of the total surface area; A minimum gap size of 40mm.",
    zones=RES_AREA, table_reference="Clause 5.8 C5.8.1")

# Landscaping (C5.9)
add(c5, S5, "vincent.deep_soil_area_min_pct.residential", "gte", 12, "%",
    "C5.9.1 Deep Soil Areas shall be provided in accordance with the following requirements: <650m2: 12% (min 1m2, 1m x 1m); 650m2-1,500m2: 12%; >1,500m2: 12% (minimum % of site).",
    zones=RES_AREA, table_reference="Clause 5.9 C5.9.1",
    condition={"min_area_m2": 1, "min_dimensions": "1m x 1m", "of": "site area"})
add(c5, S5, "vincent.deep_soil_area_reduced_min_pct.residential", "gte", 10, "%",
    "C5.9.3 The required Deep Soil Area may be reduced to 10% where mature trees, which contribute to 30% or more of the required canopy coverage, are retained.",
    zones=RES_AREA, table_reference="Clause 5.9 C5.9.3",
    condition={"requires": "retained mature trees contributing >=30% of required canopy coverage"})
add(c5, S5, "vincent.planting_area_min_pct.residential", "gte", 3, "%",
    "C5.9.2 Planting Areas shall be provided in accordance with the following requirements: all site areas 3% (minimum % of site; min 1m2, 1m x 1m).",
    zones=RES_AREA, table_reference="Clause 5.9 C5.9.2",
    condition={"min_area_m2": 1, "min_dimensions": "1m x 1m", "of": "site area"})
add(c5, S5, "vincent.canopy_coverage_min_pct.residential", "gte", 30, "%",
    "C5.9.4 At least 30% of the site area is provided as canopy coverage at maturity.",
    zones=RES_AREA, table_reference="Clause 5.9 C5.9.4",
    condition={"at": "maturity", "of": "site area"})
add(c5, S5, "vincent.carpark_canopy_coverage_min_pct", "gte", 60, "%",
    "C5.9.5 Open air car parks, including access ways, shall have a minimum of 60% canopy coverage at maturity.",
    zones=RES_AREA, table_reference="Clause 5.9 C5.9.5",
    condition={"applies_to": "open air car parks including access ways", "at": "maturity"})
add(c5, S5, "vincent.carpark_planting_strip_min_m", "gte", 1.5, "m",
    "C5.9.7 The perimeter of all open-air parking areas shall be landscaped by a planting strip with a minimum dimension of 1.5m.",
    zones=RES_AREA, table_reference="Clause 5.9 C5.9.7")

# External fixtures (C5.10)
add(c5, S5, "vincent.ac_fixture_height_max_m.residential", "lte", 1.8, "m",
    "C5.10.3 For single houses and grouped dwellings, air conditioning fixtures are to be placed at the rear of the ground floor. The highest point of the air conditioning fixture is to be a maximum 1.8 metres above natural ground level or below the existing fence line.",
    zones=RES_AREA, table_reference="Clause 5.10 C5.10.3",
    condition={"location": "rear of ground floor", "alternative": "below existing fence line"})

# Rights of way (P5.13)
add(c5, S5, "vincent.right_of_way_setback_min_m.residential", "gte", 1, "m",
    "P5.13.6 Development must be setback 1 metre from a right of way. If the site is subject to right of way widening, the setback is measured from the new lot boundary after the widening is applied.",
    zones=RES_AREA, table_reference="Clause 5.13 P5.13.6",
    condition={"replaces": "R-Codes C5.2.1 where primary street frontage is a right of way"})
add(c5, S5, "vincent.pedestrian_access_way_width_m.residential", "eq", 1.5, "m",
    "P5.13.7 Each lot that does not have direct frontage to a dedicated road is to be provided with a pedestrian access way to a dedicated road. The width of the pedestrian access way shall be 1.5 metres.",
    zones=RES_AREA, table_reference="Clause 5.13 P5.13.7")

# ============ VOLUME 1 SECTION 1 - TOWN CENTRE ============
c1 = clause("lpp711_v1_s1_town_centre",
            "LPP7.1.1 Volume 1 Section 1 Town Centre",
            "Deemed-to-comply provisions for Town Centre Built Form Areas: nil street "
            "setback, building height Table 1-1.3, landscaping, ESD.")
S1 = "Volume 1 Section 1 (Town Centre)"

add(c1, S1, "vincent.street_setback_m.town_centre", "eq", 0, "m",
    "C1.1.1 Primary and secondary street setback is nil.",
    zones=TC_AREA, table_reference="Clause 1.1 C1.1.1",
    canonical_rule_key="vincent.street_setback_m")

TC_HEIGHTS = [  # (key, location label, storeys, wall-above m)
    ("leederville_default", "Leederville (default where Masterplan silent)", 6, 19.5),
    ("leederville_vincent_st", "Leederville – Vincent Street", 5, 16.4),
    ("leederville_carr_pl", "Leederville – Carr Place", 4, 13.3),
    ("north_perth_fitzgerald_st", "North Perth – Fitzgerald Street", 6, 19.5),
    ("north_perth_angove_st", "North Perth – Angove Street", 4, 13.3),
    ("perth", "Perth", 6, 19.5),
    ("mount_lawley_highgate", "Mount Lawley / Highgate", 6, 19.5),
    ("mount_hawthorn", "Mount Hawthorn", 5, 16.4),
    ("glendalough", "Glendalough", 8, 25.7),
]
for key, label, storeys, h in TC_HEIGHTS:
    add(c1, S1, f"vincent.building_height_max_storeys.town_centre.{key}", "lte", storeys, "storeys",
        f"TABLE 1 – 1.3: Building Height – Town Centres — {label}: maximum {storeys} storeys.",
        zones=TC_AREA, table_reference="Table 1-1.3",
        condition={"location": label}, check_type="max_storeys")
    add(c1, S1, f"vincent.building_height_max_m.town_centre.{key}", "lte", h, "m",
        f"TABLE 1 – 1.3: Building Height – Town Centres — {label}: top of external wall (roof above) {h}m ({storeys} storeys).",
        zones=TC_AREA, table_reference="Table 1-1.3",
        condition={"location": label, "measurement_point": "Top of external wall (roof above)"})

add(c1, S1, "vincent.deep_soil_area_min_pct.town_centre", "gte", 12, "%",
    "C1.4.1 Deep Soil Areas shall be provided in accordance with the following requirements: <650m2: 12%; 650m2-1,500m2: 12%; >1,500m2: 12% (minimum % of site; min 1m2, 1m x 1m).",
    zones=TC_AREA, table_reference="Clause 1.4 C1.4.1",
    condition={"min_area_m2": 1, "min_dimensions": "1m x 1m", "of": "site area"})
add(c1, S1, "vincent.deep_soil_area_reduced_min_pct.town_centre", "gte", 10, "%",
    "C1.4.2 The required Deep Soil Area may be reduced to 10% where mature trees, which contribute to 30% or more of the required canopy coverage, are retained.",
    zones=TC_AREA, table_reference="Clause 1.4 C1.4.2")
add(c1, S1, "vincent.planting_area_min_pct.town_centre", "gte", 3, "%",
    "C1.4.3 Planting Areas shall be provided in accordance with the following requirements: all site areas 3% (minimum % of site; min 1m2, 1m x 1m).",
    zones=TC_AREA, table_reference="Clause 1.4 C1.4.3")
add(c1, S1, "vincent.setback_canopy_coverage_min_pct.town_centre", "gte", 80, "%",
    "C1.4.4 At least 80%* of the lot boundary setback area at ground level shall be provided as canopy coverage at maturity.",
    zones=TC_AREA, table_reference="Clause 1.4 C1.4.4",
    condition={"of": "lot boundary setback area at ground level", "at": "maturity"})
add(c1, S1, "vincent.carpark_canopy_coverage_min_pct.town_centre", "gte", 60, "%",
    "C1.4.5 Open air car parks, including access ways, shall have a minimum of 60% canopy coverage at maturity.",
    zones=TC_AREA, table_reference="Clause 1.4 C1.4.5")
add(c1, S1, "vincent.carpark_bays_per_tree_max.town_centre", "lte", 4, "bays_per_tree",
    "C1.4.6 All open-air parking areas shall be landscaped at a minimum rate of one tree per four car bays.",
    zones=TC_AREA, table_reference="Clause 1.4 C1.4.6")
add(c1, S1, "vincent.carpark_planting_strip_min_m.town_centre", "gte", 1.5, "m",
    "C1.4.7 The perimeter of all open-air parking areas shall be landscaped by a planting strip with a minimum dimension of 1.5m.",
    zones=TC_AREA, table_reference="Clause 1.4 C1.4.7")

# ESD (P1.8.4-6)
add(c1, S1, "vincent.roof_solar_absorptance_max.flat_roof", "lte", 0.4, "rating",
    "P1.8.4 Flat roof structures that are not visible from the street or adjacent properties shall have a maximum solar absorptance rating of 0.4.",
    zones=TC_AREA + AC_AREA + MU_AREA + TR_AREA + RES_AREA,
    table_reference="Clause 1.8 P1.8.4",
    condition={"roof_type": "flat, not visible from street or adjacent properties"})
add(c1, S1, "vincent.roof_solar_absorptance_max.pitched_roof", "lte", 0.5, "rating",
    "P1.8.5 Pitched roof structures or roof structures that are visible from the street or adjacent properties shall have a maximum solar absorptance rating of 0.5, unless a suitable alternative is identified in the Urban Design Study.",
    zones=TC_AREA + AC_AREA + MU_AREA + TR_AREA + RES_AREA,
    table_reference="Clause 1.8 P1.8.5",
    condition={"roof_type": "pitched or visible from street or adjacent properties"})
add(c1, S1, "vincent.gwp_max_kgco2e_per_occupant_year.residential", "lt", 2250, "kgCO2e/occupant/year",
    "Building Type Performance Requirement — Residential (BCA Class 1-3): Global Warming Potential < 2,250 kgCO2e / Occupant / Year (50% saving against Perth statistical average residences).",
    zones=TC_AREA + AC_AREA + MU_AREA + TR_AREA + RES_AREA,
    table_reference="Clause 1.8 P1.8.6 performance table",
    condition={"building_type": "Residential (BCA Class 1-3)"})
add(c1, S1, "vincent.fresh_water_max_m3_per_occupant_year.residential", "lt", 57, "m3/occupant/year",
    "Building Type Performance Requirement — Residential (BCA Class 1-3): Net Fresh Water Use < 57m3 / Occupant / Year (50% saving against Perth statistical average residences).",
    zones=TC_AREA + AC_AREA + MU_AREA + TR_AREA + RES_AREA,
    table_reference="Clause 1.8 P1.8.6 performance table",
    condition={"building_type": "Residential (BCA Class 1-3)"})
add(c1, S1, "vincent.gwp_max_kgco2e_per_m2_nla_year.office", "lt", 104, "kgCO2e/m2 NLA/year",
    "Building Type Performance Requirement — Commercial Office (BCA Class 5): Global Warming Potential < 104 kgCO2e / m2 Net Lettable Area / year (30% saving against Perth statistical average office).",
    zones=TC_AREA + AC_AREA + MU_AREA,
    table_reference="Clause 1.8 P1.8.6 performance table",
    condition={"building_type": "Commercial Office (BCA Class 5)"})
add(c1, S1, "vincent.fresh_water_max_m3_per_m2_nla_year.office", "lt", 1.25, "m3/m2 NLA/year",
    "Building Type Performance Requirement — Commercial Office (BCA Class 5): Net Fresh Water Use < 1.25 m3 / m2 Net Lettable Area / year (25% saving against Perth statistical average office).",
    zones=TC_AREA + AC_AREA + MU_AREA,
    table_reference="Clause 1.8 P1.8.6 performance table",
    condition={"building_type": "Commercial Office (BCA Class 5)"})

# ============ VOLUME 1 SECTION 2 - ACTIVITY CORRIDOR ============
c2 = clause("lpp711_v1_s2_activity_corridor",
            "LPP7.1.1 Volume 1 Section 2 Activity Corridor",
            "Building height Table 1-2.1; all other Section 1 requirements apply (cl 2.2.1).")
S2 = "Volume 1 Section 2 (Activity Corridor)"
AC_HEIGHTS = [
    ("oxford_st", "Oxford Street", 4, 13.3),
    ("scarborough_beach_rd", "Scarborough Beach Road", 4, 13.3),
    ("fitzgerald_newcastle_vincent", "Fitzgerald Street (Newcastle St to Vincent St)", 6, 19.5),
    ("fitzgerald_vincent_raglan", "Fitzgerald Street (Vincent St to Raglan Road)", 4, 13.3),
    ("newcastle_st", "Newcastle Street", 6, 19.5),
    ("beaufort_newcastle_lincoln", "Beaufort Street (Newcastle St to Lincoln St)", 5, 16.4),
    ("beaufort_lincoln_walcott", "Beaufort Street (Lincoln St to Walcott St)", 6, 19.5),
]
for key, label, storeys, h in AC_HEIGHTS:
    add(c2, S2, f"vincent.building_height_max_storeys.activity_corridor.{key}", "lte", storeys, "storeys",
        f"TABLE 1 – 2.1: Building Height – Activity Corridors — {label}: maximum {storeys} storeys.",
        zones=AC_AREA, table_reference="Table 1-2.1",
        condition={"location": label}, check_type="max_storeys")
    add(c2, S2, f"vincent.building_height_max_m.activity_corridor.{key}", "lte", h, "m",
        f"TABLE 1 – 2.1: Building Height – Activity Corridors — {label}: top of external wall (roof above) {h}m ({storeys} storeys).",
        zones=AC_AREA, table_reference="Table 1-2.1",
        condition={"location": label, "measurement_point": "Top of external wall (roof above)"})

# ============ VOLUME 1 SECTION 3 - MIXED USE ============
c3 = clause("lpp711_v1_s3_mixed_use",
            "LPP7.1.1 Volume 1 Section 3 Mixed Use",
            "Building height Table 1-3.1; all other Section 1 requirements apply (cl 3.2.1).")
S3 = "Volume 1 Section 3 (Mixed Use)"
MU_HEIGHTS = [
    ("newcastle_loftus_freeway_charles", "Area bounded by Newcastle St, Loftus St, Mitchell Freeway and Charles St", 7, 22.6),
    ("carr_charles_newcastle_fitzgerald", "Area bounded by Carr St, Charles St, Newcastle St and Fitzgerald St", 3, 10.2),
    ("between_fitzgerald_william", "Between Fitzgerald St and William St (Brisbane/Bulwer/Charles/Green/Walcott/William Sts)", 4, 13.3),
    ("north_perth_summers_lord_gff_east_parade", "North Perth – area bounded by Summers St, Lord St, Graham Farmer Freeway and East Parade", 6, 19.5),
    ("edward_st_south", "Edward St South", 8, 25.7),
    ("edward_st_north", "Edward St North", 4, 13.3),
    ("caversham_south", "Caversham South", 8, 25.7),
    ("caversham_north", "Caversham North", 10, 31.9),
    ("cheriton_south", "Cheriton South", 10, 31.9),
    ("cheriton_north", "Cheriton North", 12, 38.1),
]
for key, label, storeys, h in MU_HEIGHTS:
    add(c3, S3, f"vincent.building_height_max_storeys.mixed_use.{key}", "lte", storeys, "storeys",
        f"TABLE 1 – 3.1: Building Height – Mixed Use Areas — {label}: maximum {storeys} storeys.",
        zones=MU_AREA, table_reference="Table 1-3.1",
        condition={"location": label}, check_type="max_storeys")
    add(c3, S3, f"vincent.building_height_max_m.mixed_use.{key}", "lte", h, "m",
        f"TABLE 1 – 3.1: Building Height – Mixed Use Areas — {label}: top of external wall (roof above) {h}m ({storeys} storeys).",
        zones=MU_AREA, table_reference="Table 1-3.1",
        condition={"location": label, "measurement_point": "Top of external wall (roof above)"})

# ============ VOLUME 1 SECTION 4 - TRANSIT CORRIDOR ============
c4 = clause("lpp711_v1_s4_transit_corridor",
            "LPP7.1.1 Volume 1 Section 4 Transit Corridor",
            "Street setbacks per R-Codes, building height Table 1-4.3, street walls/fences, "
            "landscaping (50% soft landscaping front setback; deep soil 12%).")
S4 = "Volume 1 Section 4 (Transit Corridor)"
TR_HEIGHTS = [
    ("loftus_st", "Loftus Street", 3, 10.2),
    ("charles_newcastle_carr", "Charles Street: between Newcastle St and Carr St", 6, 19.5),
    ("charles_west_newcastle_east", "Charles Street: west side and lots fronting Newcastle east side", 3, 10.2),
    ("charles_carr_walcott_r60", "Charles Street (Carr Street to Walcott St) – R60", 3, 10.2),
    ("charles_carr_walcott_r80", "Charles Street (Carr Street to Walcott St) – R80", 4, 13.3),
    ("charles_carr_walcott_r100", "Charles Street (Carr Street to Walcott St) – R100", 4, 13.3),
    ("fitzgerald_angove_walcott_r60", "Fitzgerald Street (Angove St to Walcott St) – R60", 3, 10.2),
    ("fitzgerald_angove_walcott_r100", "Fitzgerald Street (Angove St to Walcott St) – R100", 4, 13.3),
    ("walcott_st", "Walcott Street", 3, 10.2),
    ("lord_st", "Lord Street", 6, 19.5),
    ("east_parade_r60", "East Parade – R60", 3, 10.2),
    ("east_parade_r100", "East Parade – R100", 4, 13.3),
    ("william_vincent_walcott", "William Street (Vincent St to Walcott St)", 4, 13.3),
]
for key, label, storeys, h in TR_HEIGHTS:
    add(c4, S4, f"vincent.building_height_max_storeys.transit_corridor.{key}", "lte", storeys, "storeys",
        f"TABLE 1 – 4.3: Building Height – Transit Corridors — {label}: maximum {storeys} storeys.",
        zones=TR_AREA, table_reference="Table 1-4.3",
        condition={"location": label}, check_type="max_storeys")
    add(c4, S4, f"vincent.building_height_max_m.transit_corridor.{key}", "lte", h, "m",
        f"TABLE 1 – 4.3: Building Height – Transit Corridors — {label}: top of external wall (roof above) {h}m ({storeys} storeys).",
        zones=TR_AREA, table_reference="Table 1-4.3",
        condition={"location": label, "measurement_point": "Top of external wall (roof above)"})

add(c4, S4, "vincent.front_setback_soft_landscaping_min_pct.transit_corridor", "gte", 50, "%",
    "C4.5.2 A minimum of 50% of the front setback shall be provided as soft landscaping.",
    zones=TR_AREA, table_reference="Clause 4.5 C4.5.2",
    condition={"of": "front setback"})
add(c4, S4, "vincent.deep_soil_area_min_pct.transit_corridor", "gte", 12, "%",
    "C4.5.1 Deep Soil Areas shall be provided in accordance with the following requirements: all site areas 12% (minimum % of site; min 1m2, 1m x 1m).",
    zones=TR_AREA, table_reference="Clause 4.5 C4.5.1")
add(c4, S4, "vincent.deep_soil_area_reduced_min_pct.transit_corridor", "gte", 10, "%",
    "C4.5.4 The required Deep Soil Area may be reduced to 10% where mature trees, which contribute to 30% or more of the required canopy coverage, are retained.",
    zones=TR_AREA, table_reference="Clause 4.5 C4.5.4")
add(c4, S4, "vincent.planting_area_min_pct.transit_corridor", "gte", 3, "%",
    "C4.5.3 Planting Areas shall be provided in accordance with the following requirements: all site areas 3% (minimum % of site; min 1m2, 1m x 1m).",
    zones=TR_AREA, table_reference="Clause 4.5 C4.5.3")
add(c4, S4, "vincent.canopy_coverage_min_pct.transit_corridor", "gte", 30, "%",
    "C4.5.5 At least 30% of the site area is provided as canopy coverage at maturity.",
    zones=TR_AREA, table_reference="Clause 4.5 C4.5.5")

# ============ VOLUME 2 SECTION 1 - TOWN CENTRE (multiple dwellings / mixed use) ============
cv2 = clause("lpp711_v2_s1_town_centre",
             "LPP7.1.1 Volume 2 Section 1 Town Centre (multiple dwellings and mixed use)",
             "Acceptable outcomes replacing R-Codes Vol 2 A3.3.4/A3.3.5/A3.3.7 (tree canopy "
             "and deep soil), A3.9.9 (parking); vehicle access and facade provisions.")
V2 = "Volume 2 Section 1 (Town Centre)"
V2Z = TC_AREA + AC_AREA + MU_AREA

add(cv2, V2, "vincent.deep_soil_area_min_pct.v2_town_centre", "gte", 12, "%",
    "A1.4.1 Deep soil areas are provided as a minimum of 12% of the site area. Deep soil areas are to be co-located with existing trees for retention and/or adjoining trees, or alternatively provided in a location that is conducive to tree growth and suitable for communal open space.",
    zones=V2Z, table_reference="Clause 1.4 A1.4.1", pathway="acceptable_outcome",
    condition={"of": "site area", "dwelling": "multiple dwellings / mixed use"})
add(cv2, V2, "vincent.deep_soil_area_retained_trees_min_pct.v2_town_centre", "gte", 10, "%",
    "A1.4.2 If existing trees, which meet the criteria of A 3.3.1 of the R Codes Volume 2, are retained on site the minimum deep soil area is to be 10% of the site area.",
    zones=V2Z, table_reference="Clause 1.4 A1.4.2", pathway="acceptable_outcome",
    condition={"requires": "existing trees retained per R-Codes Vol 2 A3.3.1"})
add(cv2, V2, "vincent.planting_area_min_pct.v2_town_centre", "gte", 3, "%",
    "A1.4.3 Planting Areas are provided as a minimum of 3% of the site area.",
    zones=V2Z, table_reference="Clause 1.4 A1.4.3", pathway="acceptable_outcome")
add(cv2, V2, "vincent.setback_canopy_coverage_min_pct.v2_town_centre", "gte", 80, "%",
    "A1.4.4 Landscaping includes existing and new trees with shade producing canopies in accordance with Tables 3.3a and 3.3b of the R Codes Volume 2 to achieve canopy coverage of 80% in the ground floor lot boundary setback.",
    zones=V2Z, table_reference="Clause 1.4 A1.4.4", pathway="acceptable_outcome",
    condition={"of": "ground floor lot boundary setback"})
add(cv2, V2, "vincent.crossover_max_count_per_lot.v2", "lte", 1, "count",
    "A1.6.10 Each lot is to provide a maximum of one crossover.",
    zones=V2Z, table_reference="Clause 1.6 A1.6.10", pathway="acceptable_outcome")
add(cv2, V2, "vincent.crossover_width_max_m.single", "lte", 3, "m",
    "A1.6.11 The maximum width of a single crossover is 3m. The maximum width of a double crossover is 5m.",
    zones=V2Z, table_reference="Clause 1.6 A1.6.11", pathway="acceptable_outcome",
    condition={"crossover_type": "single"})
add(cv2, V2, "vincent.crossover_width_max_m.double", "lte", 5, "m",
    "A1.6.11 The maximum width of a single crossover is 3m. The maximum width of a double crossover is 5m.",
    zones=V2Z, table_reference="Clause 1.6 A1.6.11", pathway="acceptable_outcome",
    condition={"crossover_type": "double"})
add(cv2, V2, "vincent.carpark_bays_per_tree_max.v2", "lte", 4, "bays_per_tree",
    "A1.7.1 Uncovered at-grade parking is planted with trees at a minimum rate of one tree per four bays to achieve canopy coverage of 60% of the site.",
    zones=V2Z, table_reference="Clause 1.7 A1.7.1", pathway="acceptable_outcome",
    condition={"target_canopy_pct": 60})
add(cv2, V2, "vincent.commercial_ground_floor_width_max_m", "lte", 9, "m",
    "A1.8.2 Commercial Ground floor spaces shall have a maximum width of 9m and a finished floor level to finished ceiling level height of a minimum of 3.5m.",
    zones=V2Z, table_reference="Clause 1.8 A1.8.2", pathway="acceptable_outcome")
add(cv2, V2, "vincent.commercial_ground_floor_ceiling_height_min_m", "gte", 3.5, "m",
    "A1.8.2 Commercial Ground floor spaces shall have a maximum width of 9m and a finished floor level to finished ceiling level height of a minimum of 3.5m.",
    zones=V2Z, table_reference="Clause 1.8 A1.8.2", pathway="acceptable_outcome")
add(cv2, V2, "vincent.commercial_doorway_depth_min_m", "gte", 0.5, "m",
    "A1.8.6 Where provided, doorways shall have a depth between 500mm and 1.5m to clearly articulate entrances to commercial buildings and tenancies.",
    zones=V2Z, table_reference="Clause 1.8 A1.8.6", pathway="acceptable_outcome")
add(cv2, V2, "vincent.commercial_doorway_depth_max_m", "lte", 1.5, "m",
    "A1.8.6 Where provided, doorways shall have a depth between 500mm and 1.5m to clearly articulate entrances to commercial buildings and tenancies.",
    zones=V2Z, table_reference="Clause 1.8 A1.8.6", pathway="acceptable_outcome")
add(cv2, V2, "vincent.commercial_glazing_visible_light_transmission_min_pct", "gte", 70, "%",
    "A1.8.9 Commercial Ground floor glazing and/or tinting shall have a minimum of 70% visible light transmission to provide unobscured visibility.",
    zones=V2Z, table_reference="Clause 1.8 A1.8.9", pathway="acceptable_outcome")
add(cv2, V2, "vincent.awning_height_min_m", "gte", 3.5, "m",
    "A1.8.11 Commercial Development shall provide a protective continuous awning over the pedestrian footpath, which shall: Be minimum height of 3.5m and a maximum height of 4m from finished floor level to the underside of the awning to accommodate under awning signage.",
    zones=V2Z, table_reference="Clause 1.8 A1.8.11", pathway="acceptable_outcome")
add(cv2, V2, "vincent.awning_height_max_m", "lte", 4, "m",
    "A1.8.11 Commercial Development shall provide a protective continuous awning over the pedestrian footpath, which shall: Be minimum height of 3.5m and a maximum height of 4m from finished floor level to the underside of the awning to accommodate under awning signage.",
    zones=V2Z, table_reference="Clause 1.8 A1.8.11", pathway="acceptable_outcome")
add(cv2, V2, "vincent.awning_kerb_setback_min_m", "gte", 0.6, "m",
    "A1.8.11 ... Be setback a minimum of 600mm from the face of kerb.",
    zones=V2Z, table_reference="Clause 1.8 A1.8.11", pathway="acceptable_outcome")
add(cv2, V2, "vincent.stall_riser_height_min_mm", "gte", 450, "mm",
    "A1.8.8 Where provided, stall risers shall be a minimum height of 450mm.",
    zones=V2Z, table_reference="Clause 1.8 A1.8.8", pathway="acceptable_outcome")

WARN = [
    "CONFLICTS WITH R-CODE DEFAULTS (by design - adopted replacements): Vol 1 cl 1.1/4.1/5.1 replace 5.1.2; cl 1.2/4.2/5.2 amend 5.1.3; cl 1.3/2.1/3.1/4.3/5.3 replace 5.1.6; cl 5.4 replaces 5.2.1; cl 5.5 replaces 5.2.2; cl 4.4/5.7 replace 5.2.4; cl 5.8 replaces 5.2.5; cl 1.4/4.5/5.9 replace 5.3.2 C2; cl 1.7/4.6/5.10 replace 5.4.4 C4.3-C4.4. Vol 2 A1.4.1-A1.4.7 replace A3.3.4/A3.3.5/A3.3.7; A1.7.1 replaces A3.9.9.",
    "Building-height location tables also appear in Volume 2 (Tables 2-1.1 etc.) with the same values for multiple dwellings; extracted once from Volume 1 to avoid duplicates.",
    "Policy note (p13): Built Form Policy D-t-C provisions are an adopted policy position but do not apply as D-t-C until related scheme amendments are approved; until then the relevant R-Codes D-t-C provisions apply. Flagged for operator awareness.",
    "Deep-soil tables list min 1m2 area and 1m x 1m dimensions across all site-area bands (<650, 650-1500, >1500 m2) at 12%; encoded as a single 12% rule per section with dimensions in condition_json.",
    "Height tables: extracted storeys cap + top-of-external-wall (roof above) metres per location; concealed/skillion/pitched roof metrics are stated alongside (wall+1m; pitched +3m) and captured in quotes/conditions for residential Table 1-5.3 (all 5 metrics encoded).",
]
write_report("/app/reports/phase6_vincent_lpp711_built_form_extraction.json",
             SV, PDF, "Volume 1 Sections 1-5; Volume 2 Section 1",
             ["Table 1-1.3", "Table 1-2.1", "Table 1-3.1", "Table 1-4.3", "Table 1-5.2a/b/c",
              "Table 1-5.3", "Clauses 1.1-1.8, 2.1-2.2, 3.1-3.2, 4.1-4.8, 5.1-5.13",
              "Vol2 Clauses 1.4-1.8"],
             C, warnings=WARN)
print("Vincent candidates:", len(C))
