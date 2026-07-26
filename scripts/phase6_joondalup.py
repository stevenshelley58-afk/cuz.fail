"""Phase 6: City of Joondalup LPP rule candidates.

Sources:
- LPP Residential Development (dbedbd59-...), Appendices 1-3 (R-Codes Vol 1
  Parts B/C/D replacement and additional D-t-C requirements).
- LPP Development in Housing Opportunity Areas (1bc7ba4a-...), sections 1-19.
"""
import sys
sys.path.insert(0, "/app/scripts/phase6")
from lpp_lib import cand, ensure_clause, write_report

COUNCIL = "City of Joondalup"
SV_RD = "dbedbd59-39ce-4baf-8485-6e0e16166412"
SV_HOA = "1bc7ba4a-d761-4d23-bec0-6b60a21dcc4f"
PDF_RD = "/app/data/raw-sources/councils/joondalup/lpp_residential_development.pdf"
PDF_HOA = "/app/data/raw-sources/councils/joondalup/lpp_development_housing_opportunity_areas.pdf"

RD = []
HOA = []

def addr(clause_id, section, *a, **k):
    k.setdefault("instrument_section", section)
    RD.append(cand(*a, clause_id=clause_id, sv_id=SV_RD, council_scope=COUNCIL, **k))

def addh(clause_id, section, *a, **k):
    k.setdefault("instrument_section", section)
    HOA.append(cand(*a, clause_id=clause_id, sv_id=SV_HOA, council_scope=COUNCIL, **k))

# ============ RESIDENTIAL DEVELOPMENT LPP ============
c_b = ensure_clause(SV_RD, "joondalup_rd_appendix1_partb",
                    "Joondalup Residential Development LPP Appendix 1 (Part B R-Codes Vol 1)",
                    "Replacement/additional D-t-C: single houses R40 and below, grouped "
                    "dwellings R25 and below, multiple dwellings R10-R25.")
c_c = ensure_clause(SV_RD, "joondalup_rd_appendix2_partc",
                    "Joondalup Residential Development LPP Appendix 2 (Part C R-Codes Vol 1)",
                    "Replacement/additional D-t-C: single houses R50 and above, grouped "
                    "dwellings R30 and above, multiple dwellings R30-R60.")
c_d = ensure_clause(SV_RD, "joondalup_rd_appendix3_partd",
                    "Joondalup Residential Development LPP Appendix 3 (Part D R-Codes Vol 1)",
                    "Additional D-t-C site area criteria for dual-coded areas (LPS3 cl 26(5), 26(7)).")

SIGHT_Q = ("Walls, fences and other structures truncated, reduced in height or visually permeable above 0.75m "
           "of natural ground level (with solid pillars not more than 1.8m above natural ground level in "
           "accordance with clause 5.2.5 C5) within 1.5m of where walls, fences or other structures adjoin")
addr(c_b, "Appendix 1 Part B cl 5.2.5 C5", "joondalup.sightline_structure_height_max_m", "lte", 0.75, "m",
     "C5 " + SIGHT_Q + ": a driveway that intersects a street, right-of-way or communal street; a right-of-way or communal street that intersects a public street; and two streets that intersect.",
     table_reference="Appendix 1 cl 5.2.5 C5",
     condition={"within_m_of_intersection": 1.5, "replaces": "R-Codes Vol 1 Part B cl 5.2.5 C5"})
addr(c_b, "Appendix 1 Part B cl 5.2.5 C5", "joondalup.sightline_pillar_height_max_m", "lte", 1.8, "m",
     "C5 " + SIGHT_Q + " (solid pillars not more than 1.8m above natural ground level).",
     table_reference="Appendix 1 cl 5.2.5 C5",
     condition={"element": "solid pillars", "measured_from": "natural ground level"})
EXC_Q = ("Excavation or filling between the street and building, or within the front setback area, whichever "
         "distance is lesser, shall not exceed 1 m from natural ground level, except where necessary to "
         "provide for pedestrian or vehicle access, drainage works or natural light for a dwelling.")
addr(c_b, "Appendix 1 Part B cl 5.3.7 C7.1", "joondalup.excavation_fill_front_max_m", "lte", 1, "m",
     "C7.1 " + EXC_Q,
     table_reference="Appendix 1 cl 5.3.7 C7.1",
     condition={"location": "between street and building or front setback area",
                "measured_from": "natural ground level",
                "replaces": "R-Codes Vol 1 Part B cl 5.3.7 C7.1"})
