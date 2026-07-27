"""Phase 6: City of Stirling LPP Manual rule candidates.

Source version 89c21932-116c-4e7c-94d1-db8cd64b52cb (Policy Manual all sections).
Sections used: 6.6 Landscaping, 6.7 Parking and Access, 6.10 Renewable Energy
Systems, 6.11 Trees and Development.
NOTE: Section 2 policies 2.6 Residential Building Heights, 2.7 Streetscapes,
2.8 Multiple Dwellings, 2.9 Single Houses and Grouped Dwellings and 6.2 Bicycle
Parking are REVOKED in this manual and were not extracted.
"""
import sys

sys.path.insert(0, "/app/scripts/phase6")
from lpp_lib import cand, ensure_clause, write_report

COUNCIL = "City of Stirling"
SV = "89c21932-116c-4e7c-94d1-db8cd64b52cb"
PDF = "/app/data/raw-sources/councils/stirling/lpp_policy_manual_all_sections.pdf"

C = []

def clause(key, title, text):
    return ensure_clause(SV, key, title, text)

def add(clause_id, section, *a, **k):
    k.setdefault("instrument_section", section)
    C.append(cand(*a, clause_id=clause_id, sv_id=SV, council_scope=COUNCIL, **k))

# ================= 6.6 LANDSCAPING =================
c66 = clause("lpp66_landscaping", "Stirling LPP 6.6 Landscaping",
             "Development provisions supplementary to SPP 7.3 R-Codes; applies to all "
             "non-residential development, grouped dwellings 5+, all multiple dwellings.")
S = "LPP 6.6 Landscaping"
add(c66, S, "stirling.planting_area_min_width_mm", "gte", 500, "mm",
    "All individual planting areas, excluding those in or adjacent to public car parks, must have a minimum width in any direction of 500mm and a minimum plantable area of two square metres.",
    table_reference="LPP 6.6 Landscaping Areas")
add(c66, S, "stirling.planting_area_min_m2", "gte", 2, "m2",
    "All individual planting areas, excluding those in or adjacent to public car parks, must have a minimum width in any direction of 500mm and a minimum plantable area of two square metres.",
    table_reference="LPP 6.6 Landscaping Areas")
add(c66, S, "stirling.mulch_depth_min_mm", "gte", 75, "mm",
    "A minimum depth of 75mm of mulch (gravel not permitted) is to be applied to all landscaping beds.",
    table_reference="LPP 6.6 Reticulation and Mulching")
add(c66, S, "stirling.carpark_bays_per_tree_max.residential", "lte", 4, "bays_per_tree",
    "A minimum of 1 tree per 4 bays for residential development and 1 tree per 6 bays for non-residetial development (Minimum 45 litre container for exotics and 11 litre container for natives) is required in open parking areas.",
    table_reference="LPP 6.6 Parking Areas",
    condition={"container_min_litres": {"exotics": 45, "natives": 11}})
add(c66, S, "stirling.carpark_bays_per_tree_max.non_residential", "lte", 6, "bays_per_tree",
    "A minimum of 1 tree per 4 bays for residential development and 1 tree per 6 bays for non-residetial development (Minimum 45 litre container for exotics and 11 litre container for natives) is required in open parking areas.",
    table_reference="LPP 6.6 Parking Areas")
add(c66, S, "stirling.commercial_landscaping_min_pct", "gte", 10, "%",
    "Development applications for commercial development must contain a minimum of 10% landscaping of the total site area. This must include 'soft' landscaped buffers, where setbacks are provided, to adjacent properties with a minimum width of 1.5m.",
    table_reference="LPP 6.6 Commercial provisions", condition={"of": "total site area"})
add(c66, S, "stirling.commercial_landscape_buffer_width_min_m", "gte", 1.5, "m",
    "Development applications for commercial development must contain a minimum of 10% landscaping of the total site area. This must include 'soft' landscaped buffers, where setbacks are provided, to adjacent properties with a minimum width of 1.5m.",
    table_reference="LPP 6.6 Commercial provisions")
add(c66, S, "stirling.industrial_street_landscaping_width_min_m", "gte", 1.5, "m",
    "In all industrial precincts (except the Balcatta Precinct), a landscaped area not less than 1.5m wide shall be provided adjoining all street boundaries, primarily as planting bed.",
    table_reference="LPP 6.6 Industrial provisions",
    condition={"excludes": "Balcatta Precinct"})
