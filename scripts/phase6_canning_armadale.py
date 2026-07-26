"""Phase 6 fast pass: City of Canning LP.01 + City of Armadale PLN 3.10.

Canning LP.01 Residential Development (f08dc22d-...): R-Codes Part B D-t-C
amendments (street setbacks w/ tree retention, garage, fences/sightlines,
outbuildings, sea containers).
Armadale PLN 3.10 R-Codes Variations & R-MD Codes (ef718abf-...): R17.5 garage
boundary walls + Table 1 R-MD 25/30/40 single house standards.
"""
import sys
sys.path.insert(0, "/app/scripts/phase6")
from lpp_lib import cand, ensure_clause, write_report

SV_CAN = "f08dc22d-69f2-4274-8509-77f8c3a1c7b9"
SV_ARM = "ef718abf-5c9e-4ed7-b2f6-de944117dcdf"
PDF_CAN = "/app/data/raw-sources/councils/canning/lp01_residential_development.pdf"
PDF_ARM = "/app/data/raw-sources/councils/armadale/pln3_10_r_codes_variations_2026.pdf"

CAN = []
ARM = []

def acan(clause_id, section, *a, **k):
    k.setdefault("instrument_section", section)
    CAN.append(cand(*a, clause_id=clause_id, sv_id=SV_CAN, council_scope="City of Canning", **k))

def aarm(clause_id, section, *a, **k):
    k.setdefault("instrument_section", section)
    ARM.append(cand(*a, clause_id=clause_id, sv_id=SV_ARM, council_scope="City of Armadale", **k))

# ============ CANNING LP.01 ============
c_c1 = ensure_clause(SV_CAN, "canning_lp01_street_boundary_setbacks",
                     "LP.01 s3.1-3.2 Street setbacks & lot boundary setbacks (tree retention)",
                     "C2.1(iii) 50% reduction w/ compensation or tree retention (9m2 deep soil, "
                     "min dim 3m); boundary wall length +3m and frontage <=12m provisions.")
c_c2 = ensure_clause(SV_CAN, "canning_lp01_garage",
                     "LP.01 s3.3-3.4 Setback of carports/garages & garage width",
                     "Garage 4.5m primary setback, reductions to 3m parallel / 0.5m behind "
                     "dwelling; garage door max 50% frontage (60% w/ upper floor or tree retention).")
c_c3 = ensure_clause(SV_CAN, "canning_lp01_fences_sightlines",
                     "LP.01 s3.5-3.6 Street walls/fences & sightlines",
                     "Pillars 1.8m/450x450mm; uniform fencing 1800/2100mm; sightlines 0.75m "
                     "within 1.5m; driveway fencing 1.8m.")
c_c4 = ensure_clause(SV_CAN, "canning_lp01_outbuildings_extras",
                     "LP.01 s3.7-3.8 Outbuildings, sea containers & external fixtures",
                     "Outbuilding area/height by lot size band; sea container max 1, 30m2, "
                     "wall 2.4m, ridge 4.2m; 15 amp outlet per garage parking space.")

TWR = {"definition_of": "tree worthy of retention (also Grass Tree)"}
acan(c_c1, "s1 Definitions", "canning.tree_worthy_retention_height_min_m", "gte", 3, "m",
     "Tree worthy of retention A tree that: a) Is equal to or in excess of 3m in height; or b) Has a trunk equal to or in excess of 100mm in diameter (sum of 200mm diameter for multiple trunk species) measured at 1.4m above ground level; or c) Has a canopy spread of 3m or more; or d) A Grass Tree",
     condition=TWR, effective_from="2024-12-10")
acan(c_c1, "s1 Definitions", "canning.tree_worthy_retention_trunk_diameter_min_mm", "gte", 100, "mm",
     "Has a trunk equal to or in excess of 100mm in diameter (sum of 200mm diameter for multiple trunk species) measured at 1.4m above ground level",
     condition={**TWR, "measured_at": "1.4m above ground level", "multi_trunk_sum_mm": 200}, effective_from="2024-12-10")
