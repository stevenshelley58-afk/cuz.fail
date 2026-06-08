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
    can_review,
    require_reviewer,
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


def test_magic_link_and_session_tokens_are_stored_only_as_hashes() -> None:
    with auth_client() as (client, store, sender, settings):
        org = store.get_or_create_org()
        store.get_or_create_user(org=org, email="Owner@Example.test", role=IdentityRole.OWNER)

        requested = client.post(
            "/api/v1/auth/magic-link/request",
            json={"email": "Owner@Example.test"},
            headers={"origin": "http://app.test"},
        )

        assert requested.status_code == 202
        assert requested.json()["status"] == "accepted"
        assert sender.sent_messages

        raw_magic_token = _token_from_magic_link(sender.sent_messages[-1].magic_link)
        magic_hash = hash_token(raw_magic_token)
        assert raw_magic_token not in store.magic_links_by_hash
        assert magic_hash in store.magic_links_by_hash
        assert not hasattr(store.magic_links_by_hash[magic_hash], "token")

        verified = client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": raw_magic_token},
            headers={"origin": "http://app.test"},
        )

        assert verified.status_code == 200
        assert "token" not in verified.json()["session"]

        raw_session_token = client.cookies.get(settings.session_cookie_name)
        assert raw_session_token is not None
        session_hash = hash_token(raw_session_token)
        assert raw_session_token not in store.sessions_by_hash
        assert session_hash in store.sessions_by_hash
        assert not hasattr(store.sessions_by_hash[session_hash], "token")

        session = client.get("/api/v1/auth/session")
        assert session.status_code == 200
        assert session.json()["user"]["email"] == "owner@example.test"

        logout = client.post("/api/v1/auth/logout", headers={"origin": "http://app.test"})
        assert logout.status_code == 200
        assert client.get("/api/v1/auth/session").status_code == 401


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


def test_reviewer_guard_accepts_owner_and_reviewer_only() -> None:
    assert can_review(IdentityRole.OWNER)
    assert can_review(IdentityRole.REVIEWER)
    assert require_reviewer("owner") == IdentityRole.OWNER
    assert require_reviewer("reviewer") == IdentityRole.REVIEWER

    assert not can_review("auditor")
    with pytest.raises(PermissionError):
        require_reviewer("auditor")


def test_magic_link_request_refuses_unprovisioned_public_user() -> None:
    with auth_client() as (client, _store, sender, _settings):
        requested = client.post(
            "/api/v1/auth/magic-link/request",
            json={"email": "new-user@example.test"},
            headers={"origin": "http://app.test"},
        )

        imported = client.post(
            "/api/v1/sources/import",
            json={
                "title": "Self Registered Import",
                "content": "A public magic-link user must not approve global sources.",
                "licence_status": "open",
            },
            headers={"origin": "http://app.test"},
        )

        assert requested.status_code == 400
        assert sender.sent_messages == []
        assert imported.status_code == 401


def test_new_v3_app_has_no_dev_login_route() -> None:
    client = TestClient(create_app())

    assert client.post("/api/v1/auth/dev-login").status_code == 404
    paths = set(client.get("/api/v1/openapi.json").json()["paths"])
    assert not any("dev-login" in path for path in paths)


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