addr(c_b, "Appendix 1 Part B cl 5.2.1 C1.5", "joondalup.garage_secondary_street_setback_min_m.hdd", "gte", 4.5, "m",
     "C1.5 Garages and carports setback 4.5 m to the secondary street where an existing or planned footpath is located in the adjacent verge area.",
     table_reference="Appendix 1 cl 5.2.1 C1.5",
     condition={"application": "Higher dual density code", "requires": "existing or planned footpath in adjacent verge"})
addr(c_b, "Appendix 1 Part B cl 5.2.1 C1.6", "joondalup.garage_row_primary_setback_min_m.hdd", "gte", 5, "m",
     "C1.6 Garages and carports abutting a right of way which acts as the primary street for the lot, setback 5 m from the street boundary.",
     table_reference="Appendix 1 cl 5.2.1 C1.6",
     condition={"application": "Higher dual density code", "right_of_way_role": "acts as primary street"})
addr(c_b, "Appendix 1 Part B cl 5.3.2 C2.3", "joondalup.street_tree_frontage_m_per_tree_max", "lte", 9, "m frontage per tree",
     "C2.3 Street verge(s) adjacent to the lot(s) shall be landscaped in accordance with any street verge guidelines published by the City of Joondalup and shall include a minimum of one street tree for every 9 m of lot frontage width (in addition to the trees required at C2.1 and C2.2). Note: Each retained existing street tree satisfies the requirement for one street tree in C2.3.",
     table_reference="Appendix 1 cl 5.3.2 C2.3",
     condition={"application": "Higher dual density code", "location": "street verge adjacent to lot"})
SOLAR_Q = ("For residential areas with a dual code and the higher code is applied, where a development site "
           "shares its southern boundary with any other adjoining property, its shadow cast at midday 21 June "
           "shall not exceed the following limits")
addr(c_b, "Appendix 1 Part B cl 5.4.2 C2.1", "joondalup.overshadowing_max_pct.adj_r60_plus", "lte", 40, "%",
     f"C2.1 {SOLAR_Q}: i. On adjoining sites coded R60 or greater — 40% of the site area.",
     table_reference="Appendix 1 cl 5.4.2 C2.1",
     condition={"adjoining_code": "R60+", "at": "midday 21 June", "of": "adjoining site area",
                "application": "Higher dual density code", "source": "LPS3 cl 26(6)"})
addr(c_b, "Appendix 1 Part B cl 5.4.2 C2.1", "joondalup.overshadowing_max_pct.adj_r30_r40", "lte", 35, "%",
     f"C2.1 {SOLAR_Q}: ii. On adjoining sites coded R30 to R40 inclusive — 35% of the site area.",
     table_reference="Appendix 1 cl 5.4.2 C2.1",
     condition={"adjoining_code": "R30-R40", "at": "midday 21 June", "of": "adjoining site area",
                "application": "Higher dual density code", "source": "LPS3 cl 26(6)"})
addr(c_b, "Appendix 1 Part B cl 5.4.2 C2.1", "joondalup.overshadowing_max_pct.adj_r25_lower", "lte", 25, "%",
     f"C2.1 {SOLAR_Q}: iii. On adjoining sites coded R25 and lower — 25% of the site area.",
     table_reference="Appendix 1 cl 5.4.2 C2.1",
     condition={"adjoining_code": "R25 and lower", "at": "midday 21 June", "of": "adjoining site area",
                "application": "Higher dual density code", "source": "LPS3 cl 26(6)"})
addr(c_b, "Appendix 1 Part B cl 5.4.2 C2.1", "joondalup.solar_collector_access_min_hours", "gte", 4, "hours/day",
     "C2.1 v. Buildings are oriented to maintain 4 hours per day solar access on 21 June for existing solar collectors on neighbouring sites.",
     table_reference="Appendix 1 cl 5.4.2 C2.1",
     condition={"at": "21 June", "for": "existing solar collectors on neighbouring sites"})

