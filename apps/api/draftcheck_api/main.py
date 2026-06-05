from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from draftcheck_api.router import router
from draftcheck_core.database import init_database


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        init_database()
        yield

    app = FastAPI(
        title="DraftCheck WA Core",
        version="0.1.0",
        description="Backend APIs for a source-cited WA residential drafting assistant.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(KeyError)
    async def _key_error(_request: Request, exc: KeyError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc).strip("'"), "code": "not_found"})

    @app.exception_handler(ValueError)
    async def _value_error(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc), "code": "bad_request"})

    app.include_router(router, prefix="/v1")
    app.include_router(router, prefix="/api")
    return app


app = create_app()
