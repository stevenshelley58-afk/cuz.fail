"""Agent memory — record and retrieve learned quirks about councils/parsers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class AgentMemory:
    """Thin persistence layer over the agent_memory table."""

    async def record(
        self,
        memory_key: str,
        subject_type: str,
        subject_id: str,
        content: str,
        confidence: float,
        session: AsyncSession,
        source_job_trace_id: str | None = None,
        ttl_days: int = 30,
    ) -> None:
        """Upsert a memory entry.

        If a row with (memory_key, subject_id) already exists it is updated
        in-place; otherwise a new row is inserted.  The caller is responsible
        for committing the session.
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=ttl_days)

        existing = await session.execute(
            text(
                """
                SELECT id FROM agent_memory
                WHERE memory_key = :key AND subject_id = :subject_id
                LIMIT 1
                """
            ),
            {"key": memory_key, "subject_id": subject_id},
        )
        row = existing.fetchone()

        if row is None:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_memory
                        (id, memory_key, subject_type, subject_id, content,
                         confidence, source_job_trace_id, expires_at,
                         created_at, updated_at)
                    VALUES
                        (:id, :key, :subject_type, :subject_id, :content,
                         :confidence, :trace_id, :expires_at,
                         :now, :now)
                    """
                ),
                {
                    "id": str(uuid4()),
                    "key": memory_key,
                    "subject_type": subject_type,
                    "subject_id": subject_id,
                    "content": content,
                    "confidence": confidence,
                    "trace_id": source_job_trace_id,
                    "expires_at": expires_at,
                    "now": now,
                },
            )
        else:
            await session.execute(
                text(
                    """
                    UPDATE agent_memory
                    SET content = :content,
                        confidence = :confidence,
                        source_job_trace_id = :trace_id,
                        expires_at = :expires_at,
                        updated_at = :now
                    WHERE id = :id
                    """
                ),
                {
                    "content": content,
                    "confidence": confidence,
                    "trace_id": source_job_trace_id,
                    "expires_at": expires_at,
                    "now": now,
                    "id": str(row[0]),
                },
            )

    async def recall(
        self,
        memory_key: str,
        subject_id: str,
        session: AsyncSession,
    ) -> str | None:
        """Return the content of the most recent active memory entry, or None."""
        now = datetime.now(UTC)
        result = await session.execute(
            text(
                """
                SELECT content FROM agent_memory
                WHERE memory_key = :key
                  AND subject_id = :subject_id
                  AND expires_at > :now
                ORDER BY updated_at DESC
                LIMIT 1
                """
            ),
            {"key": memory_key, "subject_id": subject_id, "now": now},
        )
        row = result.fetchone()
        return row[0] if row else None

    async def expire_stale(self, session: AsyncSession) -> int:
        """Delete expired memory entries.  Returns the number of rows deleted."""
        now = datetime.now(UTC)
        result = await session.execute(
            text("DELETE FROM agent_memory WHERE expires_at < :now RETURNING id"),
            {"now": now},
        )
        deleted = len(result.fetchall())
        await session.commit()
        return deleted