# Appendix 2 Part C - boundary walls (C3.4.4)
BWZ = {"application": "General residential (Part C)"}
for band, codes in (("r30_r35", ["R30", "R35"]), ("r40", ["R40"]), ("r50_r80", ["R50", "R60", "R80"])):
    addr(c_c, "Appendix 2 Part C cl 3.4 C3.4.4", f"joondalup.boundary_wall_height_max_m.{band}", "lte", 3.5, "m",
         f"C3.4.4 Boundary walls table — {band.replace('_', '-').upper()}: Maximum boundary wall height 3.5 m.",
         table_reference="Appendix 2 cl 3.4 C3.4.4 table",
         r_codes=codes, condition=dict(BWZ))
addr(c_c, "Appendix 2 Part C cl 3.4 C3.4.4", "joondalup.boundary_wall_length_max_fraction.r30_r35", "lte", 0.667, "x lot boundary length",
     "R30 – R35: Maximum two-thirds the length of the lot boundary the wall abuts, measured from behind the street setback line. Applicable up to two lot boundaries.",
     table_reference="Appendix 2 cl 3.4 C3.4.4 table",
     r_codes=["R30", "R35"], condition={"max_boundaries": 2, "measured_from": "behind street setback line"})
addr(c_c, "Appendix 2 Part C cl 3.4 C3.4.4", "joondalup.boundary_wall_length_max_fraction.r40", "lte", 0.667, "x lot boundary length",
     "R40: Maximum two-thirds the length of the lot boundary the wall abuts, measured from behind the street setback line. Applicable to all lot boundaries.",
     table_reference="Appendix 2 cl 3.4 C3.4.4 table",
     r_codes=["R40"], condition={"applicable_boundaries": "all"})
addr(c_c, "Appendix 2 Part C cl 3.4 C3.4.4", "joondalup.boundary_wall_length_max_m.r50_r80", "lte", 14, "m",
     "R50 – R80: Maximum 14 m length, at which point the wall is to be set back a minimum of 3 m measured from the lot boundary for a minimum length of 3 m.",
     table_reference="Appendix 2 cl 3.4 C3.4.4 table",
     r_codes=["R50", "R60", "R80"],
     condition={"then": "wall set back min 3m from lot boundary for min length 3m",
                "cumulative_max": "two-thirds lot boundary where frontage > 8.5m"})
addr(c_c, "Appendix 2 Part C cl 3.4 C3.4.4", "joondalup.boundary_wall_break_setback_min_m.r50_r80", "gte", 3, "m",
     "R50 – R80: Maximum 14 m length, at which point the wall is to be set back a minimum of 3 m measured from the lot boundary for a minimum length of 3 m.",
     table_reference="Appendix 2 cl 3.4 C3.4.4 table",
     r_codes=["R50", "R60", "R80"],
     condition={"after_continuous_length_m": 14, "min_break_length_m": 3})
addr(c_c, "Appendix 2 Part C cl 3.3 C3.3.4", "joondalup.garage_primary_street_setback_min_m.r30_plus", "gte", 4.5, "m",
     "C3.3.4 Garages are setback from the primary street boundary in accordance with the following: R30 and above — 4.5 m.",
     table_reference="Appendix 2 cl 3.3 C3.3.4",
     r_codes=["R30", "R35", "R40", "R50", "R60", "R80"],
     condition={"application": "Higher dual density code"})
addr(c_c, "Appendix 2 Part C cl 3.3 C3.3.6", "joondalup.garage_secondary_street_setback_min_m.r30_plus", "gte", 4.5, "m",
     "C3.3.6 i. Setback 4.5 m from the street boundary where an existing or planned footpath is located in the verge area immediately adjacent.",
     table_reference="Appendix 2 cl 3.3 C3.3.6",
     r_codes=["R30", "R35", "R40", "R50", "R60", "R80"],
     condition={"application": "Higher dual density code", "requires": "existing or planned footpath in verge"})
addr(c_c, "Appendix 2 Part C cl 3.3 C3.3.6", "joondalup.garage_row_primary_setback_min_m.r30_plus", "gte", 5, "m",
     "C3.3.6 i. Setback 5 m from the street boundary where abutting a right of way which acts as the primary street for the lot.",
     table_reference="Appendix 2 cl 3.3 C3.3.6",
     r_codes=["R30", "R35", "R40", "R50", "R60", "R80"],
     condition={"application": "Higher dual density code", "right_of_way_role": "acts as primary street"})
