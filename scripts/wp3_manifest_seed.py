"""WP3 — generate idempotent SQL batches seeding target_manifest + instrument_aliases.

Data below was scraped 2026-06-10 from the six authoritative indexes
(CORPUS_COMPLETENESS_PLAN Phase 1) plus the audit docs DATA_SOURCES.md /
DATA_ACQUISITION_RUNBOOK.md. URLs verified with curl (see reports/wp3/url_check_*.txt).

Emits reports/wp3/batch_*.sql — apply each immediately (checkpoint per index).
"""
from __future__ import annotations

import uuid
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "reports" / "wp3"
ORG = "1d31c315-5087-47df-a8d4-ebfd08efad5d"
USER = "393277fe-3581-4a29-b394-a41cfc26f01b"

NS = uuid.UUID("7b1e5a52-4f2c-4cf7-9e83-0c8f2a3d6e91")  # WP3 deterministic-id namespace


def mid(name: str, auth: str) -> str:
    return str(uuid.uuid5(NS, f"manifest|{name}|{auth}"))


def q(s: str | None) -> str:
    if s is None:
        return "NULL"
    return "'" + s.replace("'", "''") + "'"


def manifest_row(name, category, auth, index_url, canon, status, note=None, version=None):
    return (
        f"INSERT INTO target_manifest (id, instrument_name, category, issuing_authority, "
        f"index_source_url, canonical_url, expected_version_hint, status, notes, "
        f"last_checked_at, created_at, updated_at) VALUES ("
        f"'{mid(name, auth)}', {q(name)}, {q(category)}, {q(auth)}, {q(index_url)}, "
        f"{q(canon)}, {q(version)}, {q(status)}, {q(note)}, now(), now(), now()) "
        f"ON CONFLICT (instrument_name, issuing_authority) DO UPDATE SET "
        f"canonical_url = EXCLUDED.canonical_url, index_source_url = EXCLUDED.index_source_url, "
        f"expected_version_hint = EXCLUDED.expected_version_hint, last_checked_at = now(), "
        f"updated_at = now();"
    )


def alias_row(alias, name, auth):
    aid = uuid.uuid5(NS, f"alias|{alias}|exact")
    return (
        f"INSERT INTO instrument_aliases (id, alias_text, canonical_manifest_id, match_kind, "
        f"created_at, updated_at) VALUES ('{aid}', {q(alias)}, '{mid(name, auth)}', 'exact', "
        f"now(), now()) ON CONFLICT (alias_text, match_kind) DO NOTHING;"
    )


GOV = "Government of Western Australia"
WAPC = "Western Australian Planning Commission"
COC = "City of Cockburn"
ABCB = "Australian Building Codes Board"

LEG_HOME = "https://www.legislation.wa.gov.au/legislation/statutes.nsf/main_mrtitle_722_homepage.html"
LEG_SUB = "https://www.legislation.wa.gov.au/legislation/statutes.nsf/law_a9408_subsidiary.html"
SPP_IDX = "https://www.wa.gov.au/government/document-collections/state-planning-policies"
DC_IDX = "https://www.wa.gov.au/organisation/department-of-planning-lands-and-heritage/development-control-and-operational-policies"
COC_LPP_IDX = "https://www.cockburn.wa.gov.au/Building-Planning-and-Roads/Town-Planning-and-Development/Local-Planning-Policies"
NCC_IDX = "https://ncc.abcb.gov.au/editions-national-construction-code"
SLIP_IDX = "https://catalogue.data.wa.gov.au/"

OOS_ADMIN = "out_of_scope per docs/CORPUS_SCOPE.md: administrative/fees/process instrument, not a drafting-check input"

