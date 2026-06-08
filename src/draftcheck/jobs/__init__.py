"""Postgres-backed V3 job package."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Protocol, TypeVar

try:
    import procrastinate
except ModuleNotFoundError:  # pragma: no cover - exercised when optional runtime dep is absent.
    procrastinate = None


TaskFunc = TypeVar("TaskFunc", bound=Callable[..., object])


def _conninfo() -> str:
    conninfo = os.getenv("PROCRASTINATE_DB_URI")
    if conninfo:
        return conninfo
    database_url = os.getenv("DATABASE_URL", "")
    if database_url.startswith("postgresql+psycopg://"):
        return "postgresql://" + database_url.removeprefix("postgresql+psycopg://")
    if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
        return database_url
    raise RuntimeError("PROCRASTINATE_DB_URI or a PostgreSQL DATABASE_URL is required")


class _FallbackProcrastinateApp:
    def task(self, *, name: str, queue: str) -> Callable[[TaskFunc], TaskFunc]:
        def decorate(func: TaskFunc) -> TaskFunc:
            setattr(func, "procrastinate_task", {"name": name, "queue": queue})
            return func

        return decorate


class _TaskRegistrar(Protocol):
    def task(self, *, name: str, queue: str) -> Callable[[TaskFunc], TaskFunc]: ...


def _create_procrastinate_app() -> _TaskRegistrar:
    if procrastinate is None:
        return _FallbackProcrastinateApp()
    return procrastinate.App(
        connector=procrastinate.PsycopgConnector(
            conninfo=_conninfo(),
        ),
        worker_defaults={"listen_notify": False},
    )


procrastinate_app = _create_procrastinate_app()


@procrastinate_app.task(name="draftcheck.noop", queue="default")
def noop() -> str:
    return "ok"


@procrastinate_app.task(name="draftcheck.hermes.governance_canary", queue="hermes")
def hermes_governance_canary() -> dict[str, object]:
    return {
        "status": "ok",
        "trace_required": True,
        "skill_version_required": True,
        "spend_capped": True,
        "allowed_outputs": ["source candidates", "review worklists", "drafts requiring signoff"],
        "forbidden_outputs": ["compliance verdicts", "rule approval", "submission-ready exports"],
    }


@procrastinate_app.task(name="draftcheck.sources.cockburn_monitor", queue="source_freshness_audit")
def cockburn_source_monitor() -> dict[str, object]:
    return {
        "status": "monitoring",
        "local_government": "City of Cockburn",
        "canary_address": "3 Black Swan Rise, Beeliar WA 6164",
        "policy": "cite_or_refuse",
        "pending": [
            "official source fetch",
            "source version review",
            "cadastre/G-NAF import",
            "rule extraction review",
        ],
    }