addr(c_c, "Appendix 2 Part C cl 3.5 C3.5.1", "joondalup.excavation_fill_front_max_m.part_c", "lte", 1, "m",
     "C3.5.1 " + EXC_Q,
     table_reference="Appendix 2 cl 3.5 C3.5.1",
     condition={"location": "between street and building or front setback area",
                "replaces": "R-Codes Vol 1 Part C cl 3.5 C3.5.1"})
addr(c_c, "Appendix 2 Part C cl 3.7 C3.7.7", "joondalup.sightline_structure_height_max_m.part_c", "lte", 0.75, "m",
     "C3.7.7 Walls, fences and other structures truncated, reduced in height or visually permeable above 0.75m of natural ground level (with solid pillars not more than 1.8m above natural ground level in accordance with clause 3.6 C3.6.8) within 1.5m of where walls, fences or other structures adjoin.",
     table_reference="Appendix 2 cl 3.7 C3.7.7",
     condition={"within_m_of_intersection": 1.5, "replaces": "R-Codes Vol 1 Part C cl 3.7 C3.7.7"})
addr(c_c, "Appendix 2 Part C cl 1.2 C1.2.9", "joondalup.street_tree_frontage_m_per_tree_max.part_c", "lte", 9, "m frontage per tree",
     "C1.2.9 Street verge(s) adjacent to the lot(s) shall be landscaped in accordance with any street verge guidelines published by the City of Joondalup and shall include one street tree for every 9m of lot frontage width (in addition to the trees required at C1.2.4 and C1.2.5).",
     table_reference="Appendix 2 cl 1.2 C1.2.9",
     condition={"application": "Higher dual density code", "location": "street verge adjacent to lot"})

# Appendix 3 Part D - site area (dual coding)
addr(c_d, "Appendix 3 Part D cl 1.1 C1.1.9", "joondalup.min_frontage_m.dual_code_single_grouped", "gte", 9, "m",
     "C1.1.9 In residential areas where dual coding applies, site areas under the higher coding may be applied subject to the following: i. Development of single and grouped dwellings which complies with a minimum frontage of 9 m at the primary street setback.",
     table_reference="Appendix 3 cl 1.1 C1.1.9",
     condition={"application": "Higher dual density code", "dwelling": "single and grouped dwellings",
                "source": "LPS3 cl 26(5)"})
addr(c_d, "Appendix 3 Part D cl 1.1 C1.1.9", "joondalup.min_frontage_m.dual_code_corner_grouped", "gte", 6, "m",
     "C1.1.9 ii. Development of grouped dwellings on corner lots with frontage to two streets, with rear common property access, which complies with a minimum frontage of 6 m.",
     table_reference="Appendix 3 cl 1.1 C1.1.9",
     condition={"application": "Higher dual density code", "lot_type": "corner, two street frontages, rear common property access"})
addr(c_d, "Appendix 3 Part D cl 1.1 C1.1.10", "joondalup.multiple_dwelling_min_site_width_m", "gte", 20, "m",
     "C1.1.10 i. Development of multiple dwellings which complies with a minimum site width street boundary of 20 m.",
     table_reference="Appendix 3 cl 1.1 C1.1.10",
     condition={"application": "Higher dual density code", "dwelling": "multiple dwellings",
                "source": "LPS3 cl 26(7)"})

# ============ HOA LPP ============
c_hoa = ensure_clause(SV_HOA, "joondalup_hoa_sections",
                      "Joondalup Development in Housing Opportunity Areas LPP (sections 1-19)",
                      "Urban design, building height, street setbacks, side/rear setbacks, "
                      "parking location, crossovers, tree canopy and deep soil, ceiling "
                      "heights, natural ventilation.")
H = "Development in Housing Opportunity Areas LPP"
addh(c_hoa, H + " s1.3", "joondalup.blank_walls_max_pct_frontage.hoa", "lte", 20, "%",
     "1.3. Blank walls, vehicle access and building services (e.g. bin store, booster hydrant) shall not exceed 20% of the total lot frontage to the public realm, except for development with two street frontages, where no blank walls will be permitted to either street frontage.",
     table_reference="HOA s1.3", condition={"of": "total lot frontage to public realm"})
