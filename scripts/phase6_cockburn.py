"""Phase 6: City of Cockburn LPP rule candidates.

Sources:
- LPP1 Design Requirements Incidental Structures (16b08790-...) -> measurable
  numeric conditions in the provisions tables (solar, wind, tanks, cubbies,
  shade sails, poles, dishes, pergolas).
- LPP1.16 Single House Standards Medium Density (f905d3f4-...) -> provisions
  tables are embedded raster images; values NOT extracted (no calibration);
  conflicts/applicability recorded as needs_human_review + warnings.
- LPP1.2 Residential Design Guidelines (60054dab-...) -> guidelines are
  embedded raster images; policy-statement applicability clauses only.
"""
import sys

sys.path.insert(0, "/app/scripts/phase6")
from lpp_lib import cand, ensure_clause, write_report

COUNCIL = "City of Cockburn"
SV_INCIDENTAL = "16b08790-b4ca-44f6-9c96-733fdf096387"
SV_MEDIUM_DENSITY = "f905d3f4-9003-47bc-9a16-f40605985cb1"
SV_DESIGN_GUIDELINES = "60054dab-bc07-455e-a17d-5cb154b134f1"

SEC = "Policy Statement (1) Provisions"

c_inc = ensure_clause(
    SV_INCIDENTAL, "lpp1_incidental_provisions",
    "LPP1 Design Requirements for Incidental Structures — Policy Statement (1) Provisions",
    "Provisions tables: works that do not require development approval where "
    "Column 3 conditions are met (Clause 61(1), Table No. 20, LPS Regulations 2015).")

RES_CTR = ["Residential", "Regional Centre", "District Centre", "Local Centre"]
NONRES = ["Mixed Use", "Mixed Business", "Light and Service Industry", "Industry", "Rural Living", "Rural and Resource"]
C = []

def add(*a, **k):
    C.append(cand(*a, clause_id=c_inc, sv_id=SV_INCIDENTAL, council_scope=COUNCIL,
                  instrument_section=SEC, **k))

# --- Solar panels (rows 1-2) ---
q = "The works do not occupy an area greater than 25m2 and have a maximum height of 3m as measured from the natural ground level"
add("cockburn.solar_freestanding_area_max_m2.residential", "lte", 25, "m2", q,
    zones=RES_CTR, condition={"works": "free standing (ground mounted) solar energy systems"})
add("cockburn.solar_freestanding_height_max_m.residential", "lte", 3, "m", q,
    zones=RES_CTR, condition={"works": "free standing (ground mounted) solar energy systems",
                              "measured_from": "natural ground level"})
add("cockburn.solar_freestanding_area_max_m2.nonresidential", "lte", 50, "m2",
    "The works do not occupy an area greater than 50m2",
    zones=NONRES, condition={"works": "free standing (ground mounted) solar energy systems"})

# --- Wind energy (rows 3-5) ---
q = "For any lot which is 2000m2 or less in area, the maximum blade diameter does not exceed 2m"
add("cockburn.wind_turbine_blade_diameter_max_m.horizontal_axis", "lte", 2, "m", q,
    zones=["All zones"], condition={"works": "Horizontal Axis Wind Turbine",
                                    "lot_area_lte_m2": 2000})
add("cockburn.wind_turbine_height_exceedance_max_m.vertical_axis", "lte", 1, "m",
    "The works, where located on an existing residential building, do not exceed the maximum height requirements applicable to the site by 1m",
    zones=["All zones"], condition={"works": "Vertical Axis Wind Turbine",
                                    "location": "on an existing residential building"})
add("cockburn.windmill_blade_diameter_max_m", "lte", 2, "m", q,
    zones=["All zones except Residential"], condition={"works": "Windmills",
                                                       "lot_area_lte_m2": 2000})

# --- Rainwater tanks (row 6) ---
add("cockburn.rainwater_tank_height_max_m.rural", "lte", 5, "m",
    "The height of the works does not exceed 5m above the natural ground level",
    zones=["Rural Living", "Rural and Resource"],
    condition={"works": "Rainwater Tanks", "measured_from": "natural ground level"})

