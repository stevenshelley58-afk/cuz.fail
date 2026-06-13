"""Durable job-trace store backed by the job_traces DB table.

Writes each trace to the database so that the daily spend counters survive
container restarts. The adapter seeds its in-memory counters from this store
on first use.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy import text

from draftcheck.ai.substrate import JobTrace

LOGGER = logging.getLogger(__name__)

_CENTS_PER_DOLLAR = Decimal("100")
_ADAPTER_NAME = "LocalDeterministicModelAdapter"


class DbJobTraceStore:
    """Persists traces to `job_traces` and seeds daily counters from it on restart."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def append(self, trace: JobTrace) -> None:
        from draftcheck.db.models import JobTrace as DbJobTrace  # avoid circular at module level

        db_row = DbJobTrace(
            id=uuid4(),
            org_id=None,
            job_id=trace.job_id,
            correlation_id=trace.id,
            adapter_name=_ADAPTER_NAME,
            provider=trace.model_provider,
            model=trace.model,
            skill_version_id=trace.skill_version_id,
            prompt_hash=trace.prompt_hash,
            input_artifact_ids_json=list(trace.input_artifact_ids),
            output_artifact_ids_json=list(trace.output_artifact_ids),
            status=trace.status,
            input_tokens=trace.input_tokens,
            output_tokens=trace.output_tokens,
            cost_usd=Decimal(trace.cost_cents) / _CENTS_PER_DOLLAR,
            spend_metadata_json={"refusal_reason": trace.refusal_reason} if trace.refusal_reason else {},
            started_at=trace.created_at,
            finished_at=trace.created_at,
        )
        session = self._session_factory()
        try:
            session.add(db_row)
            session.commit()
        except Exception:
            session.rollback()
            LOGGER.warning("DbJobTraceStore.append failed — trace not persisted", exc_info=True)
        finally:
            session.close()

    def contains(self, trace_id: str) -> bool:
        session = self._session_factory()
        try:
            row = session.execute(
                text("SELECT 1 FROM job_traces WHERE correlation_id = :trace_id LIMIT 1"),
                {"trace_id": trace_id},
            ).fetchone()
            return row is not None
        except Exception:
            LOGGER.warning("DbJobTraceStore.contains failed", exc_info=True)
            return False
        finally:
            session.close()

    def seed_daily_counters(self, today: date) -> tuple[int, int]:
        """Return (total_tokens, cost_cents) recorded today in the DB for system traces."""
        today_utc = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        session = self._session_factory()
        try:
            row = session.execute(
                text(
                    "SELECT "
                    "  COALESCE(SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)), 0),"
                    "  COALESCE(ROUND(SUM(COALESCE(cost_usd, 0)) * 100), 0) "
                    "FROM job_traces "
                    "WHERE org_id IS NULL AND started_at >= :today"
                ),
                {"today": today_utc},
            ).fetchone()
            tokens = int(row[0]) if row else 0
            cost_cents = int(row[1]) if row else 0
            LOGGER.info(
                "DbJobTraceStore seeded daily counters: tokens=%d cost_cents=%d", tokens, cost_cents
            )
            return tokens, cost_cents
        except Exception:
            LOGGER.warning("DbJobTraceStore.seed_daily_counters failed — starting at zero", exc_info=True)
            return 0, 0
        finally:
            session.close()
