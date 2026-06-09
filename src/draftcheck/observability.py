"""Observability bootstrapping — Sentry/GlitchTip error tracking."""

from __future__ import annotations

import logging

LOGGER = logging.getLogger(__name__)


def init_sentry(dsn: str, *, app_env: str = "local", release: str | None = None) -> None:
    """Initialise Sentry SDK if a DSN is configured; no-op otherwise."""
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=app_env,
            release=release,
            traces_sample_rate=0.05,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR),
            ],
            send_default_pii=False,
        )
        LOGGER.info("Sentry initialised (env=%s)", app_env)
    except ImportError:
        LOGGER.warning("sentry-sdk not installed; error tracking disabled")
    except Exception:
        LOGGER.warning("Sentry init failed; error tracking disabled", exc_info=True)