# --- Cubby houses (row 9) ---
add("cockburn.cubby_house_primary_street_setback_min_m.rural_living", "gte", 6, "m",
    "Located a minimum 6m from the primary street", zones=["Rural Living"],
    condition={"works": "Cubby Houses"})
add("cockburn.cubby_house_boundary_setback_min_m.rural_living", "gte", 2.5, "m",
    "Located a minimum 2.5m from any other boundary", zones=["Rural Living"],
    condition={"works": "Cubby Houses"})
add("cockburn.cubby_house_floor_area_max_m2", "lte", 10, "m2",
    "Does not have a footprint or floor area of greater than 10m2",
    zones=["All other zones (R-Codes lots: Single House or Grouped Dwelling)"],
    condition={"works": "Cubby Houses"})
add("cockburn.cubby_house_height_max_m", "lte", 3, "m",
    "Does not exceed a building height of 3 metres measured from the existing natural ground level",
    zones=["All other zones (R-Codes lots: Single House or Grouped Dwelling)"],
    condition={"works": "Cubby Houses", "measured_from": "existing natural ground level"})
add("cockburn.cubby_house_max_count_per_lot", "lte", 1, "count",
    "There is only one cubby on the lot",
    zones=["All other zones (R-Codes lots: Single House or Grouped Dwelling)"],
    condition={"works": "Cubby Houses"})

# --- Shade sails (row 10) ---
SHADE_ZONES = ["Local Centre", "District centre", "Regional Centre", "Mixed Business",
               "Light and Service Industry", "Industry", "Strategic Industry"]
add("cockburn.shade_sail_primary_street_setback_min_m", "gte", 15, "m",
    "Located a minimum 15m from the primary street lot boundary",
    zones=SHADE_ZONES, condition={"works": "Shade Sails"})
add("cockburn.shade_sail_boundary_setback_min_m", "gte", 3, "m",
    "Located a minimum 3m from any other boundary",
    zones=SHADE_ZONES, condition={"works": "Shade Sails"})
add("cockburn.shade_sail_corner_lot_street_setback_min_m", "gte", 15, "m",
    "Where a lot has frontages to two streets (excluding the secondary street) then both street setbacks shall be 15m",
    zones=SHADE_ZONES, condition={"works": "Shade Sails", "lot_type": "two street frontages"})

# --- Flag poles (row 11) ---
add("cockburn.flagpole_height_max_m", "lte", 6, "m",
    "The height of the flagpole is no more than 6m above the natural ground level",
    zones=["All zones"], condition={"works": "Flag Poles", "measured_from": "natural ground level"})
add("cockburn.flagpole_diameter_max_mm", "lte", 200, "mm",
    "The flagpole is no more than 200mm in diameter",
    zones=["All zones"], condition={"works": "Flag Poles"})
add("cockburn.flagpole_max_count_per_lot", "lte", 1, "count",
    "There is no more than 1 flagpole on the lot",
    zones=["All zones"], condition={"works": "Flag Poles"})

# --- Camera poles (row 12) ---
add("cockburn.camera_pole_primary_street_setback_min_m.rural", "gte", 20, "m",
    "Located a minimum 20 m from the primary street",
    zones=["Resource and Rural"], condition={"works": "Camera Poles"})
add("cockburn.camera_pole_boundary_setback_min_m.rural", "gte", 10, "m",
    "Located a minimum 10 m from any other boundary",
    zones=["Resource and Rural"], condition={"works": "Camera Poles"})
add("cockburn.camera_pole_primary_street_setback_min_m.rural_living", "gte", 6, "m",
    "Located a minimum 6m from the primary street",
    zones=["Rural Living"], condition={"works": "Camera Poles"})
add("cockburn.camera_pole_boundary_setback_min_m.rural_living", "gte", 2.5, "m",
    "Located a minimum 2.5m from any other boundary",
    zones=["Rural Living"], condition={"works": "Camera Poles"})
add("cockburn.camera_pole_residential_interface_setback_min_m.regional_centre", "gte", 15, "m",
    "Located a minimum 15m from any boundary that adjoins residential zoned land",
    zones=["Regional Centre"], condition={"works": "Camera Poles"})
