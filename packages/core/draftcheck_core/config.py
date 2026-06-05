from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./draftcheck.db")
    object_storage_root: str = os.getenv("OBJECT_STORAGE_ROOT", ".storage")
    hermes_enabled: bool = os.getenv("HERMES_ENABLED", "false").lower() == "true"
    hermes_base_url: str = os.getenv("HERMES_BASE_URL", "")
    hermes_api_key: str = os.getenv("HERMES_API_KEY", "")
    hermes_max_concurrency: int = int(os.getenv("HERMES_MAX_CONCURRENCY", "4"))
    hermes_default_model: str = os.getenv("HERMES_DEFAULT_MODEL", "cheap-extraction-model")
    hermes_review_model: str = os.getenv("HERMES_REVIEW_MODEL", "strong-review-model")
    hermes_timeout_ms: int = int(os.getenv("HERMES_TIMEOUT_MS", "30000"))
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "mock")


def get_settings() -> Settings:
    return Settings()
