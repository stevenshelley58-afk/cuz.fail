"""Seed target_manifest from a discovery JSON for one council.

Input JSON shape (produced by the doc-discovery step):
    {"council": "City of Fremantle",
     "docs": [{"instrument_name": "...", "category": "local_planning_policy",
               "canonical_url": "https://..."}, ...]}

Idempotent: skips instrument_names already present in target_manifest.
Rows are seeded status='pending' with issuing_authority = the canonical council
name, which wp4_acquire.py uses to tag source_documents.local_government.

Run inside the api container:
    python /app/scripts/seed_council_manifest.py --json /tmp/fremantle_docs.json
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid

sys.path.insert(0, "/app/src")

import psycopg  # noqa: E402

from seed_melville_manifest import _db_url  # noqa: E402

ALLOWED_CATEGORIES = {
    "local_planning_scheme", "local_planning_policy", "local_planning_strategy",
    "structure_plan", "local_development_plan",
}

INSERT = """
INSERT INTO target_manifest (
    id, instrument_name, category, issuing_authority, canonical_url,
    status, metadata_json, created_at, updated_at
) VALUES (%s, %s, %s, %s, %s, 'pending', '{}'::jsonb, now(), now())
ON CONFLICT (id) DO NOTHING
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    args = ap.parse_args()

    with open(args.json, encoding="utf-8") as fh:
        data = json.load(fh)
    council = str(data["council"]).strip()
    if not council.startswith(("City of", "Town of", "Shire of")):
        raise SystemExit(f"council must be canonical, got {council!r}")

    ns = uuid.uuid5(uuid.NAMESPACE_URL, f"lotfile/council-manifest/{council}")
    inserted = skipped = invalid = 0
    with psycopg.connect(_db_url()) as conn:
        cur = conn.cursor()
        for doc in data["docs"]:
            name = str(doc.get("instrument_name") or "").strip()
            category = str(doc.get("category") or "").strip()
            url = str(doc.get("canonical_url") or "").strip()
            if not name or category not in ALLOWED_CATEGORIES or not url.startswith("http"):
                invalid += 1
                print(f"invalid: {name[:70]!r} category={category!r} url={url[:60]!r}")
                continue
            cur.execute("SELECT 1 FROM target_manifest WHERE instrument_name = %s", (name,))
            if cur.fetchone():
                skipped += 1
                continue
            cur.execute(INSERT, (str(uuid.uuid5(ns, name)), name, category, council, url))
            inserted += cur.rowcount
            print(f"seeded: {name[:90]}")
        conn.commit()
    print(f"council={council} inserted={inserted} skipped_existing={skipped} invalid={invalid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