add(c66, S, "stirling.balcatta_mixed_business_landscaping_min_pct", "gte", 16.67, "%",
    "In the Balcatta Precinct and the Mixed Business zone, a minimum of one-sixth of the gross site area shall be landscaped.",
    table_reference="LPP 6.6 Industrial provisions",
    condition={"fraction": "one-sixth", "of": "gross site area"})
add(c66, S, "stirling.balcatta_primary_road_landscape_strip_min_m", "gte", 6, "m",
    "In the Balcatta Precinct and the Mixed Business zone, a minimum landscaping strip of 6m wide along a primary road and 1.5m wide along a secondary road shall be provided, primarily as planting bed.",
    table_reference="LPP 6.6 Industrial provisions", condition={"road": "primary"})
add(c66, S, "stirling.balcatta_secondary_road_landscape_strip_min_m", "gte", 1.5, "m",
    "In the Balcatta Precinct and the Mixed Business zone, a minimum landscaping strip of 6m wide along a primary road and 1.5m wide along a secondary road shall be provided, primarily as planting bed.",
    table_reference="LPP 6.6 Industrial provisions", condition={"road": "secondary"})

# ================= 6.7 PARKING AND ACCESS =================
c67 = clause("lpp67_parking_access", "Stirling LPP 6.7 Parking and Access",
             "Car parking ratios (Tables 1-3), motorcycle and bicycle ratios (Table 4), "
             "residential and non-residential parking design.")
S = "LPP 6.7 Parking and Access"
add(c67, S, "stirling.delivery_bay_min_count.non_residential", "gte", 1, "count",
    "In non-residential developments with over 500m² of GFA, a minimum of one bay shall be permanently set aside and marked for the exclusive use of delivery, service, and courier vehicles.",
    table_reference="LPP 6.7 cl 5.1.1", condition={"gfa_gt_m2": 500})
add(c67, S, "stirling.ev_charging_bays_min_count.non_residential", "gte", 3, "count",
    "In non-residential developments with over 500 car parking bays on-site, a minimum of three electric car charging bays shall be provided on the site.",
    table_reference="LPP 6.7 cl 5.1.3", condition={"carpark_bays_gt": 500})

# Table 1 activity centre ratios (m2 GFA per bay, lower = more parking)
T1 = [
    (12.5, ["NC5 Flynn Street", "NC10 Mirrabooka Village", "NC15 Stirling Village",
            "NC19 Woodlands Village", "LC8 Blythe Avenue", "LC9 Brighton Road",
            "LC10 Calais Road", "LC13 Central Avenue", "LC14 Coode Street",
            "LC18 Elsie Street", "LC25 Herdsman Hotel"]),
    (20, ["NC13 North Beach Plaza", "NC14 North Beach Drive"]),
    (25, ["DC1 Dianella Plaza", "DC2 Dog Swamp", "DC9 Stirling Central",
          "NC4 Fieldgate Square", "NC6 Glendalough", "NC8 Gwelup Plaza",
          "NC12 Nollamara", "NC18 Balga Plaza",
          "LC1-LC5, LC12, LC16, LC17, LC20, LC21, LC24, LC28-LC32, LC35, LC36, LC41, LC45-LC48 (see policy Table 1)"]),
    (33, ["NC2 Coode Street", "NC7 Grindleford Drive", "NC9 Lord Street",
          "NC11 Morris Place", "NC17 Walter Road West",
          "LC6, LC11, LC19, LC26, LC27, LC34, LC38-LC40 (see policy Table 1)"]),
    (50, ["NC1 Adair Parade", "LC22 Green Avenue", "LC23 Harrison Street",
          "LC37 Powell Street", "LC43 St Peters Place", "LC44 Sylvia Street"]),
]
for ratio, centres in T1:
    add(c67, S, f"stirling.activity_centre_parking_m2_gfa_per_bay_max.r{str(ratio).replace('.','_')}",
        "lte", ratio, "m2 GFA per bay",
        f"Table 1: Activity Centre Car Parking Ratios — 1 bay per {ratio}m² GFA for: {'; '.join(centres[:4])}{' et al.' if len(centres) > 4 else ''}.",
        table_reference="LPP 6.7 Table 1",
        condition={"activity_centres": centres, "applies": "non-residential development in identified centres"})
