"""Audit and repair source chunk embeddings.

Usage inside the api container:
  python /app/scripts/reembed_chunks.py --report /app/reports/embedding_audit.json
  python /app/scripts/reembed_chunks.py --apply --batch-size 100 --report /app/reports/reembed_chunks.json

The script is idempotent: it only updates chunks whose embedding metadata is
missing, known-stub, or different from the pinned provider/model/dimension.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from draftcheck.domain.sources.library import _batch_embed, default_embedding_config


BAD_PROVIDERS = ("stub", "hash", "mock")


def dsn() -> str:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")


def pinned_config() -> dict[str, Any]:
    config = default_embedding_config()
    return {
        "provider": os.environ.get("DRAFTCHECK_EMBEDDING_PROVIDER", config.provider),
        "model": os.environ.get("DRAFTCHECK_EMBEDDING_MODEL", config.model),
        "dimension": int(os.environ.get("DRAFTCHECK_EMBEDDING_DIMENSION", str(config.dimension))),
    }


def ensure_apply_can_write_real_embeddings(pinned: dict[str, Any]) -> None:
    provider = str(pinned["provider"]).strip().lower()
    if provider == "api" and not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is required for --apply when DRAFTCHECK_EMBEDDING_PROVIDER=api; "
            "refusing to label hash fallback vectors as real API embeddings."
        )
    if provider in BAD_PROVIDERS:
        raise SystemExit(
            f"--apply refused for mock embedding provider {provider!r}; "
            "set DRAFTCHECK_EMBEDDING_PROVIDER=api with OPENAI_API_KEY for production repairs."
        )


def audit(session: Session, pinned: dict[str, Any]) -> dict[str, Any]:
    grouped = [
        dict(row._mapping)
        for row in session.execute(
            text(
                """
                SELECT embedding_provider, embedding_model, embedding_dimension, count(*) AS count
                FROM source_chunks
                GROUP BY embedding_provider, embedding_model, embedding_dimension
                ORDER BY count DESC, embedding_provider NULLS FIRST, embedding_model NULLS FIRST
                """
            )
        ).fetchall()
    ]
    needs_reembed = session.execute(
        text(
            """
            SELECT count(*)
            FROM source_chunks
            WHERE embedding IS NULL
               OR embedding_provider IS NULL
               OR embedding_model IS NULL
               OR embedding_dimension IS NULL
               OR embedding_provider = ANY(:bad_providers)
               OR embedding_provider != :provider
               OR embedding_model != :model
               OR embedding_dimension != :dimension
            """
        ),
        {"bad_providers": list(BAD_PROVIDERS), **pinned},
    ).scalar_one()
    total = session.execute(text("SELECT count(*) FROM source_chunks")).scalar_one()
    return {
        "pinned": pinned,
        "total_chunks": total,
        "needs_reembed": needs_reembed,
        "provider_model_dimension_counts": grouped,
    }


def next_batch(session: Session, pinned: dict[str, Any], batch_size: int) -> list[dict[str, Any]]:
    rows = session.execute(
        text(
            """
            SELECT id, text
            FROM source_chunks
            WHERE embedding IS NULL
               OR embedding_provider IS NULL
               OR embedding_model IS NULL
               OR embedding_dimension IS NULL
               OR embedding_provider = ANY(:bad_providers)
               OR embedding_provider != :provider
               OR embedding_model != :model
               OR embedding_dimension != :dimension
            ORDER BY id
            LIMIT :batch_size
            """
        ),
        {"bad_providers": list(BAD_PROVIDERS), "batch_size": batch_size, **pinned},
    ).fetchall()
    return [dict(row._mapping) for row in rows]


def reembed(session: Session, pinned: dict[str, Any], batch_size: int) -> int:
    config = default_embedding_config()
    processed = 0
    while True:
        rows = next_batch(session, pinned, batch_size)
        if not rows:
            return processed
        vectors = _batch_embed([str(row["text"]) for row in rows], config)
        for row, vector in zip(rows, vectors):
            session.execute(
                text(
                    """
                    UPDATE source_chunks
                    SET embedding = :embedding,
                        embedding_provider = :provider,
                        embedding_model = :model,
                        embedding_dimension = :dimension,
                        updated_at = now()
                    WHERE id = :id
                    """
                ),
                {"id": row["id"], "embedding": list(vector), **pinned},
            )
        session.commit()
        processed += len(rows)


def write_report(path: str, report: dict[str, Any]) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="update rows; default is audit only")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--report", default="")
    args = parser.parse_args()

    if args.batch_size < 1 or args.batch_size > 100:
        raise SystemExit("--batch-size must be between 1 and 100")

    engine = create_engine(dsn())
    pinned = pinned_config()
    if args.apply:
        ensure_apply_can_write_real_embeddings(pinned)
    with Session(engine) as session:
        before = audit(session, pinned)
        processed = reembed(session, pinned, args.batch_size) if args.apply else 0
        after = audit(session, pinned)

    report = {
        "wp": "B2",
        "mode": "apply" if args.apply else "audit",
        "before": before,
        "reembedded": processed,
        "after": after,
        "gate_passed": after["needs_reembed"] == 0,
    }
    print(json.dumps(report, indent=2, default=str))
    write_report(args.report, report)
    return 0 if report["gate_passed"] or not args.apply else 1


if __name__ == "__main__":
    sys.exit(main())
