"""Guest budget enforcement dependency.

Guests get the real pipeline behind a server-enforced budget. The enforced
limit is ceil(displayed * guest_quota_factor); the headroom multiplier and the
enforced number must never leak into any client-visible response.
"""

from __future__ import annotations

import math
import os
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, status

from draftcheck.api.auth import get_current_session
from draftcheck.config import Settings, get_settings
from draftcheck.domain.identity import ActiveSession, IdentityRole
from draftcheck.domain.identity.guest_usage import (
    GuestUsageStore,
    InMemoryGuestUsageStore,
    SqlAlchemyGuestUsageStore,
)


_guest_usage_store: GuestUsageStore | None = None


def get_guest_usage_store() -> GuestUsageStore:
    global _guest_usage_store
    if _guest_usage_store is None:
        database_url = os.getenv("DATABASE_URL")
        if database_url and os.getenv("DRAFTCHECK_AUTH_STORE", "auto") != "memory":
            _guest_usage_store = SqlAlchemyGuestUsageStore.from_database_url(database_url)
        else:
            _guest_usage_store = InMemoryGuestUsageStore()
    return _guest_usage_store


def enforced_limit(displayed: int, factor: float) -> int:
    return math.ceil(displayed * factor)


def guest_quota(feature: Literal["address", "chat"]):
    """Dependency factory: meter guests on `feature`; non-guests pass through."""

    def dep(
        active_session: Annotated[ActiveSession, Depends(get_current_session)],
        settings: Annotated[Settings, Depends(get_settings)],
        usage_store: Annotated[GuestUsageStore, Depends(get_guest_usage_store)],
    ) -> None:
        if active_session.user.role != IdentityRole.GUEST:
            return
        displayed = settings.guest_address_limit if feature == "address" else settings.guest_chat_limit
        limit = enforced_limit(displayed, settings.guest_quota_factor)
        if not usage_store.increment_and_check(active_session.user.id, feature, limit):
            # Deliberately number-free: never reveal the enforced limit or remaining count.
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="guest_allowance_used",
                headers={"x-lotfile-feature": feature},
            )

    return dep
