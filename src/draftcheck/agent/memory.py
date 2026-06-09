"""Agent memory — record and retrieve learned quirks about councils/parsers."""
from __future__ import annotations
import uuid
import logging

logger = logging.getLogger(__name__)


class AgentMemory:
    async def record(
        self,
        memory_key: str,
        subject_type: str,
        subject_id: str,
        content: str,
        confidence: float,
        session,
        source_job_trace_id: str | None = None,
        ttl_days: int = 30,
    ) -> None:
        from sqlalchemy import text

        await session.execute(
            text(
                "INSERT INTO agent_memory "
                "(id, memory_key, subject_type, subject_id, content, confidence, "
                "status, source_job_trace_id, expires_at, created_at, updated_at) "
                "VALUES (:id, :mk, :st, :si, :content, :conf, 'active', "
                ":trace_id, now() + :ttl * interval '1 day', now(), now()) "
                "ON CONFLICT (memory_key, subject_id) DO UPDATE SET "
                "content = EXCLUDED.content, confidence = EXCLUDED.confidence, "
                "expires_at = EXCLUDED.expires_at, updated_at = now()"
            ),
            {
                "id": str(uuid.uuid4()),
                "mk": memory_key,
                "st": subject_type,
                "si": subject_id,
                "content": content,
                "conf": confidence,
                "trace_id": source_job_trace_id,
                "ttl": ttl_days,
            },
        )
        await session.commit()

    async def recall(
        self, memory_key: str, subject_id: str, session
    ) -> str | None:
        from sqlalchemy import text

        r = await session.execute(
            text(
                "SELECT content FROM agent_memory "
                "WHERE memory_key = :mk AND subject_id = :si "
                "AND status = 'active' AND expires_at > now() "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"mk": memory_key, "si": subject_id},
        )
        row = r.fetchone()
        return row[0] if row else None

    async def expire_stale(self, session) -> int:
        from sqlalchemy import text

        r = await session.execute(
            text(
                "UPDATE agent_memory SET status = 'expired', updated_at = now() "
                "WHERE expires_at < now() AND status = 'active' "
                "RETURNING id"
            )
        )
        expired = len(r.fetchall())
        if expired:
            logger.info("Expired %d stale agent_memory entries", expired)
            await session.commit()
        return expired