# ---- Batch 1: WA legislation register (P&D Act 2005 + subsidiary legislation in force) ----
LEGISLATION = [
    # (name, category, status, note, version_hint)
    ("Planning and Development Act 2005", "act", "pending", None, "04-af0-00 (19 Feb 2026)"),
    ("Planning and Development (Local Planning Schemes) Regulations 2015", "regulations", "pending",
     "Includes Schedule 2 deemed provisions", None),
    ("Planning and Development (Planning Codes) Regulations 2024", "regulations", "pending", None, "SL 2024/24"),
    ("Planning and Development (State Planning Policies) Regulations 2024", "regulations", "pending", None, "SL 2024/26"),
    ("Planning and Development (Region Planning Schemes) Regulations 2023", "regulations", "pending", None, "SL 2023/108"),
    ("Planning and Development Regulations 2009", "regulations", "pending", None, None),
    ("Metropolitan Region Scheme", "region_scheme", "pending", "Pilot LGA (Cockburn) is within the MRS", None),
    ("Peel Region Scheme", "region_scheme", "pending", None, None),
    ("Greater Bunbury Region Scheme", "region_scheme", "pending", None, None),
    ("Planning and Development (Western Australian Planning Commission) Regulations 2024", "regulations",
     "out_of_scope", OOS_ADMIN, "SL 2024/100"),
    ("Planning and Development (Significant Development) Regulations 2024", "regulations", "out_of_scope",
     OOS_ADMIN, "SL 2024/23"),
    ("Planning and Development (Development Assessment Panels) Regulations 2011", "regulations",
     "out_of_scope", OOS_ADMIN, None),
    ("Planning and Development (Part 11B Fees) Notice 2024", "regulations", "out_of_scope", OOS_ADMIN, "SL 2024/28"),
    ("Planning and Development (Fees) Notice 2021", "regulations", "out_of_scope", OOS_ADMIN, "SL 2021/100"),
    ("Planning and Development (Part 17 Fees) Notice 2020", "regulations", "out_of_scope", OOS_ADMIN, "SL 2020/116"),
    ("Town Planning (Buildings) Uniform General By-laws 1989", "regulations", "out_of_scope", OOS_ADMIN, None),
    ("Town Planning (Height of Obstructions at Corners) General By-laws 1975", "regulations", "pending",
     "Corner-truncation sightline rules are a drafting-check input", None),
    ("Uniform General By-laws (Section 30 Subsection 1) New Subdivisions and Re-subdivisions", "regulations",
     "out_of_scope", OOS_ADMIN, None),
    ("Town Planning and Development By-laws (Excavations in Subdivided Areas)", "regulations",
     "out_of_scope", OOS_ADMIN, None),
    ("By-law under the Second Schedule of the Town Planning and Development Act 1928", "regulations",
     "out_of_scope", OOS_ADMIN, None),
    ("Town Planning and Development By-laws By-law 3", "regulations", "out_of_scope", OOS_ADMIN, None),
    ("By-law providing for enforcement of any by-law made under section 30", "regulations",
     "out_of_scope", OOS_ADMIN, None),
    ("By-laws for the Control of Hoardings", "regulations", "out_of_scope", OOS_ADMIN, None),
]
LEG_ALIASES = {
    "Planning and Development Act 2005": ["P&D Act", "PD Act 2005"],
    "Planning and Development (Local Planning Schemes) Regulations 2015": [
        "LPS Regulations 2015", "LPS Regulations", "the deemed provisions", "deemed provisions",
        "Planning and Development (Local Planning Schemes) Regulations",
    ],
    "Metropolitan Region Scheme": ["MRS"],
    "Peel Region Scheme": ["PRS"],
    "Greater Bunbury Region Scheme": ["GBRS"],
}

