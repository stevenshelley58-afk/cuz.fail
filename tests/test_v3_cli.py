from __future__ import annotations

from io import StringIO
import json
from uuid import uuid4
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
    assert store.orgs_by_slug["pilot"].name == "LotFile"

    consumed_user, consumed_org, consumed_record = store.consume_magic_link(raw_token)
    assert consumed_user.id == user.id
    assert consumed_org.slug == "pilot"
    assert consumed_record.id == record.id
    with pytest.raises(MagicLinkTokenConsumedError):
        store.consume_magic_link(raw_token)


def test_login_link_defaults_to_owner_email_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    raw_token = "fixed-owner-env-token"
    monkeypatch.setattr(identity_tokens, "generate_raw_token", lambda: raw_token)
    monkeypatch.setenv("DRAFTCHECK_OWNER_EMAIL", "Owner@Example.test")
    store = InMemoryIdentityStore(token_hash_pepper="pepper")
    stdout = StringIO()
    stderr = StringIO()

    status = cli.main(
        [
            "login-link",
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
        "https://app.test/auth/magic-link/verify?token=fixed-owner-env-token"
    ]

    token = parse_qs(urlparse(stdout.getvalue().strip()).query)["token"][0]
    user, org, _record = store.consume_magic_link(token)
    assert user.email == "owner@example.test"
    assert user.role == IdentityRole.OWNER
    assert org.slug == "pilot"


def test_login_link_defaults_to_steven_owner_email(monkeypatch: pytest.MonkeyPatch) -> None:
    raw_token = "fixed-owner-default-token"
    monkeypatch.setattr(identity_tokens, "generate_raw_token", lambda: raw_token)
    monkeypatch.delenv("DRAFTCHECK_OWNER_EMAIL", raising=False)
    store = InMemoryIdentityStore(token_hash_pepper="pepper")
    stdout = StringIO()
    stderr = StringIO()

    status = cli.main(
        ["login-link", "--frontend-url", "https://app.test"],
        stdout=stdout,
        stderr=stderr,
        store=store,
        settings=Settings(frontend_url="https://app.test", auth_token_hash_pepper="pepper"),
    )

    assert status == 0
    assert stderr.getvalue() == ""
    token = parse_qs(urlparse(stdout.getvalue().strip()).query)["token"][0]
    user, _org, _record = store.consume_magic_link(token)
    assert user.email == "stevenshelley58@gmail.com"


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


def test_cli_surface_exposes_operational_commands_without_dev_login() -> None:
    parser_help = cli.build_parser().format_help()
    stdout = StringIO()
    stderr = StringIO()

    status = cli.main(["dev-login"], stdout=stdout, stderr=stderr)

    assert "login-link" in parser_help
    assert "seed-source-manifest" in parser_help
    assert "fetch-pending-sources" in parser_help
    assert "discover-source-links" in parser_help
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


def test_seed_source_manifest_requires_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    stdout = StringIO()
    stderr = StringIO()

    status = cli.main(["seed-source-manifest"], stdout=stdout, stderr=stderr)

    assert status == 2
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == "error: DATABASE_URL is required for durable source seeding\n"


def test_fetch_pending_sources_requires_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    stdout = StringIO()
    stderr = StringIO()

    status = cli.main(
        ["fetch-pending-sources", "--operator-email", "reviewer@example.test"],
        stdout=stdout,
        stderr=stderr,
    )

    assert status == 2
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == "error: DATABASE_URL is required for durable source fetching\n"


def test_seed_source_manifest_filters_cockburn_and_records_fetch_logs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    manifest = tmp_path / "source_manifest.yaml"
    manifest.write_text(
        """
sources:
  - title: Cockburn anchor
    jurisdiction: WA
    authority: City of Cockburn
    local_government: Cockburn
    source_type: local_planning_policy
    canonical_url: https://www.cockburn.wa.gov.au/planning
    licence_notes: Official page must be fetched, reviewed, and approved before citation.
    access_type: public
    scrape_allowed: true
    version_label: anchor-only
  - title: Fremantle anchor
    jurisdiction: WA
    authority: City of Fremantle
    local_government: Fremantle
    source_type: local_planning_policy
    canonical_url: https://www.fremantle.wa.gov.au/planning
    licence_notes: Fixture.
    access_type: public
    scrape_allowed: true
    version_label: anchor-only
""",
        encoding="utf-8",
    )
    calls: dict[str, object] = {}
    org_id = uuid4()
    user_id = uuid4()

    class FakeIdentityStore:
        @classmethod
        def from_database_url(cls, database_url: str):
            calls["identity_database_url"] = database_url
            return cls()

        def get_or_create_org(self, *, slug, name):
            calls["org"] = {"slug": slug, "name": name}
            return type("Org", (), {"id": org_id})()

        def get_or_create_user(self, *, org, email, role):
            calls["user"] = {"org_id": org.id, "email": email, "role": role.value}
            return type("User", (), {"id": user_id})()

    class FakeSourceLibrary:
        @classmethod
        def from_database_url(cls, database_url: str):
            calls["source_database_url"] = database_url
            return cls()

        def seed_manifest(self, manifest, *, local_government, org_id, requested_by_user_id):
            calls["seed"] = {
                "sources": len(manifest["sources"]),
                "local_government": local_government,
                "org_id": str(org_id),
                "requested_by_user_id": str(requested_by_user_id),
            }
            return {"imported": 1, "duplicates": 0, "skipped": 1, "fetch_logs": 1, "items": []}

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://fixture")
    monkeypatch.setattr(cli, "SqlAlchemyIdentityStore", FakeIdentityStore)
    monkeypatch.setattr(cli, "SqlAlchemySourceLibrary", FakeSourceLibrary)
    stdout = StringIO()
    stderr = StringIO()

    status = cli.main(
        [
            "seed-source-manifest",
            str(manifest),
            "--local-government",
            "Cockburn",
            "--operator-email",
            "reviewer@example.test",
            "--org-slug",
            "draftcheck",
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert status == 0
    assert stderr.getvalue() == ""
    assert json.loads(stdout.getvalue()) == {
        "imported": 1,
        "duplicates": 0,
        "skipped": 1,
        "fetch_logs": 1,
        "items": [],
    }
    assert calls["identity_database_url"] == "postgresql+psycopg://fixture"
    assert calls["source_database_url"] == "postgresql+psycopg://fixture"
    assert calls["org"] == {"slug": "draftcheck", "name": "LotFile"}
    assert calls["user"] == {
        "org_id": org_id,
        "email": "reviewer@example.test",
        "role": "owner",
    }
    assert calls["seed"] == {
        "sources": 2,
        "local_government": "Cockburn",
        "org_id": str(org_id),
        "requested_by_user_id": str(user_id),
    }


def test_fetch_pending_sources_uses_operator_and_local_government(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}
    org_id = uuid4()
    user_id = uuid4()

    class FakeIdentityStore:
        @classmethod
        def from_database_url(cls, database_url: str):
            calls["identity_database_url"] = database_url
            return cls()

        def get_or_create_org(self, *, slug, name):
            calls["org"] = {"slug": slug, "name": name}
            return type("Org", (), {"id": org_id})()

        def get_or_create_user(self, *, org, email, role):
            calls["user"] = {"org_id": org.id, "email": email, "role": role.value}
            return type("User", (), {"id": user_id})()

    class FakeSourceLibrary:
        @classmethod
        def from_database_url(cls, database_url: str):
            calls["source_database_url"] = database_url
            return cls()

        def fetch_pending_sources(
            self,
            *,
            local_government,
            source_type,
            title_contains,
            readiness,
            max_declared_size_mb,
            limit,
            org_id,
            requested_by_user_id,
            force,
        ):
            calls["fetch"] = {
                "local_government": local_government,
                "source_type": source_type,
                "title_contains": title_contains,
                "readiness": readiness,
                "max_declared_size_mb": max_declared_size_mb,
                "limit": limit,
                "org_id": str(org_id),
                "requested_by_user_id": str(requested_by_user_id),
                "force": force,
            }
            return {"fetched": 2, "failed": 0, "skipped": 0, "items": []}

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://fixture")
    monkeypatch.setattr(cli, "SqlAlchemyIdentityStore", FakeIdentityStore)
    monkeypatch.setattr(cli, "SqlAlchemySourceLibrary", FakeSourceLibrary)
    stdout = StringIO()
    stderr = StringIO()

    status = cli.main(
        [
            "fetch-pending-sources",
            "--local-government",
            "Cockburn",
            "--source-type",
            "scheme_map",
            "--title-contains",
            "Beeliar",
            "--readiness",
            "parse_quality_review_required",
            "--max-declared-size-mb",
            "10",
            "--limit",
            "2",
            "--operator-email",
            "reviewer@example.test",
            "--org-slug",
            "draftcheck",
            "--force",
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert status == 0
    assert stderr.getvalue() == ""
    assert json.loads(stdout.getvalue()) == {
        "fetched": 2,
        "failed": 0,
        "skipped": 0,
        "items": [],
    }
    assert calls["source_database_url"] == "postgresql+psycopg://fixture"
    assert calls["fetch"] == {
        "local_government": "Cockburn",
        "source_type": "scheme_map",
        "title_contains": "Beeliar",
        "readiness": "parse_quality_review_required",
        "max_declared_size_mb": 10.0,
        "limit": 2,
        "org_id": str(org_id),
        "requested_by_user_id": str(user_id),
        "force": True,
    }


def test_repair_parse_quality_sources_uses_operator_and_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}
    org_id = uuid4()
    user_id = uuid4()

    class FakeIdentityStore:
        @classmethod
        def from_database_url(cls, database_url: str):
            calls["identity_database_url"] = database_url
            return cls()

        def get_or_create_org(self, *, slug, name):
            calls["org"] = {"slug": slug, "name": name}
            return type("Org", (), {"id": org_id})()

        def get_or_create_user(self, *, org, email, role):
            calls["user"] = {"org_id": org.id, "email": email, "role": role.value}
            return type("User", (), {"id": user_id})()

    class FakeSourceLibrary:
        @classmethod
        def from_database_url(cls, database_url: str):
            calls["source_database_url"] = database_url
            return cls()

        def repair_parse_quality_sources(
            self,
            *,
            local_government,
            source_type,
            title_contains,
            limit,
            org_id,
            requested_by_user_id,
            force,
            ocr,
            max_ocr_pages,
            ocr_dpi,
        ):
            calls["repair"] = {
                "local_government": local_government,
                "source_type": source_type,
                "title_contains": title_contains,
                "limit": limit,
                "org_id": str(org_id),
                "requested_by_user_id": str(requested_by_user_id),
                "force": force,
                "ocr": ocr,
                "max_ocr_pages": max_ocr_pages,
                "ocr_dpi": ocr_dpi,
            }
            return {"repaired": 1, "failed": 0, "skipped": 0, "items": []}

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://fixture")
    monkeypatch.setattr(cli, "SqlAlchemyIdentityStore", FakeIdentityStore)
    monkeypatch.setattr(cli, "SqlAlchemySourceLibrary", FakeSourceLibrary)
    stdout = StringIO()
    stderr = StringIO()

    status = cli.main(
        [
            "repair-parse-quality-sources",
            "--local-government",
            "Cockburn",
            "--source-type",
            "structure_plan",
            "--title-contains",
            "Koorilla",
            "--limit",
            "3",
            "--operator-email",
            "reviewer@example.test",
            "--org-slug",
            "draftcheck",
            "--force",
            "--ocr",
            "--max-ocr-pages",
            "12",
            "--ocr-dpi",
            "180",
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert status == 0
    assert stderr.getvalue() == ""
    assert json.loads(stdout.getvalue()) == {
        "repaired": 1,
        "failed": 0,
        "skipped": 0,
        "items": [],
    }
    assert calls["source_database_url"] == "postgresql+psycopg://fixture"
    assert calls["repair"] == {
        "local_government": "Cockburn",
        "source_type": "structure_plan",
        "title_contains": "Koorilla",
        "limit": 3,
        "org_id": str(org_id),
        "requested_by_user_id": str(user_id),
        "force": True,
        "ocr": True,
        "max_ocr_pages": 12,
        "ocr_dpi": 180,
    }


def test_discover_source_links_uses_operator_and_local_government(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}
    org_id = uuid4()
    user_id = uuid4()

    class FakeIdentityStore:
        @classmethod
        def from_database_url(cls, database_url: str):
            calls["identity_database_url"] = database_url
            return cls()

        def get_or_create_org(self, *, slug, name):
            calls["org"] = {"slug": slug, "name": name}
            return type("Org", (), {"id": org_id})()

        def get_or_create_user(self, *, org, email, role):
            calls["user"] = {"org_id": org.id, "email": email, "role": role.value}
            return type("User", (), {"id": user_id})()

    class FakeSourceLibrary:
        @classmethod
        def from_database_url(cls, database_url: str):
            calls["source_database_url"] = database_url
            return cls()

        def discover_child_sources(
            self,
            *,
            local_government,
            limit,
            org_id,
            requested_by_user_id,
        ):
            calls["discover"] = {
                "local_government": local_government,
                "limit": limit,
                "org_id": str(org_id),
                "requested_by_user_id": str(requested_by_user_id),
            }
            return {"discovered": 3, "duplicates": 1, "skipped": 0, "links_seen": 4, "items": []}

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://fixture")
    monkeypatch.setattr(cli, "SqlAlchemyIdentityStore", FakeIdentityStore)
    monkeypatch.setattr(cli, "SqlAlchemySourceLibrary", FakeSourceLibrary)
    stdout = StringIO()
    stderr = StringIO()

    status = cli.main(
        [
            "discover-source-links",
            "--local-government",
            "Cockburn",
            "--limit",
            "4",
            "--operator-email",
            "reviewer@example.test",
            "--org-slug",
            "draftcheck",
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert status == 0
    assert stderr.getvalue() == ""
    assert json.loads(stdout.getvalue()) == {
        "discovered": 3,
        "duplicates": 1,
        "skipped": 0,
        "links_seen": 4,
        "items": [],
    }
    assert calls["source_database_url"] == "postgresql+psycopg://fixture"
    assert calls["discover"] == {
        "local_government": "Cockburn",
        "limit": 4,
        "org_id": str(org_id),
        "requested_by_user_id": str(user_id),
    }
