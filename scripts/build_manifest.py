"""Build data/manifest.csv for the WA Planning Corpus.

Seed rows are curated from the live DPLH / legislation.wa.gov.au / council
index pages (verified 2026-06-10). Discovery crawls then fill:
  - Fremantle LPPs (FRE-LPP-*)
  - subsidiary legislation under the P&D Act (REG-*)
  - other Acts' home pages (LEG-*)
  - Melville LPS6 scheme text + map sheets from the wa.gov.au collection
Joondalup LPPs are appended by scripts/joondalup_lpps.py (playwright crawl).

Idempotent: re-running preserves status/notes of existing rows (merged by id).

Usage: python scripts/build_manifest.py [--no-discover]
"""
from __future__ import annotations

import asyncio
import re
import sys

from bs4 import BeautifulSoup

from acquire_all import http_get, make_client
from corpus_lib import (
    MANIFEST_PATH,
    log,
    normalize_name,
    read_manifest,
    today,
    write_manifest,
)

WA = "https://www.wa.gov.au"
LEG = "https://www.legislation.wa.gov.au/legislation/statutes.nsf"
MEL = "https://www.melvillecity.com.au"
MELG = "https://www.melville.wa.gov.au"
FRE = "https://www.fremantle.wa.gov.au"

SPP_INDEX = f"{WA}/government/document-collections/planning-codes-and-state-planning-policies"
DC_INDEX = f"{WA}/organisation/department-of-planning-lands-and-heritage/development-control-and-operational-policies"
PS_INDEX = f"{WA}/organisation/department-of-planning-lands-and-heritage/position-statements"
PB_INDEX = f"{WA}/government/document-collections/planning-bulletins"
MEL_LPP_INDEX = f"{MEL}/planning-and-building/local-planning-strategy,-scheme-policies-and-plans/local-planning-policies"
MEL_SCH_INDEX = f"{WA}/government/document-collections/city-of-melville-planning-information"
MEL_SP_INDEX = f"{MEL}/planning-and-building/local-planning-strategy,-scheme-policies-and-plans/activity-centre-and-structure-plans"
FRE_LPP_INDEX = f"{FRE}/planning-and-building/town-planning/local-planning-policies/"
FRE_SCH_INDEX = f"{FRE}/planning-and-building/town-planning/town-planning-documents/"
JOO_LPP_INDEX = "https://www.joondalup.wa.gov.au/plan-and-build/localplanninginformationandpolicies/local-planning-policies"
NCC_INDEX = "https://ncc.abcb.gov.au"

WAPC = "Western Australian Planning Commission"
DPLH = "Department of Planning, Lands and Heritage"
WAGOV = "Government of Western Australia"


def mel_asset(path: str) -> str:
    return f"{MEL}{path}"


