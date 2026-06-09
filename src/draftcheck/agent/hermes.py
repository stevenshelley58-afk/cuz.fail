"""Hermes — autonomous background agent for source processing and rule extraction."""
from __future__ import annotations
import asyncio
import logging
from typing import Callable

logger = logging.getLogger(__name__)


class HermesAgent:
    """Polls for pending work and orchestrates extraction + memory curation."""

    def __init__(
        self,
        session_factory: Callable,
        adapter,
        poll_interval_seconds: int = 60,
    ) -> None:
        self._session_factory = session_factory
        self._adapter = adapter
        self._poll_interval = poll_interval_seconds
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Hermes agent started (poll_interval=%ds)", self._poll_interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Hermes agent stopped")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except Exception:
                logger.exception("Hermes tick error")
            await asyncio.sleep(self._poll_interval)

    async def _tick(self) -> None:
        async with self._session_factory() as session:
            await self._process_pending_source_versions(session)
            await self._process_pending_clauses(session)
            await self._curate_memory(session)

    async def _process_pending_source_versions(self, session) -> None:
        """Find source_versions needing clause extraction and trigger parsing."""
        from sqlalchemy import text

        result = await session.execute(
            text(
                "SELECT id FROM source_versions "
                "WHERE review_status = 'pending' "
                "LIMIT 5"
            )
        )
        rows = result.fetchall()
        for row in rows:
            try:
                from draftcheck.agent.clause_parser import ClauseParser

                parser = ClauseParser()
                await parser.parse_source_version(str(row[0]), session)
                await session.execute(
                    text(
                        "UPDATE source_versions SET review_status = 'processing' "
                        "WHERE id = :id"
                    ),
                    {"id": str(row[0])},
                )
                await session.commit()
            except Exception:
                logger.exception("Failed to process source_version %s", row[0])

    async def _process_pending_clauses(self, session) -> None:
        """Run extraction on rule-bearing clauses that have no candidates yet."""
        from sqlalchemy import text

        result = await session.execute(
            text(
                "SELECT c.id, c.clause_key "
                "FROM clauses c "
                "LEFT JOIN rule_candidates rc ON rc.clause_id = c.id "
                "WHERE c.disposition = 'rule_bearing' AND rc.id IS NULL "
                "LIMIT 10"
            )
        )
        rows = result.fetchall()
        for clause_id, clause_key in rows:
            try:
                from draftcheck.jobs.extraction import run_extraction_group

                await run_extraction_group(  # type: ignore[call-arg]
                    clause_id=str(clause_id),
                    clause_key=clause_key,
                    adapter=self._adapter,
                    session=session,
                )
            except Exception:
                logger.exception("Extraction failed for clause %s", clause_id)

    async def _curate_memory(self, session) -> None:
        """Expire stale agent_memory entries."""
        from draftcheck.agent.memory import AgentMemory

        memory = AgentMemory()
        await memory.expire_stale(session)
