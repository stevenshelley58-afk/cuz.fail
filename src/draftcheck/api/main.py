"""FastAPI shell for the V3 DraftCheck API."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from draftcheck.api.v1 import create_v1_router
from draftcheck.config import get_settings


LOGGER = logging.getLogger("draftcheck.api")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="DraftCheck WA API",
        version="0.1.0",
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid4().hex
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            LOGGER.exception(
                json.dumps(
                    {
                        "event": "request.failed",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                    },
                    sort_keys=True,
                )
            )
            raise
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["x-request-id"] = request_id
        LOGGER.info(
            json.dumps(
                {
                    "event": "request.completed",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "elapsed_ms": elapsed_ms,
                },
                sort_keys=True,
            )
        )
        return response

    @app.exception_handler(NotImplementedError)
    async def not_implemented_handler(
        request: Request,
        exc: NotImplementedError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=501,
            media_type="application/problem+json",
            content={
                "type": "about:blank",
                "title": "Not Implemented",
                "status": 501,
                "detail": str(exc) or "This V3 endpoint is a contract stub.",
                "instance": str(request.url.path),
            },
        )

    app.include_router(create_v1_router(), prefix="/api/v1")
    return app


app = create_app()