add(c67, S, "stirling.office_upper_floor_parking_m2_gfa_per_bay_max", "lte", 50, "m2 GFA per bay",
    "A parking ratio of 1 bay per 50m² GFA applies to Office land uses on upper floors as per Table 2. Reductions available in Table 3 are also applicable to Office land uses on upper floors.",
    table_reference="LPP 6.7 cl 5.2(e)", condition={"use": "Office", "floor": "upper floors"})

# Table 2 land use ratios
def ratio(key, value, unit, quote, cond=None):
    add(c67, S, key, "lte", value, unit, quote, table_reference="LPP 6.7 Table 2", condition=cond or {})

ratio("stirling.parking_m2_gfa_per_bay_max.industry", 50, "m2 GFA per bay",
      "Industry (Extractive, General, Light, Noxious, Service), Motor Vehicle Repair, Office, Warehouse — 1 bay per 50m2 of GFA.",
      {"uses": ["Industry - Extractive", "Industry - General", "Industry - Light", "Industry - Noxious",
                "Industry - Service", "Motor Vehicle Repair", "Office", "Warehouse"]})
ratio("stirling.parking_m2_public_floorspace_per_bay_max.fast_food_group", 10, "m2 public floorspace per bay",
      "Club Premises, Drive-Through Fast Food Outlet, Fast Food Outlet, Reception Centre, Restaurant — 1 bay per 10m2 of public floorspace.",
      {"uses": ["Club Premises", "Drive-Through Fast Food Outlet", "Fast Food Outlet", "Reception Centre", "Restaurant"]})
ratio("stirling.parking_m2_public_floorspace_per_bay_max.tavern_small_bar", 6, "m2 public floorspace per bay",
      "Small Bar, Tavern — 1 bay per 6m2 of public floorspace.",
      {"uses": ["Small Bar", "Tavern"]})
ratio("stirling.parking_m2_per_bay_max.alfresco", 14, "m2 alfresco floor area per bay",
      "Alfresco Area: 0 - 30m2 - no bays required; Greater than 30m2 - 1 bay per 14m2 of alfresco floor area. (Note - for example a 60m2 alfresco requires 4.2 bays.)",
      {"applies_when": "alfresco floor area > 30m2"})
ratio("stirling.parking_m2_display_per_bay_max.retail_display", 80, "m2 display area per bay",
      "Garden Centre, Motor Vehicle Boat or Caravan Sale, Hardware Showroom, Retail Establishment, Showroom — 1 bay per 80m2 of display area.",
      {"uses": ["Garden Centre", "Motor Vehicle Boat or Caravan Sale", "Hardware Showroom", "Retail Establishment", "Showroom"]})
ratio("stirling.parking_m2_gla_per_bay_max.shop_small", 12.5, "m2 GLA per bay",
      "Convenience Store, Personal Care Services, Personal Services, Shop: 5,000m2 or less - 1 bay per 12.5m2 of GLA.",
      {"gla_lte_m2": 5000})
ratio("stirling.parking_bays_base.shop_medium", 400, "bays",
      "Convenience Store, Personal Care Services, Personal Services, Shop: 5,001 - 10,000m2 - 400 bays; and 1 bay per 14.25m2 of GLA in excess of 5,000m2.",
      {"gfa_range_m2": [5001, 10000]})
ratio("stirling.parking_m2_gla_per_bay_max.shop_medium_excess", 14.25, "m2 GLA per bay",
      "Convenience Store, Personal Care Services, Personal Services, Shop: 5,001 - 10,000m2 - 400 bays; and 1 bay per 14.25m2 of GLA in excess of 5,000m2.",
      {"of": "GLA in excess of 5,000m2"})
ratio("stirling.parking_bays_base.shop_large", 750, "bays",
      "Convenience Store, Personal Care Services, Personal Services, Shop: 10,001m2 or more - 750 bays; and 1 bay per 16.5m2 of GLA in excess of 10,000m2.",
      {"gfa_gte_m2": 10001})
ratio("stirling.parking_m2_gla_per_bay_max.shop_large_excess", 16.5, "m2 GLA per bay",
      "Convenience Store, Personal Care Services, Personal Services, Shop: 10,001m2 or more - 750 bays; and 1 bay per 16.5m2 of GLA in excess of 10,000m2.",
      {"of": "GLA in excess of 10,000m2"})

add(c67, S, "stirling.parking_bays_min_per_bedroom.boarding_house", "gte", 1, "bay per bedroom",
    "Boarding House — 1 bay per separately lodged bedroom.",
    table_reference="LPP 6.7 Table 2", check_type="min_ratio")
