"""Guest usage counters: atomic increment-and-check against a hidden enforced limit."""

from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from draftcheck.db.engine import create_session_factory
from draftcheck.domain.identity.tokens import utc_now


GuestFeature = str  # 'address' | 'chat'


class InMemoryGuestUsageStore:
    """Test/dev counterpart of the SQL-backed store."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._used: dict[tuple[UUID, str], int] = {}

    def increment_and_check(self, user_id: UUID, feature: GuestFeature, enforced_limit: int) -> bool:
        with self._lock:
            used = self._used.get((user_id, feature), 0)
            if used >= enforced_limit:
                return False
            self._used[(user_id, feature)] = used + 1
            return True


class SqlAlchemyGuestUsageStore:
    """Durable guest usage store with the same public method as the in-memory one."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    @classmethod
    def from_database_url(cls, database_url: str) -> SqlAlchemyGuestUsageStore:
        return cls(create_session_factory(database_url))

    def increment_and_check(self, user_id: UUID, feature: GuestFeature, enforced_limit: int) -> bool:
        now = utc_now()
        with self._session_factory() as session:
            with session.begin():
                session.execute(
                    text(
                        "INSERT INTO guest_usage (user_id, feature, used, updated_at) "
                        "VALUES (:user_id, :feature, 0, :now) "
                        "ON CONFLICT (user_id, feature) DO NOTHING"
                    ),
                    {"user_id": user_id, "feature": feature, "now": now},
                )
                result = session.execute(
                    text(
                        "UPDATE guest_usage SET used = used + 1, updated_at = :now "
                        "WHERE user_id = :user_id AND feature = :feature AND used < :limit"
                    ),
                    {"user_id": user_id, "feature": feature, "limit": enforced_limit, "now": now},
                )
                return (result.rowcount or 0) > 0


GuestUsageStore = InMemoryGuestUsageStore | SqlAlchemyGuestUsageStore


__all__ = [
    "GuestUsageStore",
    "InMemoryGuestUsageStore",
    "SqlAlchemyGuestUsageStore",
]
