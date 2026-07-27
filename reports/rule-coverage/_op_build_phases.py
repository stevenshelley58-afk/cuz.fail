"""Operator build script: Phases 4, 7, 10, 12 rule coverage.

Registers metadata-only sources (SQL, mirroring existing restricted/metadata
pattern), creates provision clauses, and emits candidate extraction report
JSONs to /app/reports/ for validate_extraction.py + bulk_approve_rules.py.

All quotes are either (a) verbatim text extracted from registered PDFs on the
VPS, or (b) explicit metadata-only verification pointers that reference a
provision identifier without reproducing licence-restricted content.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from uuid import uuid4

import psycopg

APPROVER = "393277fe-3581-4a29-b394-a41cfc26f01b"

DB_URL = os.environ["DATABASE_URL"].replace(
    "postgresql+asyncpg://", "postgresql://"
).replace("postgresql+psycopg://", "postgresql://")

# ---------------------------------------------------------------------------
# Existing source versions
# ---------------------------------------------------------------------------
SV_BUSHFIRE_GUIDELINES = "dab29595-c9d0-486a-a2ba-c6a849a60d39"  # Guidelines for Planning in Bushfire Prone Areas v1.4 (registered this run)
SV_HERITAGE_ACT = "3af5b793-b7ed-4acc-8fc5-9f0e6a24a1ec"          # Heritage Act 2018 (registered this run)
SV_COASTAL_SPP26 = "1c9fe296-7a27-4c20-b01e-4161c700db58"          # SPP 2.6 (registered this run)
SV_CONTAMINATED = "f8e39d86-40bb-479c-80c4-ccfd9f76234d"           # Contaminated Sites Act 2003 (pre-existing, open/approved)
SV_DIVIDING_FENCES = "a925e8ae-951c-43bf-aa29-c14d26b3c67d"        # Dividing Fences Act 1961 (pre-existing, open/approved)

# ---------------------------------------------------------------------------
# Metadata-only sources to create (no content stored)
# ---------------------------------------------------------------------------
METADATA_SOURCES = {
    "ncc": {
        "title": "National Construction Code 2022",
        "authority": "Australian Building Codes Board",
        "source_type": "ncc",
        "jurisdiction": "AU",
        "version_label": "2022-amendment-1",
        "licence_status": "restricted",
        "canonical_url": "https://ncc.abcb.gov.au/",
        "note": ("Licence-restricted. No NCC content downloaded or stored. "
              "Metadata-only registration; rules are verification pointers "
              "referencing NCC provision identifiers only."),
    },
    "flood": {
        "title": "Department of Water and Environmental Regulation - Floodplain Mapping (1:100 ARI)",
        "authority": "Department of Water and Environmental Regulation",
        "source_type": "spatial_dataset",
        "jurisdiction": "WA",
        "version_label": "current-metadata-only",
        "licence_status": "metadata_only",
        "canonical_url": "https://www.wa.gov.au/organisation/department-of-water-and-environmental-regulation",
        "note": ("Metadata-only registration of DWER floodplain mapping service. "
              "No spatial data stored; referral-trigger rules only."),
    },
    "ass": {
        "title": "Department of Water and Environmental Regulation - Acid Sulfate Soil Risk Maps",
        "authority": "Department of Water and Environmental Regulation",
        "source_type": "spatial_dataset",
        "jurisdiction": "WA",
        "version_label": "current-metadata-only",
        "licence_status": "metadata_only",
        "canonical_url": None,
        "note": ("Metadata-only registration of DWER acid sulfate soil risk mapping. "
              "No spatial data stored; referral-trigger rules only."),
    },
    "watercorp": {
        "title": "Water Corporation - Water and Wastewater Service Connection Requirements",
        "authority": "Water Corporation",
        "source_type": "planning_guidance",
        "jurisdiction": "WA",
        "version_label": "current-metadata-only",
        "licence_status": "metadata_only",
        "canonical_url": "https://www.watercorporation.com.au/",
        "note": ("Metadata-only registration. Service connection verification "
              "triggers only; no Water Corporation technical content stored."),
    },
    "westernpower": {
        "title": "Western Power - Electricity Connection Requirements",
        "authority": "Western Power",
        "source_type": "planning_guidance",
        "jurisdiction": "WA",
        "version_label": "current-metadata-only",
        "licence_status": "metadata_only",
        "canonical_url": "https://www.westernpower.com.au/",
        "note": ("Metadata-only registration. Service connection verification "
              "triggers only; no Western Power technical content stored."),
    },
    "treelaw": {
        "title": "WA Local Government Tree Preservation Local Laws (generic register)",
        "authority": "Various WA local governments",
        "source_type": "local_planning_policy",
        "jurisdiction": "WA",
        "version_label": "generic-metadata-only",
        "licence_status": "metadata_only",
        "canonical_url": None,
        "note": ("Metadata-only register for tree preservation / significant tree "
              "local laws, which vary per council. Generic trigger rules only; "
              "per-council verification required."),
    },
}

# ---------------------------------------------------------------------------
# Rule definitions
# Each rule: (rule_key, clause_key, section_ref, clause_title, quote,
#             raw_text, evaluable, check_type)
# ---------------------------------------------------------------------------

def r(key, ck, ref, title, quote, raw, ev="yes", ct="conditional"):
    return {"rule_key": key, "clause_key": ck, "section_ref": ref, "clause_title": title,
                "quote": quote, "raw_text": raw, "evaluable": ev, "check_type": ct}


NCC_PTR = " (metadata-only verification pointer — NCC 2022 is licence-restricted; no NCC text reproduced or stored; verify against licensed NCC 2022 Volume Two / ABCB Housing Provisions)"

RULES_PHASE4_NCC = [
    r("ncc_structure_class1_verification", "ncc_h1p1", "H1P1", "Structure",
      "NCC 2022 Vol Two H1P1 'Structure'" + NCC_PTR,
      "verify Class 1/10 structural stability per NCC 2022 H1P1 (ABCB Housing Provisions Parts 2-8)"),
    r("ncc_flood_hazard_area_construction", "ncc_h1p2", "H1P2/H1D10", "Buildings in flood hazard areas",
      "NCC 2022 Vol Two H1P2/H1D10 'Flood hazard areas'" + NCC_PTR,
      "verify construction in flood hazard area per NCC 2022 H1P2/H1D10 (ABCB Standard for Construction of Buildings in Flood Hazard Areas)"),
    r("ncc_damp_weatherproofing", "ncc_h2p2", "H2P2", "Weatherproofing",
      "NCC 2022 Vol Two H2P2 'Weatherproofing'" + NCC_PTR,
      "verify damp and weatherproofing per NCC 2022 H2P2/H2D2"),
    r("ncc_subfloor_ventilation", "ncc_h2d5", "H2D5", "Subfloor ventilation",
      "NCC 2022 Vol Two H2D5 'Subfloor ventilation'" + NCC_PTR,
      "verify subfloor ventilation per NCC 2022 H2D5"),
    r("ncc_fire_spread_external_walls", "ncc_h3d3", "H3P1/H3D3", "Fire separation of external walls",
      "NCC 2022 Vol Two H3P1 'Spread of fire' / H3D3 'Fire separation of external walls'" + NCC_PTR,
      "verify fire separation of external walls near boundaries per NCC 2022 H3P1/H3D3"),
    r("ncc_frl_external_wall_boundary", "ncc_h3d3_frl", "H3D3", "Fire-resistance levels (FRL)",
      "NCC 2022 Vol Two H3D3 referencing ABCB Housing Provisions fire-resistance requirements" + NCC_PTR,
      "verify FRL of external walls within boundary distance per NCC 2022 H3D3 / Housing Provisions (category: FRL)"),
    r("ncc_fire_separation_separating_walls", "ncc_h3d4", "H3D4", "Fire protection of separating walls and floors",
      "NCC 2022 Vol Two H3D4 'Fire protection of separating walls and floors'" + NCC_PTR,
      "verify separating wall/floor fire protection for attached dwellings per NCC 2022 H3D4"),
    r("ncc_garage_top_dwelling_fire", "ncc_h3d5", "H3D5", "Fire separation of garage-top dwellings",
      "NCC 2022 Vol Two H3D5 'Fire separation of garage-top-dwellings'" + NCC_PTR,
      "verify garage-top dwelling fire separation per NCC 2022 H3D5"),
    r("ncc_smoke_alarms", "ncc_h3d6", "H3P2/H3D6", "Smoke alarms",
      "NCC 2022 Vol Two H3P2 'Automatic warning for occupants' / H3D6 'Smoke alarms and evacuation lighting'" + NCC_PTR,
      "verify smoke alarm provision per NCC 2022 H3P2/H3D6"),
    r("ncc_wet_areas", "ncc_h4p1", "H4P1/H4D2", "Wet areas",
      "NCC 2022 Vol Two H4P1 'Wet areas' / H4D2" + NCC_PTR,
      "verify wet area waterproofing per NCC 2022 H4P1/H4D2"),
    r("ncc_room_heights", "ncc_h4d4", "H4P2/H4D4", "Room heights",
      "NCC 2022 Vol Two H4P2 'Room heights' / H4D4 (operator example referenced H3P1; verified identifier is H4P2/H4D4)" + NCC_PTR,
      "verify ceiling height >= 2400mm to habitable rooms per NCC 2022 H4P2/H4D4 (category: dwelling amenity)"),
    r("ncc_facilities", "ncc_h4p3", "H4P3", "Personal hygiene and other facilities",
      "NCC 2022 Vol Two H4P3 'Personal hygiene and other facilities'" + NCC_PTR,
      "verify required sanitary/kitchen/laundry facilities per NCC 2022 H4P3"),
    r("ncc_natural_light", "ncc_h4p4", "H4P4", "Lighting",
      "NCC 2022 Vol Two H4P4 'Lighting'" + NCC_PTR,
      "verify natural/artificial light to habitable rooms per NCC 2022 H4P4"),
    r("ncc_ventilation", "ncc_h4p5", "H4P5", "Ventilation",
      "NCC 2022 Vol Two H4P5 'Ventilation'" + NCC_PTR,
      "verify ventilation per NCC 2022 H4P5"),
    r("ncc_sound_insulation", "ncc_h4p6", "H4P6", "Sound insulation",
      "NCC 2022 Vol Two H4P6 'Sound insulation'" + NCC_PTR,
      "verify sound insulation of separating walls/floors (attached dwellings) per NCC 2022 H4P6"),
    r("ncc_condensation_management", "ncc_h4p7", "H4P7", "Condensation and water vapour management",
      "NCC 2022 Vol Two H4P7 'Condensation and water vapour management'" + NCC_PTR,
      "verify condensation management per NCC 2022 H4P7"),
    r("ncc_safe_movement_egress", "ncc_h5p1", "H5P1", "Movement to and within a building",
      "NCC 2022 Vol Two H5P1 'Movement to and within a building'" + NCC_PTR,
      "verify safe movement/egress provisions per NCC 2022 H5P1 (category: egress)"),
    r("ncc_fall_prevention_barriers", "ncc_h5p2", "H5P2", "Fall prevention barriers",
      "NCC 2022 Vol Two H5P2 'Fall prevention barriers'" + NCC_PTR,
      "verify barriers for fall prevention (balustrades etc.) per NCC 2022 H5P2"),
    r("ncc_energy_efficiency_envelope", "ncc_h6p1", "H6P1/H6D2", "Energy efficiency - building envelope (NatHERS)",
      "NCC 2022 Vol Two H6P1/H6D2 'Energy efficiency' (NatHERS thermal performance pathway)" + NCC_PTR,
      "verify NatHERS thermal performance compliance per NCC 2022 H6P1/H6D2 (category: NatHERS)"),
    r("ncc_energy_efficiency_services", "ncc_h6p2", "H6P2", "Energy efficiency - services (whole-of-home)",
      "NCC 2022 Vol Two H6P2 'Energy usage' (whole-of-home)" + NCC_PTR,
      "verify whole-of-home energy budget for services per NCC 2022 H6P2 (category: NatHERS)",
      ev="needs_human_review"),
    r("ncc_swimming_pool_safety_barrier", "ncc_h7p1", "H7P1/H7D2", "Swimming pool access",
      "NCC 2022 Vol Two H7P1 'Swimming pool access' / H7D2 'Swimming pools'" + NCC_PTR,
      "verify swimming pool safety barrier per NCC 2022 H7P1/H7D2"),
    r("ncc_bushfire_construction_as3959", "ncc_h7d4", "H7D4", "Construction in bushfire prone areas",
      "NCC 2022 Vol Two H7D4 'Construction in bushfire prone areas'" + NCC_PTR,
      "verify construction per NCC 2022 H7D4 (references AS 3959; AS 3959 values are paid Standards - not codified)"),
    r("ncc_livable_housing_design", "ncc_h8", "Part H8 (identifier unverified)", "Livable housing design",
      "NCC 2022 liveable housing design provisions (ABCB Livable Housing Design Standard); exact Volume Two provision identifier unverified" + NCC_PTR,
      "verify livable housing design applicability/adoption per NCC 2022 (WA adoption status varies)",
      ev="needs_human_review"),
]

Q_BAL_TRIG = ("Under the LPS Regulations 2015, a BAL assessment or BAL Contour Map is required "
              "for the development of all habitable buildings or specified")
Q_BAL40FZ = ("If the BAL shown on the Contour Map and/or BAL assessment is BAL\u201340 or BAL\u2013FZ, "
             "development approval is always required.")
Q_BAL_DEF = ("A BAL assessment is the means of measuring the severity of a buildings\u2019 potential "
             "exposure to ember attack")
Q_BAL_CONTOUR = ("A BAL Contour Map is a scale map of the subject [site] and associated indicative "
                 "BAL ratings in reference to any vegetation remaining within 150 metres")
Q_BPC = ("The bushfire protection criteria (Appendix Four) are a performance-based system of "
         "assessing bushfire risk")
Q_DFES_ADVICE = "seeking comments and advice from DFES in relation to"
Q_BAL_PRONE = ("risk (BAL\u201340 or BAL\u2013Flame Zone). They specifically require a BAL assessment "
               "or BAL Contour Map be undertaken for any habitable or specified building")

RULES_PHASE7_BUSHFIRE = [
    r("bal_assessment_required_habitable", "bf_s11_bal_trigger", "Guidelines s.5.4 / LPS Regs 2015",
      "BAL assessment trigger", Q_BAL_TRIG,
      "trigger: BAL assessment or BAL Contour Map required for development of habitable/specified buildings in designated bushfire prone areas"),
    r("bal_contour_map_alternative", "bf_bal_contour", "Guidelines s.4.2", "BAL Contour Map",
      Q_BAL_CONTOUR,
      "BAL Contour Map (scale map of indicative BAL ratings, vegetation within 150m) acceptable alternative to site-specific BAL assessment"),
    r("bal40_balfz_dev_approval_always", "bf_bal40fz", "Guidelines s.2.2", "BAL-40 / BAL-FZ development approval trigger",
      Q_BAL40FZ,
      "trigger: where BAL is BAL-40 or BAL-FZ, development approval is always required"),
    r("bal_assessment_bushfire_prone_area", "bf_prone_trigger", "Guidelines s.2.2", "Bushfire prone area BAL trigger",
      Q_BAL_PRONE,
      "trigger: in bushfire prone areas a BAL assessment or BAL Contour Map is required for habitable/specified buildings"),
    r("bal_category_bal_low", "bf_balcat_low", "Guidelines Table 2", "BAL category BAL-LOW",
      "Table 2: BAL and corresponding descriptions of the predicted levels of exposure and heat flux exposure thresholds",
      "BAL category name: BAL-LOW (name only; AS 3959 heat flux values are paid Standards - not codified)"),
    r("bal_category_bal_125", "bf_balcat_125", "Guidelines Table 2", "BAL category BAL-12.5",
      "Table 2: BAL and corresponding descriptions of the predicted levels of exposure and heat flux exposure thresholds",
      "BAL category name: BAL-12.5 (name only; AS 3959 values not codified)"),
    r("bal_category_bal_19", "bf_balcat_19", "Guidelines Table 2", "BAL category BAL-19",
      "Table 2: BAL and corresponding descriptions of the predicted levels of exposure and heat flux exposure thresholds",
      "BAL category name: BAL-19 (name only; AS 3959 values not codified)"),
    r("bal_category_bal_29", "bf_balcat_29", "Guidelines Table 2", "BAL category BAL-29",
      "Table 2: BAL and corresponding descriptions of the predicted levels of exposure and heat flux exposure thresholds",
      "BAL category name: BAL-29 (name only; AS 3959 values not codified)"),
    r("bal_category_bal_40", "bf_balcat_40", "Guidelines Table 2", "BAL category BAL-40",
      "Table 2: BAL and corresponding descriptions of the predicted levels of exposure and heat flux exposure thresholds",
      "BAL category name: BAL-40 (name only; AS 3959 values not codified)"),
    r("bal_category_bal_fz", "bf_balcat_fz", "Guidelines Table 2", "BAL category BAL-FZ (Flame Zone)",
      "Table 2: BAL and corresponding descriptions of the predicted levels of exposure and heat flux exposure thresholds",
      "BAL category name: BAL-FZ / BAL-Flame Zone (name only; AS 3959 values not codified)"),
    r("bushfire_protection_criteria_appendix4", "bf_bpc_app4", "Guidelines Appendix 4", "Bushfire protection criteria",
      Q_BPC,
      "bushfire protection criteria (Appendix 4) are the performance-based assessment basis: Elements 1-4 (location, siting and design, vehicular access, water) and Element 5 (vulnerable tourism land uses)"),
    r("bmp_required_with_application", "bf_bmp", "Guidelines s.5.5/s.5.6", "Bushfire Management Plan trigger",
      "The application must also be accompanied by a BMP.",
      "trigger: applications for vulnerable/high-risk land uses in bushfire prone areas must be accompanied by a Bushfire Management Plan"),
    r("dfes_advice_referral", "bf_dfes", "Guidelines s.6.4", "DFES advice referral",
      Q_DFES_ADVICE,
      "trigger: seek DFES comments/advice for bushfire local planning policies, BMP performance-principle solutions, Method 2 assessments per AS 3959, and strategic proposals with a BMP"),
]

Q_H73A = ("73. Referral of certain proposals to Council (1) A decision-maker considering a proposal "
          "to which this Subdivision applies must refer the proposal to the Council for its advice.")
Q_H73B = ("(2) The decision-maker must refer the proposal under subsection (1) as soon as "
          "practicable after it becomes aware of the proposal.")
Q_H72 = ("proposal means - (a) an application for development approval; or (b) a proposal, project, "
         "plan, programme, policy, public")
Q_H74 = ("74. Advice on referred proposal (1) The Council must provide advice on a referred "
         "proposal to the decision-maker and, if the proposal is an application for development "
         "approval, to the applicant.")
Q_H74_4 = ("the Council may advise that a decision to approve a proposal relating to the land must "
           "be conditional upon the owner of that land entering into a heritage agreement")
Q_H79 = ("79. Permit for works affecting registered place (1) In this section - works means "
         "anything - (a) the doing of which would contravene section 129 but not section 130")
Q_H129 = ("129. Damaging registered place (1) Subject to subsection (4), a person must not in, or "
          "in relation to, a registered place - (a) alter the fabric of the place or any part of, or "
          "thing in,")
Q_HREG = ("registered place means a place in relation to which there is an entry in the register")
Q_H73_3 = ("Subsection (1) does not apply to a proposal to alter the interior fabric of a church or "
           "other building used primarily for services of worship if")
Q_H56 = ("the Minister may make an order under this section in relation to a registered place (a "
         "repair order) requiring the owner or occupier of the place to undertake")

RULES_PHASE7_HERITAGE = [
    r("heritage_registered_place_check", "ha_reg", "s.15 (definitions)", "Registered place definition",
      Q_HREG,
      "check: is the subject land (or adjacent land) a registered place in the State Register of Heritage Places"),
    r("heritage_proposal_scope", "ha_s72", "s.72", "Proposals to which referral applies",
      Q_H72,
      "scope: 'proposal' includes an application for development approval affecting a registered place"),
    r("heritage_referral_trigger", "ha_s73", "s.73(1)", "Referral of certain proposals to Council",
      Q_H73A,
      "trigger: decision-maker considering a proposal affecting a registered place must refer it to the Heritage Council for advice"),
    r("heritage_referral_timing", "ha_s73_2", "s.73(2)", "Referral timing",
      Q_H73B,
      "referral must occur as soon as practicable after the decision-maker becomes aware of the proposal"),
    r("heritage_council_advice", "ha_s74", "s.74(1)", "Advice on referred proposal",
      Q_H74,
      "Heritage Council must provide advice on a referred proposal to the decision-maker and (for a development application) the applicant"),
    r("heritage_agreement_condition", "ha_s74_4", "s.74(4)", "Heritage agreement condition",
      Q_H74_4,
      "trigger: Council may advise approval be conditional on the owner entering into a heritage agreement"),
    r("heritage_works_permit_trigger", "ha_s79", "s.79", "Permit for works affecting registered place",
      Q_H79,
      "trigger: works affecting a registered place with no other decision-maker require a works permit under s.79"),
    r("heritage_damage_offence", "ha_s129", "s.129", "Damaging registered place",
      Q_H129,
      "check: works must not alter the fabric / demolish / damage a registered place except as authorised (s.129 offence)"),
    r("heritage_church_interior_exemption", "ha_s73_3", "s.73(3)", "Church interior referral exemption",
      Q_H73_3,
      "exemption: referral not required for interior alterations to a place of worship where s.73(3) conditions are met (60 days notice, liturgical declaration)"),
    r("heritage_repair_order_risk", "ha_s56", "s.56", "Repair order",
      Q_H56,
      "check: Minister may make a repair order for a registered place suffering prescribed neglect"),
]

Q_C55 = ("5.5 Coastal hazard risk management and adaptation planning (i) Adequate coastal hazard "
         "risk management and adaptation planning should be undertaken by the responsible "
         "management authority and/or proponent where existing or proposed development or "
         "landholders are in an area at risk of being affected by coastal hazards over the "
         "planning timeframe.")
Q_C55II = ("On consideration of approval for subdivision and/or development current and/or future "
           "lot owners should be made aware of the coastal hazard risk by providing the following "
           "notification on the certificate on title: VULNERABLE COASTAL")
Q_C55H = ("(1) Avoid the presence of new development within an area identified to be affected by "
          "coastal hazards.")
Q_C59 = ("5.9 Coastal foreshore reserve (i) Coastal foreshore reserves are required to accommodate "
         "a range of functions and values.")
Q_C59II = ("(ii) The required coastal foreshore reserve will vary according to the circumstances of "
           "any particular proposal. Each proposal must be assessed on its merits having regard to "
           "this policy, including the principles and guidelines of Schedule One")
Q_CSCH1 = ("Schedule One Calculation of coastal processes")
Q_CPW = ("New coastal protection works are not permitted, except where such works are considered "
         "only after all other options for avoiding and adapting to coastal hazards have been fully "
         "explored")
Q_C54 = ("5.4 Building height limits (i) The provisions of this part of the policy apply to all "
         "development within 300 metres of")

RULES_PHASE7_COASTAL = [
    r("coastal_chrmap_trigger", "spp26_s55", "s.5.5(i)", "Coastal hazard risk management trigger",
      Q_C55,
      "trigger: where proposed development is in an area at risk of coastal hazards over the planning timeframe, coastal hazard risk management and adaptation planning (CHRMAP) is required"),
    r("coastal_title_notification", "spp26_s55ii", "s.5.5(ii)", "Coastal hazard title notification",
      Q_C55II,
      "trigger: on subdivision/development approval, notification of coastal hazard risk on certificate of title (VULNERABLE COASTAL ...)"),
    r("coastal_avoidance_hierarchy", "spp26_s55h", "s.5.5(iii)", "Adaptation planning hierarchy",
      Q_C55H,
      "check: adaptation hierarchy applied sequentially - avoid, planned/managed retreat, accommodate, then protect"),
    r("coastal_foreshore_reserve_determination", "spp26_s59", "s.5.9(i)", "Coastal foreshore reserve",
      Q_C59,
      "check: delineation of coastal foreshore reserve considers coastal hazards, habitats, access, recreation and safety"),
    r("coastal_foreshore_reserve_merits", "spp26_s59ii", "s.5.9(ii)", "Foreshore reserve merits assessment",
      Q_C59II,
      "trigger: each proposal assessed on merits against Schedule One and Coastal Planning Policy Guidelines for foreshore reserve width"),
    r("coastal_schedule_one_processes", "spp26_sch1", "Schedule One", "Calculation of coastal processes",
      Q_CSCH1,
      "check: coastal processes allowance (setback basis) estimated per Schedule One methodology"),
    r("coastal_protection_works_presumption", "spp26_s56", "s.5.6", "Coastal protection works presumption",
      Q_CPW,
      "check: new coastal protection works not permitted except after avoidance/adaptation options fully explored"),
    r("coastal_building_height_300m", "spp26_s54", "s.5.4", "Coastal building height limits",
      Q_C54,
      "trigger: building height provisions apply to all development within 300 metres of the coast"),
]

RULES_PHASE10_BAL = [
    r("bal_overlay_bal_fz", "bf_ov_fz", "Guidelines Table 2 / s.2.2", "Overlay: BAL-FZ",
      Q_BAL40FZ,
      "overlay: BAL-FZ (Flame Zone) - development approval always required; highest construction referral category (name only, no AS 3959 values)"),
    r("bal_overlay_bal_40", "bf_ov_40", "Guidelines Table 2 / s.2.2", "Overlay: BAL-40",
      Q_BAL40FZ,
      "overlay: BAL-40 - development approval always required; construction referral category (name only, no AS 3959 values)"),
    r("bal_overlay_bal_29", "bf_ov_29", "Guidelines Table 2", "Overlay: BAL-29",
      "Table 2: BAL and corresponding descriptions of the predicted levels of exposure and heat flux exposure thresholds",
      "overlay: BAL-29 construction referral category (name only, no AS 3959 values)"),
    r("bal_overlay_bal_19", "bf_ov_19", "Guidelines Table 2", "Overlay: BAL-19",
      "Table 2: BAL and corresponding descriptions of the predicted levels of exposure and heat flux exposure thresholds",
      "overlay: BAL-19 construction referral category (name only, no AS 3959 values)"),
    r("bal_overlay_bal_125", "bf_ov_125", "Guidelines Table 2", "Overlay: BAL-12.5",
      "Table 2: BAL and corresponding descriptions of the predicted levels of exposure and heat flux exposure thresholds",
      "overlay: BAL-12.5 construction referral category (name only, no AS 3959 values)"),
    r("bal_overlay_bal_low", "bf_ov_low", "Guidelines Table 2", "Overlay: BAL-LOW",
      "Table 2: BAL and corresponding descriptions of the predicted levels of exposure and heat flux exposure thresholds",
      "overlay: BAL-LOW - no bushfire construction category applies (name only, no AS 3959 values)"),
]

F_PTR = " (metadata-only verification pointer - DWER floodplain mapping not stored; verify against current DWER 1:100 ARI floodplain dataset)"
RULES_PHASE10_FLOOD = [
    r("flood_1_in_100_ari_referral", "fl_ari", "metadata-only", "1:100 ARI flood referral",
      "DWER floodplain mapping (1:100 ARI)" + F_PTR,
      "trigger: development within 1:100 ARI floodplain area requires flood risk assessment and referral to DWER/local government drainage authority"),
    r("flood_level_verification", "fl_level", "metadata-only", "Flood level verification",
      "DWER floodplain mapping (1:100 ARI)" + F_PTR,
      "verify: habitable floor levels relative to 1:100 ARI flood level per DWER/local government requirements"),
    r("floodway_obstruction_check", "fl_way", "metadata-only", "Floodway obstruction",
      "DWER floodplain mapping (1:100 ARI)" + F_PTR,
      "check: development must not obstruct designated floodway fringe/floodway - per-council and DWER criteria vary",
      ev="needs_human_review"),
]

Q_CS11 = ("Penalty: $250 000, and a daily penalty of $50 000. (4) The following persons have a duty "
          "to report a site under subsection (3)")
Q_CS15 = ("15. Notice of classification is to be given (1) As soon as is practicable after a site "
          "is classified, and in any event not later than 10 days after the site is classified, the "
          "CEO is to cause written notice of the classification")
Q_CS16 = ("16. Site classified as possibly contaminated - investigation required")
Q_CS23 = ("The only sites that are required to be remediated under this Act are sites classified as "
          "contaminated - remediation required.")
Q_CS58 = ("58. Memorial is to be lodged if notice given, or land classified as contaminated")

RULES_PHASE10_CONTAMINATED = [
    r("contaminated_duty_to_report", "cs_s11", "s.11", "Duty to report known/suspected contamination",
      Q_CS11,
      "trigger: duty to report a known or suspected contaminated site to DWER (Contaminated Sites Act 2003 s.11)"),
    r("contaminated_classification_notice", "cs_s15", "s.15", "Classification notice",
      Q_CS15,
      "check: CEO classifies reported sites and issues written notice of classification within 10 days"),
    r("contaminated_investigation_required", "cs_s16", "s.16", "Possibly contaminated - investigation required",
      Q_CS16,
      "trigger: site classified 'possibly contaminated - investigation required' - mandatory site investigation before development reliance"),
    r("contaminated_remediation_required", "cs_s23", "s.23", "Contaminated - remediation required",
      Q_CS23,
      "trigger: sites classified 'contaminated - remediation required' must be remediated; memorial on title restricts dealings"),
    r("contaminated_memorial_on_title", "cs_s58", "s.58", "Memorial on title",
      Q_CS58,
      "check: memorial lodged on title where land classified contaminated - verify memorial status before settlement/development"),
]

A_PTR = " (metadata-only verification pointer - DWER ASS risk mapping not stored; verify against current DWER acid sulfate soil risk maps)"
RULES_PHASE10_ASS = [
    r("ass_risk_map_check", "ass_map", "metadata-only", "Acid sulfate soil risk check",
      "DWER acid sulfate soil risk maps" + A_PTR,
      "trigger: check DWER ASS risk mapping for the subject land; ground disturbance in ASS risk areas requires investigation"),
    r("ass_investigation_trigger", "ass_inv", "metadata-only", "ASS investigation trigger",
      "DWER acid sulfate soil risk maps" + A_PTR,
      "trigger: where earthworks/dewatering proposed in ASS risk area, ASS investigation and (if confirmed) management plan required"),
    r("ass_dewatering_trigger", "ass_dew", "metadata-only", "ASS dewatering trigger",
      "DWER acid sulfate soil risk maps" + A_PTR,
      "trigger: dewatering in ASS risk areas requires ASS management measures - per-council/DWER criteria vary",
      ev="needs_human_review"),
]

RULES_PHASE10_COASTAL = [
    r("coastal_setback_schedule_one_verification", "spp26_sb_sch1", "Schedule One", "Coastal setback basis",
      Q_CSCH1,
      "verify: coastal setback / coastal processes allowance calculated per SPP 2.6 Schedule One (no fixed numeric setback codified - site-specific)"),
    r("coastal_setback_foreshore_reserve", "spp26_sb_59", "s.5.9(i)", "Foreshore reserve as setback",
      Q_C59,
      "check: development setback must respect coastal foreshore reserve delineation under s.5.9"),
    r("coastal_hazard_referral_300m", "spp26_sb_300", "s.5.4", "Coastal zone referral extent",
      Q_C54,
      "trigger: development within 300 metres of the coast engages SPP 2.6 provisions (height limits; hazard checks)"),
    r("coastal_infill_adaptation_review", "spp26_sb_55r", "s.5.5(iv)", "Review on new hazard information",
      ("(iv) Where new information or methods become available that significantly modify the "
       "understanding of the coastal hazards then all areas within the newly defined risk areas "
       "should be reviewed again through the coastal hazard risk management and adaptation planning "
       "hierarchy above"),
      "check: previously approved coastal risk areas subject to re-review when hazard information materially changes"),
]

WC_PTR = " (metadata-only verification pointer - Water Corporation technical requirements not stored; verify with Water Corporation)"
RULES_PHASE12_WATERCORP = [
    r("svc_water_connection_verification", "wc_water", "metadata-only", "Water service connection",
      "Water Corporation water service connection requirements" + WC_PTR,
      "verify: potable water service available/connection approved with Water Corporation before occupancy"),
    r("svc_sewer_connection_verification", "wc_sewer", "metadata-only", "Wastewater connection",
      "Water Corporation wastewater connection requirements" + WC_PTR,
      "verify: sewer connection or approved on-site wastewater disposal per Water Corporation / health requirements"),
    r("svc_watercorp_referral_trigger", "wc_ref", "metadata-only", "Water Corporation referral",
      "Water Corporation referral requirements" + WC_PTR,
      "trigger: subdivision/development affecting Water Corporation infrastructure referred to Water Corporation for conditions"),
    r("svc_stormwater_drainage_connection", "wc_storm", "metadata-only", "Stormwater drainage",
      "Local government / Water Corporation stormwater drainage requirements" + WC_PTR,
      "verify: stormwater disposal to approved drainage system or on-site containment per local government requirements"),
]

WP_PTR = " (metadata-only verification pointer - Western Power technical requirements not stored; verify with Western Power)"
RULES_PHASE12_WESTERNPOWER = [
    r("svc_power_connection_verification", "wp_conn", "metadata-only", "Electricity connection",
      "Western Power connection requirements" + WP_PTR,
      "verify: electricity connection available/applied for with Western Power before occupancy"),
    r("svc_underground_power_check", "wp_ug", "metadata-only", "Underground power requirement",
      "Western Power / local government underground power requirements" + WP_PTR,
      "check: whether underground power required for new development/subdivision in the locality"),
    r("svc_westernpower_design_approval", "wp_design", "metadata-only", "Network design approval",
      "Western Power network design approval requirements" + WP_PTR,
      "trigger: developments requiring network extension/upgrade need Western Power design approval"),
    r("svc_transmission_easement_check", "wp_ease", "metadata-only", "Transmission easement proximity",
      "Western Power transmission corridor/easement constraints" + WP_PTR,
      "check: proximity to transmission lines/easements; building exclusion zones vary - verify with Western Power",
      ev="needs_human_review"),
]

Q_DF7 = ("Subject to this Act the owners of adjoining lands not divided by a sufficient fence are "
         "liable to join in or contribute in equal proportions to the construction of a dividing "
         "fence between those lands.")
Q_DF8 = ("An owner of land desiring to compel the owner of adjoining land to join in or contribute "
         "to the construction of a dividing fence under this Act may give him a notice which shall")
Q_DFDEF = ("dividing fence means a fence that separates the lands of different owners whether the "
           "fence is on the common boundary")
Q_DF9 = ("determine - (g) the boundary or line upon which the dividing fence is to be constructed")
Q_DF14 = ("14. Liability of adjoining owners to repair dividing fence")

RULES_PHASE12_DIVIDING_FENCES = [
    r("fence_cost_sharing_trigger", "df_s7", "s.7", "Equal cost sharing",
      Q_DF7,
      "trigger: owners of adjoining lands not divided by a sufficient fence are liable to contribute in equal proportions to construction (Dividing Fences Act 1961 s.7)"),
    r("fence_notice_trigger", "df_s8", "s.8", "Notice to adjoining owner",
      Q_DF8,
      "trigger: owner may give notice to adjoining owner to compel contribution to a dividing fence (s.8 notice requirements)"),
    r("fence_dividing_fence_definition", "df_def", "s.5 (definitions)", "Dividing fence definition",
      Q_DFDEF,
      "check: 'dividing fence' separates lands of different owners whether or not on the common boundary"),
    r("fence_court_boundary_determination", "df_s9", "s.9", "Court determination on dispute",
      Q_DF9,
      "trigger: where owners disagree on need/kind of fence, Magistrates Court may determine matters including the boundary line (s.9)"),
    r("fence_repair_liability", "df_s14", "s.14", "Repair liability",
      Q_DF14,
      "trigger: adjoining owners liable to repair dividing fence (s.14) - exact apportionment to be verified against current consolidated text",
      ev="needs_human_review"),
]

TL_PTR = " (metadata-only register - tree preservation local laws vary per council; verify applicable local law)"
RULES_PHASE12_TREELAW = [
    r("tree_preservation_permit_check", "tl_check", "metadata-only", "Tree preservation permit check",
      "WA local government tree preservation local laws (generic)" + TL_PTR,
      "trigger: check whether the applicable council has a tree preservation/significant tree local law requiring a permit for removal or pruning of regulated trees"),
    r("tree_local_law_per_council", "tl_council", "metadata-only", "Per-council tree local law",
      "WA local government tree preservation local laws (generic)" + TL_PTR,
      "check: per-council variation - regulated species, trunk diameter thresholds and exemptions differ by local government; requires per-council verification",
      ev="needs_human_review"),
]

# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------

REPORTS = []  # (filename, source_key_or_uuid, instrument_section, rules, warnings)


def main() -> int:
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()

    # 1. Ensure metadata-only sources
    sv_ids: dict[str, str] = {}
    for key, spec in METADATA_SOURCES.items():
        cur.execute(
            "SELECT id FROM source_documents WHERE title = %s AND authority = %s",
            (spec["title"], spec["authority"]),
        )
        row = cur.fetchone()
        if not row and spec["canonical_url"]:
            cur.execute(
                "SELECT id FROM source_documents WHERE authority = %s AND canonical_url = %s",
                (spec["authority"], spec["canonical_url"]),
            )
            row = cur.fetchone()
        if row:
            doc_id = str(row[0])
        else:
            doc_id = str(uuid4())
            cur.execute(
                """INSERT INTO source_documents
                   (id, title, jurisdiction, authority, source_type, canonical_url,
                    access_type, status, metadata_json, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, 'public', 'active',
                           %s::jsonb, now(), now())""",
                (doc_id, spec["title"], spec["jurisdiction"], spec["authority"],
                 spec["source_type"], spec["canonical_url"],
                 json.dumps({"metadata_only": True, "note": spec["note"]})),
            )
        cur.execute(
            "SELECT id FROM source_versions WHERE source_id = %s AND version_label = %s",
            (doc_id, spec["version_label"]),
        )
        vrow = cur.fetchone()
        if vrow:
            sv_ids[key] = str(vrow[0])
        else:
            vid = str(uuid4())
            descriptor = f"metadata-only:{spec['title']}:{spec['version_label']}"
            sha = hashlib.sha256(descriptor.encode()).hexdigest()
            cur.execute(
                """INSERT INTO source_versions
                   (id, source_id, version_label, sha256, storage_manifest_json,
                    licence_status, review_status, effective_from, fetched_at,
                    metadata_json, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s::jsonb, %s, 'approved', NULL, now(),
                           %s::jsonb, now(), now())""",
                (vid, doc_id, spec["version_label"], sha,
                 json.dumps({"metadata_only": True, "note": spec["note"],
                             "no_content_stored": True}),
                 spec["licence_status"],
                 json.dumps({"metadata_only": True, "registered_by": "operator",
                             "note": spec["note"]})),
            )
            sv_ids[key] = vid
    conn.commit()

    sv = {
        "ncc": sv_ids["ncc"], "flood": sv_ids["flood"], "ass": sv_ids["ass"],
        "watercorp": sv_ids["watercorp"], "westernpower": sv_ids["westernpower"],
        "treelaw": sv_ids["treelaw"],
        "bushfire": SV_BUSHFIRE_GUIDELINES, "heritage": SV_HERITAGE_ACT,
        "coastal": SV_COASTAL_SPP26, "contaminated": SV_CONTAMINATED,
        "dividing_fences": SV_DIVIDING_FENCES,
    }

    reports = [
        ("phase4_ncc_extraction.json", "ncc", "Volume Two Housing Provisions", RULES_PHASE4_NCC,
         ["Licence-constrained: NCC 2022 full text not downloaded/stored. All rules are verification pointers.",
          "Operator example cited H3P1 for ceiling heights; verified identifier is H4P2/H4D4 (room heights). H3P1 is 'Spread of fire'."]),
        ("phase7_bushfire_extraction.json", "bushfire", "Guidelines v1.4", RULES_PHASE7_BUSHFIRE,
         ["wa.gov.au file name for this v1.4 PDF is marked 'repealed'; registered per operator instruction. Confirm current edition before relying on these rules.",
          "AS 3959 BAL heat-flux values are paid Standards content and were deliberately not codified."]),
        ("phase7_heritage_extraction.json", "heritage", "Part 5 / s.129", RULES_PHASE7_HERITAGE, []),
        ("phase7_coastal_extraction.json", "coastal", "SPP 2.6", RULES_PHASE7_COASTAL, []),
        ("phase10_bal_extraction.json", "bushfire", "Guidelines Table 2 overlays", RULES_PHASE10_BAL,
         ["BAL overlay categories are names/triggers only; AS 3959 values deliberately not codified."]),
        ("phase10_flood_extraction.json", "flood", "metadata-only", RULES_PHASE10_FLOOD,
         ["Metadata-only source; referral triggers only."]),
        ("phase10_contaminated_extraction.json", "contaminated", "Contaminated Sites Act 2003", RULES_PHASE10_CONTAMINATED,
         ["Reused pre-existing approved source version (no duplicate registration)."]),
        ("phase10_ass_extraction.json", "ass", "metadata-only", RULES_PHASE10_ASS,
         ["Metadata-only source; referral triggers only."]),
        ("phase10_coastal_extraction.json", "coastal", "SPP 2.6 setbacks", RULES_PHASE10_COASTAL, []),
        ("phase12_watercorp_extraction.json", "watercorp", "metadata-only", RULES_PHASE12_WATERCORP,
         ["Metadata-only source; service verification triggers only."]),
        ("phase12_westernpower_extraction.json", "westernpower", "metadata-only", RULES_PHASE12_WESTERNPOWER,
         ["Metadata-only source; service verification triggers only."]),
        ("phase12_dividing_fences_extraction.json", "dividing_fences", "Parts II-III", RULES_PHASE12_DIVIDING_FENCES,
         ["Reused pre-existing approved source version (no duplicate registration)."]),
        ("phase12_tree_locallaw_extraction.json", "treelaw", "metadata-only", RULES_PHASE12_TREELAW,
         ["Generic per-council register; per-council verification flagged."]),
    ]

    # 2. Ensure clauses (idempotent on uq_clauses_version_key)
    clause_ids: dict[tuple[str, str], str] = {}
    for _fname, skey, _sec, rules, _w in reports:
        for rule in rules:
            k = (skey, rule["clause_key"])
            if k in clause_ids:
                continue
            cur.execute(
                "SELECT id FROM clauses WHERE source_version_id = %s AND clause_key = %s",
                (sv[skey], rule["clause_key"]),
            )
            row = cur.fetchone()
            if row:
                clause_ids[k] = str(row[0])
            else:
                cid = str(uuid4())
                cur.execute(
                    """INSERT INTO clauses
                       (id, source_version_id, source_chunk_id, parent_clause_id,
                        clause_key, clause_path, clause_type, title, section_ref,
                        disposition, text, quote, parser_name, parser_version,
                        metadata_json, created_at, updated_at)
                       VALUES (%s, %s, NULL, NULL, %s, %s, 'clause', %s, %s,
                               'rule_bearing', %s, %s, 'operator_handbuilt', 'v1',
                               '{}', now(), now())""",
                    (cid, sv[skey], rule["clause_key"], rule["clause_key"],
                     rule["clause_title"], rule["section_ref"],
                     rule["quote"], rule["quote"]),
                )
                clause_ids[k] = cid
    conn.commit()

    # 3. Emit report JSONs
    out_paths = []
    for fname, skey, section, rules, warnings in reports:
        candidates = []
        for rule in rules:
            candidates.append({
                "rule_key": rule["rule_key"],
                "canonical_rule_key": rule["rule_key"],
                "rule_type": "standard",
                "pathway": "none",
                "dwelling_type": None,
                "applicable_r_codes": ["ALL"],
                "applicable_zones": None,
                "council_scope": None,
                "operator": "eq",
                "value_json": {"raw_text": rule["raw_text"]},
                "unit": None,
                "condition_json": {},
                "quote": rule["quote"],
                "instrument_section": section,
                "table_reference": None,
                "effective_from": None,
                "effective_to": None,
                "source_version_id": sv[skey],
                "clause_id": clause_ids[(skey, rule["clause_key"])],
                "extractor_model": "operator_handbuilt:v1",
                "check_type": rule["check_type"],
                "evaluable": rule["evaluable"],
            })
        report = {
            "source_version_id": sv[skey],
            "instrument_section": section,
            "candidates_extracted": len(candidates),
            "warnings": warnings,
            "candidates": candidates,
        }
        path = f"/app/reports/{fname}"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        out_paths.append(path)

    conn.close()
    print(json.dumps({"source_version_ids": sv, "reports": out_paths}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