# (id, name, category, authority, index_url, canonical_url, version_hint, status, notes)
SEED: list[tuple[str, str, str, str, str, str, str, str, str]] = [
    # --- Planning codes (R-Codes) ---
    ("PC-001", "State Planning Policy 7.3 Residential Design Codes Volume 1", "planning_code", WAPC,
     SPP_INDEX, f"{WA}/government/document-collections/state-planning-policy-73-residential-design-codes",
     "current consolidated", "pending", "R-Codes Vol 1"),
    ("PC-002", "State Planning Policy 7.3 Residential Design Codes Volume 2 - Apartments", "planning_code", WAPC,
     SPP_INDEX, f"{WA}/government/document-collections/state-planning-policy-73-residential-design-codes-apartments",
     "current consolidated", "pending", "R-Codes Vol 2 (apartments)"),
    # --- State Planning Policies ---
    ("SPP-001", "State Planning Policy 1 State Planning Framework", "SPP", WAPC,
     SPP_INDEX, f"{WA}/system/files/2021-06/SPP_1_State_Planning_Framework.pdf", "2021", "pending", ""),
    ("SPP-002", "State Planning Policy 2.0 Environment and Natural Resources Policy", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-20-environment-and-natural-resources-policy", "", "pending", ""),
    ("SPP-003", "State Planning Policy 2.4 Planning for Basic Raw Materials", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-24-basic-raw-materials", "", "pending", ""),
    ("SPP-004", "State Planning Policy 2.5 Rural Planning", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-25-rural-planning", "", "pending", ""),
    ("SPP-005", "State Planning Policy 2.6 State Coastal Planning", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-26-coastal-planning", "", "pending", ""),
    ("SPP-006", "State Planning Policy 2.8 Bushland Policy for the Perth Metropolitan Region", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-28-bushland-policy-the-perth-metropolitan-region", "", "pending", ""),
    ("SPP-007", "State Planning Policy 2.9 Planning for Water", "SPP", WAPC,
     SPP_INDEX, "https://www.planning.wa.gov.au/state-planning-policy-2.9-water", "", "pending", ""),
    ("SPP-008", "State Planning Policy 3.0 Urban Growth and Settlement", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-30-urban-growth-and-settlement", "", "pending", ""),
    ("SPP-009", "State Planning Policy 3.2 Aboriginal Settlements", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-32-aboriginal-settlements", "", "pending", ""),
    ("SPP-010", "State Planning Policy 3.4 Natural Hazards and Disasters", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-34-natural-hazards-and-disasters", "", "pending", ""),
    ("SPP-011", "State Planning Policy 3.5 Historic Heritage Conservation", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-35-historic-heritage-conservation", "", "pending", ""),
    ("SPP-012", "State Planning Policy 3.6 Infrastructure Contributions", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-36-infrastructure-contributions", "", "pending", ""),
    ("SPP-013", "State Planning Policy 3.7 Planning in Bushfire Prone Areas", "SPP", WAPC,
     SPP_INDEX, "https://www.planning.wa.gov.au/state-planning-policy-3.7-bushfire", "", "pending", ""),
    ("SPP-014", "State Planning Policy 4.1 Industrial Interface", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/draft-state-planning-policy-41-industrial-interface", "", "pending",
     "URL slug says draft - verify which version this serves"),
    ("SPP-015", "State Planning Policy 4.2 Activity Centres for Perth and Peel", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-42-activity-centres-perth-and-peel", "", "pending", ""),
    ("SPP-016", "State Planning Policy 5.1 Land Use Planning in the Vicinity of Perth Airport", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-51-land-use-planning-the-vicinity-of-perth-airport", "", "pending", ""),
    ("SPP-017", "State Planning Policy 5.2 Telecommunications Infrastructure", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-52-telecommunications-infrastructure", "", "pending", ""),
    ("SPP-018", "State Planning Policy 5.3 Land Use Planning in the Vicinity of Jandakot Airport", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-53-land-use-planning-the-vicinity-of-jandakot-airport", "", "pending", ""),
    ("SPP-019", "State Planning Policy 5.4 Road and Rail Noise", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-54-road-and-rail-noise", "", "pending", ""),
    ("SPP-020", "State Planning Policy 6.1 Leeuwin-Naturaliste Ridge", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-61-leeuwin-naturaliste-ridge", "", "pending", ""),
    ("SPP-021", "State Planning Policy 6.3 Ningaloo Coast", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-63-ningaloo-coast", "", "pending", ""),
    ("SPP-022", "State Planning Policy 7.0 Design of the Built Environment", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-70-design-of-the-built-environment", "", "pending", ""),
    ("SPP-023", "State Planning Policy 7.2 Precinct Design", "SPP", WAPC,
     SPP_INDEX, f"{WA}/government/publications/state-planning-policy-72-precinct-design", "", "pending", ""),
    # --- Development Control / Operational policies ---
    ("DC-001", "Operational Policy 1.1 Subdivision of Land - General Principles", "DC", WAPC,
     DC_INDEX, f"{WA}/government/publications/operational-policy-11-subdivision-of-land-general-principles", "", "pending", ""),
    ("DC-002", "Development Control Policy 1.3 Strata Titles", "DC", WAPC,
     DC_INDEX, f"{WA}/government/publications/development-control-policy-13-strata-titles", "", "pending", ""),
    ("DC-003", "Development Control Policy 1.5 Bicycle Planning", "DC", WAPC,
     DC_INDEX, f"{WA}/government/publications/development-control-policy-15-bicycle-planning", "", "pending", ""),
    ("DC-004", "Development Control Policy 1.6 Planning to Support Transit Use and Development", "DC", WAPC,
     DC_INDEX, f"{WA}/government/publications/development-control-policy-16-planning-support-transit-use-and-development", "", "pending", ""),
    ("DC-005", "Development Control Policy 1.7 General Road Planning", "DC", WAPC,
     DC_INDEX, f"{WA}/government/publications/development-control-policy-17-general-road-planning", "", "pending", ""),
    ("DC-006", "Development Control Policy 1.8 Canal Estates and Artificial Waterway Developments", "DC", WAPC,
     DC_INDEX, f"{WA}/government/publications/development-control-policy-18-canal-estates-and-artificial-waterway-developments", "", "pending", ""),
    ("DC-007", "Development Control Policy 1.10 Freeway Service Centres and Roadhouses", "DC", WAPC,
     DC_INDEX, f"{WA}/government/publications/development-control-policy-110-freeway-services-centres-roadhouses-incl-signage", "", "pending", ""),
    ("DC-008", "Development Control Policy 1.11 Community Schemes", "DC", WAPC,
     DC_INDEX, f"{WA}/government/publications/development-control-policy-111-community-schemes", "", "pending", ""),
    ("DC-009", "Development Control Policy 2.2 Residential Subdivision", "DC", WAPC,
     DC_INDEX, f"{WA}/government/publications/development-control-policy-22-residential-subdivision", "", "pending", ""),
    ("DC-010", "Development Control Policy 2.4 School Sites", "DC", WAPC,
     DC_INDEX, f"{WA}/government/publications/development-control-policy-24-school-sites", "", "pending", ""),
    ("DC-011", "Development Control Policy 2.6 Residential Road Planning", "DC", WAPC,
     DC_INDEX, f"{WA}/government/publications/development-control-policy-26-residential-road-planning", "", "pending", ""),
    ("DC-012", "Development Control Policy 3.4 Subdivision of Rural Land", "DC", WAPC,
     DC_INDEX, f"{WA}/government/publications/development-control-policy-34-subdivision-of-rural-land", "", "pending", ""),
    ("DC-013", "Development Control Policy 4.1 Industrial Subdivision", "DC", WAPC,
     DC_INDEX, f"{WA}/government/publications/development-control-policy-41-industrial-subdivision", "", "pending", ""),
    ("DC-014", "Development Control Policy 4.2 Planning for Hazards and Safety", "DC", WAPC,
     DC_INDEX, f"{WA}/government/publications/development-control-policy-42-planning-hazards-and-safety", "", "pending", ""),
    ("DC-015", "Development Control Policy 5.1 Regional Roads (Vehicular Access)", "DC", WAPC,
     DC_INDEX, f"{WA}/government/publications/development-control-policy-51-regional-roads-vehicular-access", "", "pending", ""),
    ("DC-016", "Development Control Policy 5.3 Use of Land Reserved for Parks, Recreation and Regional Open Space", "DC", WAPC,
     DC_INDEX, f"{WA}/government/publications/development-control-policy-53-use-of-land-reserved-parks-recreation-and-regional-open-space", "", "pending", ""),
    ("DC-017", "Development Control Policy 5.4 Advertising on Reserved Land", "DC", WAPC,
     DC_INDEX, f"{WA}/government/publications/development-control-policy-54-advertising-reserved-land", "", "pending", ""),
    # --- Position statements ---
    ("PS-001", "Position Statement: Purpose-built Student Accommodation", "position_statement", WAPC,
     PS_INDEX, f"{WA}/government/publications/position-statement-purpose-built-student-accommodation", "", "pending", ""),
    ("PS-002", "Position Statement: Public Open Space", "position_statement", WAPC,
     PS_INDEX, f"{WA}/government/document-collections/position-statement-public-open-space", "", "pending", ""),
    ("PS-003", "Position Statement: Planning for Tourism and Short-term Rental Accommodation", "position_statement", WAPC,
     PS_INDEX, f"{WA}/system/files/2024-11/position-statement-planning-for-tourism-active-nov-2024.pdf", "Nov 2024", "pending", ""),
    ("PS-004", "Position Statement: Electric Vehicle Charging Infrastructure", "position_statement", WAPC,
     PS_INDEX, f"{WA}/government/publications/draft-position-statement-electric-vehicle-charging-infrastructure", "", "pending",
     "URL slug says draft - verify which version this serves"),
    ("PS-005", "Position Statement: Special Residential Zones", "position_statement", WAPC,
     PS_INDEX, f"{WA}/government/publications/position-statement-special-residential-zone", "", "pending", ""),
    ("PS-006", "Position Statement: Residential Accommodation for Ageing Persons", "position_statement", WAPC,
     PS_INDEX, f"{WA}/government/publications/position-statement-residential-accommodation-ageing-persons", "", "pending", ""),
    ("PS-007", "Position Statement: Container Deposit Scheme Infrastructure", "position_statement", WAPC,
     PS_INDEX, f"{WA}/government/publications/position-statement-container-deposit-scheme-infrastructure", "", "pending", ""),
    ("PS-008", "Position Statement: Renewable Energy Facilities", "position_statement", WAPC,
     PS_INDEX, f"{WA}/government/publications/position-statement-renewable-energy-facilities", "", "pending", ""),
    ("PS-009", "Position Statement: Housing on Lots Less than 100m2", "position_statement", WAPC,
     PS_INDEX, f"{WA}/government/publications/position-statement-housing-lots-less-100m2", "", "pending", ""),
    ("PS-010", "Position Statement: Workforce Accommodation", "position_statement", WAPC,
     PS_INDEX, f"{WA}/government/publications/position-statement-workforce-accommodation", "", "pending", ""),
    ("PS-011", "Position Statement: Dark Sky and Astrotourism", "position_statement", WAPC,
     PS_INDEX, f"{WA}/government/publications/draft-planning-position-statement-dark-sky-and-astrotourism", "", "pending",
     "URL slug says draft - verify which version this serves"),
    # --- Planning bulletins (residential-relevant subset) ---
    ("PB-001", "Planning Bulletin 33 Rights-of-way or Laneways in Established Areas", "planning_bulletin", WAPC,
     PB_INDEX, f"{WA}/system/files/2021-07/PB_33_Rights_of_way.pdf", "", "pending", ""),
    ("PB-002", "Planning Bulletin 112 Medium-density Single House Development Standards", "planning_bulletin", WAPC,
     PB_INDEX, f"{WA}/system/files/2024-04/planning_bulletin_112-mar2024.pdf", "Mar 2024", "pending", ""),
    ("PB-003", "Planning Bulletin 113 Multiple Dwellings in R40 Coded Areas", "planning_bulletin", WAPC,
     PB_INDEX, f"{WA}/system/files/2021-07/PB_113_multiple_dwellings_R40_44526.pdf", "", "pending", ""),
    ("PB-004", "Planning Bulletin 114 Residential Design Codes Volume 1 and 2", "planning_bulletin", WAPC,
     PB_INDEX, f"{WA}/system/files/2024-03/planning_bulletin_114_mar20242.pdf", "Mar 2024", "pending", ""),
    ("PB-005", "Planning Bulletin 115 Short-Term Rental Accommodation Guide", "planning_bulletin", WAPC,
     PB_INDEX, f"{WA}/system/files/2024-09/planning_bulletin_115_2024_0.pdf", "2024", "pending", ""),
    ("PB-006", "Planning Bulletin 100 State Planning Policy 3.6 Development Contributions", "planning_bulletin", WAPC,
     PB_INDEX, f"{WA}/system/files/2021-07/PB_100_SPP3-6_development_contributions_infrastructure.pdf", "", "pending", ""),
    ("PB-007", "Planning Bulletin 107 Model Subdivision Conditions", "planning_bulletin", WAPC,
     PB_INDEX, f"{WA}/system/files/2021-07/PB_107_New_Model_Subdivision.pdf", "", "pending", ""),
    # --- Legislation ---
    ("LEG-001", "Planning and Development Act 2005", "legislation", "Parliament of Western Australia",
     f"{LEG}/actsif_p.html", f"{LEG}/RedirectURL?OpenAgent&query=mrdoc_49203.pdf", "consolidated 19 Feb 2026", "pending",
     "official consolidated PDF"),
    ("LEG-002", "Building Act 2011", "legislation", "Parliament of Western Australia",
     f"{LEG}/actsif_b.html", "", "current consolidated", "pending", "resolve via actsif_b.html"),
    ("LEG-003", "Building Regulations 2012", "legislation", "Parliament of Western Australia",
     f"{LEG}/law_a146877_subsidiary.html", "", "current consolidated", "pending", "resolve via Building Act subsidiary page"),
    ("LEG-004", "Strata Titles Act 1985", "legislation", "Parliament of Western Australia",
     f"{LEG}/actsif_s.html", "", "current consolidated", "pending", "resolve via actsif_s.html"),
    ("LEG-005", "Environmental Protection Act 1986", "legislation", "Parliament of Western Australia",
     f"{LEG}/actsif_e.html", "", "current consolidated", "pending", "resolve via actsif_e.html"),
    ("LEG-006", "Bush Fires Act 1954", "legislation", "Parliament of Western Australia",
     f"{LEG}/actsif_b.html", "", "current consolidated", "pending", "resolve via actsif_b.html"),
    ("LEG-007", "Heritage Act 2018", "legislation", "Parliament of Western Australia",
     f"{LEG}/actsif_h.html", "", "current consolidated", "pending", "resolve via actsif_h.html"),
    ("REG-001", "Planning and Development (Local Planning Schemes) Regulations 2015", "legislation", "Parliament of Western Australia",
     f"{LEG}/law_a9408_subsidiary.html", "", "current consolidated incl Schedule 2 deemed provisions", "pending",
     "resolve via P&D Act subsidiary page"),
    ("REG-002", "Planning and Development (Development Assessment Panels) Regulations 2011", "legislation", "Parliament of Western Australia",
     f"{LEG}/law_a9408_subsidiary.html", "", "current consolidated", "pending", "resolve via P&D Act subsidiary page"),
    ("REG-003", "Planning and Development Regulations 2009", "legislation", "Parliament of Western Australia",
     f"{LEG}/law_a9408_subsidiary.html", "", "current consolidated", "pending", "resolve via P&D Act subsidiary page"),
    # --- Region schemes ---
    ("RS-001", "Metropolitan Region Scheme", "region_scheme", WAPC,
     f"{WA}/government/document-collections/metropolitan-region-scheme", f"{WA}/government/document-collections/metropolitan-region-scheme",
     "current scheme text", "pending", "MRS scheme text"),
    ("RS-002", "Peel Region Scheme", "region_scheme", WAPC,
     f"{WA}/government/document-collections/peel-region-scheme", f"{WA}/government/document-collections/peel-region-scheme",
     "current scheme text", "pending", ""),
    ("RS-003", "Greater Bunbury Region Scheme", "region_scheme", WAPC,
     f"{WA}/government/document-collections/greater-bunbury-region-scheme", f"{WA}/government/document-collections/greater-bunbury-region-scheme",
     "current scheme text", "pending", ""),
    # --- City of Melville: scheme + strategy + maps ---
    ("MEL-SCH-001", "City of Melville Local Planning Scheme No. 6 - Scheme Text", "scheme", "City of Melville",
     MEL_SCH_INDEX, MEL_SCH_INDEX, "current consolidated", "pending", "scheme text hosted in wa.gov.au collection"),
    ("MEL-SCH-002", "City of Melville Local Planning Strategy", "strategy", "City of Melville",
     MEL_LPP_INDEX.rsplit("/", 1)[0], mel_asset("/getContentAsset/953e49d3-7475-4236-85b0-315d9243f3a3/3ca954ad-3848-47c6-8f97-68cebe0b47a2/city-of-melville-local-planning-strategy?language=en"),
     "", "pending", ""),
    ("MEL-MAP-001", "City of Melville LPS6 Scheme Map Sheet 1", "scheme_map", "City of Melville", MEL_SCH_INDEX, "", "", "pending", "resolve from wa.gov.au Melville collection"),
    ("MEL-MAP-002", "City of Melville LPS6 Scheme Map Sheet 2", "scheme_map", "City of Melville", MEL_SCH_INDEX, "", "", "pending", "resolve from wa.gov.au Melville collection"),
    ("MEL-MAP-003", "City of Melville LPS6 Scheme Map Sheet 3", "scheme_map", "City of Melville", MEL_SCH_INDEX, "", "", "pending", "resolve from wa.gov.au Melville collection"),
    ("MEL-MAP-004", "City of Melville LPS6 Scheme Map Sheet 4", "scheme_map", "City of Melville", MEL_SCH_INDEX, "", "", "pending", "resolve from wa.gov.au Melville collection"),
    ("MEL-MAP-005", "City of Melville LPS6 Scheme Map Sheet 5", "scheme_map", "City of Melville", MEL_SCH_INDEX, "", "", "pending", "resolve from wa.gov.au Melville collection"),
    ("MEL-MAP-006", "City of Melville LPS6 Scheme Map Sheet 6", "scheme_map", "City of Melville", MEL_SCH_INDEX, "", "", "pending", "resolve from wa.gov.au Melville collection"),
    ("MEL-MAP-007", "City of Melville LPS6 Scheme Map Sheet 7", "scheme_map", "City of Melville", MEL_SCH_INDEX, "", "", "pending", "resolve from wa.gov.au Melville collection"),
    ("MEL-MAP-008", "City of Melville LPS6 Scheme Map Sheet 8", "scheme_map", "City of Melville", MEL_SCH_INDEX, "", "", "pending", "resolve from wa.gov.au Melville collection"),
]

# Melville LPPs sorted by policy number -> MEL-LPP-### (matches workbench ids:
# 1.9 -> 009, 1.17 -> 014, 3.1 -> 021)
MEL_LPPS: list[tuple[str, str, str]] = [
    ("1.1", "Planning Process and Decision Making", "/getContentAsset/0e1cbf0b-d0fd-4377-b62d-60de395848a3/3ca954ad-3848-47c6-8f97-68cebe0b47a2/LPP1-1-Planning-Process-and-Decision-Making-May-2025.pdf?language=en"),
    ("1.2", "Design Review Panel", "/getContentAsset/2fdfcfa4-c637-4f26-acc5-8f8af024d544/3ca954ad-3848-47c6-8f97-68cebe0b47a2/LPP-1-2-Design-Review-Panel.pdf?language=en"),
    ("1.3", "Waste and Recyclables Collection", "/getContentAsset/633ebfff-fbd1-430b-955a-4c094d7cd29d/3ca954ad-3848-47c6-8f97-68cebe0b47a2/waste-and-recyclables-collection-for-multiple-dwel?language=en"),
    ("1.4", "Provision of Public Art", "/getContentAsset/3c0e658f-1832-49e9-9fda-caba31787366/3ca954ad-3848-47c6-8f97-68cebe0b47a2/LPP-1-4-Provision-of-Public-Art-in-Development-Proposals.pdf?language=en"),
    ("1.5", "Energy Efficiency in Building Design", "/getContentAsset/8c17265a-6482-44ed-bbb4-cdba38cd6d33/3ca954ad-3848-47c6-8f97-68cebe0b47a2/energy-efficiency-in-building-design?language=en"),
    ("1.6", "Car Parking and Access", "/getContentAsset/f53fbfee-ea82-4f6f-bb3b-b617fbd122d4/3ca954ad-3848-47c6-8f97-68cebe0b47a2/LPP1-6-Parking-and-Access-Final-Version-June-2025.pdf?language=en"),
    ("1.7", "Telecommunications Facilities", "/getContentAsset/8c362444-1e5a-4104-a6a5-e0335ef16edf/3ca954ad-3848-47c6-8f97-68cebe0b47a2/LPP1-7-Telecommunications-Facilities-and-Communications-Equipment-FINAL.pdf?language=en"),
    ("1.8", "Crime Prevention Through Environmental Design", "/getContentAsset/b3236e04-a9b2-4e90-a58a-1f9c0e4511d1/3ca954ad-3848-47c6-8f97-68cebe0b47a2/crime-prevention-through-environmental-design-of-b?language=en"),
    ("1.9", "Height of Buildings", "/getContentAsset/9a1fae81-39e4-4433-9eb5-70ddb49f4d7f/3ca954ad-3848-47c6-8f97-68cebe0b47a2/height-of-buildings?language=en"),
    ("1.10", "Amenity Policy", "/getContentAsset/cb1f9aac-bef9-4b77-bacc-0b0afa09dac5/3ca954ad-3848-47c6-8f97-68cebe0b47a2/LPP1-10-Amenity-Policy.pdf?language=en"),
    ("1.12", "Child Minding Centres and Family Day Care", "/getContentAsset/7d19bbd6-e185-4952-808f-09c41d48596f/3ca954ad-3848-47c6-8f97-68cebe0b47a2/child-minding-centres-and-family-day-care?language=en"),
    ("1.14", "Temporary Structures", "/getContentAsset/e97109ff-e91a-47ef-8f97-51d64523553c/3ca954ad-3848-47c6-8f97-68cebe0b47a2/temporary-structures?language=en"),
    ("1.16", "Flood and Security Lighting", "/our-city/publications-and-forms/building-and-development/flood-and-security-lighting"),
    ("1.17", "Additional Development Exemptions", "/getContentAsset/c2b52afc-cdb6-4605-84a8-1019a3cf1c8b/3ca954ad-3848-47c6-8f97-68cebe0b47a2/additional-development-exemptions?language=en"),
    ("1.19", "Canning Bridge Activity Centre Plan - Community Benefit", "/getContentAsset/8d7b2dce-9569-44f5-a833-794108c1c7e1/3ca954ad-3848-47c6-8f97-68cebe0b47a2/local-planning-policy-canning-bridge-activity-ce?language=en"),
    ("1.20", "Canning Bridge Activity Centre Plan - Density and Bonus", "/getContentAsset/e80d231d-9d16-4c24-bc36-0bd702080a17/3ca954ad-3848-47c6-8f97-68cebe0b47a2/lpp1-20-canning-bridge-activity-centre-plan-E2-80-93-dens?language=en"),
    ("1.21", "Short Term Accommodation", "/getContentAsset/a4315d6b-c817-426e-8ed7-ddabdf53755f/3ca954ad-3848-47c6-8f97-68cebe0b47a2/short-term-accommodation?language=en"),
    ("1.22", "Construction Management Plans", "/getContentAsset/587dc567-816b-4325-b559-94eade617513/3ca954ad-3848-47c6-8f97-68cebe0b47a2/local-planning-policy-construction-management-plan?language=en"),
    ("2.1", "Non-Residential Development", "/getContentAsset/e33ebad7-9b3a-46a6-a5c8-71466ac52510/3ca954ad-3848-47c6-8f97-68cebe0b47a2/non-residential-development?language=en"),
    ("2.2", "Outdoor Advertising and Signage", "/getContentAsset/f9368ae7-c309-467a-a330-6928de37353a/3ca954ad-3848-47c6-8f97-68cebe0b47a2/local-planning-policy-outdoor-advertising-and-si?language=en"),
    ("3.1", "Residential Development", "/getContentAsset/916d8eac-8f3d-4b2a-9e26-66baeefe4e16/3ca954ad-3848-47c6-8f97-68cebe0b47a2/local-planning-policy-residential-development?language=en"),
    ("3.3", "Exhibition and Display Homes", "/getContentAsset/e3fb0de5-d57a-4763-8c26-bc2cbd615c6b/3ca954ad-3848-47c6-8f97-68cebe0b47a2/LPP3-3-Exhibition-and-Display-Homes-(FINAL).pdf?language=en"),
    ("3.4", "Tennis Courts", "/getContentAsset/ff4acaa0-64a2-4767-b43b-e5ed1606c002/3ca954ad-3848-47c6-8f97-68cebe0b47a2/local-planning-policy-tennis-courts?language=en"),
    ("3.5", "Home Occupation Relative to Sexual Services", "/getContentAsset/de47197f-3bb2-4c6f-a62c-e9a6cd76f58e/3ca954ad-3848-47c6-8f97-68cebe0b47a2/local-planning-policy-home-occupation-relative-t?language=en"),
    ("4.1", "RAAFA Master Plan", "/getContentAsset/3f701d20-cefa-45ba-9a49-ed0fe6a30941/3ca954ad-3848-47c6-8f97-68cebe0b47a2/local-planning-policy-royal-australian-air-force?language=en"),
    ("4.4", "Murdoch Health and Knowledge Precinct", "/getContentAsset/8886da73-06db-49ac-88a2-e06ebc0dedb5/3ca954ad-3848-47c6-8f97-68cebe0b47a2/local-planning-policy-E2-80-A2murdoch-health-and-knowle?language=en"),
    ("4.5", "Carawatha Development Design Guidelines", "/getContentAsset/fcf0b20b-84f5-47b1-a21e-0159c911ae3c/3ca954ad-3848-47c6-8f97-68cebe0b47a2/LPP-4-5-Carawatha-Development-Design-Guidelines_1.pdf?language=en"),
]

MEL_STRUCTURE_PLANS: list[tuple[str, str]] = [
    ("Canning Bridge Activity Centre Plan", f"{MELG}/planning-and-building/local-planning-strategy,-scheme-policies-and-plans/activity-centre-and-structure-plans/canningbridgeactivitycentre"),
    ("Kardinya District Precinct Plan", f"{MELG}/planning-and-building/local-planning-strategy,-scheme-policies-and-plans/activity-centre-and-structure-plans/kardinya-district-precinct-plan"),
    ("Melville City Centre Structure Plan", f"{MELG}/planning-and-building/local-planning-strategy,-scheme-policies-and-plans/activity-centre-and-structure-plans/melville-city-centre-structure-plan"),
    ("Melville District Activity Centre Structure Plan", f"{MELG}/planning-and-building/local-planning-strategy,-scheme-policies-and-plans/activity-centre-and-structure-plans/melville-district-activity-centre"),
    ("Murdoch Specialised Activity Centre Structure Plan", f"{MELG}/planning-and-building/local-planning-strategy,-scheme-policies-and-plans/activity-centre-and-structure-plans/murdoch-specialised-activity-centre"),
    ("Riseley Activity Centre Structure Plan", f"{MELG}/planning-and-building/local-planning-strategy,-scheme-policies-and-plans/activity-centre-and-structure-plans/riseley-activity-centre"),
    ("Willagee Structure Plan", f"{MELG}/planning-and-building/local-planning-strategy,-scheme-policies-and-plans/activity-centre-and-structure-plans/willagee-structure-plan"),
]

# --- Fremantle / Joondalup / NCC seeds (discovery fills the rest) ---
EXTRA_SEED: list[tuple[str, str, str, str, str, str, str, str, str]] = [
    ("FRE-SCH-001", "City of Fremantle Local Planning Scheme No. 4 - Scheme Text", "scheme", "City of Fremantle",
     FRE_SCH_INDEX, FRE_SCH_INDEX, "current consolidated", "pending", "resolve scheme text PDF from town planning documents page"),
    ("FRE-LPP-006", "City of Fremantle LPP 2.2 Split Density Codes", "LPP", "City of Fremantle",
     FRE_LPP_INDEX, "", "", "pending", "resolve from Fremantle LPP list"),
    ("NCC-001", "National Construction Code 2022 Volume One", "building_code", "Australian Building Codes Board",
     NCC_INDEX, f"{NCC_INDEX}/editions/ncc-2022/adopted/volume-one", "NCC 2022", "metadata_only",
     "NCC requires free registration to download; index metadata only"),
    ("NCC-002", "National Construction Code 2022 Volume Two", "building_code", "Australian Building Codes Board",
     NCC_INDEX, f"{NCC_INDEX}/editions/ncc-2022/adopted/volume-two", "NCC 2022", "metadata_only",
     "NCC requires free registration to download; index metadata only"),
    ("NCC-003", "NCC 2022 Housing Provisions Standard", "building_code", "Australian Building Codes Board",
     NCC_INDEX, f"{NCC_INDEX}/editions/ncc-2022/adopted/housing-provisions", "NCC 2022", "metadata_only",
     "NCC requires free registration to download; index metadata only"),
]


def _mel_sort_key(num: str) -> tuple[int, int]:
    major, minor = num.split(".")
    return int(major), int(minor)


def build_seed_rows() -> list[dict]:
    rows = []
    for t in SEED:
        rows.append(dict(zip(
            ("id", "instrument_name", "category", "issuing_authority", "index_source_url",
             "canonical_url", "expected_version_hint", "status", "notes"), t)))
    for i, (num, name, path) in enumerate(sorted(MEL_LPPS, key=lambda x: _mel_sort_key(x[0])), start=1):
        rows.append({
            "id": f"MEL-LPP-{i:03d}",
            "instrument_name": f"City of Melville LPP {num} {name}",
            "category": "LPP",
            "issuing_authority": "City of Melville",
            "index_source_url": MEL_LPP_INDEX,
            "canonical_url": mel_asset(path),
            "expected_version_hint": "",
            "status": "pending",
            "notes": "",
        })
    for i, (name, url) in enumerate(MEL_STRUCTURE_PLANS, start=1):
        rows.append({
            "id": f"MEL-SP-{i:03d}",
            "instrument_name": f"City of Melville {name}",
            "category": "structure_plan",
            "issuing_authority": "City of Melville",
            "index_source_url": MEL_SP_INDEX,
            "canonical_url": url,
            "expected_version_hint": "",
            "status": "pending",
            "notes": "",
        })
    for t in EXTRA_SEED:
        rows.append(dict(zip(
            ("id", "instrument_name", "category", "issuing_authority", "index_source_url",
             "canonical_url", "expected_version_hint", "status", "notes"), t)))
    for r in rows:
        r.setdefault("source_document_id", "")
        r.setdefault("last_checked_at", today())
    return rows


# ----------------------------- discovery ---------------------------------

async def discover_legislation(client, rows: list[dict]) -> None:
    """Fill canonical_url for LEG-*/REG-* rows from legislation.wa.gov.au pages."""
    targets = [r for r in rows if r["id"].startswith(("LEG-", "REG-")) and not r["canonical_url"]]
    pages: dict[str, str] = {}
    for r in targets:
        idx = r["index_source_url"]
        if idx not in pages:
            try:
                resp = await http_get(client, idx)
                pages[idx] = resp.text if resp.status_code < 400 else ""
            except Exception as exc:
                log(f"  legislation index fetch failed {idx}: {exc}")
                pages[idx] = ""
        html = pages[idx]
        if not html:
            continue
        soup = BeautifulSoup(html, "lxml")
        want = normalize_name(r["instrument_name"])
        for a in soup.find_all("a", href=True):
            text = normalize_name(a.get_text(" ", strip=True))
            if text.startswith(want) or want.startswith(text) and len(text) > 12:
                href = a["href"]
                if href.startswith("law_"):
                    href = f"{LEG}/{href}"
                r["canonical_url"] = href
                r["notes"] = (r["notes"] + " | url resolved from index page").strip(" |")
                log(f"  resolved {r['id']} -> {href[:90]}")
                break


async def discover_melville_collection(client, rows: list[dict]) -> None:
    """Fill MEL-SCH-001 and MEL-MAP-* from the wa.gov.au Melville collection."""
    try:
        resp = await http_get(client, MEL_SCH_INDEX)
    except Exception as exc:
        log(f"  melville collection fetch failed: {exc}")
        return
    if resp.status_code >= 400:
        log(f"  melville collection HTTP {resp.status_code}")
        return
    soup = BeautifulSoup(resp.text, "lxml")
    links = [(a.get_text(" ", strip=True), a["href"]) for a in soup.find_all("a", href=True)]
    for r in rows:
        if not r["id"].startswith("MEL-MAP-") or r["canonical_url"]:
            continue
        sheet = r["instrument_name"].rsplit(" ", 1)[-1]  # sheet number
        for text, href in links:
            low = text.lower()
            if "map" in low and re.search(rf"\b(?:sheet\s*)?{sheet}\b", low):
                r["canonical_url"] = href if href.startswith("http") else f"{WA}{href}"
                log(f"  resolved {r['id']} -> {r['canonical_url'][:90]}")
                break


async def discover_fremantle(client, rows: list[dict]) -> None:
    """Enumerate Fremantle LPPs; fill FRE-LPP-006, append the rest."""
    try:
        resp = await http_get(client, FRE_LPP_INDEX)
        html = resp.text
        if resp.status_code >= 400 or len(html) < 2000:
            raise RuntimeError(f"HTTP {resp.status_code}")
    except Exception:
        from fetch_js import fetch_rendered
        try:
            html, _, _ = await asyncio.to_thread(fetch_rendered, FRE_LPP_INDEX)
        except Exception as exc:
            log(f"  fremantle LPP crawl failed entirely: {exc}")
            return
    soup = BeautifulSoup(html, "lxml")
    found: list[tuple[str, str]] = []
    seen_urls: set[str] = set()
    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text(" ", strip=True).split())
        m = re.search(r"\b(?:LPP|local planning policy)\s*(\d+\.\d+)\b(.{0,80})", text, re.IGNORECASE)
        if not m:
            continue
        href = a["href"]
        url = href if href.startswith("http") else f"{FRE}{href}"
        if url in seen_urls:
            continue
        seen_urls.add(url)
        found.append((text[:120], url))
    if not found:
        log("  fremantle LPP crawl: no LPP links recognised (page may need manual review)")
        return
    existing_ids = {r["id"] for r in rows}
    by_norm = {normalize_name(r["instrument_name"]): r for r in rows if r["id"].startswith("FRE-LPP-")}
    next_n = 1
    for text, url in sorted(found):
        # split density goes to the seeded FRE-LPP-006
        if "split density" in text.lower():
            for r in rows:
                if r["id"] == "FRE-LPP-006" and not r["canonical_url"]:
                    r["canonical_url"] = url
                    log(f"  resolved FRE-LPP-006 -> {url[:90]}")
            continue
        if normalize_name(f"City of Fremantle {text}") in by_norm:
            continue
        while f"FRE-LPP-{next_n:03d}" in existing_ids or next_n == 6:
            next_n += 1
        new_id = f"FRE-LPP-{next_n:03d}"
        existing_ids.add(new_id)
        rows.append({
            "id": new_id,
            "instrument_name": f"City of Fremantle {text}",
            "category": "LPP",
            "issuing_authority": "City of Fremantle",
            "index_source_url": FRE_LPP_INDEX,
            "canonical_url": url,
            "expected_version_hint": "",
            "status": "pending",
            "source_document_id": "",
            "last_checked_at": today(),
            "notes": "discovered from Fremantle LPP index",
        })
    log(f"  fremantle discovery: {len(found)} LPP links")


async def discover(rows: list[dict]) -> None:
    async with make_client() as client:
        await discover_legislation(client, rows)
        await discover_melville_collection(client, rows)
        await discover_fremantle(client, rows)


def main() -> None:
    existing = {r["id"]: r for r in read_manifest()}
    rows = build_seed_rows()
    # idempotent merge: keep status/progress fields from any existing manifest
    for r in rows:
        old = existing.pop(r["id"], None)
        if old:
            for keep in ("status", "source_document_id", "last_checked_at", "notes"):
                if old.get(keep):
                    r[keep] = old[keep]
            if old.get("canonical_url"):
                r["canonical_url"] = old["canonical_url"]
    rows.extend(existing.values())  # rows added by other scripts (e.g. Joondalup)

    if "--no-discover" not in sys.argv:
        log("running discovery crawls...")
        asyncio.run(discover(rows))

    write_manifest(rows)
    n_url = sum(1 for r in rows if r.get("canonical_url"))
    log(f"manifest written: {len(rows)} rows ({n_url} with canonical_url) -> {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