add(c67, S, "stirling.parking_bays_min_per_bed.hostel", "gte", 1, "bay per bed",
    "Hostel — 1 bay per separately lodged bed in a shared room.",
    table_reference="LPP 6.7 Table 2", check_type="min_ratio")
add(c67, S, "stirling.parking_bays_min_per_staff.child_care", "gte", 1, "bay per staff member",
    "Child Care Premises — 1 bay per staff member in attendance; and 1 bay per 7 children in attendance.",
    table_reference="LPP 6.7 Table 2", check_type="min_ratio")
add(c67, S, "stirling.parking_children_per_bay_max.child_care", "lte", 7, "children per bay",
    "Child Care Premises — 1 bay per staff member in attendance; and 1 bay per 7 children in attendance.",
    table_reference="LPP 6.7 Table 2")
add(c67, S, "stirling.parking_bays_min_per_classroom.primary", "gte", 3.5, "bays per classroom",
    "Education Establishment Pre-primary / Primary - 1 bay per staff member in attendance; and 3.5 bays per classroom.",
    table_reference="LPP 6.7 Table 2", check_type="min_ratio")
add(c67, S, "stirling.parking_bays_min_per_classroom.secondary", "gte", 3, "bays per classroom",
    "Education Establishment Secondary - 1 bay per staff member in attendance; and 3 bays per classroom.",
    table_reference="LPP 6.7 Table 2", check_type="min_ratio")
add(c67, S, "stirling.parking_students_per_bay_max.tertiary", "lte", 3.5, "students per bay",
    "Education Establishment Tertiary / Technical - 1 bay per 3.5 students in attendance; and 1.25 bays per classroom.",
    table_reference="LPP 6.7 Table 2")
add(c67, S, "stirling.parking_bays_min_per_classroom.tertiary", "gte", 1.25, "bays per classroom",
    "Education Establishment Tertiary / Technical - 1 bay per 3.5 students in attendance; and 1.25 bays per classroom.",
    table_reference="LPP 6.7 Table 2", check_type="min_ratio")
add(c67, S, "stirling.parking_bays_min_per_practitioner.medical", "gte", 5, "bays per practitioner",
    "Consulting Rooms, Medical Centre, Veterinary Centre — 5 bays for each practitioner in attendance up to 2 practitioners; 2 additional bays for each practitioner in attendance in excess of 2 practitioners.",
    table_reference="LPP 6.7 Table 2", check_type="min_ratio",
    condition={"first_practitioners": 2})
add(c67, S, "stirling.parking_bays_min_per_practitioner_over2.medical", "gte", 2, "bays per practitioner",
    "Consulting Rooms, Medical Centre, Veterinary Centre — 5 bays for each practitioner in attendance up to 2 practitioners; 2 additional bays for each practitioner in attendance in excess of 2 practitioners.",
    table_reference="LPP 6.7 Table 2", check_type="min_ratio",
    condition={"practitioners_beyond": 2})
add(c67, S, "stirling.parking_patient_beds_per_bay_max.hospital", "lte", 2, "patient beds per bay",
    "Hospital, Nursing Home, Place of Worship, Public Amusement, Public Amusement (Cinema/Theatre), Recreation - Private — 1 bay per 2 patient beds; and 1 bay per staff member in attendance.",
    table_reference="LPP 6.7 Table 2")
add(c67, S, "stirling.parking_bays_min_per_staff.hospital", "gte", 1, "bay per staff member",
    "Hospital, Nursing Home, Place of Worship, Public Amusement, Public Amusement (Cinema/Theatre), Recreation - Private — 1 bay per 2 patient beds; and 1 bay per staff member in attendance.",
    table_reference="LPP 6.7 Table 2", check_type="min_ratio")
add(c67, S, "stirling.parking_persons_per_bay_max.public_amusement_cinema", "lte", 4, "persons per bay",
    "Public Amusement (Cinema/Theatre) — 1 bay per 4 persons in attendance.",
    table_reference="LPP 6.7 Table 2")
add(c67, S, "stirling.parking_bays_min_per_service_bay.service_station", "gte", 1, "bay per service bay",
    "Service Station — 1 bay per service bay provided: and any other specific uses are to be as per the relevant activity / use ratio.",
    table_reference="LPP 6.7 Table 2", check_type="min_ratio")

# Table 3 reductions
add(c67, S, "stirling.parking_reduction_max_cumulative_pct", "lte", 50, "%",
    "Reductions to calculations may be granted cumulatively, to a maximum cumulative reduction of 50% of the number of bays identified by Table 2.",
    table_reference="LPP 6.7 cl 5.4")
