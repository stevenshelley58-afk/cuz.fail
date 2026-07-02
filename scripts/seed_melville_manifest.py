"""Seed target_manifest with the City of Melville local instruments missing
from the first (stalled) ingestion pass — 20 LPPs, the Canning Bridge Activity
Centre Plan, and the WAPC-endorsed Local Planning Strategy.

Source of truth for the LPP list + asset URLs: the council's Local Planning
Policies page (fetched 2026-07-02). Idempotent: uuid5 ids, ON CONFLICT DO NOTHING.

Run inside the api container:
    python /app/scripts/seed_melville_manifest.py
"""
from __future__ import annotations

import os
import sys
import uuid

sys.path.insert(0, "/app/src")

import psycopg  # noqa: E402


def _db_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


MELVILLE = "City of Melville"
BASE = "https://www.melvillecity.com.au"

ROWS: list[tuple[str, str, str]] = [
    # (instrument_name, category, canonical_url)
    ("City of Melville LPP 1.3 - Waste and Recyclables Collection for Multiple Dwellings, Mixed Use and Non-Residential Developments", "local_planning_policy", f"{BASE}/getContentAsset/633ebfff-fbd1-430b-955a-4c094d7cd29d/3ca954ad-3848-47c6-8f97-68cebe0b47a2/waste-and-recyclables-collection-for-multiple-dwel?language=en"),
    ("City of Melville LPP 1.5 - Energy Efficiency in Building Design", "local_planning_policy", f"{BASE}/getContentAsset/8c17265a-6482-44ed-bbb4-cdba38cd6d33/3ca954ad-3848-47c6-8f97-68cebe0b47a2/energy-efficiency-in-building-design?language=en"),
    ("City of Melville LPP 1.8 - Crime Prevention Through Environmental Design of Buildings", "local_planning_policy", f"{BASE}/getContentAsset/b3236e04-a9b2-4e90-a58a-1f9c0e4511d1/3ca954ad-3848-47c6-8f97-68cebe0b47a2/crime-prevention-through-environmental-design-of-b?language=en"),
    ("City of Melville LPP 1.9 - Height of Buildings", "local_planning_policy", f"{BASE}/getContentAsset/9a1fae81-39e4-4433-9eb5-70ddb49f4d7f/3ca954ad-3848-47c6-8f97-68cebe0b47a2/height-of-buildings?language=en"),
    ("City of Melville LPP 1.12 - Child Minding Centres and Family Day Care", "local_planning_policy", f"{BASE}/getContentAsset/7d19bbd6-e185-4952-808f-09c41d48596f/3ca954ad-3848-47c6-8f97-68cebe0b47a2/child-minding-centres-and-family-day-care?language=en"),
    ("City of Melville LPP 1.14 - Temporary Structures", "local_planning_policy", f"{BASE}/getContentAsset/e97109ff-e91a-47ef-8f97-51d64523553c/3ca954ad-3848-47c6-8f97-68cebe0b47a2/temporary-structures?language=en"),
    ("City of Melville LPP 1.16 - Flood and Security Lighting", "local_planning_policy", f"{BASE}/our-city/publications-and-forms/building-and-development/flood-and-security-lighting"),
    ("City of Melville LPP 1.17 - Additional Development Exemptions", "local_planning_policy", f"{BASE}/getContentAsset/c2b52afc-cdb6-4605-84a8-1019a3cf1c8b/3ca954ad-3848-47c6-8f97-68cebe0b47a2/additional-development-exemptions?language=en"),
    ("City of Melville LPP 1.19 - Canning Bridge Activity Centre Plan - Community Benefit for Ceding of Road Widening Land", "local_planning_policy", f"{BASE}/getContentAsset/8d7b2dce-9569-44f5-a833-794108c1c7e1/3ca954ad-3848-47c6-8f97-68cebe0b47a2/local-planning-policy-canning-bridge-activity-ce?language=en"),
    ("City of Melville LPP 1.20 - Canning Bridge Activity Centre Plan - Density and Bonus Provisions", "local_planning_policy", f"{BASE}/getContentAsset/e80d231d-9d16-4c24-bc36-0bd702080a17/3ca954ad-3848-47c6-8f97-68cebe0b47a2/lpp1-20-canning-bridge-activity-centre-plan-E2-80-93-dens?language=en"),
    ("City of Melville LPP 1.21 - Short Term Rental Accommodation", "local_planning_policy", f"{BASE}/getContentAsset/a4315d6b-c817-426e-8ed7-ddabdf53755f/3ca954ad-3848-47c6-8f97-68cebe0b47a2/short-term-accommodation?language=en"),
    ("City of Melville LPP 1.22 - Construction Management Plans", "local_planning_policy", f"{BASE}/getContentAsset/587dc567-816b-4325-b559-94eade617513/3ca954ad-3848-47c6-8f97-68cebe0b47a2/local-planning-policy-construction-management-plan?language=en"),
    ("City of Melville LPP 2.1 - Non-Residential Development", "local_planning_policy", f"{BASE}/getContentAsset/e33ebad7-9b3a-46a6-a5c8-71466ac52510/3ca954ad-3848-47c6-8f97-68cebe0b47a2/non-residential-development?language=en"),
    ("City of Melville LPP 2.2 - Outdoor Advertising and Signage", "local_planning_policy", f"{BASE}/getContentAsset/f9368ae7-c309-467a-a330-6928de37353a/3ca954ad-3848-47c6-8f97-68cebe0b47a2/local-planning-policy-outdoor-advertising-and-si?language=en"),
    ("City of Melville LPP 3.1 - Residential Development", "local_planning_policy", f"{BASE}/getContentAsset/916d8eac-8f3d-4b2a-9e26-66baeefe4e16/3ca954ad-3848-47c6-8f97-68cebe0b47a2/local-planning-policy-residential-development?language=en"),
    ("City of Melville LPP 3.4 - Tennis Courts", "local_planning_policy", f"{BASE}/getContentAsset/ff4acaa0-64a2-4767-b43b-e5ed1606c002/3ca954ad-3848-47c6-8f97-68cebe0b47a2/local-planning-policy-tennis-courts?language=en"),
    ("City of Melville LPP 3.5 - Home Occupation Relative to Sexual Services Business", "local_planning_policy", f"{BASE}/getContentAsset/de47197f-3bb2-4c6f-a62c-e9a6cd76f58e/3ca954ad-3848-47c6-8f97-68cebe0b47a2/local-planning-policy-home-occupation-relative-t?language=en"),
    ("City of Melville LPP 4.1 - RAAFA Master Plan", "local_planning_policy", f"{BASE}/getContentAsset/3f701d20-cefa-45ba-9a49-ed0fe6a30941/3ca954ad-3848-47c6-8f97-68cebe0b47a2/local-planning-policy-royal-australian-air-force?language=en"),
    ("City of Melville LPP 4.4 - Murdoch Health and Knowledge Precinct Design Guidelines", "local_planning_policy", f"{BASE}/getContentAsset/8886da73-06db-49ac-88a2-e06ebc0dedb5/3ca954ad-3848-47c6-8f97-68cebe0b47a2/local-planning-policy-E2-80-A2murdoch-health-and-knowle?language=en"),
    ("City of Melville LPP 4.5 - Carawatha Development Design Guidelines", "local_planning_policy", f"{BASE}/getContentAsset/fcf0b20b-84f5-47b1-a21e-0159c911ae3c/3ca954ad-3848-47c6-8f97-68cebe0b47a2/LPP-4-5-Carawatha-Development-Design-Guidelines_1.pdf?language=en"),
    ("Canning Bridge Activity Centre Plan (City of Melville)", "structure_plan", f"{BASE}/CityOfMelville/media/Documents-and-PDF-s/Development-Applications/Canning-Bridge-Activity-Centre-Plan.pdf"),
    ("City of Melville Local Planning Strategy", "local_planning_strategy", "https://www.wa.gov.au/system/files/2021-11/LST-Melville.pdf"),
]

INSERT = """
INSERT INTO target_manifest (
    id, instrument_name, category, issuing_authority, canonical_url,
    status, metadata_json, created_at, updated_at
) VALUES (%s, %s, %s, %s, %s, 'pending', '{}'::jsonb, now(), now())
ON CONFLICT (id) DO NOTHING
"""


def main() -> int:
    ns = uuid.uuid5(uuid.NAMESPACE_URL, "lotfile/melville-manifest")
    inserted = 0
    with psycopg.connect(_db_url()) as conn:
        cur = conn.cursor()
        for name, category, url in ROWS:
            row_id = str(uuid.uuid5(ns, name))
            # Skip anything already known under this instrument name.
            cur.execute(
                "SELECT 1 FROM target_manifest WHERE instrument_name = %s", (name,)
            )
            if cur.fetchone():
                print(f"exists: {name}")
                continue
            cur.execute(INSERT, (row_id, name, category, MELVILLE, url))
            inserted += cur.rowcount
            print(f"seeded: {name}")
        conn.commit()
    print(f"inserted {inserted} pending manifest rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
