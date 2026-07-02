"""Parse clauses for all City of Melville source_versions.

The Hermes agent polls review_status='pending', but wp4_acquire sets
pending_review.  This script bridges the gap for the Melville rollout by
running the clause parser directly and marking versions as processed.

Run inside the api container:
    python /app/scripts/wp4a_parse_melville_clauses.py
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, "/app/src")

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from draftcheck.agent.clause_parser import ClauseParser  # noqa: E402


def db_url() -> str:
    return os.environ["DATABASE_URL"]


async def main() -> int:
    engine = create_async_engine(db_url())
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(
            text("""
                SELECT sv.id::text
                FROM source_versions sv
                JOIN source_documents sd ON sv.source_id = sd.id
                WHERE sd.authority = 'City of Melville'
                  AND sd.local_government = 'City of Melville'
                ORDER BY sd.source_type, sd.title
            """)
        )
        sv_ids = [row[0] for row in result.fetchall()]

    print(f"Parsing clauses for {len(sv_ids)} Melville source versions...")
    parser = ClauseParser()
    total_created = 0
    for sv_id in sv_ids:
        async with async_session() as session:
            try:
                res = await parser.parse_source_version(sv_id, session)
                await session.execute(
                    text("UPDATE source_versions SET review_status='processing' WHERE id = :id"),
                    {"id": sv_id},
                )
                await session.commit()
                total_created += res.clauses_created
                print(f"  {sv_id}: created {res.clauses_created}, updated {res.clauses_updated}, errors {len(res.errors)}")
            except Exception as exc:
                print(f"  ERROR {sv_id}: {exc}")
                await session.rollback()

    print(f"Total clauses created: {total_created}")
    await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