add(c67, S, "stirling.parking_reduction_pct.rail_800m", "lte", 10, "%",
    "Table 3: 10% reduction — the proposed development is within 800 metres of a rail station; or 20% within 400 metres of a rail station.",
    table_reference="LPP 6.7 Table 3", condition={"within_m_of_rail_station": 800})
add(c67, S, "stirling.parking_reduction_pct.rail_400m", "lte", 20, "%",
    "Table 3: 10% reduction — the proposed development is within 800 metres of a rail station; or 20% within 400 metres of a rail station.",
    table_reference="LPP 6.7 Table 3", condition={"within_m_of_rail_station": 400})
add(c67, S, "stirling.parking_reduction_pct.hf_bus_400m", "lte", 10, "%",
    "Table 3: 10% reduction — within 400 metres of a stop on a high frequency bus route or a bus station; or 15% within 200 metres.",
    table_reference="LPP 6.7 Table 3", condition={"within_m_of_hf_bus_stop": 400})
add(c67, S, "stirling.parking_reduction_pct.hf_bus_200m", "lte", 15, "%",
    "Table 3: 10% reduction — within 400 metres of a stop on a high frequency bus route or a bus station; or 15% within 200 metres.",
    table_reference="LPP 6.7 Table 3", condition={"within_m_of_hf_bus_stop": 200})
add(c67, S, "stirling.parking_reduction_pct.centre_or_heritage", "lte", 10, "%",
    "Table 3: 10% reduction — the proposed development is within a Regional Centre, District Centre or Neighbourhood Centre as detailed in the City's Local Planning Strategy; 10% where the building/place is listed on the City's Heritage List, Heritage Survey, or the State Register of Heritage Places.",
    table_reference="LPP 6.7 Table 3")
add(c67, S, "stirling.shared_parking_max_pct.minimal_overlap", "lte", 90, "%",
    "The City may consider the following shared parking arrangements: a) Up to 90% of the parking requirement specified, where there is minimal overlap (less than 30 minutes) in the operating times of uses; or b) Up to 50% of the parking requirement specified, where there is partial overlap (not more than 50 percent) in operating times of the uses.",
    table_reference="LPP 6.7 cl 5.5", condition={"overlap": "minimal (<30 minutes)"})
add(c67, S, "stirling.shared_parking_max_pct.partial_overlap", "lte", 50, "%",
    "The City may consider the following shared parking arrangements: a) Up to 90% of the parking requirement specified, where there is minimal overlap (less than 30 minutes) in the operating times of uses; or b) Up to 50% of the parking requirement specified, where there is partial overlap (not more than 50 percent) in operating times of the uses.",
    table_reference="LPP 6.7 cl 5.5", condition={"overlap": "partial (<=50%)"})

# Motorcycle / bicycle / design
add(c67, S, "stirling.motorcycle_parking_m2_gfa_per_space_max", "lte", 1000, "m2 GFA per space",
    "All non-residential components of developments with 500m² or more of gross floor area, where works increase the number of non-residential car parking bays provided on site, one motorcycle parking space shall be provided for every 1,000m2 of gross floor area.",
    table_reference="LPP 6.7 cl 6", condition={"gfa_gte_m2": 500})
add(c67, S, "stirling.bicycle_spaces_per_students.primary_secondary", "lte", 5, "students per space",
    "Table 4: Bicycle Parking Ratios — Educational Establishment Pre-primary / Primary: 1 space per 5 students (over year 4); Secondary: 1 space per 5 students; Tertiary / Technical: 1 space per 20 students.",
    table_reference="LPP 6.7 Table 4")
add(c67, S, "stirling.bicycle_spaces_per_students.tertiary", "lte", 20, "students per space",
    "Table 4: Bicycle Parking Ratios — Educational Establishment Pre-primary / Primary: 1 space per 5 students (over year 4); Secondary: 1 space per 5 students; Tertiary / Technical: 1 space per 20 students.",
    table_reference="LPP 6.7 Table 4")
add(c67, S, "stirling.bicycle_m2_gfa_per_space_max.retail_small", "lte", 150, "m2 GFA per space",
    "Table 4: Bicycle Parking Ratios — Retail (Convenience Store, Personal Care Services, Personal Services, Shop): 0 - 5000m² - 1 space per 150m² of GFA; 5000m² - 10,000m2 - 1 space per 175m² of GFA; 10,000m2 plus - 1 space per 200m² of GFA.",
    table_reference="LPP 6.7 Table 4", condition={"gfa_lte_m2": 5000})