for code, primary in (("R20/R25", 4.0), ("R20/R30", 4.0), ("R20/R40", 4.0), ("R20/R60", 2.0)):
    ckey = code.replace("/", "_").lower()
    addh(c_hoa, H + " s4.1", f"joondalup.building_height_max_storeys.hoa.{ckey}", "lte", 2, "storeys",
         f"4.1 Building height — {code}: Maximum 2 storeys. Note: Refer Table 2.2, Figure 2.2a, Figure 2.2b of SPP7.3 — Volume 2 for interpretation of indicative overall height in metres.",
         table_reference="HOA s4.1", condition={"dual_code": code},
         check_type="max_storeys")
    addh(c_hoa, H + " s5.1", f"joondalup.primary_street_setback_min_m.hoa.{ckey}", "gte", primary, "m",
         f"5.1. Street setbacks — {code}: Primary street {primary} metres. Note: The setbacks listed above are minimum setbacks. Averaging is not permitted.",
         table_reference="HOA s5.1", condition={"dual_code": code, "averaging": "not permitted"})
addh(c_hoa, H + " s5.1", "joondalup.secondary_street_setback_min_m.hoa", "gte", 2.0, "m",
     "5.1. Street setbacks — Secondary street: 2.0 metres (R20/R25, R20/R30, R20/R40, R20/R60). Note: The setbacks listed above are minimum setbacks. Averaging is not permitted.",
     table_reference="HOA s5.1", condition={"dual_codes": ["R20/R25", "R20/R30", "R20/R40", "R20/R60"]})
addh(c_hoa, H + " s5.2", "joondalup.porch_projection_max_m.hoa", "lte", 1.0, "m",
     "5.2. A porch, balcony, verandah, chimney or equivalent may (subject to the Building Code of Australia) project not more than 1.0 metre into the street setback area. Projections up to 1.0 metre shall not exceed 50 per cent of the building façade as viewed from the street.",
     table_reference="HOA s5.2")
addh(c_hoa, H + " s5.2", "joondalup.porch_projection_max_pct_facade.hoa", "lte", 50, "%",
     "5.2. A porch, balcony, verandah, chimney or equivalent may (subject to the Building Code of Australia) project not more than 1.0 metre into the street setback area. Projections up to 1.0 metre shall not exceed 50 per cent of the building façade as viewed from the street.",
     table_reference="HOA s5.2", condition={"of": "building façade as viewed from street"})
addh(c_hoa, H + " s6.1", "joondalup.side_setback_ground_floor_min_m.multiple_dwelling", "gte", 2.0, "m",
     "6.1. A minimum side lot boundary setback of: a. 2.0 metres to the ground floor; and b. 3.0 metres to the upper floor.",
     table_reference="HOA s6.1", condition={"storey": "ground floor", "dwelling": "multiple dwelling"})
addh(c_hoa, H + " s6.1", "joondalup.side_setback_upper_floor_min_m.multiple_dwelling", "gte", 3.0, "m",
     "6.1. A minimum side lot boundary setback of: a. 2.0 metres to the ground floor; and b. 3.0 metres to the upper floor.",
     table_reference="HOA s6.1", condition={"storey": "upper floor", "dwelling": "multiple dwelling"})
addh(c_hoa, H + " s6.2", "joondalup.boundary_wall_length_max_m.hoa", "lte", 9.0, "m",
     "6.2. A wall may be built up to one side lot boundary behind the street setback within the following limits: a. A maximum length of 9.0 metres; b. A maximum height of 3.5 metres from natural ground level; and, c. An average height of 3.0 metres from natural ground level.",
     table_reference="HOA s6.2")
addh(c_hoa, H + " s6.2", "joondalup.boundary_wall_height_max_m.hoa", "lte", 3.5, "m",
     "6.2. A wall may be built up to one side lot boundary behind the street setback within the following limits: a. A maximum length of 9.0 metres; b. A maximum height of 3.5 metres from natural ground level; and, c. An average height of 3.0 metres from natural ground level.",
     table_reference="HOA s6.2", condition={"measured_from": "natural ground level"})