# ---- Batch 2: SPP index (+ R-Codes Vol 1/2 from DPLH pages, audit-verified URLs) ----
SPPS = [
    ("SPP 1", "State Planning Policy 1 - State Planning Framework",
     "https://www.wa.gov.au/system/files/2021-06/SPP_1_State_Planning_Framework.pdf", "pending", "Variation 3, gazetted Nov 2017"),
    ("SPP 2.0", "State Planning Policy 2.0 - Environment and Natural Resources",
     "https://www.wa.gov.au/government/publications/state-planning-policy-20-environment-and-natural-resources-policy", "pending", None),
    ("SPP 2.4", "State Planning Policy 2.4 - Planning for Basic Raw Materials",
     "https://www.wa.gov.au/government/publications/state-planning-policy-24-basic-raw-materials", "pending", None),
    ("SPP 2.5", "State Planning Policy 2.5 - Rural Planning",
     "https://www.wa.gov.au/government/publications/state-planning-policy-25-rural-planning", "pending", None),
    ("SPP 2.6", "State Planning Policy 2.6 - State Coastal Planning Policy",
     "https://www.wa.gov.au/government/publications/state-planning-policy-26-coastal-planning", "pending", None),
    ("SPP 2.8", "State Planning Policy 2.8 - Bushland Policy for the Perth Metropolitan Region",
     "https://www.wa.gov.au/government/publications/state-planning-policy-28-bushland-policy-the-perth-metropolitan-region", "pending", None),
    ("SPP 2.9", "State Planning Policy 2.9 - Water",
     "https://www.planning.wa.gov.au/state-planning-policy-2.9-water", "pending", None),
    ("SPP 3.0", "State Planning Policy 3.0 - Urban Growth and Settlement",
     "https://www.wa.gov.au/government/publications/state-planning-policy-30-urban-growth-and-settlement", "pending", None),
    ("SPP 3.2", "State Planning Policy 3.2 - Aboriginal Settlements",
     "https://www.wa.gov.au/government/publications/state-planning-policy-32-aboriginal-settlements", "pending", None),
    ("SPP 3.4", "State Planning Policy 3.4 - Natural Hazards and Disasters",
     "https://www.wa.gov.au/government/publications/state-planning-policy-34-natural-hazards-and-disasters", "pending", None),
    ("SPP 3.5", "State Planning Policy 3.5 - Historic Heritage Conservation",
     "https://www.wa.gov.au/government/publications/state-planning-policy-35-historic-heritage-conservation", "pending", None),
    ("SPP 3.6", "State Planning Policy 3.6 - Infrastructure Contributions",
     "https://www.wa.gov.au/government/publications/state-planning-policy-36-infrastructure-contributions", "pending", None),
    ("SPP 3.7", "State Planning Policy 3.7 - Planning in Bushfire Prone Areas",
     "https://www.planning.wa.gov.au/state-planning-policy-3.7-bushfire", "pending", None),
    ("SPP 4.1", "State Planning Policy 4.1 - Industrial Interface",
     "https://www.wa.gov.au/government/publications/draft-state-planning-policy-41-industrial-interface", "out_of_scope",
     "Listed as draft on the SPP index — not in force; drafts are out of scope per docs/CORPUS_SCOPE.md"),
    ("SPP 4.2", "State Planning Policy 4.2 - Activity Centres for Perth and Peel",
     "https://www.wa.gov.au/government/publications/state-planning-policy-42-activity-centres-perth-and-peel", "pending", None),
    ("SPP 5.1", "State Planning Policy 5.1 - Land Use Planning in the Vicinity of Perth Airport",
     "https://www.wa.gov.au/government/publications/state-planning-policy-51-land-use-planning-the-vicinity-of-perth-airport", "pending", None),
    ("SPP 5.2", "State Planning Policy 5.2 - Telecommunications Infrastructure",
     "https://www.wa.gov.au/government/publications/state-planning-policy-52-telecommunications-infrastructure", "pending", None),
    ("SPP 5.3", "State Planning Policy 5.3 - Land Use Planning in the Vicinity of Jandakot Airport",
     "https://www.wa.gov.au/government/publications/state-planning-policy-53-land-use-planning-the-vicinity-of-jandakot-airport", "pending",
     "Jandakot Airport is within the pilot LGA (Cockburn)"),
    ("SPP 5.4", "State Planning Policy 5.4 - Road and Rail Noise",
     "https://www.wa.gov.au/government/publications/state-planning-policy-54-road-and-rail-noise", "pending", None),
    ("SPP 6.1", "State Planning Policy 6.1 - Leeuwin-Naturaliste Ridge",
     "https://www.wa.gov.au/government/publications/state-planning-policy-61-leeuwin-naturaliste-ridge", "pending", None),
    ("SPP 6.3", "State Planning Policy 6.3 - Ningaloo Coast",
     "https://www.wa.gov.au/government/publications/state-planning-policy-63-ningaloo-coast", "pending", None),
    ("SPP 7.0", "State Planning Policy 7.0 - Design of the Built Environment",
     "https://www.wa.gov.au/government/publications/state-planning-policy-70-design-of-the-built-environment", "pending", None),
    ("SPP 7.2", "State Planning Policy 7.2 - Precinct Design",
     "https://www.wa.gov.au/government/publications/state-planning-policy-72-precinct-design", "pending", None),
]
RCODES_V1 = "State Planning Policy 7.3 - Residential Design Codes Volume 1"
RCODES_V2 = "State Planning Policy 7.3 - Residential Design Codes Volume 2 - Apartments"