acan(c_c1, "s1 Definitions", "canning.tree_worthy_retention_canopy_min_m", "gte", 3, "m",
     "Has a canopy spread of 3m or more",
     condition=TWR, effective_from="2024-12-10")
acan(c_c1, "s3.1 C2.1(iii)", "canning.primary_street_setback_reduction_max_pct", "lte", 50, "%",
     "C2.1 Buildings, excluding carports, porches, balconies, verandahs, or equivalent, set back from the primary street boundary: iii. Reduced by up to 50 per cent provided that the area of any building, including a garage encroaching into the setback area, is compensated for by: a. At least an equal area of open space that is located between the street setback line and a line drawn parallel to it at twice the setback distance, or, b. Where a tree worthy of retention is retained between the street setback line and twice the setback distance with a minimum of 9m2 (minimum dimension 3m) of deep soil area.",
     condition={"requires": "equal-area open space compensation OR retained tree + 9m2 deep soil"},
     evaluable="needs_human_review", effective_from="2024-12-10")
acan(c_c1, "s3.1 C2.1(iii)b / s3.2 C3.2(v)", "canning.tree_retention_deep_soil_area_min_m2", "gte", 9, "m2",
     "Where a tree worthy of retention is retained between the street setback line and twice the setback distance with a minimum of 9m2 (minimum dimension 3m) of deep soil area.",
     condition={"for": "tree worthy of retention retention concession"}, effective_from="2024-12-10")
acan(c_c1, "s3.1 C2.1(iii)b / s3.2 C3.2(v)", "canning.tree_retention_deep_soil_min_dimension_m", "gte", 3, "m",
     "with a minimum of 9m2 (minimum dimension 3m) of deep soil area.",
     condition={"applies_to": "length and width"}, effective_from="2024-12-10")
acan(c_c1, "s3.2 C3.2(v)", "canning.boundary_wall_length_extension_max_m", "lte", 3, "m",
     "v. The maximum length to one boundary wall can be increased by up to 3m where a tree worthy of retention is retained with a minimum of 9m2 (minimum dimension 3m) of deep soil area and is located behind twice the setback distance.",
     condition={"requires": "retained tree + 9m2 deep soil behind twice the setback distance"}, effective_from="2024-12-10")

acan(c_c2, "s3.3 C1.1", "canning.garage_primary_street_setback_min_m", "gte", 4.5, "m",
     "C1.1 Garages set back 4.5m from the primary street except that the setback may be reduced: i. In accordance with Part B Figure 8b where the garage adjoins a dwelling provided the garage is at least 0.5m behind the dwelling alignment ...; or ii. To 3m where the garage allows vehicles to be parked parallel to the street ...; iii. Where the garage is setback in accordance with Clause 5.1.2 C2.1 iii b.",
     effective_from="2024-12-10")
acan(c_c2, "s3.3 C1.1(i)", "canning.garage_behind_dwelling_alignment_min_m", "gte", 0.5, "m",
     "the garage adjoins a dwelling provided the garage is at least 0.5m behind the dwelling alignment (excluding any porch, verandah or balcony)",
     condition={"reduction_path": "garage adjoins dwelling (Part B Figure 8b)"}, effective_from="2024-12-10")
acan(c_c2, "s3.3 C1.1(ii)", "canning.garage_setback_parallel_parking_min_m", "gte", 3, "m",
     "To 3m where the garage allows vehicles to be parked parallel to the street. The wall parallel to the street must include openings.",
     condition={"requires": "parallel parking + openings in street-parallel wall"}, effective_from="2024-12-10")