addh(c_hoa, H + " s6.2", "joondalup.boundary_wall_avg_height_max_m.hoa", "lte", 3.0, "m",
     "6.2. A wall may be built up to one side lot boundary behind the street setback within the following limits: a. A maximum length of 9.0 metres; b. A maximum height of 3.5 metres from natural ground level; and, c. An average height of 3.0 metres from natural ground level.",
     table_reference="HOA s6.2", condition={"measured_from": "natural ground level", "metric": "average"})
addh(c_hoa, H + " s7.1", "joondalup.resident_parking_setback_min_m.hoa", "gte", 5.5, "m",
     "7.1. Resident parking, including a carport, garage or other hardstand area, shall be setback a minimum of 5.5 metres from the public road boundary.",
     table_reference="HOA s7.1")
addh(c_hoa, H + " s7.2", "joondalup.parking_manoeuvring_space_min_m.hoa", "gte", 6, "m",
     "7.2. Resident parking up to a boundary abutting a private street or right-of-way which is not the primary or secondary street for the dwelling, shall be provided with a manoeuvring space of at least six metres, located immediately in front of the parking and permanently available.",
     table_reference="HOA s7.2",
     condition={"location": "abutting private street or ROW (not primary/secondary street)"})
addh(c_hoa, H + " s7.4", "joondalup.garage_width_max_pct_frontage.hoa", "lte", 50, "%",
     "7.4. The width of an enclosed garage and its supporting structures facing the primary street shall not occupy more than 50% of the frontage at the setback line as viewed from the street. This may be increased to 60% where an upper floor habitable room with a major opening or balcony extends for the full width of the garage and the entrance to the dwelling is clearly visible from the primary street.",
     table_reference="HOA s7.4", condition={"at": "setback line"})
addh(c_hoa, H + " s7.4", "joondalup.garage_width_max_pct_frontage_with_upper_room.hoa", "lte", 60, "%",
     "7.4. ... This may be increased to 60% where an upper floor habitable room with a major opening or balcony extends for the full width of the garage and the entrance to the dwelling is clearly visible from the primary street.",
     table_reference="HOA s7.4",
     condition={"requires": "upper floor habitable room/balcony full width of garage; entrance visible from street"})
addh(c_hoa, H + " s9.1", "joondalup.location_a_train_walkable_catchment_m.hoa", "lte", 800, "m",
     "9.1. Location A parking requirements: Resident parking ratios shall be in accordance with Location A (SPP7.3) where: a. Development is within an 800 metre walkable catchment of a train station within or adjacent to a Housing Opportunity Area. b. Development is within a 200 metres walkable catchment of a high frequency bus stop.",
     table_reference="HOA s9.1", condition={"of": "train station within/adjacent to HOA",
                                            "amends": "R-Codes Location A definition"})
addh(c_hoa, H + " s9.1", "joondalup.location_a_hf_bus_walkable_catchment_m.hoa", "lte", 200, "m",
     "9.1. Location A parking requirements: ... b. Development is within a 200 metres walkable catchment of a high frequency bus stop.",
     table_reference="HOA s9.1", condition={"of": "high frequency bus stop",
                                            "amends": "R-Codes Location A definition"})
addh(c_hoa, H + " s10.1", "joondalup.crossover_width_max_m.yield_over_10", "lte", 6.0, "m",
     "10.1. A crossover shall be limited to a maximum width as detailed below: a. Where the proposed development yield exceeds 10 dwellings, then a maximum crossover width of 6.0 metres is permitted.",
     table_reference="HOA s10.1", condition={"development_yield_gt_dwellings": 10})
addh(c_hoa, H + " s10.1", "joondalup.crossover_width_max_m.yield_lte_10", "lte", 4.5, "m",
     "10.1. ... b. Where the proposed development yield does not exceed 10 dwellings, then a maximum crossover width of 4.5 metres is permitted, except where required to facilitate access to communal onsite visitor parking or onsite bin collection where a maximum crossover width of 6.0 metres is permitted.",
     table_reference="HOA s10.1", condition={"development_yield_lte_dwellings": 10,
                                             "exception_6m": "communal visitor parking or bin collection access"})
addh(c_hoa, H + " s11.1", "joondalup.landscape_area_min_pct.hoa", "gte", 20, "%",
     "11.1 The minimum landscape area is to be calculated as 20% of the site area.",
     table_reference="HOA s11.1", condition={"of": "site area",
                                             "replaces": "R-Codes Vol 1 cl 5.3.2 C2 / Vol 2 El 3.3"})
