"""WP-0: scope Cockburn local rules to their canonical council.

Prerequisite before adding any second council.  Idempotent: safe to re-run.

1. Sets `rules.council_scope = 'City of Cockburn'` on approved rules whose
   source document is tagged with a Cockburn local government.
2. Leaves state-doc rules (`source_documents.local_government IS NULL`) as
   global (`council_scope = NULL`).

Run inside the api container:
    python /app/scripts/wp0_scope_cockburn.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from sqlalchemy import create_engine, text  # noqa: E402

CANONICAL = "City of Cockburn"


def _db_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql+psycopg://")


def main() -> int:
    engine = create_engine(_db_url())
    with engine.begin() as conn:
        # Idempotency: reset any previous non-canonical Cockburn scopes first.
        reset = conn.execute(
            text(
                """
                UPDATE rules r
                SET council_scope = NULL
                FROM source_versions sv, source_documents sd
                WHERE r.source_version_id = sv.id AND sv.source_id = sd.id
                  AND r.lifecycle_status = 'approved'
                  AND sd.local_government ILIKE '%cockburn%'
                  AND r.council_scope IS NOT NULL
                  AND r.council_scope != :canonical
                """
            ),
            {"canonical": CANONICAL},
        )
        print(f"reset non-canonical Cockburn scopes: {reset.rowcount}")

        result = conn.execute(
            text(
                """
                UPDATE rules r
                SET council_scope = :canonical
                FROM source_versions sv, source_documents sd
                WHERE r.source_version_id = sv.id AND sv.source_id = sd.id
                  AND r.lifecycle_status = 'approved'
                  AND sd.local_government ILIKE '%cockburn%'
                  AND (r.council_scope IS NULL OR r.council_scope != :canonical)
                """
            ),
            {"canonical": CANONICAL},
        )
        print(f"scoped Cockburn local rules: {result.rowcount}")

        # Sanity check: no approved rule should still carry the old bbox suffix.
        stale = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM rules
                WHERE lifecycle_status = 'approved'
                  AND council_scope ILIKE '%(bbox extent)%'
                """
            )
        ).scalar()
        print(f"stale '(bbox extent)' scopes remaining: {stale}")
        if stale:
            raise SystemExit(1)

        # Summary: approved rules by council_scope.
        summary = conn.execute(
            text(
                """
                SELECT council_scope, COUNT(*) FROM rules
                WHERE lifecycle_status = 'approved'
                GROUP BY council_scope
                ORDER BY COUNT(*) DESC
                """
            )
        ).all()
        print("approved rules by council_scope:")
        for scope, count in summary:
            print(f"  {scope!r}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