acan(c_c2, "s3.4 C2.1", "canning.garage_door_width_max_pct_frontage", "lte", 50, "%",
     "C2.1 A garage door and its supporting structures (or a garage wall where a garage is aligned parallel to the street) facing the primary street is not to occupy more than 50 per cent of the frontage at the setback line as viewed from the street. This may be increased up to 60 per cent where an upper floor or balcony extends for more than half the width of the garage ... and the entrance to the dwelling is clearly visible from the primary street.",
     condition={"measured_at": "setback line as viewed from street"}, effective_from="2024-12-10")
acan(c_c2, "s3.4 C2.1", "canning.garage_door_width_max_pct_frontage.upper_floor", "lte", 60, "%",
     "This may be increased up to 60 per cent where an upper floor or balcony extends for more than half the width of the garage and its supporting structures and the entrance to the dwelling is clearly visible from the primary street.",
     condition={"requires": "upper floor/balcony over half garage width + visible entrance"}, effective_from="2024-12-10")
acan(c_c2, "s3.4 C2.2", "canning.garage_door_width_max_pct_frontage.tree_retention", "lte", 60, "%",
     "C2.2 For lots with 12m frontage or less, where a tree worthy of retention is retained in accordance with Clause 5.1.2 C2.1 iii b, a garage door and its supporting structures ... facing the primary street is not to occupy more than 60 per cent of the frontage at the setback line as viewed from the street.",
     condition={"frontage_max_m": 12, "requires": "retained tree per C2.1(iii)b"}, effective_from="2024-12-10")

acan(c_c3, "s3.5 C4.2", "canning.fence_pillar_height_max_m", "lte", 1.8, "m",
     "C4.2 Solid pillars that form part of front fences not more than 1.8m above natural ground level provided the horizontal dimension of the pillars is not greater than 450mm by 450mm and pillars are separated by visually permeable fencing.",
     condition={"measured_from": "natural ground level", "requires": "visually permeable fencing between pillars"}, effective_from="2024-12-10")
acan(c_c3, "s3.5 C4.2 / C4.5", "canning.fence_pillar_dimension_max_mm", "lte", 450, "mm",
     "the horizontal dimension of the pillars is not greater than 450mm by 450mm",
     condition={"applies_to": "front fence pillars and uniform fencing piers (both dimensions)"}, effective_from="2024-12-10")
acan(c_c3, "s3.5 C4.4(ii)", "canning.metal_fence_height_front_setback_max_m", "lte", 1.2, "m",
     "ii. The height of the metal sheeting fence (e.g. Colorbond) is to a maximum height of 1.2m within the front setback line.",
     condition={"location": "within primary street setback area", "material": "metal sheeting"}, effective_from="2024-12-10")
acan(c_c3, "s3.5 C4.5 major transport corridors", "canning.uniform_fence_height_max_mm.transport_corridor", "lte", 2100, "mm",
     "Along Major Transport Corridors (Railway Reservation, and a Primary or Other Regional Road Reservations) Only: i. Fencing maximum height shall be 2100mm above natural ground level;",
     condition={"location": "abutting major transport corridor", "requires": "anti-graffiti coating"}, effective_from="2024-12-10")
acan(c_c3, "s3.5 C4.5 all other locations", "canning.uniform_fence_height_max_mm.other", "lte", 1800, "mm",
     "All other locations: i. Fencing maximum height shall be 1800mm above natural ground level, with solid sections not exceeding a maximum height of 1.2m, and visually permeable infill panels above up to 1.8m height between piers;",
     condition={"location": "uniform fencing all other locations", "requires": "anti-graffiti coating"}, effective_from="2024-12-10")
acan(c_c3, "s3.5 C4.5 all other locations", "canning.uniform_fence_solid_height_max_m", "lte", 1.2, "m",
     "with solid sections not exceeding a maximum height of 1.2m, and visually permeable infill panels above up to 1.8m height between piers",
     condition={"location": "uniform fencing all other locations"}, effective_from="2024-12-10")
acan(c_c3, "s3.5 C4.5 all other locations", "canning.uniform_fence_solid_length_max_pct", "lte", 50, "%",
     "iii. The solid section of fencing shall be maximum length of 50% of the length of the boundary behind the primary street setback line;",
     condition={"of": "boundary length behind primary street setback line"}, effective_from="2024-12-10")
