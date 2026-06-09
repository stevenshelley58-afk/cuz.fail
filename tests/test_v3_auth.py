from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Iterator
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from draftcheck.api.auth import get_email_sender, get_identity_store
import draftcheck.api.auth as auth_module
from draftcheck.api.main import create_app
from draftcheck.config import Settings, get_settings
from draftcheck.domain.identity import (
    DevLogEmailSender,
    IdentityRole,
    InMemoryIdentityStore,
    MAGIC_LINK_TTL,
    SESSION_TTL,
    MagicLinkTokenExpiredError,
)
from draftcheck.domain.identity.tokens import hash_token


@contextmanager
def auth_client() -> Iterator[tuple[TestClient, InMemoryIdentityStore, DevLogEmailSender, Settings]]:
    app = create_app()
    store = InMemoryIdentityStore()
    sender = DevLogEmailSender()
    settings = Settings(
        frontend_url="http://app.test",
        session_cookie_secure=False,
        cors_allowed_origins=("http://app.test",),
    )
    app.dependency_overrides[get_identity_store] = lambda: store
    app.dependency_overrides[get_email_sender] = lambda: sender
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        yield client, store, sender, settings


def test_magic_link_endpoints_are_disabled() -> None:
    with auth_client() as (client, _store, _sender, _settings):
        assert client.post(
            "/api/v1/auth/magic-link/request",
            json={"email": "owner@example.test"},
            headers={"origin": "http://app.test"},
        ).status_code == 404

        assert client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": "a" * 32},
            headers={"origin": "http://app.test"},
        ).status_code == 404


def test_magic_link_and_session_expiry_windows() -> None:
    now = datetime(2026, 6, 7, 12, 0, tzinfo=UTC)
    store = InMemoryIdentityStore()
    org = store.get_or_create_org(now=now)
    store.get_or_create_user(org=org, email="owner@example.test", role=IdentityRole.OWNER, now=now)

    expired_issue = store.request_magic_link(email="owner@example.test", now=now)
    assert expired_issue.record.expires_at == now + MAGIC_LINK_TTL
    with pytest.raises(MagicLinkTokenExpiredError):
        store.consume_magic_link(
            expired_issue.token,
            now=now + MAGIC_LINK_TTL + timedelta(seconds=1),
        )

    issue = store.request_magic_link(email="owner@example.test", now=now)
    user, org, _record = store.consume_magic_link(issue.token, now=now + timedelta(minutes=1))
    session = store.create_session(user=user, org=org, now=now)

    assert session.session.expires_at == now + SESSION_TTL
    assert (
        store.get_session(
            session.token,
            now=now + SESSION_TTL + timedelta(seconds=1),
        )
        is None
    )




def test_dev_login_issues_session_for_valid_credentials() -> None:
    with auth_client() as (client, store, _sender, settings):
        response = client.post(
            "/api/v1/auth/dev-login",
            json={"username": "jemma", "password": "jemma123"},
            headers={"origin": "http://app.test"},
        )

        assert response.status_code == 200
        body = response.json()
        assert "token" not in body["session"]
        assert body["session"]["user"]["email"] == "jemma@dev.local"
        assert body["session"]["user"]["role"] == "owner"

        raw_session_token = client.cookies.get(settings.session_cookie_name)
        assert raw_session_token is not None
        assert hash_token(raw_session_token) in store.sessions_by_hash

        session = client.get("/api/v1/auth/session")
        assert session.status_code == 200
        assert session.json()["user"]["email"] == "jemma@dev.local"


def test_dev_login_rejects_invalid_credentials() -> None:
    with auth_client() as (client, _store, _sender, _settings):
        response = client.post(
            "/api/v1/auth/dev-login",
            json={"username": "jemma", "password": "nope"},
            headers={"origin": "http://app.test"},
        )

        assert response.status_code == 401



def test_auth_dependency_uses_durable_store_when_database_url_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, str | None]] = []
    backing_store = InMemoryIdentityStore(token_hash_pepper="pepper")

    class FakeSqlAlchemyIdentityStore:
        @classmethod
        def from_database_url(
            cls,
            database_url: str,
            *,
            token_hash_pepper: str | None = None,
        ) -> InMemoryIdentityStore:
            calls.append({"database_url": database_url, "token_hash_pepper": token_hash_pepper})
            return backing_store

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://fixture")
    monkeypatch.setattr(auth_module, "SqlAlchemyIdentityStore", FakeSqlAlchemyIdentityStore)
    monkeypatch.setattr(auth_module, "_identity_store", None)

    store = get_identity_store(Settings(auth_token_hash_pepper="pepper"))

    assert store is backing_store
    assert calls == [
        {
            "database_url": "postgresql+psycopg://fixture",
            "token_hash_pepper": "pepper",
        }
    ]
    monkeypatch.setattr(auth_module, "_identity_store", None)


def _token_from_magic_link(magic_link: str) -> str:
    values = parse_qs(urlparse(magic_link).query)
    return values["token"][0]
