"""Identity domain helpers for V3."""

from draftcheck.domain.identity.email import DevLogEmailSender, EmailSender, MagicLinkEmail
from draftcheck.domain.identity.roles import IdentityRole, can_review, normalize_role, require_reviewer
from draftcheck.domain.identity.store import (
    MAGIC_LINK_TTL,
    SESSION_TTL,
    ActiveSession,
    IdentitySession,
    InMemoryIdentityStore,
    InvalidIdentityInputError,
    MagicLinkIssue,
    MagicLinkRecord,
    MagicLinkTokenConsumedError,
    MagicLinkTokenExpiredError,
    MagicLinkTokenNotFoundError,
    OrgIdentity,
    SessionIssue,
    UserIdentity,
)
from draftcheck.domain.identity.tokens import (
    IssuedToken,
    generate_raw_token,
    hash_token,
    issue_magic_link_token,
    issue_session_token,
    token_hash_matches,
)

__all__ = [
    "MAGIC_LINK_TTL",
    "SESSION_TTL",
    "ActiveSession",
    "DevLogEmailSender",
    "EmailSender",
    "IdentityRole",
    "IdentitySession",
    "InMemoryIdentityStore",
    "InvalidIdentityInputError",
    "IssuedToken",
    "MagicLinkEmail",
    "MagicLinkIssue",
    "MagicLinkRecord",
    "MagicLinkTokenConsumedError",
    "MagicLinkTokenExpiredError",
    "MagicLinkTokenNotFoundError",
    "OrgIdentity",
    "SessionIssue",
    "UserIdentity",
    "can_review",
    "generate_raw_token",
    "hash_token",
    "issue_magic_link_token",
    "issue_session_token",
    "normalize_role",
    "require_reviewer",
    "token_hash_matches",
]
