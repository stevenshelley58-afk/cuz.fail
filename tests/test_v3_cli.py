from __future__ import annotations

from io import StringIO
from urllib.parse import parse_qs, urlparse

import pytest

from draftcheck import cli
from draftcheck.config import Settings
from draftcheck.domain.identity import (
    IdentityRole,
    InMemoryIdentityStore,
    MagicLinkTokenConsumedError,
)
import draftcheck.domain.identity.tokens as identity_tokens
from draftcheck.domain.identity.tokens import hash_token


def test_login_link_outputs_only_one_time_url_and_hashes_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_token = "fixed-bootstrap-token"
    monkeypatch.setattr(identity_tokens, "generate_raw_token", lambda: raw_token)
    store = InMemoryIdentityStore(token_hash_pepper="pepper")
    stdout = StringIO()
    stderr = StringIO()

    status = cli.main(
        [
            "login-link",
            "Owner@Example.test",
            "--org-slug",
            "Pilot",
            "--frontend-url",
            "https://app.test",
        ],
        stdout=stdout,
        stderr=stderr,
        store=store,
        settings=Settings(frontend_url="https://app.test", auth_token_hash_pepper="pepper"),
    )

    assert status == 0
    assert stderr.getvalue() == ""
    assert stdout.getvalue().splitlines() == [
        "https://app.test/auth/magic-link/verify?token=fixed-bootstrap-token"
    ]

    link = stdout.getvalue().strip()
    token = parse_qs(urlparse(link).query)["token"][0]
    token_hash = hash_token(token, pepper="pepper")
    record = store.magic_links_by_hash[token_hash]
    user = store.users_by_id[record.user_id]

    assert token == raw_token
    assert raw_token not in store.magic_links_by_hash
    assert token_hash not in stdout.getvalue()
    assert "pepper" not in stdout.getvalue()
    assert record.email == "owner@example.test"
    assert user.role == IdentityRole.OWNER
    assert store.orgs_by_slug["pilot"].name == "DraftCheck WA"

    consumed_user, consumed_org, consumed_record = store.consume_magic_link(raw_token)
    assert consumed_user.id == user.id
    assert consumed_org.slug == "pilot"
    assert consumed_record.id == record.id
    with pytest.raises(MagicLinkTokenConsumedError):
        store.consume_magic_link(raw_token)


def test_login_link_rejects_non_http_frontend_url_before_token_issue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_generate_raw_token() -> str:
        raise AssertionError("token generation should not run")

    monkeypatch.setattr(identity_tokens, "generate_raw_token", fail_generate_raw_token)
    store = InMemoryIdentityStore()
    stdout = StringIO()
    stderr = StringIO()

    status = cli.main(
        ["login-link", "owner@example.test", "--frontend-url", "file:///tmp/draftcheck"],
        stdout=stdout,
        stderr=stderr,
        store=store,
        settings=Settings(frontend_url="https://app.test"),
    )

    assert status == 2
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == "error: frontend URL must be an absolute http(s) URL\n"
    assert store.orgs_by_slug == {}
    assert store.magic_links_by_hash == {}


def test_cli_surface_is_login_link_only() -> None:
    parser_help = cli.build_parser().format_help()
    stdout = StringIO()
    stderr = StringIO()

    status = cli.main(["dev-login"], stdout=stdout, stderr=stderr)

    assert "login-link" in parser_help
    assert "dev-login" not in parser_help
    assert status == 2
    assert stdout.getvalue() == ""
    assert "invalid choice" in stderr.getvalue()
    assert "token=" not in stderr.getvalue()


def test_login_link_uses_durable_store_when_database_url_is_set(
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
    monkeypatch.setattr(cli, "SqlAlchemyIdentityStore", FakeSqlAlchemyIdentityStore)
    stdout = StringIO()
    stderr = StringIO()

    status = cli.main(
        [
            "login-link",
            "owner@example.test",
            "--org-slug",
            "pilot",
            "--frontend-url",
            "https://app.test",
        ],
        stdout=stdout,
        stderr=stderr,
        settings=Settings(frontend_url="https://app.test", auth_token_hash_pepper="pepper"),
    )

    assert status == 0
    assert stderr.getvalue() == ""
    assert calls == [
        {
            "database_url": "postgresql+psycopg://fixture",
            "token_hash_pepper": "pepper",
        }
    ]
    token = parse_qs(urlparse(stdout.getvalue().strip()).query)["token"][0]
    assert backing_store.consume_magic_link(token)[0].email == "owner@example.test"