acan(c_c3, "s3.6 C5.1", "canning.sightline_structure_height_max_m", "lte", 0.75, "m",
     "C5.1 Walls, fences and other structures truncated or reduced to no higher than 0.75m within 1.5m of where walls, fences, or other structures adjoin: i. a driveway that intersects a street, right-of-way or communal street; ii. a right-of-way or communal street that intersects a public street; and iii. two streets that intersect.",
     condition={"within_m_of_intersection": 1.5}, effective_from="2024-12-10")
acan(c_c3, "s3.6 C5.2", "canning.driveway_fence_height_max_m", "lte", 1.8, "m",
     "C5.2 Fencing no higher than 1.8m high above natural ground level within 1.5m of where a driveway meets a street with: i. no more than one solid pillar provided the horizontal dimension of the pillar is not greater than 450mm by 450mm; ii. no more than two panels ... with visually permeable fencing ...; iv. where there are no existing or planned footpaths adjacent to the property boundary.",
     condition={"within_m_of_driveway_street_junction": 1.5, "max_solid_pillars": 1}, effective_from="2024-12-10")

OB = [
    ("lot_le_600", 60, 4.2, "Lots up to 600m2 in site area", {"lot_area_max_m2": 600}),
    ("lot_601_800", 80, 4.2, "Lots 601m2 - 800m2 in site area", {"lot_area_min_m2": 601, "lot_area_max_m2": 800}),
    ("lot_801_1000", 90, 4.8, "Lots 801m2 - 1000m2 in site area", {"lot_area_min_m2": 801, "lot_area_max_m2": 1000}),
    ("lot_1001_2000", 100, 4.8, "Lots 1001m2 - 2000m2", {"lot_area_min_m2": 1001, "lot_area_max_m2": 2000}),
    ("lot_gt_2000", 130, 4.8, "Lots over 2001m2", {"lot_area_min_m2": 2001}),
]
for key, area, ridge, label, cond in OB:
    acan(c_c4, "s3.7 C3 Table B", f"canning.outbuilding_area_max_m2.{key}", "lte", area, "m2",
         f"{label}: individually or collectively does not exceed {area}m2 in area or 10 percent in aggregate of the site area, whichever is the lesser.",
         table_reference="s3.7 C3 Table B Large and multiple outbuildings",
         condition={**cond, "alternative_cap": "10% of site area, whichever is lesser"}, effective_from="2024-12-10")
    acan(c_c4, "s3.7 C3 Table B", f"canning.outbuilding_ridge_height_max_m.{key}", "lte", ridge, "m",
         f"{label}: does not exceed a ridge height of {ridge}m.",
         table_reference="s3.7 C3 Table B Large and multiple outbuildings",
         condition=cond, effective_from="2024-12-10")
acan(c_c4, "s3.7 C3 Table B", "canning.outbuilding_area_max_pct_site", "lte", 10, "%",
     "individually or collectively does not exceed ... 10 percent in aggregate of the site area, whichever is the lesser",
     table_reference="s3.7 C3 Table B Large and multiple outbuildings",
     condition={"applies": "all lot size bands, aggregate of all outbuildings"}, effective_from="2024-12-10")
acan(c_c4, "s3.7 C3 Table B", "canning.outbuilding_wall_height_max_m", "lte", 3, "m",
     "does not exceed a wall height of 3m (all lot size bands)",
     table_reference="s3.7 C3 Table B Large and multiple outbuildings",
     condition={"applies": "all lot size bands"}, effective_from="2024-12-10")
acan(c_c4, "s3.7 C Sea Containers", "canning.sea_container_max_count", "lte", 1, "containers",
     "C. Sea Containers i. Only one (1) sea container is permitted per site to a maximum area of 30m2;",
     check_type="max_count", effective_from="2024-12-10")
