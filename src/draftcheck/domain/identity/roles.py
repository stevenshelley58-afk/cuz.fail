"""Identity roles and guards for V3."""

from __future__ import annotations

from enum import StrEnum


class IdentityRole(StrEnum):
    OWNER = "owner"
    REVIEWER = "reviewer"


REVIEWER_ROLES = frozenset({IdentityRole.OWNER, IdentityRole.REVIEWER})


def normalize_role(role: IdentityRole | str) -> IdentityRole:
    try:
        return role if isinstance(role, IdentityRole) else IdentityRole(role)
    except ValueError as exc:
        raise PermissionError(f"unknown identity role: {role}") from exc


def can_review(role: IdentityRole | str) -> bool:
    try:
        return normalize_role(role) in REVIEWER_ROLES
    except PermissionError:
        return False


def require_reviewer(role: IdentityRole | str) -> IdentityRole:
    normalized = normalize_role(role)
    if normalized not in REVIEWER_ROLES:
        raise PermissionError("reviewer role required")
    return normalized
