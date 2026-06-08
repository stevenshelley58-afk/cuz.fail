from __future__ import annotations

import argparse
import os

from draftcheck_core.config import Settings, get_settings
from draftcheck_core.database import init_database
from draftcheck_core.queue import check_rq_ready, redis_connection
from draftcheck_worker.jobs import missing_required_job_types, registered_job_types


def check_worker_ready(settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    rq = check_rq_ready(settings)
    missing_handlers = sorted(missing_required_job_types())
    checks = {
        "rq": rq,
        "registered_job_types": {"status": "ok", "detail": ", ".join(sorted(registered_job_types()))},
        "missing_job_types": {
            "status": "warning" if missing_handlers else "ok",
            "detail": ", ".join(missing_handlers) if missing_handlers else "none",
        },
    }
    status = "ok" if rq["status"] == "ok" else "error"
    return {"status": status, "checks": checks}


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="DraftCheck WA RQ worker")
    parser.add_argument("--check-ready", action="store_true", help="run worker readiness probe and exit")
    args = parser.parse_args()

    if args.check_ready:
        readiness = check_worker_ready(settings)
        print(readiness)
        raise SystemExit(0 if readiness["status"] == "ok" else 1)

    if not settings.rq_enabled:
        raise SystemExit("DraftCheck WA worker disabled because RQ_ENABLED=false")

    try:
        from rq import SimpleWorker, Worker
    except ImportError as exc:  # pragma: no cover - dependency is declared in pyproject
        raise SystemExit("rq package is required to run the DraftCheck worker") from exc

    init_database()
    worker_class = SimpleWorker if os.name == "nt" else Worker
    worker = worker_class(list(settings.rq_queues), connection=redis_connection(settings))
    worker.work(burst=settings.rq_worker_burst)


if __name__ == "__main__":
    main()