acan(c_c4, "s3.7 C Sea Containers", "canning.sea_container_area_max_m2", "lte", 30, "m2",
     "Only one (1) sea container is permitted per site to a maximum area of 30m2; not located within a primary or secondary street setback area;",
     condition={"not_in": "primary or secondary street setback area"}, effective_from="2024-12-10")
acan(c_c4, "s3.7 C Sea Containers", "canning.sea_container_wall_height_max_m", "lte", 2.4, "m",
     "iv. does not exceed a wall height of 2.4m;", effective_from="2024-12-10")
acan(c_c4, "s3.7 C Sea Containers", "canning.sea_container_ridge_height_max_m", "lte", 4.2, "m",
     "v. does not exceed a ridge height of 4.2m;", effective_from="2024-12-10")
acan(c_c4, "s3.8 C4.9", "canning.garage_power_outlet_min_amp", "gte", 15, "amp",
     "C4.9 A power outlet (minimum 15 amp) shall be provided to each car parking space within a garage.",
     condition={"per": "car parking space within a garage"}, effective_from="2024-12-10")
acan(c_c4, "s4.1 Other exemptions", "canning.sea_container_temporary_max_months", "lte", 1, "months",
     "Sea containers can be placed within a residential property and incidental to a dwelling for a temporary period of up to one (1) month ... The occurrence only happens once per calendar year to the lot.",
     condition={"development_approval": "not required", "max_occurrences_per_calendar_year": 1}, effective_from="2024-12-10")

# ============ ARMADALE PLN 3.10 ============
c_a1 = ensure_clause(SV_ARM, "armadale_310_boundary_garage_r175",
                     "PLN 3.10 s4.1 Boundary walls - garages (R17.5)",
                     "R17.5 garages to one boundary: height 3.0m, length 9m, setbacks "
                     "4.5m primary / 1.5m secondary street.")
c_a2 = ensure_clause(SV_ARM, "armadale_310_rmd_table1",
                     "PLN 3.10 s4.4 Table 1 R-MD Codes (Urban Development zone)",
                     "R-MD 25/30/40 single house standards: setbacks, fences, boundary "
                     "walls, open space, garage, overshadowing, privacy.")

R175 = ["R17.5"]
aarm(c_a1, "s4.1", "armadale.garage_boundary_wall_height_max_m.r175", "lte", 3.0, "m",
     "In R17.5 coded areas, garages may be constructed up to one site boundary provided they do not exceed 3.0m in height above natural ground level, are no longer than 9m in length and maintain a minimum street setback of 4.5m from a primary street or 1.5m from a secondary street.",
     r_codes=R175, condition={"measured_from": "natural ground level", "boundaries": "one site boundary"},
     effective_from="2026-03-23")
aarm(c_a1, "s4.1", "armadale.garage_boundary_wall_length_max_m.r175", "lte", 9, "m",
     "are no longer than 9m in length",
     r_codes=R175, effective_from="2026-03-23")
aarm(c_a1, "s4.1", "armadale.garage_boundary_wall_primary_setback_min_m.r175", "gte", 4.5, "m",
     "maintain a minimum street setback of 4.5m from a primary street or 1.5m from a secondary street.",
     r_codes=R175, condition={"street": "primary"}, effective_from="2026-03-23")
aarm(c_a1, "s4.1", "armadale.garage_boundary_wall_secondary_setback_min_m.r175", "gte", 1.5, "m",
     "maintain a minimum street setback of 4.5m from a primary street or 1.5m from a secondary street.",
     r_codes=R175, condition={"street": "secondary"}, effective_from="2026-03-23")

T1 = "PLN 3.10 Table 1 R-MD Codes"
RMD = {"zone": "Urban Development", "ldp": "no approved LDP, or LDP approved after 25 May 2020",
       "excluded_estates": ["Heron Park", "Kamara", "Mason Green", "Holland Park",
                            "Piara Gardens", "Riva", "The Nursery"],
       "ldp_prevails": True}
