"""Identity roles for V3."""

from __future__ import annotations

from enum import StrEnum


class IdentityRole(StrEnum):
    OWNER = "owner"


def normalize_role(role: IdentityRole | str) -> IdentityRole:
    try:
        return role if isinstance(role, IdentityRole) else IdentityRole(role)
    except ValueError as exc:
        raise PermissionError(f"unknown identity role: {role}") from exc
