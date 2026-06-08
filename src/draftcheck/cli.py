"""DraftCheck operational CLI."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from functools import partial
import sys
from typing import Any, Sequence, TextIO, cast
from urllib.parse import urlencode, urlparse

from draftcheck.config import Settings
from draftcheck.domain.identity import (
    IdentityRole,
    InMemoryIdentityStore,
    InvalidIdentityInputError,
    normalize_role,
)
from draftcheck.domain.identity.store import DEFAULT_ORG_NAME


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
    identity_store = store or InMemoryIdentityStore(
        token_hash_pepper=active_settings.auth_token_hash_pepper or None,
    )
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
    login_link.add_argument("email", help="Provisioned operator email address.")
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
    return parser


def _run_login_link(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
    store: InMemoryIdentityStore | None,
    settings: Settings | None,
) -> int:
    try:
        result = issue_login_link(
            email=args.email,
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
