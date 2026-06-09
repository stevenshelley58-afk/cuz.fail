"""Hermes — autonomous background agent for source processing and rule extraction."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class HermesAgent:
    """Continuous poll-based background agent.

    Responsibilities:
    - Monitor source_versions for new/stale documents needing clause extraction.
    - Run 3-pass LLM extraction on unprocessed rule-bearing clauses.
    - Curate agent_memory (council/parser quirks learned over time).
    """

    def __init__(
        self,
        session_factory,
        adapter,
        poll_interval_seconds: int = 60,
    ) -> None:
        self.session_factory = session_factory
        self.adapter = adapter
        self.poll_interval = poll_interval_seconds
        self._running = False

    async def start(self) -> None:
        """Start the continuous poll loop."""
        self._running = True
        logger.info("Hermes agent started (poll_interval=%ds)", self.poll_interval)
        while self._running:
            try:
                await self._tick()
            except Exception as exc:  # noqa: BLE001
                logger.error("Hermes tick error: %s", exc, exc_info=True)
            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        """Signal the loop to exit after the current tick."""
        self._running = False
        logger.info("Hermes agent stopping")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _tick(self) -> None:
        """One poll cycle: process pending work in priority order."""
        async with self.session_factory() as session:
            await self._process_pending_source_versions(session)
            await self._process_pending_clauses(session)
            await self._curate_memory(session)

    async def _process_pending_source_versions(self, session: AsyncSession) -> None:
        """Find source_versions in 'pending' state and trigger clause parsing."""
        from draftcheck.agent.clause_parser import ClauseParser  # local import to avoid cycles

        now = datetime.now(UTC)
        result = await session.execute(
            text(
                """
                SELECT id FROM source_versions
                WHERE review_status = 'pending'
                  AND effective_from <= :now
                ORDER BY effective_from
                LIMIT 5
                """
            ),
            {"now": now},
        )
        rows = result.fetchall()
        if not rows:
            return

        parser = ClauseParser()
        for (sv_id,) in rows:
            try:
                await session.execute(
                    text(
                        "UPDATE source_versions SET review_status = 'processing' WHERE id = :id"
                    ),
                    {"id": sv_id},
                )
                await session.commit()
                parse_result = await parser.parse_source_version(str(sv_id), session)
                logger.info(
                    "Hermes parsed source_version %s: created=%d updated=%d",
                    sv_id,
                    parse_result.clauses_created,
                    parse_result.clauses_updated,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Hermes failed to parse source_version %s: %s", sv_id, exc, exc_info=True
                )
                await session.rollback()
                await session.execute(
                    text(
                        "UPDATE source_versions SET review_status = 'error' WHERE id = :id"
                    ),
                    {"id": sv_id},
                )
                await session.commit()

    async def _process_pending_clauses(self, session: AsyncSession) -> None:
        """Enqueue extraction for rule-bearing clauses that have no candidates yet."""
        from draftcheck.domain.rules.service import enqueue_extraction_group  # local import

        result = await session.execute(
            text(
                """
                SELECT c.id, c.skill_version_id
                FROM clauses c
                LEFT JOIN rule_candidates rc ON rc.clause_id = c.id
                WHERE c.disposition = 'rule_bearing'
                  AND rc.id IS NULL
                ORDER BY c.created_at
                LIMIT 10
                """
            )
        )
        rows = result.fetchall()
        if not rows:
            return

        for (clause_id, skill_version_id) in rows:
            try:
                group_id = enqueue_extraction_group(clause_id, skill_version_id, session)  # type: ignore[arg-type]
                await session.commit()
                logger.info(
                    "Hermes enqueued extraction group %s for clause %s", group_id, clause_id
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Hermes failed to enqueue extraction for clause %s: %s",
                    clause_id,
                    exc,
                    exc_info=True,
                )
                await session.rollback()

    async def _curate_memory(self, session: AsyncSession) -> None:
        """Record refusal patterns and expire stale memory entries."""
        from draftcheck.agent.memory import AgentMemory  # local import to avoid cycles

        memory = AgentMemory()

        # Expire stale entries first
        await memory.expire_stale(session)

        # Find job_traces with repeated refusals in the last hour
        cutoff = datetime.now(UTC) - timedelta(hours=1)
        result = await session.execute(
            text(
                """
                SELECT source_version_id, COUNT(*) as refusal_count
                FROM job_traces
                WHERE status = 'refused'
                  AND created_at > :cutoff
                  AND source_version_id IS NOT NULL
                GROUP BY source_version_id
                HAVING COUNT(*) >= 3
                """
            ),
            {"cutoff": cutoff},
        )
        rows = result.fetchall()
        for (sv_id, count) in rows:
            key = "repeated_refusal"
            content = (
                f"Source version {sv_id} produced {count} LLM refusals in the last hour. "
                "Check content for prohibited material or overly broad queries."
            )
            try:
                await memory.record(
                    memory_key=key,
                    subject_type="source_version",
                    subject_id=str(sv_id),
                    content=content,
                    confidence=min(0.5 + count * 0.1, 0.95),
                    session=session,
                    ttl_days=7,
                )
                await session.commit()
                logger.warning(
                    "Hermes recorded refusal memory for source_version %s (%d refusals)",
                    sv_id,
                    count,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Hermes failed to record memory for %s: %s", sv_id, exc, exc_info=True
                )
                await session.rollback()