# ---- Batch 3: DC / operational policies index ----
DCS = [
    ("OP 1.1", "Operational Policy 1.1 - Subdivision of land - general principles",
     "https://www.wa.gov.au/government/publications/operational-policy-11-subdivision-of-land-general-principles", "pending", None),
    ("DC 1.3", "Development Control Policy 1.3 - Strata titles",
     "https://www.wa.gov.au/government/publications/development-control-policy-13-strata-titles", "pending", None),
    ("DC 1.5", "Development Control Policy 1.5 - Bicycle Planning",
     "https://www.wa.gov.au/government/publications/development-control-policy-15-bicycle-planning", "pending", None),
    ("DC 1.6", "Development Control Policy 1.6 - Planning to support transit use and development",
     "https://www.wa.gov.au/government/publications/development-control-policy-16-planning-support-transit-use-and-development", "pending", None),
    ("DC 1.7", "Development Control Policy 1.7 - General road planning",
     "https://www.wa.gov.au/government/publications/development-control-policy-17-general-road-planning", "pending", None),
    ("DC 1.8", "Development Control Policy 1.8 - Canal estates and artificial waterway developments",
     "https://www.wa.gov.au/government/publications/development-control-policy-18-canal-estates-and-artificial-waterway-developments", "pending", None),
    ("DC 1.10", "Development Control Policy 1.10 - Freeway service centres, roadhouses incl signage",
     "https://www.wa.gov.au/government/publications/development-control-policy-110-freeway-services-centres-roadhouses-incl-signage", "pending", None),
    ("DC 1.11", "Development Control Policy 1.11 - Community schemes",
     "https://www.wa.gov.au/government/publications/development-control-policy-111-community-schemes", "pending", None),
    ("DC 2.2", "Development Control Policy 2.2 - Residential subdivision",
     "https://www.wa.gov.au/government/publications/development-control-policy-22-residential-subdivision", "pending", None),
    ("DC 2.4", "Development Control Policy 2.4 - School sites",
     "https://www.wa.gov.au/government/publications/development-control-policy-24-school-sites", "pending", None),
    ("DC 2.6", "Development Control Policy 2.6 - Residential road planning",
     "https://www.wa.gov.au/government/publications/development-control-policy-26-residential-road-planning", "pending", None),
    ("DC 3.4", "Development Control Policy 3.4 - Subdivision of rural land",
     "https://www.wa.gov.au/government/publications/development-control-policy-34-subdivision-of-rural-land", "pending", None),
    ("DC 4.1", "Development Control Policy 4.1 - Industrial subdivision",
     "https://www.wa.gov.au/government/publications/development-control-policy-41-industrial-subdivision", "pending", None),
    ("DC 4.2", "Development Control Policy 4.2 - Planning for hazards and safety",
     "https://www.wa.gov.au/government/publications/development-control-policy-42-planning-hazards-and-safety", "pending", None),
    ("DC 5.1", "Development Control Policy 5.1 - Regional roads (vehicular access)",
     "https://www.wa.gov.au/government/publications/development-control-policy-51-regional-roads-vehicular-access", "pending", None),
    ("DC 5.3", "Development Control Policy 5.3 - Use of land reserved for parks, recreation and regional open space",
     "https://www.wa.gov.au/government/publications/development-control-policy-53-use-of-land-reserved-parks-recreation-and-regional-open-space", "pending", None),
    ("DC 5.4", "Development Control Policy 5.4 - Advertising on reserved land",
     "https://www.wa.gov.au/government/publications/development-control-policy-54-advertising-reserved-land", "pending", None),
    ("Draft OP 1.12", "Draft Operational Policy 1.12 - Planning Proposals Adjoining Regional Roads in Western Australia",
     "https://www.wa.gov.au/government/publications/draft-operational-policy-112-planning-proposals-adjoining-regional-roads-western-australia",
     "out_of_scope", "Draft — not in force; drafts are out of scope per docs/CORPUS_SCOPE.md"),
    ("Draft DC 4.3", "Draft Development Control Policy 4.3 - Planning for high-pressure gas pipelines",
     "https://www.wa.gov.au/government/publications/draft-development-control-policy-43-planning-high-pressure-gas-pipelines",
     "out_of_scope", "Draft — not in force; drafts are out of scope per docs/CORPUS_SCOPE.md"),
]