add("cockburn.camera_pole_max_density.regional_centre", "lte", 1, "per 2000m2",
    "Where there is not more than one (1) camera pole per 2,000m2 of lot area",
    zones=["Regional Centre"], condition={"works": "Camera Poles"})
add("cockburn.camera_pole_height_max_m", "lte", 6, "m",
    "Where the height of the structure does not exceed the wall height of the existing/proposed dwelling on-site, to a maximum height of 6m",
    zones=["All other zones"], condition={"works": "Camera Poles",
                                          "also_lte": "wall height of existing/proposed dwelling"})
add("cockburn.camera_pole_max_count_per_lot", "lte", 1, "count",
    "Where only one (1) structure is proposed per lot",
    zones=["All other zones"], condition={"works": "Camera Poles"})

# --- Satellite dishes (row 13 + explanatory note 6) ---
add("cockburn.satellite_dish_diameter_max_m.residential", "lt", 1.2, "m",
    "Has a diameter of less than 1.2m",
    zones=["Residential", "Local Centre"], condition={"works": "Satellite Dishes"})
add("cockburn.satellite_dish_diameter_max_m.other_zones", "lt", 3, "m",
    "Has a diameter of less than 3m",
    zones=["All other zones"], condition={"works": "Satellite Dishes"})
add("cockburn.satellite_dish_max_count_per_lot", "lte", 2, "count",
    "No more than 2 dishes are proposed on any one lot",
    zones=["All zones"], condition={"works": "Satellite Dishes"})
add("cockburn.satellite_dish_ground_mounted_diameter_max_m", "lte", 3, "m",
    "Dishes must be ground mounted with a maximum diameter of 3m.",
    zones=["All zones"], pathway="design_principle",
    condition={"works": "Satellite Dishes requiring development approval"})

# --- Pergolas/Vergolas (row 17, non-residential) ---
add("cockburn.pergola_primary_street_setback_min_m.nonresidential", "gte", 15, "m",
    "Located 15m from the primary street boundary",
    zones=["All other zones (non-residential)"], condition={"works": "Pergolas/Vergolas"})
add("cockburn.pergola_boundary_setback_min_m.nonresidential", "gte", 3, "m",
    "Located 3m from any other boundary",
    zones=["All other zones (non-residential)"], condition={"works": "Pergolas/Vergolas"})
add("cockburn.pergola_corner_lot_street_setback_min_m.nonresidential", "gte", 15, "m",
    "Where a lot has frontages to two streets (excluding the secondary street) then both street setbacks shall be 15m",
    zones=["All other zones (non-residential)"],
    condition={"works": "Pergolas/Vergolas", "lot_type": "two street frontages"})

write_report("/app/reports/phase6_cockburn_lpp1_incidental_extraction.json",
             SV_INCIDENTAL,
             "/app/data/raw-sources/councils/cockburn/lpp1_design_requirements_incidental_structures.docx",
             SEC,
             ["Provisions tables rows 1-17"],
             C,
             warnings=[
                 "All values transcribed verbatim from DOCX provisions tables (python-docx); quotes are operative condition text.",
                 "Rules are development-approval exemption conditions (Clause 61(1) Table 20 LPS Regs); expressed as standards for evaluation.",
             ])

# --- LPP1.16 medium density: sunset/applicability recorded for review ---
c_md = ensure_clause(
    SV_MEDIUM_DENSITY, "lpp1_16_medium_density_policy",
    "LPP1.16 Single House Standards for Medium Density Housing in the Development Zone",
    "Policy replaces deemed-to-comply R-Codes clauses 5.12, 5.13, 5.21 (setbacks), "
    "5.1.4 (open space), 5.3.3 (parking), 5.4.1 (visual privacy), 5.4.2 (solar access) "
    "for medium density (R25-R60) single dwellings in the Development Zone. Provisions "
    "tables are embedded raster images in the DOCX and were not machine-readable.")