aarm(c_a2, "s4.4 Table 1 Street Setbacks", "armadale.rmd_primary_street_setback_min_m.rmd25", "gte", 3, "m",
     "Street Setbacks (R-Codes 5.1.2) R-MD 25: 3m minimum (no average). 1.5m to porch/veranda (no max length). 1.5m minimum to secondary street.",
     table_reference=T1, r_codes=["R25"], condition={**RMD, "no_average": True}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Street Setbacks", "armadale.rmd_primary_street_setback_min_m.rmd30_40", "gte", 2, "m",
     "R-MD 30 & R-MD 40: 2m minimum (no average). 1.5m to porch/veranda (no max length). 1m minimum to secondary street.",
     table_reference=T1, r_codes=["R30", "R35", "R40"], condition={**RMD, "no_average": True}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Street Setbacks", "armadale.rmd_porch_setback_min_m", "gte", 1.5, "m",
     "1.5m to porch/veranda (no max length) (R-MD 25, 30 and 40)",
     table_reference=T1, r_codes=["R25", "R30", "R35", "R40"], condition={**RMD, "element": "porch/veranda"}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Street Setbacks", "armadale.rmd_secondary_street_setback_min_m.rmd25", "gte", 1.5, "m",
     "1.5m minimum to secondary street (R-MD 25)",
     table_reference=T1, r_codes=["R25"], condition=dict(RMD), effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Street Setbacks", "armadale.rmd_secondary_street_setback_min_m.rmd30_40", "gte", 1, "m",
     "1m minimum to secondary street (R-MD 30 & R-MD 40)",
     table_reference=T1, r_codes=["R30", "R35", "R40"], condition=dict(RMD), effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Front Fences", "armadale.rmd_front_fence_height_max_mm.rmd30_40", "lte", 900, "mm",
     "Front fences within the primary street setback area being a maximum height of 900mm above natural ground level, measured from the primary street side of the front fence.",
     table_reference=T1, r_codes=["R30", "R35", "R40"],
     condition={**RMD, "location": "within primary street setback area", "measured_from": "primary street side"}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Lot Boundary Setback", "armadale.rmd_lot_boundary_setback_min_m.no_major_openings", "gte", 1, "m",
     "Lot Boundary Setback (R-Codes 5.1.3, C3.1): 1m for wall height 3.5m or less without major openings. 1.2m for wall height 3.5m or less with major openings.",
     table_reference=T1, r_codes=["R25", "R30", "R35", "R40"],
     condition={**RMD, "wall_height_max_m": 3.5, "major_openings": False}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Lot Boundary Setback", "armadale.rmd_lot_boundary_setback_min_m.major_openings", "gte", 1.2, "m",
     "1.2m for wall height 3.5m or less with major openings.",
     table_reference=T1, r_codes=["R25", "R30", "R35", "R40"],
     condition={**RMD, "wall_height_max_m": 3.5, "major_openings": True}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Walls to Boundary", "armadale.rmd_boundary_wall_max_length_fraction.first_side.rmd30", "lte", 0.667, "x side boundary length",
     "Walls to Boundary R-MD 30: To both side boundaries subject to: 2/3 maximum length to one side boundary; 1/3 max length to second side boundary, for wall height 3.5m or less.",
     table_reference=T1, r_codes=["R30", "R35"], condition={**RMD, "wall_height_max_m": 3.5, "side": "one side boundary"}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Walls to Boundary", "armadale.rmd_boundary_wall_max_length_fraction.second_side.rmd30", "lte", 0.333, "x side boundary length",
     "1/3 max length to second side boundary (R-MD 30), for wall height 3.5m or less.",
     table_reference=T1, r_codes=["R30", "R35"], condition={**RMD, "wall_height_max_m": 3.5, "side": "second side boundary"}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Walls to Boundary", "armadale.rmd_boundary_wall_max_length_fraction.second_side.rmd40", "lte", 0.667, "x side boundary length",
     "Walls to Boundary R-MD 40: To both side boundaries subject to: No maximum length to one side boundary; 2/3 max length to second side boundary, for wall height 3.5m or less.",
     table_reference=T1, r_codes=["R40"], condition={**RMD, "wall_height_max_m": 3.5, "side": "second side boundary"}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Open Space", "armadale.rmd_ola_area_min_pct_lot", "gte", 10, "%",
     "An outdoor living area (OLA) with an area of 10% of the lot size or 20m2, whichever is greater, directly accessible from a habitable room of the dwelling and located behind the street setback area.",
     table_reference=T1, r_codes=["R25", "R30", "R35", "R40"],
     condition={**RMD, "alternative_min_m2": 20, "whichever": "greater", "no_other_site_cover_standards": True}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Open Space", "armadale.rmd_ola_area_min_m2", "gte", 20, "m2",
     "An outdoor living area (OLA) with an area of 10% of the lot size or 20m2, whichever is greater, directly accessible from a habitable room of the dwelling and located behind the street setback area.",
     table_reference=T1, r_codes=["R25", "R30", "R35", "R40"],
     condition={**RMD, "alternative_min_pct": 10, "whichever": "greater"}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Open Space", "armadale.rmd_ola_uncovered_min_pct", "gte", 70, "%",
     "At least 70% of the OLA must be uncovered and includes areas under eaves which adjoin uncovered areas.",
     table_reference=T1, r_codes=["R25", "R30", "R35", "R40"], condition=dict(RMD), effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Open Space", "armadale.rmd_ola_min_dimension_m", "gte", 3, "m",
     "The OLA has a minimum 3m length and width dimension.",
     table_reference=T1, r_codes=["R25", "R30", "R35", "R40"], condition={**RMD, "applies_to": "length and width"}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Garage Setback", "armadale.rmd_garage_laneway_setback_min_m.rear_load", "gte", 0.5, "m",
     "Rear load: 0.5m garage setback to laneway.",
     table_reference=T1, r_codes=["R25", "R30", "R35", "R40"], condition={**RMD, "access": "rear load"}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Garage Setback", "armadale.rmd_garage_primary_setback_min_m.front_load", "gte", 4.5, "m",
     "Front load: 4.5m garage setback from the primary street and 1.5m from a secondary street.",
     table_reference=T1, r_codes=["R25", "R30", "R35", "R40"], condition={**RMD, "access": "front load"}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Garage Setback", "armadale.rmd_garage_secondary_setback_min_m.front_load", "gte", 1.5, "m",
     "Front load: 4.5m garage setback from the primary street and 1.5m from a secondary street.",
     table_reference=T1, r_codes=["R25", "R30", "R35", "R40"], condition={**RMD, "access": "front load", "street": "secondary"}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Garage Setback", "armadale.rmd_garage_primary_setback_reduced_min_m.front_load", "gte", 4, "m",
     "The garage setback from the primary street may be reduced to 4m where an existing or planned footpath or shared path is located more than 0.5m from the street boundary.",
     table_reference=T1, r_codes=["R25", "R30", "R35", "R40"],
     condition={**RMD, "access": "front load", "requires": "footpath/shared path >0.5m from street boundary"}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Garage Width", "armadale.rmd_double_garage_width_max_m", "lte", 6, "m",
     "For front loaded lots with street frontages between 10.5 and 12m, a double garage is permitted to a maximum width of 6m as viewed from the street subject to: Garage setback a minimum of 0.5m behind the building alignment; A major opening to a habitable room directly facing the primary street; An entry feature consisting of a porch or veranda with a minimum depth of 1.2m; and No vehicular crossover wider than 4.5m where it meets the street.",
     table_reference=T1, r_codes=["R25", "R30", "R35", "R40"],
     condition={**RMD, "frontage_min_m": 10.5, "frontage_max_m": 12, "garage_behind_alignment_min_m": 0.5,
                "entry_feature_min_depth_m": 1.2}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Garage Width", "armadale.rmd_crossover_width_max_m", "lte", 4.5, "m",
     "No vehicular crossover wider than 4.5m where it meets the street.",
     table_reference=T1, r_codes=["R25", "R30", "R35", "R40"], condition={**RMD, "measured_at": "street"}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Overshadowing", "armadale.rmd_overshadowing_rear_half_max_pct.rmd25", "lte", 25, "%",
     "Overshadowing R-MD 25: No maximum overshadowing for wall height 3.5m or less. No maximum overshadowing for wall height greater than 3.5m where overshadowing is confined to the front half of the lot. If overshadowing intrudes into rear half of the lot, shadow cast does not exceed 25%.",
     table_reference=T1, r_codes=["R25"], condition={**RMD, "of": "adjoining site area", "trigger": "intrudes into rear half of lot"}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Overshadowing", "armadale.rmd_overshadowing_rear_half_max_pct.rmd30_40", "lte", 35, "%",
     "Overshadowing R-MD 30 & R-MD 40: If overshadowing intrudes into rear half of the lot, shadow cast does not exceed 35%.",
     table_reference=T1, r_codes=["R30", "R35", "R40"], condition={**RMD, "of": "adjoining site area", "trigger": "intrudes into rear half of lot"}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Privacy", "armadale.rmd_privacy_setback_bedrooms_min_m", "gte", 3, "m",
     "Privacy: R-Codes clause 5.4.1 C1.1 applies, however the setback distances are: 3m to bedrooms and studies; 4.5m to major openings to habitable rooms other than bedrooms and studies; and 6m to unenclosed outdoor active habitable spaces.",
     table_reference=T1, r_codes=["R25", "R30", "R35", "R40"], condition={**RMD, "opening_type": "bedrooms and studies"}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Privacy", "armadale.rmd_privacy_setback_habitable_min_m", "gte", 4.5, "m",
     "4.5m to major openings to habitable rooms other than bedrooms and studies;",
     table_reference=T1, r_codes=["R25", "R30", "R35", "R40"], condition={**RMD, "opening_type": "major openings to habitable rooms other than bedrooms/studies"}, effective_from="2026-03-23")