# ---- Batch 4: City of Cockburn — TPS3 + all LPPs (scraped from council LPP index) ----
COC_BASE = "https://www.cockburn.wa.gov.au"
COC_LPPS = [
    ("LPP 1.2", "Residential Design Guidelines", "/getattachment/93e008eb-46d1-4485-a128-65bc91740e13/ECM_4517027_v14_Residential-Design-Guidelines-LPP1-docx.aspx"),
    ("LPP 1.3", "Special Purpose Dwellings", "/getattachment/f33baf86-3e50-4329-8bd1-75118c6afa09/ECM_4514426_v10_Special-Purpose-Dwellings-LPP1-docx.aspx"),
    ("LPP 1.8", "Design Requirements for Incidental Structures", "/getattachment/886b4b14-8406-415e-bd9c-51f04e9e8247/ECM_4518813_v11_Design-Requirements-for-Incidental-Structures-LPP1-docx.aspx"),
    ("LPP 1.10", "Planning Around Mosquito and Midge Infested Wetlands", "/getattachment/6aab2e13-45a4-43ea-a72a-e90249bf25c8/ECM_4922955_v7_Planning-Around-Mosquito-and-Midge-Infested-Wetlands-LPP1-docx.aspx"),
    ("LPP 1.12", "Noise Attenuation", "/getattachment/9bdea550-8053-4acc-8ce7-44c213a99f7a/ECM_4518974_v9_Noise-Attenuation-LPP1-docx.aspx"),
    ("LPP 1.14", "Waste Management", "/getattachment/4b9a77f4-8467-4943-9fdd-459a49d93632/ECM_4517800_v9_Waste-Management-LPP1-docx.aspx"),
    ("LPP 1.15", "Tourist Accommodation", "/getattachment/1f4ffe93-5d91-4693-a0e1-b6aa30f6e71a/ECM_5092850_v12_Tourist-Accommodation-LPP1-docx.aspx"),
    ("LPP 1.16", "Single House Standards for Medium Density Housing in the Development Zone", "/getattachment/cc98d8e2-4454-42ba-88a7-7820e9e811b6/ECM_5487140_v12_Single-House-Standards-for-Medium-Density-Housing-in-the-Development-Zone-LPP1-docx.aspx"),
    ("LPP 1.17", "Non-Residential Uses in Residential Zones", "/getattachment/d8d948e0-fcfd-4723-b1a2-95ab67098653/ECM_7633670_v7_Non-Residential-Uses-in-Residential-Zones-LPP1-docx.aspx"),
    ("LPP 2.1", "Rural Subdivision and Development", "/getattachment/6680cfaa-83a0-4689-8cb7-a9a81c3f20d9/ECM_4514270_v12_Rural-Subdivision-and-Development-LPP2-docx.aspx"),
    ("LPP 3.1", "Commercial Development", "/getattachment/19f59bc9-275c-4eb8-b4b4-c98a73775947/ECM_4516039_v13_Commercial-Development-LPP3-docx.aspx"),
    ("LPP 3.5", "Alfresco Dining", "/getattachment/183f2426-9e6f-4d29-abfb-69b35c54ad2d/ECM_4516897_v9_Alfresco-Dining-LPP3-docx.aspx"),
    ("LPP 3.7", "Signs & Advertising", "/getattachment/650bb2c3-dd4e-46e7-bb72-13dc855a5216/ECM_4518397_v12_Signs-Advertising-LPP3-docx.aspx"),
    ("LPP 3.8", "Industrial Subdivision and Development", "/getattachment/158357bb-03bb-498f-b948-d4257c3d2242/ECM_4513812_v9_Industrial-Subdivision-LPP3-docx.aspx"),
    ("LPP 4.2", "Cockburn Central North (Muriel Court) Structure Plan - Design Guidelines", "/getattachment/8f5a40ce-3604-471f-bd46-4e87479f2ac8/ECM_4517094_v10_Cockburn-Central-North-(Muriel-Court)-Structure-Plan-Design-Guidelines-LPP4-docx.aspx"),
    ("LPP 4.3", "Newmarket Precinct Design Guidelines", "/getattachment/2577d3ec-630d-4b18-9daf-9b17185c1d4b/ECM_4517282_v10_Newmarket-Precinct-Design-Guidelines-LPP4-docx.aspx"),
    ("LPP 4.4", "Heritage Conservation Design Guidelines", "/getattachment/e3eb83c1-03bb-433b-84d4-d97cf23b8f26/ECM_4517607_v9_Heritage-Conservation-Design-Guidelines-LPP4-docx.aspx"),
    ("LPP 4.5", "Naval Base Holiday Park Heritage Area", "/getattachment/008fdcf9-2c33-4ef1-9a6a-8af8396e7067/ECM_4517732_v8_Naval-Base-Holiday-Park-Heritage-Area-LPP4-docx.aspx"),
    ("LPP 4.6", "Cockburn Coast Design Guidelines for Robb Jetty & Emplacement Precincts", "/getattachment/9129254d-87fb-4183-ad79-9ca18a12b136/ECM_4518689_v18_Cockburn-Coast-Design-Guidelines-for-Robb-Jetty-Emplacement-Precincts-LPP4-docx.aspx"),
    ("LPP 4.7", "Phoenix Activity Centre Design Guidelines", "/getattachment/34f9e494-088a-4c5b-a978-235e7bb62e36/ECM_6583632_v8_Phoenix-Activity-Centre-Design-Guidelines-LPP4-docx.aspx"),
    ("LPP 5.1", "Development of the Public Realm", "/getattachment/7a88b7de-f0e0-4edf-b75e-767a4477bdfa/ECM_4514044_v7_Development-of-the-Public-Realm-LPP5-docx.aspx"),
    ("LPP 5.3", "Engineering, Drainage and Construction Standards", "/getattachment/ac6c4a9b-4817-47ec-b4bd-327cb951bd75/ECM_4514799_v8_Engineering,-Drainage-and-Construction-Standards-LPP5-docx.aspx"),
    ("LPP 5.4", "Utility Infrastructure", "/getattachment/342b9b9a-7509-4a4e-95c0-df803709ba0b/ECM_4515277_v9_Utility-Infrastructure-LPP5-docx.aspx"),
    ("LPP 5.5", "Local Development Plans", "/getattachment/37852f4c-c8fd-4cbd-bef0-8cf698c6c2c6/ECM_4514879_v12_Local-Development-Plans-LPP5-docx.aspx"),
    ("LPP 5.6", "Vehicle Access", "/getattachment/f3d336e1-9fa5-45b9-82e3-e9a6b2abec1e/ECM_4517299_v10_Vehicle-Access-LPP5-docx.aspx"),
    ("LPP 5.8", "Sea Containers", "/getattachment/5b69177d-38a1-470f-a7bf-bfac2bb76990/ECM_4516539_v9_Sea-Containers-LPP5-docx.aspx"),
    ("LPP 5.11", "Filling and Retaining of Land", "/getattachment/b46f5086-fda0-4714-bfc7-f8ff2721e88b/ECM_4515127_v8_Filling-and-Retaining-of-Land-LPP5-docx.aspx"),
    ("LPP 5.13", "Percent for Art", "/getattachment/6faa6b0c-32c1-4060-9c2f-c3dafb7b9598/ECM_4518964_v9_Percent-for-Art-LPP5-docx.aspx"),
    ("LPP 5.16", "Design Review Panel", "/getattachment/77794547-d790-458a-a646-f64d3afe749b/ECM_5092951_v12_Design-Review-Panel-LPP5-docx.aspx"),
    ("LPP 5.18", "Subdivision and Development - Street Trees", "/getattachment/03354f75-f282-4773-a878-8630535242c8/ECM_5670114_v13_Subdivision-and-Development-Street-Trees-LPP5-docx.aspx"),
    ("LPP 5.21", "Temporary Events", "/getattachment/60b5bcfb-13b0-41c3-afe2-69dced92588d/ECM_12060237_v4_Temporary-Events-LPP5-docx.aspx"),
    ("LPP 5.22", "Environmental Conservation", "/getattachment/6baa86a7-bad6-4631-98da-740654f704b4/ECM_8503481_v4_Environmental-Conservation-Policy-docx.aspx"),
    ("LPP 5.23", "Tree Protection", "/getattachment/b65c1904-779e-43ec-bbd1-a14f475b5528/ECM_12734624_v1_Tree-Protection-LPP-5-docx.aspx"),
]