add(c67, S, "stirling.bicycle_m2_gfa_per_space_max.retail_medium", "lte", 175, "m2 GFA per space",
    "Table 4: Bicycle Parking Ratios — Retail: 5000m² - 10,000m2 - 1 space per 175m² of GFA.",
    table_reference="LPP 6.7 Table 4", condition={"gfa_range_m2": [5000, 10000]})
add(c67, S, "stirling.bicycle_m2_gfa_per_space_max.retail_large", "lte", 200, "m2 GFA per space",
    "Table 4: Bicycle Parking Ratios — Retail: 10,000m2 plus - 1 space per 200m² of GFA.",
    table_reference="LPP 6.7 Table 4", condition={"gfa_gt_m2": 10000})
add(c67, S, "stirling.bicycle_m2_gfa_per_space_max.other_uses", "lte", 400, "m2 GFA per space",
    "Table 4: Bicycle Parking Ratios — All other uses: 1 space per 400m² of gross floor area (GFA).",
    table_reference="LPP 6.7 Table 4")
add(c67, S, "stirling.residential_manoeuvring_depth_min_m.single_garage", "gte", 6.0, "m",
    "As per the Australian Standards AS 2890.1, a manoeuvring depth of: a) 6.0 metres is required for single vehicle garages or multiple vehicles garages containing internal walls and/or obstructions between vehicles.",
    table_reference="LPP 6.7 cl 8.1")
add(c67, S, "stirling.residential_manoeuvring_depth_min_m.multi_garage_open", "gte", 5.8, "m",
    "As per the Australian Standards AS 2890.1, a manoeuvring depth of: b) 5.8 metres may be considered for multiple vehicle garages with no internal walls and/or obstructions between vehicles.",
    table_reference="LPP 6.7 cl 8.1")
add(c67, S, "stirling.driveway_taper_max", "lte", 0.2, "ratio (1:5)",
    "As per the Australian Standards AS 2890.1, to ensure vehicles can traverse a driveway: a) A maximum internal driveway taper of 1:5 is permitted.",
    table_reference="LPP 6.7 cl 8.2", extra_value={"raw_text": "maximum internal driveway taper of 1:5"})

# ================= 6.10 RENEWABLE ENERGY SYSTEMS =================
c610 = clause("lpp610_renewable_energy", "Stirling LPP 6.10 Renewable Energy Systems",
              "Wind energy system development standards (Table 1); solar energy systems "
              "permitted without development approval.")
S = "LPP 6.10 Renewable Energy Systems"
WQ = "TABLE 1 – Wind Energy System Development Standards"
add(c610, S, "stirling.wind_system_max_count_per_lot.residential", "lte", 1, "count",
    f"{WQ} — Residential zones, Small Wind Energy System Permitted: NUMBER OF SYSTEMS 1 per lot.",
    table_reference="LPP 6.10 Table 1", zones=["Residential"])
add(c610, S, "stirling.wind_nameplate_capacity_max_kw.small", "lte", 2, "kW",
    f"{WQ} — Small Wind Energy System: NAMEPLATE CAPACITY Max 2kW.",
    table_reference="LPP 6.10 Table 1", zones=["Residential"])
add(c610, S, "stirling.wind_pole_height_max_m.residential", "lte", 6, "m",
    f"{WQ} — Residential zones: HEIGHT Pole Mounted: Max 6m total height (above NGL).",
    table_reference="LPP 6.10 Table 1", zones=["Residential"],
    condition={"mounting": "pole", "measured_from": "natural ground level"})
add(c610, S, "stirling.wind_pole_height_max_m.non_residential", "lte", 10, "m",
    f"{WQ} — Mixed Use Zone and Non-Residential Zone: HEIGHT Pole Mounted: Max 10m total height (above NGL).",
    table_reference="LPP 6.10 Table 1", zones=["Mixed Use", "Non-Residential"],
    condition={"mounting": "pole", "measured_from": "natural ground level"})
add(c610, S, "stirling.wind_roof_mounted_height_above_roofline_max_m.residential", "lte", 3.0, "m",
    f"{WQ} — Residential zones: Roof Mounted: Maximum total height 3.0m above roofline.",
    table_reference="LPP 6.10 Table 1", zones=["Residential"],
    condition={"mounting": "roof"})
