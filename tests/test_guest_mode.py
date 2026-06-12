"""Guest-first-class tests: real sessions for guests, hidden server-enforced budgets.

Covers:
  1. POST /auth/guest issues a guest-role session; repeat call with the cookie
     is idempotent.
  2. Address budget: guests can create projects up to the enforced limit
     (ceil(displayed * factor)), then get 429 guest_allowance_used.
  3. Chat budget: same for /assistant.
  4. The 429 body and headers leak no numbers.
  5. Non-guest sessions are never metered.
  6. Guest orgs are isolated from each other.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Boot-time SQLite patches — must execute before SQLAlchemy model usage.
# (Same pattern as tests/test_projects_api.py.)
# ---------------------------------------------------------------------------

from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler  # noqa: E402

if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):

    def _visit_jsonb(self, type_, **kw):  # type: ignore[misc]
        return "JSON"

    SQLiteTypeCompiler.visit_JSONB = _visit_jsonb  # type: ignore[attr-defined]

import draftcheck.db.models as _models_mod  # noqa: E402

_to_drop = []
for _tbl in _models_mod.Base.metadata.tables.values():
    if _tbl.name == "documents":
        for _idx in list(_tbl.indexes):
            if _idx.name == "ix_documents_sha256" and len(_idx.columns) == 1:
                _to_drop.append(_idx)
for _idx in _to_drop:
    _idx.table.indexes.discard(_idx)

# ---------------------------------------------------------------------------
# Normal imports
# ---------------------------------------------------------------------------

import math  # noqa: E402
import os  # noqa: E402
from contextlib import contextmanager  # noqa: E402
from typing import Iterator  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import draftcheck.api.auth as auth_module  # noqa: E402
from draftcheck.api.auth import get_identity_store  # noqa: E402
from draftcheck.api.deps import get_db_session  # noqa: E402
from draftcheck.api.guest_quota import enforced_limit, get_guest_usage_store  # noqa: E402
from draftcheck.api.main import create_app  # noqa: E402
from draftcheck.config import Settings, get_settings  # noqa: E402
from draftcheck.db.models import Base  # noqa: E402
from draftcheck.domain.identity import InMemoryIdentityStore  # noqa: E402
from draftcheck.domain.identity.guest_usage import InMemoryGuestUsageStore  # noqa: E402


ORIGIN = "http://app.test"
HEADERS = {"origin": ORIGIN}

_SETTINGS = Settings(
    frontend_url=ORIGIN,
    cors_allowed_origins=(ORIGIN,),
    session_cookie_secure=False,
)

_ADDRESS_ENFORCED = enforced_limit(_SETTINGS.guest_address_limit, _SETTINGS.guest_quota_factor)
_CHAT_ENFORCED = enforced_limit(_SETTINGS.guest_chat_limit, _SETTINGS.guest_quota_factor)

_ENGINE = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
_NEEDED_TABLES = ["orgs", "projects", "properties", "property_facts", "proposals"]
Base.metadata.create_all(
    _ENGINE,
    tables=[Base.metadata.tables[t] for t in _NEEDED_TABLES],
)
_SESSION_FACTORY = sessionmaker(bind=_ENGINE, autoflush=False, autocommit=False, expire_on_commit=False)


def _db_session() -> Iterator:
    session = _SESSION_FACTORY()
    try:
        yield session
        session.commit()
    finally:
        session.close()


@contextmanager
def guest_app() -> Iterator:
    app = create_app()
    store = InMemoryIdentityStore()
    usage = InMemoryGuestUsageStore()
    app.dependency_overrides[get_identity_store] = lambda: store
    app.dependency_overrides[get_settings] = lambda: _SETTINGS
    app.dependency_overrides[get_guest_usage_store] = lambda: usage
    app.dependency_overrides[get_db_session] = _db_session
    auth_module._guest_session_window.clear()
    yield app, store


def _client(app) -> TestClient:
    return TestClient(app, headers=HEADERS)


def test_guest_session_created_and_idempotent() -> None:
    with guest_app() as (app, _store):
        client = _client(app)
        first = client.post("/api/v1/auth/guest")
        assert first.status_code == 200
        session = first.json()["session"]
        assert session["user"]["role"] == "guest"
        assert session["user"]["email"].endswith("@guest.lotfile.app")

        # Same cookie → same session, no new budget.
        second = client.post("/api/v1/auth/guest")
        assert second.status_code == 200
        assert second.json()["session"]["id"] == session["id"]

        # /auth/session reports the guest role for the SPA.
        whoami = client.get("/api/v1/auth/session")
        assert whoami.status_code == 200
        assert whoami.json()["user"]["role"] == "guest"


def test_guest_mode_disabled_returns_404() -> None:
    with guest_app() as (app, _store):
        disabled = Settings(
            frontend_url=ORIGIN,
            cors_allowed_origins=(ORIGIN,),
            guest_mode_enabled=False,
        )
        app.dependency_overrides[get_settings] = lambda: disabled
        client = _client(app)
        assert client.post("/api/v1/auth/guest").status_code == 404


def test_guest_address_budget_enforced_with_hidden_headroom() -> None:
    assert _ADDRESS_ENFORCED == math.ceil(_SETTINGS.guest_address_limit * 1.5)
    with guest_app() as (app, _store):
        client = _client(app)
        assert client.post("/api/v1/auth/guest").status_code == 200

        for i in range(_ADDRESS_ENFORCED):
            created = client.post("/api/v1/projects", json={"name": f"Check {i}"})
            assert created.status_code == 201, created.text

        blocked = client.post("/api/v1/projects", json={"name": "One too many"})
        assert blocked.status_code == 429
        assert blocked.json() == {"detail": "guest_allowance_used"}
        assert blocked.headers["x-lotfile-feature"] == "address"


def test_guest_chat_budget_enforced_with_hidden_headroom() -> None:
    with guest_app() as (app, _store):
        client = _client(app)
        assert client.post("/api/v1/auth/guest").status_code == 200

        for i in range(_CHAT_ENFORCED):
            r = client.post("/api/v1/assistant", json={"message": f"What does R20 allow? ({i})"})
            assert r.status_code == 200, r.text

        blocked = client.post("/api/v1/assistant", json={"message": "One more"})
        assert blocked.status_code == 429
        assert blocked.json() == {"detail": "guest_allowance_used"}
        assert blocked.headers["x-lotfile-feature"] == "chat"


def test_429_leaks_no_numbers() -> None:
    with guest_app() as (app, _store):
        client = _client(app)
        client.post("/api/v1/auth/guest")
        for _ in range(_ADDRESS_ENFORCED):
            client.post("/api/v1/projects", json={"name": "Check"})
        blocked = client.post("/api/v1/projects", json={"name": "Check"})
        assert blocked.status_code == 429
        assert not any(ch.isdigit() for ch in blocked.text)
        for name, value in blocked.headers.items():
            if name.lower().startswith("x-lotfile"):
                assert not any(ch.isdigit() for ch in value)


def test_non_guest_sessions_are_never_metered() -> None:
    with guest_app() as (app, _store):
        client = _client(app)
        login = client.post(
            "/api/v1/auth/dev-login",
            json={
                "username": os.getenv("DEV_LOGIN_USERNAME", "jemma"),
                "password": os.getenv("DEV_LOGIN_PASSWORD", "jemma" + "123"),
            },
        )
        assert login.status_code == 200
        assert login.json()["session"]["user"]["role"] == "owner"

        for i in range(_ADDRESS_ENFORCED + 2):
            assert client.post("/api/v1/projects", json={"name": f"Owner {i}"}).status_code == 201
        for i in range(_CHAT_ENFORCED + 2):
            assert client.post("/api/v1/assistant", json={"message": f"Q {i}"}).status_code == 200


def test_guest_orgs_are_isolated() -> None:
    with guest_app() as (app, _store):
        client_a = _client(app)
        client_b = _client(app)
        assert client_a.post("/api/v1/auth/guest").status_code == 200
        assert client_b.post("/api/v1/auth/guest").status_code == 200

        created = client_a.post("/api/v1/projects", json={"name": "Guest A project"})
        assert created.status_code == 201
        project_id = created.json()["id"]

        # Guest B cannot read guest A's project; 404 avoids existence leaks.
        assert client_b.get(f"/api/v1/projects/{project_id}").status_code == 404
        assert client_b.get("/api/v1/projects").json() == []
        # Guest A still can.
        assert client_a.get(f"/api/v1/projects/{project_id}").status_code == 200


def test_guest_create_rate_limited_per_ip() -> None:
    with guest_app() as (app, _store):
        for _ in range(auth_module._GUEST_SESSION_LIMIT_PER_HOUR):
            # Fresh client each time → no cookie → new guest session.
            assert _client(app).post("/api/v1/auth/guest").status_code == 200
        assert _client(app).post("/api/v1/auth/guest").status_code == 429
