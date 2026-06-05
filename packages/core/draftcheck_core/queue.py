from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from draftcheck_core.config import get_settings


@dataclass(frozen=True)
class QueueHandle:
    queue_name: str
    backend: str


def queue_handle(queue_name: str = "default") -> QueueHandle:
    settings = get_settings()
    backend = "redis-rq" if settings.hermes_enabled else "local-disabled"
    return QueueHandle(queue_name=queue_name, backend=backend)


def enqueue_local_placeholder(job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    handle = queue_handle(job_type)
    return {
        "job_type": job_type,
        "queue_name": handle.queue_name,
        "backend": handle.backend,
        "payload": payload,
        "status": "disabled" if handle.backend == "local-disabled" else "queued",
    }