add(c610, S, "stirling.wind_roof_mounted_height_above_roofline_max_m.non_residential", "lte", 7.5, "m",
    f"{WQ} — Mixed Use Zone and Non-Residential Zone: Roof Mounted: Maximum 7.5m above roofline; Minimum 1m clearance from roofline.",
    table_reference="LPP 6.10 Table 1", zones=["Mixed Use", "Non-Residential"],
    condition={"mounting": "roof", "min_clearance_from_roofline_m": 1})
add(c610, S, "stirling.wind_blade_diameter_max_m.residential", "lte", 2, "m",
    f"{WQ} — Residential zones: DIAMETER 2m blade diameter max.",
    table_reference="LPP 6.10 Table 1", zones=["Residential"])
add(c610, S, "stirling.wind_blade_diameter_max_m.non_residential", "lte", 5.5, "m",
    f"{WQ} — Mixed Use Zone and Non-Residential Zone: DIAMETER 5.5m blade diameter max.",
    table_reference="LPP 6.10 Table 1", zones=["Mixed Use", "Non-Residential"])
add(c610, S, "stirling.wind_roof_mounted_major_opening_distance_min_m", "gte", 7.5, "m",
    f"{WQ} — Roof Mounted: No minimum setback from boundary, however Wind Energy System to be located minimum of 7.5 metres from major opening of adjoining dwelling / adjoining building.",
    table_reference="LPP 6.10 Table 1",
    condition={"mounting": "roof", "from": "major opening of adjoining building"})
add(c610, S, "stirling.wind_pole_boundary_setback_min_height_fraction.residential", "gte", 1.0, "x total height",
    f"{WQ} — Pole Mounted (Residential): BOUNDARY SETBACKS (SIDE & REAR): The setback from boundaries is not less than the total height of the wind energy system.",
    table_reference="LPP 6.10 Table 1", zones=["Residential"],
    condition={"mounting": "pole", "of": "total height of wind energy system"})
add(c610, S, "stirling.wind_pole_boundary_setback_min_height_fraction.non_residential", "gte", 0.5, "x total height",
    f"{WQ} — Pole Mounted (Mixed Use / Non-Residential): The setback from boundaries is not less than half of the total height of the wind energy system.",
    table_reference="LPP 6.10 Table 1", zones=["Mixed Use", "Non-Residential"],
    condition={"mounting": "pole", "of": "total height of wind energy system"})

# ================= 6.11 TREES AND DEVELOPMENT =================
c611 = clause("lpp611_trees_development", "Stirling LPP 6.11 Trees and Development",
              "Significant tree retention, advanced tree planting ratios (Table 1), soil "
              "space, crossover setbacks from street trees.")
S = "LPP 6.11 Trees and Development"
add(c611, S, "stirling.significant_tree_height_min_m", "gte", 4, "m",
    "'Significant Tree' - means a woody plant at a height of at least four (4) metres above ground level and meets one of the following criteria.",
    table_reference="LPP 6.11 cl 4.0", check_type="definition")
add(c611, S, "stirling.significant_tree_trunk_circumference_min_mm.single_trunk", "gte", 500, "mm",
    "for a single trunk species, a trunk circumference of at least 500mm at a height of one (1.0) metre above ground level.",
    table_reference="LPP 6.11 cl 4.0", check_type="definition",
    condition={"trunk": "single", "measured_at_m": 1.0})
add(c611, S, "stirling.significant_tree_trunk_circumference_min_mm.multi_trunk", "gte", 250, "mm",
    "for a multi trunk species, a trunk circumference of at least 250mm at a height of one (1.0) metre above ground level.",
    table_reference="LPP 6.11 cl 4.0", check_type="definition",
    condition={"trunk": "multi", "measured_at_m": 1.0})
add(c611, S, "stirling.advanced_tree_container_min_litres", "gte", 90, "litres",
    "'Advanced Tree' - means a tree which requires planting in at least a 90 litre container or greater size and which is at least 2 metres in height and at least 2 years of age.",
    table_reference="LPP 6.11 cl 4.0", check_type="definition")
add(c611, S, "stirling.advanced_tree_height_min_m", "gte", 2, "m",
    "'Advanced Tree' - means a tree which requires planting in at least a 90 litre container or greater size and which is at least 2 metres in height and at least 2 years of age.",
    table_reference="LPP 6.11 cl 4.0", check_type="definition")
