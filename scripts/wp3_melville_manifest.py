"""WP3 Batch 7 — City of Melville local planning manifest.

Sources verified 2026-06-16 from:
  - WA.gov.au: https://www.wa.gov.au/government/document-collections/city-of-melville-planning-information
  - Melville LPP index: https://www.melvillecity.com.au/planning-and-building/local-planning-strategy,-scheme-policies-and-plans/local-planning-policies

Emits reports/wp3/batch7_melville.sql — apply inside the api container:
    psql $DATABASE_URL -f /app/reports/wp3/batch7_melville.sql
"""
from __future__ import annotations

import uuid
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "reports" / "wp3"
ORG = "1d31c315-5087-47df-a8d4-ebfd08efad5d"
NS = uuid.UUID("7b1e5a52-4f2c-4cf7-9e83-0c8f2a3d6e91")
MEL = "City of Melville"
MEL_BASE = "https://www.melvillecity.com.au"
WA_GOV = "https://www.wa.gov.au"


def mid(name: str, auth: str) -> str:
    return str(uuid.uuid5(NS, f"manifest|{name}|{auth}"))


def q(s: str | None) -> str:
    if s is None:
        return "NULL"
    return "'" + s.replace("'", "''") + "'"


def manifest_row(name, category, auth, index_url, canon, status="pending", note=None, version=None):
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


# Verified PDF URLs.  Scheme text is the consolidated WA.gov.au copy.
LPS6_TEXT = f"{WA_GOV}/system/files/2026-02/melville_6_schemetext.pdf"
LPP_INDEX = f"{MEL_BASE}/planning-and-building/local-planning-strategy,-scheme-policies-and-plans/local-planning-policies"

MEL_LPPs = [
    ("LPP 1.1", "Planning Process and Decision Making", "/getContentAsset/0e1cbf0b-d0fd-4377-b62d-60de395848a3/3ca954ad-3848-47c6-8f97-68cebe0b47a2/LPP1-1-Planning-Process-and-Decision-Making-May-2025.pdf?language=en"),
    ("LPP 1.2", "Design Review Panel", "/getContentAsset/2fdfcfa4-c637-4f26-acc5-8f8af024d544/3ca954ad-3848-47c6-8f97-68cebe0b47a2/LPP-1-2-Design-Review-Panel.pdf?language=en"),
    ("LPP 1.4", "Provision of Public Art in Development Proposals", "/getContentAsset/3c0e658f-1832-49e9-9fda-caba31787366/3ca954ad-3848-47c6-8f97-68cebe0b47a2/LPP-1-4-Provision-of-Public-Art-in-Development-Proposals.pdf?language=en"),
    ("LPP 1.6", "Parking and Access", "/getContentAsset/f53fbfee-ea82-4f6f-bb3b-b617fbd122d4/3ca954ad-3848-47c6-8f97-68cebe0b47a2/LPP1-6-Parking-and-Access-Final-Version-June-2025.pdf?language=en"),
    ("LPP 1.7", "Telecommunications Facilities and Communications Equipment", "/getContentAsset/8c362444-1e5a-4104-a6a5-e0335ef16edf/3ca954ad-3848-47c6-8f97-68cebe0b47a2/LPP1-7-Telecommunications-Facilities-and-Communications-Equipment-FINAL.pdf?language=en"),
    ("LPP 1.10", "Amenity Policy", "/getContentAsset/cb1f9aac-bef9-4b77-bacc-0b0afa09dac5/3ca954ad-3848-47c6-8f97-68cebe0b47a2/LPP1-10-Amenity-Policy.pdf?language=en"),
    ("LPP 3.3", "Exhibition and Display Homes", "/getContentAsset/e3fb0de5-d57a-4763-8c26-bc2cbd615c6b/3ca954ad-3848-47c6-8f97-68cebe0b47a2/LPP3-3-Exhibition-and-Display-Homes-(FINAL).pdf?language=en"),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    sql = ["BEGIN;"]

    # Local Planning Scheme No. 6
    lps_name = "City of Melville Local Planning Scheme No. 6 - Scheme Text"
    sql.append(manifest_row(lps_name, "local_planning_scheme", MEL,
                            f"{MEL_BASE}/planning-and-building/local-planning-strategy,-scheme-policies-and-plans/local-planning-strategy-and-scheme",
                            LPS6_TEXT, status="pending",
                            note="Consolidated scheme text published 2026-02", version="2026-02"))
    for a in ["LPS6", "LPS No. 6", "Local Planning Scheme No. 6", "Melville Scheme Text",
              "Melville Local Planning Scheme 6", "the Scheme"]:
        sql.append(alias_row(a, lps_name, MEL))

    # Local Planning Policies
    for short, title, path in MEL_LPPs:
        name = f"City of Melville {short} - {title}"
        url = MEL_BASE + path
        sql.append(manifest_row(name, "local_planning_policy", MEL, LPP_INDEX, url,
                                status="pending", note=None))
        sql.append(alias_row(short, name, MEL))
        sql.append(alias_row(f"{short} {title}", name, MEL))

    sql.append("COMMIT;")

    (OUT / "batch7_melville.sql").write_text("\n".join(sql), encoding="utf-8")
    print(f"wrote {OUT / 'batch7_melville.sql'} ({len(MEL_LPPs)} LPPs + 1 LPS)")


if __name__ == "__main__":
    main()
