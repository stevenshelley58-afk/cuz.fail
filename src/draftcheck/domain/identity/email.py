"""Email sender port for identity flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Protocol


LOGGER = logging.getLogger("draftcheck.identity.email")


@dataclass(frozen=True)
class MagicLinkEmail:
    recipient: str
    magic_link: str
    expires_at: datetime


class EmailSender(Protocol):
    def send_magic_link(self, recipient: str, magic_link: str, expires_at: datetime) -> None:
        """Send or record a magic-link email."""


@dataclass
class DevLogEmailSender:
    """Development sender that records and logs links instead of sending email."""

    sent_messages: list[MagicLinkEmail] = field(default_factory=list)
    logger: logging.Logger = LOGGER

    def send_magic_link(self, recipient: str, magic_link: str, expires_at: datetime) -> None:
        message = MagicLinkEmail(
            recipient=recipient,
            magic_link=magic_link,
            expires_at=expires_at,
        )
        self.sent_messages.append(message)
        self.logger.info(
            "dev magic link generated for %s; expires_at=%s; url=%s",
            recipient,
            expires_at.isoformat(),
            magic_link,
        )
