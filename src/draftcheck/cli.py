"""DraftCheck operational CLI."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from functools import partial
import os
from pathlib import Path
import sys
from typing import Any, Sequence, TextIO, cast
from urllib.parse import urlencode, urlparse
from uuid import UUID

import yaml

from draftcheck.config import Settings
from draftcheck.domain.identity import (
    IdentityRole,
    InMemoryIdentityStore,
    InvalidIdentityInputError,
    normalize_role,
)
from draftcheck.domain.identity.sqlalchemy_store import SqlAlchemyIdentityStore
from draftcheck.domain.identity.store import DEFAULT_ORG_NAME
from draftcheck.domain.sources.sqlalchemy_store import SqlAlchemySourceLibrary


DEFAULT_OWNER_EMAIL = "stevenshelley58@gmail.com"


@dataclass(frozen=True)
class LoginLinkResult:
    url: str
    expires_at: datetime


class _ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, stderr: TextIO | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._stderr = stderr

    def _print_message(self, message: str, file: Any = None) -> None:
        if not message:
            return
        target = self._stderr or file or sys.stderr
        target.write(message)


def _normalize_frontend_url(frontend_url: str) -> str:
    normalized = frontend_url.strip().rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("frontend URL must be an absolute http(s) URL")
    return normalized


def _magic_link_url(frontend_url: str, token: str) -> str:
    query = urlencode({"token": token})
    return f"{_normalize_frontend_url(frontend_url)}/auth/magic-link/verify?{query}"


def issue_login_link(
    *,
    email: str,
    org_slug: str | None = None,
    org_name: str = DEFAULT_ORG_NAME,
    role: IdentityRole | str = IdentityRole.OWNER,
    frontend_url: str | None = None,
    store: InMemoryIdentityStore | None = None,
    settings: Settings | None = None,
) -> LoginLinkResult:
    """Provision a bootstrap identity and issue a single-use magic-link URL."""

    active_settings = settings or Settings.from_env()
    normalized_frontend_url = _normalize_frontend_url(frontend_url or active_settings.frontend_url)
    identity_store = store or _default_identity_store(active_settings)
    normalized_role = normalize_role(role)

    org = identity_store.get_or_create_org(slug=org_slug, name=org_name)
    identity_store.get_or_create_user(org=org, email=email, role=normalized_role)
    issue = identity_store.request_magic_link(
        email=email,
        org_slug=org.slug,
        org_name=org.name,
        user_agent="draftcheck-cli login-link",
    )
    return LoginLinkResult(
        url=_magic_link_url(normalized_frontend_url, issue.token),
        expires_at=issue.record.expires_at,
    )


def _default_identity_store(settings: Settings) -> InMemoryIdentityStore | SqlAlchemyIdentityStore:
    token_hash_pepper = settings.auth_token_hash_pepper or None
    database_url = os.getenv("DATABASE_URL")
    if database_url and os.getenv("DRAFTCHECK_AUTH_STORE", "auto") != "memory":
        return SqlAlchemyIdentityStore.from_database_url(
            database_url,
            token_hash_pepper=token_hash_pepper,
        )
    return InMemoryIdentityStore(token_hash_pepper=token_hash_pepper)


def build_parser(*, stderr: TextIO | None = None) -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="draftcheck",
        description="DraftCheck operational CLI.",
        stderr=stderr,
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=cast(Any, partial(_ArgumentParser, stderr=stderr)),
    )

    login_link = subparsers.add_parser(
        "login-link",
        help="Issue a one-time bootstrap magic-link URL.",
    )
    login_link.add_argument(
        "email",
        nargs="?",
        default=None,
        help="Provisioned operator email address. Defaults to DRAFTCHECK_OWNER_EMAIL.",
    )
    login_link.add_argument(
        "--org-slug",
        default=None,
        help="Organisation slug to provision or reuse.",
    )
    login_link.add_argument(
        "--org-name",
        default=DEFAULT_ORG_NAME,
        help="Organisation display name when provisioning a new org.",
    )
    login_link.add_argument(
        "--role",
        choices=[role.value for role in IdentityRole],
        default=IdentityRole.OWNER.value,
        help="Identity role to provision for the operator.",
    )
    login_link.add_argument(
        "--frontend-url",
        default=None,
        help="Frontend base URL. Defaults to FRONTEND_URL or local settings.",
    )
    seed_sources = subparsers.add_parser(
        "seed-source-manifest",
        help="Record source manifest anchors into the durable V3 source tables.",
    )
    seed_sources.add_argument(
        "manifest_path",
        nargs="?",
        default="data/seed/source_manifest.example.yaml",
        help="YAML source manifest to seed.",
    )
    seed_sources.add_argument(
        "--local-government",
        default=None,
        help="Optional local government filter, for example Cockburn.",
    )
    seed_sources.add_argument(
        "--operator-email",
        default=None,
        help="Provision/reuse this reviewer to record source fetch log rows.",
    )
    seed_sources.add_argument(
        "--org-slug",
        default=None,
        help="Organisation slug for fetch log ownership.",
    )
    seed_sources.add_argument(
        "--org-name",
        default=DEFAULT_ORG_NAME,
        help="Organisation display name when provisioning a new org.",
    )
    fetch_sources = subparsers.add_parser(
        "fetch-pending-sources",
        help="Lawfully fetch pending public source anchors into pending-review source versions.",
    )
    fetch_sources.add_argument(
        "--local-government",
        default=None,
        help="Optional local government filter, for example Cockburn.",
    )
    fetch_sources.add_argument(
        "--source-type",
        default=None,
        help="Optional source type filter, for example scheme_map or local_planning_scheme.",
    )
    fetch_sources.add_argument(
        "--title-contains",
        default=None,
        help="Only fetch pending sources whose title contains this text.",
    )
    fetch_sources.add_argument(
        "--readiness",
        default=None,
        help="Only fetch sources whose current quality readiness matches this value.",
    )
    fetch_sources.add_argument(
        "--max-declared-size-mb",
        type=float,
        default=None,
        help="Skip pending sources whose title declares a larger PDF size.",
    )
    fetch_sources.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of pending source anchors to fetch.",
    )
    fetch_sources.add_argument(
        "--operator-email",
        required=True,
        help="Provision/reuse this reviewer to own fetch log rows.",
    )
    fetch_sources.add_argument(
        "--org-slug",
        default=None,
        help="Organisation slug for fetch log ownership.",
    )
    fetch_sources.add_argument(
        "--org-name",
        default=DEFAULT_ORG_NAME,
        help="Organisation display name when provisioning a new org.",
    )
    fetch_sources.add_argument(
        "--force",
        action="store_true",
        help="Refetch even when the latest version already has fetched text.",
    )
    discover_links = subparsers.add_parser(
        "discover-source-links",
        help="Register child source links from fetched public source pages as pending-review fetch targets.",
    )
    discover_links.add_argument(
        "--local-government",
        default=None,
        help="Optional local government filter, for example Cockburn.",
    )
    discover_links.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of discovered child source links to register.",
    )
    discover_links.add_argument(
        "--operator-email",
        required=True,
        help="Provision/reuse this reviewer to own discovery fetch log rows.",
    )
    discover_links.add_argument(
        "--org-slug",
        default=None,
        help="Organisation slug for discovery log ownership.",
    )
    discover_links.add_argument(
        "--org-name",
        default=DEFAULT_ORG_NAME,
        help="Organisation display name when provisioning a new org.",
    )
    return parser


def _run_login_link(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
    store: InMemoryIdentityStore | None,
    settings: Settings | None,
) -> int:
    email = args.email or os.getenv("DRAFTCHECK_OWNER_EMAIL") or DEFAULT_OWNER_EMAIL
    try:
        result = issue_login_link(
            email=email,
            org_slug=args.org_slug,
            org_name=args.org_name,
            role=args.role,
            frontend_url=args.frontend_url,
            store=store,
            settings=settings,
        )
    except (InvalidIdentityInputError, PermissionError, ValueError) as exc:
        stderr.write(f"error: {exc}\n")
        return 2

    stdout.write(f"{result.url}\n")
    return 0


def _run_seed_source_manifest(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        stderr.write("error: DATABASE_URL is required for durable source seeding\n")
        return 2
    manifest_path = Path(args.manifest_path)
    if not manifest_path.is_file():
        stderr.write(f"error: manifest not found: {manifest_path}\n")
        return 2
    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        stderr.write(f"error: invalid source manifest YAML: {exc}\n")
        return 2
    if not isinstance(manifest, dict):
        stderr.write("error: source manifest must be a YAML object\n")
        return 2

    org_id = None
    user_id = None
    if args.operator_email:
        identity_store = SqlAlchemyIdentityStore.from_database_url(database_url)
        org = identity_store.get_or_create_org(slug=args.org_slug, name=args.org_name)
        user = identity_store.get_or_create_user(
            org=org,
            email=args.operator_email,
            role=IdentityRole.REVIEWER,
        )
        org_id = org.id
        user_id = user.id

    source_library = SqlAlchemySourceLibrary.from_database_url(database_url)
    try:
        result = source_library.seed_manifest(
            manifest,
            local_government=args.local_government,
            org_id=org_id,
            requested_by_user_id=user_id,
        )
    except ValueError as exc:
        stderr.write(f"error: {exc}\n")
        return 2

    stdout.write(json.dumps(result, sort_keys=True))
    stdout.write("\n")
    return 0


def _operator_ids(
    *,
    database_url: str,
    email: str,
    org_slug: str | None,
    org_name: str,
) -> tuple[UUID, UUID]:
    identity_store = SqlAlchemyIdentityStore.from_database_url(database_url)
    org = identity_store.get_or_create_org(slug=org_slug, name=org_name)
    user = identity_store.get_or_create_user(
        org=org,
        email=email,
        role=IdentityRole.REVIEWER,
    )
    return org.id, user.id


def _run_fetch_pending_sources(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        stderr.write("error: DATABASE_URL is required for durable source fetching\n")
        return 2
    if args.limit < 1:
        stderr.write("error: --limit must be at least 1\n")
        return 2
    org_id, user_id = _operator_ids(
        database_url=database_url,
        email=args.operator_email,
        org_slug=args.org_slug,
        org_name=args.org_name,
    )
    source_library = SqlAlchemySourceLibrary.from_database_url(database_url)
    result = source_library.fetch_pending_sources(
        local_government=args.local_government,
        source_type=args.source_type,
        title_contains=args.title_contains,
        readiness=args.readiness,
        max_declared_size_mb=args.max_declared_size_mb,
        limit=args.limit,
        org_id=org_id,
        requested_by_user_id=user_id,
        force=args.force,
    )
    stdout.write(json.dumps(result, sort_keys=True))
    stdout.write("\n")
    return 0


def _run_discover_source_links(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        stderr.write("error: DATABASE_URL is required for durable source discovery\n")
        return 2
    if args.limit < 1:
        stderr.write("error: --limit must be at least 1\n")
        return 2
    org_id, user_id = _operator_ids(
        database_url=database_url,
        email=args.operator_email,
        org_slug=args.org_slug,
        org_name=args.org_name,
    )
    source_library = SqlAlchemySourceLibrary.from_database_url(database_url)
    result = source_library.discover_child_sources(
        local_government=args.local_government,
        limit=args.limit,
        org_id=org_id,
        requested_by_user_id=user_id,
    )
    stdout.write(json.dumps(result, sort_keys=True))
    stdout.write("\n")
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    store: InMemoryIdentityStore | None = None,
    settings: Settings | None = None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    parser = build_parser(stderr=err)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1

    if args.command == "login-link":
        return _run_login_link(args, stdout=out, stderr=err, store=store, settings=settings)
    if args.command == "seed-source-manifest":
        return _run_seed_source_manifest(args, stdout=out, stderr=err)
    if args.command == "fetch-pending-sources":
        return _run_fetch_pending_sources(args, stdout=out, stderr=err)
    if args.command == "discover-source-links":
        return _run_discover_source_links(args, stdout=out, stderr=err)

    err.write("error: unsupported command\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "LoginLinkResult",
    "build_parser",
    "issue_login_link",
    "main",
]
