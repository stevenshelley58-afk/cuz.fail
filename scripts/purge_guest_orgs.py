"""Delete throwaway guest orgs older than the retention window.

Guest sessions each get a fresh org (slug 'guest-*'). Run nightly via cron:

    0 3 * * * cd /srv/draftcheck/app && DATABASE_URL=... .venv/bin/python scripts/purge_guest_orgs.py

Deleting the org cascades to its users, sessions, projects, and guest_usage
rows via the existing ON DELETE CASCADE foreign keys.
"""

from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text


RETENTION_DAYS = int(os.getenv("GUEST_ORG_RETENTION_DAYS", "14"))


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set; nothing to purge.", file=sys.stderr)
        return 1
    engine = create_engine(database_url)
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "DELETE FROM orgs WHERE slug LIKE 'guest-%' "
                "AND created_at < now() - make_interval(days => :days)"
            ),
            {"days": RETENTION_DAYS},
        )
        print(f"Purged {result.rowcount} guest org(s) older than {RETENTION_DAYS} days.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
