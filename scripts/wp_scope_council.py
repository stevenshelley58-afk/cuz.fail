"""Scope a council's approved local rules to their canonical council name.

Generic successor to wp0_scope_cockburn.py — run once per council after its
correct/filter passes. Sets ``rules.council_scope`` on approved rules whose
source document carries the council's ``local_government`` tag; state-doc rules
(``local_government IS NULL``) stay global. Idempotent.

Run inside the api container:
    python /app/scripts/wp_scope_council.py --council "City of Melville"
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from sqlalchemy import create_engine, text  # noqa: E402

from draftcheck.domain.address.lga import canonical_local_government_name  # noqa: E402


def _db_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql+psycopg://")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--council", required=True, help='canonical name, e.g. "City of Melville"')
    args = ap.parse_args()

    canonical = canonical_local_government_name(args.council)
    if canonical != args.council:
        raise SystemExit(f"--council must be canonical; got {args.council!r}, expected {canonical!r}")

    engine = create_engine(_db_url())
    with engine.begin() as conn:
        reset = conn.execute(
            text(
                """
                UPDATE rules r
                SET council_scope = NULL
                FROM source_versions sv, source_documents sd
                WHERE r.source_version_id = sv.id AND sv.source_id = sd.id
                  AND r.lifecycle_status = 'approved'
                  AND sd.local_government = :canonical
                  AND r.council_scope IS NOT NULL
                  AND r.council_scope != :canonical
                """
            ),
            {"canonical": canonical},
        )
        print(f"reset non-canonical scopes: {reset.rowcount}")

        result = conn.execute(
            text(
                """
                UPDATE rules r
                SET council_scope = :canonical
                FROM source_versions sv, source_documents sd
                WHERE r.source_version_id = sv.id AND sv.source_id = sd.id
                  AND r.lifecycle_status = 'approved'
                  AND sd.local_government = :canonical
                  AND r.council_scope IS DISTINCT FROM :canonical
                """
            ),
            {"canonical": canonical},
        )
        print(f"scoped {canonical} local rules: {result.rowcount}")

        summary = conn.execute(
            text(
                """
                SELECT council_scope, COUNT(*) FROM rules
                WHERE lifecycle_status = 'approved'
                GROUP BY council_scope ORDER BY COUNT(*) DESC
                """
            )
        ).all()
        print("approved rules by council_scope:")
        for scope, count in summary:
            print(f"  {scope!r}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