aarm(c_a2, "s4.4 Table 1 Privacy", "armadale.rmd_privacy_setback_outdoor_active_min_m", "gte", 6, "m",
     "6m to unenclosed outdoor active habitable spaces.",
     table_reference=T1, r_codes=["R25", "R30", "R35", "R40"], condition={**RMD, "opening_type": "unenclosed outdoor active habitable spaces"}, effective_from="2026-03-23")

write_report("/app/reports/phase6_canning_lp01_residential_extraction.json",
             SV_CAN, PDF_CAN, "LP.01 Residential Development",
             ["s3.7 C3 Table B Large and multiple outbuildings"], CAN,
             ["s3.5 C4.3 (prohibited fence materials) is qualitative — not extracted.",
              "s3.8 C4.8 waste management plan trigger (multiple/5+ grouped dwellings) is "
              "procedural — not extracted.",
              "Figures 1-5 are illustrative only; numeric values captured in rule conditions."])
write_report("/app/reports/phase6_armadale_pln310_rcodes_variations_extraction.json",
             SV_ARM, PDF_ARM, "PLN 3.10 R-Codes Variations & R-MD Codes",
             ["Table 1 Single House Standards for Medium Density in Urban Development zone"],
             ARM,
             ["s4.2 (carport/patio height) defers to R-Codes Table 3 Category A — no override, not extracted.",
              "s4.3 (outbuildings) defers to PLN 3.4 Outbuildings — separate policy, not extracted.",
              "R-MD 25 front fences 'as per R-Codes' — no override.",
              "Lots with frontage <10.5m require single/tandem garaging — qualitative, not extracted."])