MD = [
    cand("cockburn.rmd_r60_provisions_sunset", "eq", "2026-04-10", None,
         "The provisions relating to R60 within this policy shall be of no effect as of 10 April 2026 in accordance with WAPC Planning Bulletin 114/2024. At this point, lots with a density coding of R60 shall be assessed against the provisions of Part C of the R-Codes.",
         clause_id=c_md, sv_id=SV_MEDIUM_DENSITY, council_scope=COUNCIL,
         instrument_section="Policy Purpose",
         r_codes=["R60"], zones=["Development"],
         check_type="temporal_scope", evaluable="needs_human_review",
         extra_value={"raw_text": "R60 provisions sunset 2026-04-10; R60 lots then assessed under R-Codes Part C"}),
    cand("cockburn.rmd_replaced_rcodes_clauses", "eq", "5.12,5.13,5.21,5.1.4,5.3.3,5.4.1,5.4.2", None,
         "The purpose of this policy is to replace the deemed-to-comply requirements of the following clauses of the R-Codes with those set out in the provisions of this policy: Building and Garage setbacks (5.12, 5.13, 5.21); Open Space (5.1.4); Parking (5.3.3); Visual Privacy (5.4.1); Solar Access (5.4.2).",
         clause_id=c_md, sv_id=SV_MEDIUM_DENSITY, council_scope=COUNCIL,
         instrument_section="Policy Purpose",
         r_codes=["R25", "R30", "R35", "R40", "R50", "R60"], zones=["Development"],
         check_type="policy_override_scope", evaluable="needs_human_review",
         extra_value={"raw_text": "Replacement values are in raster-image provisions tables; not extracted without calibration"}),
]
write_report("/app/reports/phase6_cockburn_lpp1_16_medium_density_extraction.json",
             SV_MEDIUM_DENSITY,
             "/app/data/raw-sources/councils/cockburn/lpp1_single_house_standards_medium_density.docx",
             "Policy Purpose / Policy Statement",
             ["Provisions (raster image - not extracted)"],
             MD,
             warnings=[
                 "CONFLICT WITH R-CODE DEFAULTS: policy replaces R-Codes D-t-C clauses 5.12, 5.13, 5.21, 5.1.4, 5.3.3, 5.4.1, 5.4.2 for R25-R60 single houses in Development Zone; replacement values are embedded raster images (word/media/image2.png, image3.png) and cannot be transcribed without calibration - flagged for operator review.",
                 "R60 provisions sunset 10 April 2026 (Planning Bulletin 114/2024); R60 then assessed under R-Codes Part C.",
             ])

# --- LPP1.2 design guidelines: applicability only (guidelines are raster images) ---
c_dg = ensure_clause(
    SV_DESIGN_GUIDELINES, "lpp1_2_design_guidelines_policy",
    "LPP1.2 Residential Design Guidelines — Policy Statement",
    "Attachment 1 (Residential Design Guidelines) is embedded as raster images; "
    "policy statement applicability clauses transcribed.")
DG = [
    cand("cockburn.design_guidelines_applicability_single_house", "eq", "frontage<10.5m or lot<260m2", None,
         "This policy applies to single houses on lots with a frontage less than 10.5m wide; single houses on lots less than 260m².",
         clause_id=c_dg, sv_id=SV_DESIGN_GUIDELINES, council_scope=COUNCIL,
         instrument_section="Policy Statement (4)",
         check_type="policy_applicability", evaluable="needs_human_review",
         extra_value={"raw_text": "applicability threshold: frontage < 10.5m; lot area < 260m2"}),
]
write_report("/app/reports/phase6_cockburn_lpp1_2_design_guidelines_extraction.json",
             SV_DESIGN_GUIDELINES,
             "/app/data/raw-sources/councils/cockburn/lpp1_2_residential_design_guidelines.docx",
             "Policy Statement",
             ["Attachment 1 (raster images - not extracted)"],
             DG,
             warnings=[
                 "Residential Design Guidelines (Attachment 1, incl. garage widths cl 10.4, fencing cl 10.5, split-coded lots cl 9.1/9.2) are embedded raster images; not extracted without calibration - flagged for operator review.",
             ])
print("Cockburn builders complete:",
      len(C), "incidental +", len(MD), "medium-density +", len(DG), "design-guidelines")
