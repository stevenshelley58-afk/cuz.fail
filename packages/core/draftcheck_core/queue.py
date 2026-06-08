from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from draftcheck_core.config import Settings, get_settings


@dataclass(frozen=True)
class QueueHandle:
    queue_name: str
    backend: str
    redis_url: str | None = None


@dataclass(frozen=True)
class EnqueueResult:
    job_type: str
    queue_name: str
    backend: str
    status: str
    rq_job_id: str | None
    payload: dict[str, Any]


def queue_handle(queue_name: str | None = None, settings: Settings | None = None) -> QueueHandle:
    settings = settings or get_settings()
    resolved_queue_name = queue_name or settings.rq_default_queue
    backend = "redis-rq" if settings.rq_enabled else "local-disabled"
    return QueueHandle(
        queue_name=resolved_queue_name,
        backend=backend,
        redis_url=settings.rq_redis_url if settings.rq_enabled else None,
    )


def redis_connection(settings: Settings | None = None):
    settings = settings or get_settings()
    try:
        from redis import Redis
    except ImportError as exc:  # pragma: no cover - dependency is declared in pyproject
        raise RuntimeError("redis package is required when RQ_ENABLED=true") from exc
    return Redis.from_url(
        settings.rq_redis_url,
        socket_connect_timeout=settings.rq_socket_connect_timeout_seconds,
        socket_timeout=settings.rq_socket_timeout_seconds,
    )


def rq_queue(queue_name: str, settings: Settings | None = None):
    settings = settings or get_settings()
    try:
        from rq import Queue
    except ImportError as exc:  # pragma: no cover - dependency is declared in pyproject
        raise RuntimeError("rq package is required when RQ_ENABLED=true") from exc
    return Queue(
        queue_name,
        connection=redis_connection(settings),
        default_timeout=settings.rq_job_timeout_seconds,
    )


def enqueue_background_job(
    job_id: str,
    job_type: str,
    payload: dict[str, Any],
    *,
    queue_name: str | None = None,
    settings: Settings | None = None,
) -> EnqueueResult:
    settings = settings or get_settings()
    handle = queue_handle(queue_name or job_type, settings=settings)
    if not settings.rq_enabled:
        return EnqueueResult(
            job_type=job_type,
            queue_name=handle.queue_name,
            backend=handle.backend,
            status="disabled",
            rq_job_id=None,
            payload=payload,
        )

    queue = rq_queue(handle.queue_name, settings=settings)
    kwargs: dict[str, Any] = {
        "job_timeout": settings.rq_job_timeout_seconds,
        "meta": {"background_job_id": job_id, "job_type": job_type},
    }
    if settings.rq_retry_max > 0:
        from rq import Retry

        kwargs["retry"] = Retry(
            max=settings.rq_retry_max,
            interval=[settings.rq_retry_interval_seconds] * settings.rq_retry_max,
        )
    rq_job = queue.enqueue("draftcheck_worker.jobs.run_background_job", job_id, **kwargs)
    return EnqueueResult(
        job_type=job_type,
        queue_name=handle.queue_name,
        backend=handle.backend,
        status="queued",
        rq_job_id=rq_job.id,
        payload=payload,
    )


def fetch_rq_job_status(remote_job_id: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    try:
        from rq.job import Job
    except ImportError as exc:  # pragma: no cover - dependency is declared in pyproject
        raise RuntimeError("rq package is required when RQ_ENABLED=true") from exc
    rq_job = Job.fetch(remote_job_id, connection=redis_connection(settings))
    return {
        "id": rq_job.id,
        "status": rq_job.get_status(refresh=True),
        "error": rq_job.exc_info,
    }


def check_rq_ready(settings: Settings | None = None) -> dict[str, str]:
    settings = settings or get_settings()
    if not settings.rq_enabled:
        return {
            "status": "disabled",
            "backend": "local-disabled",
            "detail": "RQ_ENABLED=false",
        }
    try:
        redis_connection(settings).ping()
    except Exception as exc:
        return {
            "status": "error",
            "backend": "redis-rq",
            "detail": str(exc),
        }
    return {
        "status": "ok",
        "backend": "redis-rq",
        "detail": "Redis ping ok",
    }