addh(c_hoa, H + " s11.4", "joondalup.permeable_paving_max_pct_landscape_area.hoa", "lte", 30, "%",
     "11.4 Permeable paving or decking within a landscape area is permitted provided it does not exceed 30% of the landscape area and will not inhibit the planting and growth of adjacent trees in the landscape area.",
     table_reference="HOA s11.4", condition={"of": "landscape area"})
addh(c_hoa, H + " s11.5", "joondalup.landscape_area_min_dimension_m.hoa", "gte", 1.5, "m",
     "11.5 The minimum dimension of any landscape area shall be 1.5 metres.",
     table_reference="HOA s11.5")
addh(c_hoa, H + " s11.6", "joondalup.front_setback_landscape_min_pct.hoa", "gte", 50, "%",
     "11.6 A minimum of 50% of the area between the front of the dwelling and the street lot boundary (front setback area) shall be landscape area.",
     table_reference="HOA s11.6", condition={"of": "front setback area"})
addh(c_hoa, H + " s13.1", "joondalup.small_tree_m2_landscape_per_tree_max.hoa", "lte", 20.0, "m2 landscape area per tree",
     "13.1. The minimum number of trees to be provided onsite (with shade producing canopies) within deep soil areas shall be determined by the landscape area as follows: 1 small tree for every 20.0 square metres of landscape area.",
     table_reference="HOA s13.1 trees table",
     condition={"tree_size": "small", "applies": "all lot area bands (see policy table)"})
addh(c_hoa, H + " s13.1", "joondalup.medium_tree_m2_landscape_per_tree_max.hoa", "lte", 60.0, "m2 landscape area per tree",
     "13.1. ... 1 medium tree for every 60.0 square metres of landscape area.",
     table_reference="HOA s13.1 trees table",
     condition={"tree_size": "medium", "applies": "all lot area bands (see policy table)"})
addh(c_hoa, H + " s13.1", "joondalup.large_tree_m2_landscape_per_tree_max.hoa", "lte", 100.0, "m2 landscape area per tree",
     "13.1. ... 1 large tree for every 100.0 square metres of landscape area.",
     table_reference="HOA s13.1 trees table",
     condition={"tree_size": "large", "applies": "all lot area bands (see policy table)"})
addh(c_hoa, H + " s13.2", "joondalup.street_tree_frontage_m_per_tree_max.hoa", "lte", 10.0, "m frontage per tree",
     "13.2. The verge(s) adjacent to the lot(s) shall be landscaped to the specifications and satisfaction of the City and shall include one street tree for every 10.0 metres of lot frontage width.",
     table_reference="HOA s13.2", condition={"location": "verge adjacent to lot"})
addh(c_hoa, H + " s14.1", "joondalup.tree_retention_credit_m2.medium", "eq", 75, "m2 landscape area",
     "14.1. The landscape area specified in Clause 14 can be reduced where existing medium and large trees (as per Table 3.3b of SPP7.3 — Volume 2) are retained onsite, equivalent to the following: a. Retention of a mature medium tree is equivalent to 75 square metres landscape area.",
     table_reference="HOA s14.1", condition={"tree_size": "mature medium"})
addh(c_hoa, H + " s14.1", "joondalup.tree_retention_credit_m2.large", "eq", 125, "m2 landscape area",
     "14.1. ... b. Retention of a mature large tree is equivalent to 125 square metres landscape area.",
     table_reference="HOA s14.1", condition={"tree_size": "mature large"})
addh(c_hoa, H + " s16.2", "joondalup.ceiling_height_min_m.habitable", "gte", 2.7, "m",
     "16.2. Dwellings shall have a minimum ceiling height of 2.7 metres in habitable rooms and 2.4 metres in non-habitable spaces.",
     table_reference="HOA s16.2", condition={"room": "habitable"})
addh(c_hoa, H + " s16.2", "joondalup.ceiling_height_min_m.non_habitable", "gte", 2.4, "m",
     "16.2. Dwellings shall have a minimum ceiling height of 2.7 metres in habitable rooms and 2.4 metres in non-habitable spaces.",
     table_reference="HOA s16.2", condition={"room": "non-habitable"})
