from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: str) -> int:
    return int(os.getenv(name, default))


def _env_float(name: str, default: str) -> float:
    return float(os.getenv(name, default))


def _env_csv(name: str, default: str) -> tuple[str, ...]:
    return tuple(value.strip() for value in os.getenv(name, default).split(",") if value.strip())


def _database_url() -> str:
    raw_url = os.getenv("DATABASE_URL", "sqlite:///./draftcheck.db")
    if raw_url.startswith("postgres://"):
        return f"postgresql+psycopg://{raw_url.removeprefix('postgres://')}"
    if raw_url.startswith("postgresql://"):
        return f"postgresql+psycopg://{raw_url.removeprefix('postgresql://')}"
    return raw_url


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=_database_url)
    object_storage_root: str = field(default_factory=lambda: os.getenv("OBJECT_STORAGE_ROOT", ".storage"))
    require_durable_database: bool = field(default_factory=lambda: _env_bool("REQUIRE_DURABLE_DATABASE"))
    require_durable_object_storage: bool = field(
        default_factory=lambda: _env_bool("REQUIRE_DURABLE_OBJECT_STORAGE")
    )
    s3_endpoint_url: str = field(default_factory=lambda: os.getenv("S3_ENDPOINT_URL", ""))
    s3_region: str = field(default_factory=lambda: os.getenv("S3_REGION", "us-east-1"))
    s3_access_key_id: str = field(default_factory=lambda: os.getenv("S3_ACCESS_KEY_ID", ""))
    s3_secret_access_key: str = field(default_factory=lambda: os.getenv("S3_SECRET_ACCESS_KEY", ""))
    s3_session_token: str = field(default_factory=lambda: os.getenv("S3_SESSION_TOKEN", ""))
    s3_bucket_raw_sources: str = field(default_factory=lambda: os.getenv("S3_BUCKET_RAW_SOURCES", "raw-sources"))
    s3_bucket_parsed_sources: str = field(
        default_factory=lambda: os.getenv("S3_BUCKET_PARSED_SOURCES", "parsed-sources")
    )
    s3_bucket_uploads: str = field(default_factory=lambda: os.getenv("S3_BUCKET_UPLOADS", "uploads"))
    s3_bucket_exports: str = field(default_factory=lambda: os.getenv("S3_BUCKET_EXPORTS", "exports"))
    hermes_enabled: bool = field(default_factory=lambda: _env_bool("HERMES_ENABLED"))
    hermes_base_url: str = field(default_factory=lambda: os.getenv("HERMES_BASE_URL", ""))
    hermes_api_key: str = field(default_factory=lambda: os.getenv("HERMES_API_KEY", ""))
    hermes_max_concurrency: int = field(default_factory=lambda: _env_int("HERMES_MAX_CONCURRENCY", "4"))
    hermes_default_model: str = field(default_factory=lambda: os.getenv("HERMES_DEFAULT_MODEL", "cheap-extraction-model"))
    hermes_review_model: str = field(default_factory=lambda: os.getenv("HERMES_REVIEW_MODEL", "strong-review-model"))
    hermes_timeout_ms: int = field(default_factory=lambda: _env_int("HERMES_TIMEOUT_MS", "30000"))
    rq_enabled: bool = field(default_factory=lambda: _env_bool("RQ_ENABLED"))
    rq_redis_url: str = field(
        default_factory=lambda: os.getenv("RQ_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    )
    rq_default_queue: str = field(default_factory=lambda: os.getenv("RQ_DEFAULT_QUEUE", "default"))
    rq_queues: tuple[str, ...] = field(
        default_factory=lambda: _env_csv(
            "RQ_QUEUES",
            "default,source_ingestion,council_pack,rfi_analysis,source_freshness_audit",
        )
    )
    rq_job_timeout_seconds: int = field(default_factory=lambda: _env_int("RQ_JOB_TIMEOUT_SECONDS", "300"))
    rq_retry_max: int = field(default_factory=lambda: _env_int("RQ_RETRY_MAX", "1"))
    rq_retry_interval_seconds: int = field(default_factory=lambda: _env_int("RQ_RETRY_INTERVAL_SECONDS", "30"))
    rq_socket_connect_timeout_seconds: int = field(default_factory=lambda: _env_int("RQ_SOCKET_CONNECT_TIMEOUT_SECONDS", "1"))
    rq_socket_timeout_seconds: int = field(default_factory=lambda: _env_int("RQ_SOCKET_TIMEOUT_SECONDS", "1"))
    rq_worker_burst: bool = field(default_factory=lambda: _env_bool("RQ_WORKER_BURST"))
    upload_max_bytes: int = field(default_factory=lambda: _env_int("UPLOAD_MAX_BYTES", str(25 * 1024 * 1024)))
    rate_limit_enabled: bool = field(default_factory=lambda: _env_bool("RATE_LIMIT_ENABLED", "true"))
    rate_limit_window_seconds: float = field(default_factory=lambda: _env_float("RATE_LIMIT_WINDOW_SECONDS", "60"))
    rate_limit_chat_requests: int = field(default_factory=lambda: _env_int("RATE_LIMIT_CHAT_REQUESTS", "120"))
    rate_limit_upload_requests: int = field(default_factory=lambda: _env_int("RATE_LIMIT_UPLOAD_REQUESTS", "20"))
    api_auth_enabled: bool = field(default_factory=lambda: _env_bool("API_AUTH_ENABLED"))
    api_auth_keys: tuple[str, ...] = field(default_factory=lambda: _env_csv("API_AUTH_KEYS", ""))
    cors_allowed_origins: tuple[str, ...] = field(default_factory=lambda: _env_csv("CORS_ALLOWED_ORIGINS", "*"))
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "mock"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-5.5"))
    llm_timeout_seconds: int = field(default_factory=lambda: _env_int("LLM_TIMEOUT_SECONDS", "30"))
    llm_max_output_tokens: int = field(default_factory=lambda: _env_int("LLM_MAX_OUTPUT_TOKENS", "700"))
    embedding_provider: str = field(default_factory=lambda: os.getenv("EMBEDDING_PROVIDER", "mock"))
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", ""))
    embedding_dimensions: int = field(default_factory=lambda: _env_int("EMBEDDING_DIMENSIONS", "0"))
    embedding_timeout_seconds: int = field(default_factory=lambda: _env_int("EMBEDDING_TIMEOUT_SECONDS", "30"))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    openrouter_api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    openrouter_base_url: str = field(
        default_factory=lambda: os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    )
    openrouter_site_url: str = field(
        default_factory=lambda: os.getenv("OPENROUTER_SITE_URL", "https://app.cuz.fail")
    )
    openrouter_app_name: str = field(default_factory=lambda: os.getenv("OPENROUTER_APP_NAME", "LotFile"))
    bootstrap_demo_source_library: bool = field(default_factory=lambda: _env_bool("BOOTSTRAP_DEMO_SOURCE_LIBRARY"))


def get_settings() -> Settings:
    return Settings()