TREE_RATIO = [
    ("lte500", "1m2 - 500m2", 1), ("501_1000", "501m2 - 1,000m2", 2),
    ("1001_1500", "1,001m2 - 1,500m2", 3), ("1501_2000", "1,501m2 - 2,000m2", 4),
]
for key, band, n in TREE_RATIO:
    add(c611, S, f"stirling.advanced_trees_min_count.site_{key}", "gte", n, "count",
        f"Table 1 – Maximum Ratio of Advanced Trees (excluding Multiple Dwellings): SITE AREA {band} — NUMBER OF ADVANCED TREES TO BE PLANTED {n}.",
        table_reference="LPP 6.11 Table 1", condition={"site_area_band": band},
        check_type="min_count")
add(c611, S, "stirling.advanced_trees_min_per_500m2.site_over_2000", "gte", 1, "per 500m2",
    "Table 1 – Maximum Ratio of Advanced Trees (excluding Multiple Dwellings): Over 2,000m2 — 1 for every 500m² (or part thereof).",
    table_reference="LPP 6.11 Table 1", condition={"site_area_gt_m2": 2000})
add(c611, S, "stirling.tree_soil_space_min_m2", "gte", 9, "m2",
    "Where the Council approves development on a site with a condition of development approval requiring the retention of a significant tree or the planting of an advanced tree, the following minimum soil space (at ground level free of intrusions) is required around each tree: For all other development: 9m2.",
    table_reference="LPP 6.11 cl 5.1(d)",
    condition={"excludes": "Multiple Dwellings (R-Codes Vol 2 Table 3.3b applies)"})
add(c611, S, "stirling.crossover_setback_from_street_tree_min_m.dbh_lte200", "gte", 1, "m",
    "A minimum setback of a crossover/driveway from any street tree on the verge is required. The setback distance will be in direct relation to the Diameter at Breast Height (DBH) of the street tree: DBH of up to 200mm requires a minimum setback of one metre.",
    table_reference="LPP 6.11 cl 5.2(c)", condition={"street_tree_dbh": "<= 200mm"})
add(c611, S, "stirling.crossover_setback_from_street_tree_min_m.dbh_201_400", "gte", 2, "m",
    "DBH of 201mm to 400mm requires a minimum setback of two metres.",
    table_reference="LPP 6.11 cl 5.2(c)", condition={"street_tree_dbh": "201-400mm"})
add(c611, S, "stirling.crossover_setback_from_street_tree_min_m.dbh_gte401", "gte", 3, "m",
    "DBH of 401mm or greater requires a minimum setback of three metres.",
    table_reference="LPP 6.11 cl 5.2(c)", condition={"street_tree_dbh": ">= 401mm"})
add(c611, S, "stirling.crossover_setback_from_street_tree_absolute_min_m", "gte", 1.0, "m",
    "To keep retained trees in a sound condition and to reduce the impact on its root system, no setback requests less than 1.0 metre will be accepted.",
    table_reference="LPP 6.11 cl 5.2(d)")

WARN = [
    "REVOKED sections NOT extracted: 2.6 Residential Building Heights (revoked 20 Feb 2023), 2.7 Streetscapes (2016), 2.8 Multiple Dwellings (2019), 2.9 Single Houses and Grouped Dwellings (2017), 6.2 Bicycle Parking (revoked 20 Jan 2023, superseded by LPP 6.7 Table 4).",
    "LPP 6.7 cl 5.2(c): R-Codes (SPP 7.3) parking applies to all residential components; Table 1/2 ratios are non-residential only - no conflict with R-Code residential parking defaults.",
    "Character Retention Guidelines Inglewood (3.1A) contains street-setback augmentations to R-Codes 5.1.2/5.1.3/5.1.6/5.3.7/5.2.1 (e.g. 2m single-storey addition setback, garage 0.5m behind dwelling alignment) - heritage-area specific, flagged for a future pass.",
    "Parking ratios encoded as 'm2 per bay' maximums (smaller value = more parking) to keep numeric comparability; check semantics at evaluation time.",
]
write_report("/app/reports/phase6_stirling_lpp_manual_extraction.json",
             SV, PDF, "LPP 6.6, 6.7, 6.10, 6.11",
             ["LPP 6.6 provisions", "LPP 6.7 Tables 1-4 + cl 5.1-9", "LPP 6.10 Table 1",
              "LPP 6.11 cl 4-5 + Table 1"],
             C, warnings=WARN)
print("Stirling candidates:", len(C))