# ---- Batch 5: NCC (ABCB editions index) ----
NCCS = [
    ("National Construction Code 2025 Volume One", "pending", "NCC 2025 — current edition in force"),
    ("National Construction Code 2025 Volume Two", "pending", "NCC 2025 — current edition in force"),
    ("National Construction Code 2025 Volume Three", "pending", "NCC 2025 — current edition in force"),
    ("National Construction Code 2025 Housing Provisions Standard", "pending", "NCC 2025 — current edition in force"),
    ("National Construction Code 2022 (all volumes)", "out_of_scope", "superseded — NCC 2025 in force since 1 May 2025"),
]

# ---- Batch 6: PlanWA / SLIP catalogue spatial layers + AS standards (metadata_only) ----
SPATIAL = [
    ("G-NAF Geocoded National Address File (WA)", "Geoscape Australia",
     "https://data.gov.au/data/dataset/geocoded-national-address-file-g-naf", "CC BY 4.0; quarterly refresh"),
    ("Cadastre (No Attributes) - SLIP public", "Landgate",
     "https://catalogue.data.wa.gov.au/dataset/cadastre-polygon", "Public geometry tier; free SLIP account"),
    ("Cadastre (Polygon) LGATE-217", "Landgate",
     "https://catalogue.data.wa.gov.au/dataset/cadastre-polygon",
     "Fees apply — subscription. Unblock: email customerexperience@landgate.wa.gov.au"),
    ("LPS Zones and Reserves DPLH-071", "Department of Planning, Lands and Heritage",
     "https://catalogue.data.wa.gov.au/dataset/local-planning-scheme-zones-and-reserves-dop-025",
     "WMS open; bulk vector Government-Use-Only. Unblock: email spatialdata@dplh.wa.gov.au"),
    ("LPS R-Codes DPLH-070", "Department of Planning, Lands and Heritage",
     "https://catalogue.data.wa.gov.au/dataset/local-planning-scheme-r-codes-dop-101",
     "WMS open; bulk vector Government-Use-Only. Unblock: email spatialdata@dplh.wa.gov.au"),
    ("LPS Special Control Areas DPLH-068", "Department of Planning, Lands and Heritage",
     "https://catalogue.data.wa.gov.au/dataset/local-planning-scheme-special-area-dop-090",
     "WMS open; bulk vector Government-Use-Only. Unblock: email spatialdata@dplh.wa.gov.au"),
    ("Region Scheme Zones and Reserves DPLH-023", "Department of Planning, Lands and Heritage",
     "https://catalogue.data.wa.gov.au/dataset/region-scheme-zones-and-reserves-dop-072",
     "Display free; vector restricted"),
    ("Bush Fire Prone Areas 2025 OBRM-024", "Department of Fire and Emergency Services",
     "https://catalogue.data.wa.gov.au/dataset/bush-fire-prone-areas-2025", "Open CC BY 4.0; free SLIP login for vectors"),
    ("Heritage Council State Register DPLH-006", "Department of Planning, Lands and Heritage",
     "https://catalogue.data.wa.gov.au/dataset/heritage-council-wa-state-register", "Open"),
    ("Heritage List DPLH-090", "Department of Planning, Lands and Heritage",
     "https://catalogue.data.wa.gov.au/dataset/heritage-list-dplh-090", "Open"),
]


