from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import inspect, text

from draftcheck_core.auth import (
    authenticate_api_key,
    check_api_auth_ready,
    reset_current_auth_context,
    set_current_auth_context,
)
from draftcheck_core.config import get_settings
from draftcheck_core.database import (
    SessionLocal,
    check_database_extensions_ready,
    check_database_migrations_ready,
    check_database_persistence_ready,
)
from draftcheck_api.router import router
from draftcheck_api.rate_limit import (
    InMemoryRateLimiter,
    check_rate_limit_ready,
    rate_limit_key,
    request_rate_limit,
)
from draftcheck_core.database import init_database
from draftcheck_core.object_storage import check_object_storage_ready
from draftcheck_core.queue import check_rq_ready


CORE_READY_TABLES = ("source_documents", "source_versions", "background_jobs", "audit_events")


def create_app() -> FastAPI:
    startup_settings = get_settings()

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
        allow_origins=list(_cors_allowed_origins_for_runtime(startup_settings)),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.rate_limiter = InMemoryRateLimiter()

    @app.middleware("http")
    async def _api_auth(request: Request, call_next):
        settings = get_settings()
        context_token = set_current_auth_context(None)
        try:
            if _is_cors_preflight(request):
                return await call_next(request)
            if not _is_auth_exempt_path(request.url.path):
                deployment_blocker = _deployment_readiness_blocker(settings)
                if deployment_blocker:
                    return deployment_blocker
            if not settings.api_auth_enabled or _is_auth_exempt_path(request.url.path):
                return await call_next(request)
            auth_ready = check_api_auth_ready(settings)
            if auth_ready["status"] == "error":
                return JSONResponse(status_code=503, content={"detail": auth_ready["detail"], "code": "auth_not_ready"})
            auth_context = authenticate_api_key(_request_api_token(request), settings)
            if not auth_context:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Missing or invalid API key", "code": "unauthorized"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            reset_current_auth_context(context_token)
            context_token = set_current_auth_context(auth_context)
            return await call_next(request)
        finally:
            reset_current_auth_context(context_token)

    @app.middleware("http")
    async def _rate_limit(request: Request, call_next):
        settings = get_settings()
        limit_config = request_rate_limit(request, settings)
        if limit_config:
            bucket, limit = limit_config
            if limit > 0 and settings.rate_limit_window_seconds > 0:
                decision = app.state.rate_limiter.check(
                    key=rate_limit_key(request, bucket, settings),
                    limit=limit,
                    window_seconds=settings.rate_limit_window_seconds,
                )
                if not decision.allowed:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "Rate limit exceeded",
                            "code": "rate_limited",
                            "limit": decision.limit,
                            "window_seconds": decision.window_seconds,
                        },
                        headers={"Retry-After": str(decision.retry_after_seconds)},
                    )
        return await call_next(request)

    @app.get("/", include_in_schema=False)
    async def _root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    @app.get("/health")
    async def _health() -> dict[str, str]:
        return {"status": "ok", "service": "draftcheck-wa-core"}

    @app.get("/ready")
    async def _ready() -> JSONResponse:
        settings = get_settings()
        checks: dict[str, dict[str, str]] = _database_ready_checks()
        checks["database_persistence"] = check_database_persistence_ready(settings)
        checks["api_auth"] = check_api_auth_ready(settings)
        checks["cors"] = check_cors_ready(settings)
        checks["rate_limit"] = check_rate_limit_ready(settings)
        checks["object_storage"] = check_object_storage_ready(settings=settings)
        checks["rq"] = check_rq_ready(settings)
        status_code = 200 if all(value["status"] in {"ok", "disabled"} for value in checks.values()) else 503
        return JSONResponse(
            status_code=status_code,
            content={"status": "ok" if status_code == 200 else "error", "checks": checks},
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


def _request_api_token(request: Request) -> str:
    api_key = request.headers.get("x-api-key", "").strip()
    if api_key:
        return api_key
    authorization = request.headers.get("authorization", "").strip()
    scheme, separator, token = authorization.partition(" ")
    if separator and scheme.lower() == "bearer":
        return token.strip()
    return ""


def _deployment_readiness_blocker(settings) -> JSONResponse | None:
    if not settings.require_durable_database and not settings.require_durable_object_storage:
        return None

    checks = {
        "database_persistence": check_database_persistence_ready(settings),
        "api_auth": check_api_auth_ready(settings),
        "cors": check_cors_ready(settings),
        "rate_limit": check_rate_limit_ready(settings),
        "object_storage": check_object_storage_ready(settings=settings),
    }
    if settings.require_durable_database and checks["database_persistence"]["status"] != "error":
        checks.update(_database_ready_checks())
    if settings.rq_enabled:
        checks["rq"] = check_rq_ready(settings)
    failed = {name: check for name, check in checks.items() if check["status"] == "error"}
    if not failed:
        return None
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Deployment is not ready for protected API traffic; see /ready.",
            "code": "deployment_not_ready",
            "checks": failed,
        },
    )


def _database_ready_checks() -> dict[str, dict[str, str]]:
    checks: dict[str, dict[str, str]] = {}
    try:
        with SessionLocal() as db:
            db.execute(text("select 1"))
            bind = db.get_bind()
            inspector = inspect(bind)
            missing_tables = [table for table in CORE_READY_TABLES if not inspector.has_table(table)]
            checks["database"] = {
                "status": "ok" if not missing_tables else "error",
                "detail": "ok" if not missing_tables else f"missing tables: {', '.join(missing_tables)}",
            }
            checks["database_extensions"] = check_database_extensions_ready(db)
            checks["database_migrations"] = check_database_migrations_ready(db)
    except Exception as exc:
        checks["database"] = {"status": "error", "detail": str(exc)}
        checks["database_extensions"] = {"status": "error", "detail": "database connection unavailable"}
        checks["database_migrations"] = {"status": "error", "detail": "database connection unavailable"}
    return checks


def check_cors_ready(settings) -> dict[str, str]:
    origins = settings.cors_allowed_origins
    if settings.require_durable_database or settings.require_durable_object_storage:
        if not origins:
            return {
                "status": "error",
                "detail": "Durable deployments require CORS_ALLOWED_ORIGINS to include at least one explicit origin.",
            }
        if "*" in origins:
            return {
                "status": "error",
                "detail": "Durable deployments must not use wildcard CORS; configure CORS_ALLOWED_ORIGINS.",
            }
        return {"status": "ok", "detail": "explicit CORS origins configured"}
    if not origins or "*" in origins:
        return {"status": "disabled", "detail": "wildcard CORS allowed for local/test deployment"}
    return {"status": "ok", "detail": "explicit CORS origins configured"}


def _cors_allowed_origins_for_runtime(settings) -> tuple[str, ...]:
    origins = settings.cors_allowed_origins
    if settings.require_durable_database or settings.require_durable_object_storage:
        if not origins or "*" in origins:
            return ()
    return origins


def _is_auth_exempt_path(path: str) -> bool:
    if path in {"/", "/health", "/ready", "/docs", "/openapi.json", "/redoc"}:
        return True
    if path.endswith("/auth/dev-login"):
        return True
    return path.startswith(("/docs/", "/redoc/"))


def _is_cors_preflight(request: Request) -> bool:
    return (
        request.method.upper() == "OPTIONS"
        and bool(request.headers.get("origin"))
        and bool(request.headers.get("access-control-request-method"))
    )


app = create_app()