addh(c_hoa, H + " s18.2", "joondalup.window_glass_area_min_pct_floor_area.hoa", "gte", 15, "%",
     "18.2. Habitable rooms shall have a window in an external wall which: a. Has a minimum glass area not less than 15% of the floor area of the room; b. Comprise a minimum of 50% clear glazing; and, c. Is openable for 50% the size of the window.",
     table_reference="HOA s18.2", condition={"of": "floor area of room"})
addh(c_hoa, H + " s18.2", "joondalup.window_clear_glazing_min_pct.hoa", "gte", 50, "%",
     "18.2. Habitable rooms shall have a window in an external wall which: ... b. Comprise a minimum of 50% clear glazing.",
     table_reference="HOA s18.2")
addh(c_hoa, H + " s18.2", "joondalup.window_openable_min_pct.hoa", "gte", 50, "%",
     "18.2. Habitable rooms shall have a window in an external wall which: ... c. Is openable for 50% the size of the window.",
     table_reference="HOA s18.2", condition={"of": "window size"})

WARN_RD = [
    "CONFLICTS WITH R-CODE DEFAULTS (adopted replacements): App 1 replaces Part B cl 5.2.5 C5, 5.3.7 C7.1, 5.4.2 C2.1-C2.2; adds 5.2.1 C1.5-C1.6, 5.3.1 C1.3, 5.3.2 C2.3. App 2 replaces Part C cl 3.4 C3.4.4, 3.5 C3.5.1, 3.7 C3.7.7, 3.3 C3.3.4/C3.3.6, 3.9 C3.9.1-C3.9.3; adds 1.1 C1.1.5, 1.2 C1.2.9. App 3 adds Part D cl 1.1 C1.1.9-C1.1.10.",
    "Solar access (overshadowing) provisions restate LPS3 cl 26(6) 'for completeness' - policy notes LPS3 is the operative instrument; encoded once from Part B Appendix 1 (identical text in Part C cl 3.9).",
    "Sightline and excavation replacements are identical in Appendices 1 and 2; encoded once per Part (Part B primary, Part C duplicates keyed .part_c).",
]
WARN_HOA = [
    "CONFLICTS WITH R-CODE DEFAULTS (adopted replacements): s4.1 replaces Vol 1 cl 5.1.6 C6 / Vol 2 El 2.2.1 (2 storeys max in HOAs); s5 amends cl 5.1.2 (no setback averaging); s6 amends cl 5.1.3; s7 replaces cl 5.2.1 C1.1-C1.5 and 5.2.2 C2; s9 amends cl 5.3.3 Location A definition; s11-14 replace cl 5.3.2 C2 / Vol 2 El 3.3 (20% landscape area replaces open space/tree requirements).",
    "HOA street setbacks prohibit averaging (explicit policy note) - overrides R-Codes cl 5.1.2 C2.3 averaging.",
    "Tree ratios in s13.1 vary by lot-area band; encoded as per-tree landscape-area ratios (small 20m2, medium 60m2, large 100m2) which apply across bands; see policy table for band-specific combinations.",
    "Sections 2/3 (frontage 9m/6m; multiple dwelling site width 20m) restate LPS3 cl 26(5)/26(7); encoded from the Residential Development LPP Appendix 3 (same values) and not duplicated here.",
]
write_report("/app/reports/phase6_joondalup_residential_development_extraction.json",
             SV_RD, PDF_RD, "Appendices 1-3 (Parts B, C, D)",
             ["Appendix 1 Part B clauses", "Appendix 2 Part C clauses + C3.4.4 boundary wall table",
              "Appendix 3 Part D cl 1.1"],
             RD, warnings=WARN_RD)
write_report("/app/reports/phase6_joondalup_hoa_extraction.json",
             SV_HOA, PDF_HOA, "Sections 1-19",
             ["s1 urban design", "s4 height table", "s5 street setback table", "s6 side/rear",
              "s7 parking location", "s9-10 access", "s11-15 tree canopy/deep soil tables",
              "s16-18 dwelling layout"],
             HOA, warnings=WARN_HOA)
print("Joondalup candidates:", len(RD), "resdev +", len(HOA), "hoa")