def fetch_log(source_doc_id: str, url: str, note: str) -> str:
    fid = uuid.uuid5(NS, f"fetch|{url}|2026-06-10")
    meta = '{"wp": "WP3", "kind": "index_scrape", "url": "%s", "note": "%s"}' % (url, note)
    return (
        f"INSERT INTO source_fetch_log (id, org_id, source_id, requested_by_user_id, fetch_kind, "
        f"status, requested_at, completed_at, metadata_json) VALUES ('{fid}', '{ORG}', "
        f"'{source_doc_id}', '{USER}', 'index_scrape', 'succeeded', now(), now(), '{meta}'::jsonb) "
        f"ON CONFLICT (id) DO NOTHING;"
    )


def anchor_doc(doc_id: str, title: str, authority: str, url: str, source_type: str) -> str:
    return (
        f"INSERT INTO source_documents (id, org_id, title, jurisdiction, authority, source_type, "
        f"canonical_url, access_type, status, metadata_json, created_at, updated_at) VALUES ("
        f"'{doc_id}', '{ORG}', {q(title)}, 'WA', {q(authority)}, {q(source_type)}, {q(url)}, "
        f"'public', 'active', '{{\"wp\": \"WP3\", \"role\": \"index_anchor\"}}'::jsonb, now(), now()) "
        f"ON CONFLICT (authority, canonical_url) DO NOTHING;"
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # Batch 0 — index anchor docs + fetch log
    anchors = [
        (str(uuid.uuid5(NS, "anchor|leg")), "WA legislation register — Planning and Development Act 2005 home page", GOV, LEG_HOME),
        (str(uuid.uuid5(NS, "anchor|leg_sub")), "WA legislation register — P&D Act 2005 subsidiary legislation index", GOV, LEG_SUB),
        (str(uuid.uuid5(NS, "anchor|spp")), "DPLH State Planning Policies index", WAPC, SPP_IDX),
        (str(uuid.uuid5(NS, "anchor|dc")), "DPLH Development control and operational policies index", WAPC, DC_IDX),
        (str(uuid.uuid5(NS, "anchor|ncc")), "ABCB NCC editions index", ABCB, NCC_IDX),
        (str(uuid.uuid5(NS, "anchor|slip")), "SLIP / data.wa.gov.au catalogue (PlanWA spatial layers)", GOV, SLIP_IDX),
    ]
    b0 = ["BEGIN;"]
    for did, title, auth, url in anchors:
        b0.append(anchor_doc(did, title, auth, url, "index_page"))
        b0.append(fetch_log(did, url, "WP3 index scrape 2026-06-10"))
    # Cockburn LPP index page already exists as a source_document
    b0.append(fetch_log("08cafa09-c5a7-5dca-95b7-c3f8d0273ade", COC_LPP_IDX, "WP3 index scrape 2026-06-10"))
    b0.append("COMMIT;")
    (OUT / "batch0_anchors.sql").write_text("\n".join(b0), encoding="utf-8")

    # Batch 1 — legislation
    b1 = ["BEGIN;"]
    for name, cat, status, note, ver in LEGISLATION:
        b1.append(manifest_row(name, cat, GOV, LEG_SUB if name != "Planning and Development Act 2005" else LEG_HOME,
                               LEG_SUB if name != "Planning and Development Act 2005" else LEG_HOME,
                               status, note, ver))
    for name, aliases in LEG_ALIASES.items():
        for a in aliases:
            b1.append(alias_row(a, name, GOV))
    b1.append("COMMIT;")
    (OUT / "batch1_legislation.sql").write_text("\n".join(b1), encoding="utf-8")

    # Batch 2 — SPPs + R-Codes volumes
    b2 = ["BEGIN;"]
    for short, name, url, status, note in SPPS:
        b2.append(manifest_row(name, "state_planning_policy", WAPC, SPP_IDX, url, status, note))
        b2.append(alias_row(short, name, WAPC))
    b2.append(manifest_row(RCODES_V1, "state_planning_policy", WAPC, "https://www.dplh.wa.gov.au/rcodes",
                           "https://www.wa.gov.au/system/files/2026-04/r-codes-volume-1-10-april-2026.pdf",
                           "pending", "Primary rule source", "10 April 2026"))
    b2.append(manifest_row(RCODES_V2, "state_planning_policy", WAPC, "https://www.dplh.wa.gov.au/rcodes",
                           "https://www.wa.gov.au/government/document-collections/state-planning-policy-73-residential-design-codes-apartments",
                           "pending", None, "operational 24 May 2019"))
    for a in ["SPP 7.3", "R-Codes", "the R-Codes", "Residential Design Codes",
              "Residential Design Codes Volume 1", "R-Codes Volume 1"]:
        b2.append(alias_row(a, RCODES_V1, WAPC))
    for a in ["R-Codes Volume 2", "SPP 7.3 Volume 2", "Residential Design Codes Volume 2",
              "Residential Design Codes - Apartments", "Apartment Codes"]:
        b2.append(alias_row(a, RCODES_V2, WAPC))
    b2.append("COMMIT;")
    (OUT / "batch2_spp.sql").write_text("\n".join(b2), encoding="utf-8")

    # Batch 3 — DC policies
    b3 = ["BEGIN;"]
    for short, name, url, status, note in DCS:
        b3.append(manifest_row(name, "dc_policy", WAPC, DC_IDX, url, status, note))
        b3.append(alias_row(short, name, WAPC))
    b3.append("COMMIT;")
    (OUT / "batch3_dc.sql").write_text("\n".join(b3), encoding="utf-8")

    # Batch 4 — Cockburn TPS3 + LPPs
    b4 = ["BEGIN;"]
    tps3 = "City of Cockburn Town Planning Scheme No. 3 - Scheme Text"
    b4.append(manifest_row(tps3, "local_planning_scheme", COC,
                           "https://www.cockburn.wa.gov.au/Building-Planning-and-Roads/Town-Planning-and-Development/Local-Planning-Scheme",
                           "https://www.wa.gov.au/system/files/2026-05/cockburn3_schemetext.pdf",
                           "pending", None, "consolidation published 2026-05"))
    for a in ["TPS3", "TPS No. 3", "Town Planning Scheme No. 3", "Cockburn Scheme Text",
              "Cockburn Town Planning Scheme 3", "the Scheme"]:
        b4.append(alias_row(a, tps3, COC))
    for short, title, path in COC_LPPS:
        name = f"City of Cockburn {short} - {title}"
        b4.append(manifest_row(name, "local_planning_policy", COC, COC_LPP_IDX, COC_BASE + path, "pending", None))
        b4.append(alias_row(short, name, COC))
        b4.append(alias_row(f"{short} {title}", name, COC))
    b4.append("COMMIT;")
    (OUT / "batch4_cockburn.sql").write_text("\n".join(b4), encoding="utf-8")

    # Batch 5 — NCC
    b5 = ["BEGIN;"]
    for name, status, note in NCCS:
        b5.append(manifest_row(name, "building_code", ABCB, NCC_IDX, NCC_IDX, status,
                               note + "; free download, ABCB registration optional"))
    b5.append(alias_row("NCC", "National Construction Code 2025 Volume One", ABCB))
    b5.append(alias_row("National Construction Code", "National Construction Code 2025 Volume One", ABCB))
    b5.append(alias_row("NCC Volume One", "National Construction Code 2025 Volume One", ABCB))
    b5.append(alias_row("NCC Volume Two", "National Construction Code 2025 Volume Two", ABCB))
    b5.append(alias_row("NCC Volume Three", "National Construction Code 2025 Volume Three", ABCB))
    b5.append(alias_row("Building Code of Australia", "National Construction Code 2025 Volume One", ABCB))
    b5.append(alias_row("BCA", "National Construction Code 2025 Volume One", ABCB))
    b5.append(alias_row("Housing Provisions", "National Construction Code 2025 Housing Provisions Standard", ABCB))
    b5.append("COMMIT;")
    (OUT / "batch5_ncc.sql").write_text("\n".join(b5), encoding="utf-8")

    # Batch 6 — spatial layers + standards (metadata_only)
    b6 = ["BEGIN;"]
    for name, auth, url, note in SPATIAL:
        b6.append(manifest_row(name, "spatial_layer", auth, SLIP_IDX, url, "metadata_only", note))
    as3959 = "AS 3959 Construction of buildings in bushfire-prone areas"
    b6.append(manifest_row(as3959, "standard", "Standards Australia", "https://www.standards.org.au/",
                           "https://www.standards.org.au/", "metadata_only",
                           "Paid/proprietary — never store full text. Unblock: purchase licence from Standards Australia"))
    b6.append(alias_row("AS 3959", as3959, "Standards Australia"))
    b6.append(alias_row("AS3959", as3959, "Standards Australia"))
    b6.append("COMMIT;")
    (OUT / "batch6_spatial.sql").write_text("\n".join(b6), encoding="utf-8")

    print("wrote batches to", OUT)


if __name__ == "__main__":
    main()
