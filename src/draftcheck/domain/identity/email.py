"""Email sender port for identity flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr
import logging
import smtplib
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


class EmailConfigurationError(RuntimeError):
    """Email delivery is not configured well enough to send."""


class EmailDeliveryError(RuntimeError):
    """Email delivery was attempted and failed."""


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


@dataclass(frozen=True)
class MissingEmailSender:
    """Production-safe sender that fails clearly when SMTP is absent."""

    reason: str = "SMTP_HOST and SMTP_FROM must be configured to send magic links"

    def send_magic_link(self, recipient: str, magic_link: str, expires_at: datetime) -> None:
        raise EmailConfigurationError(self.reason)


@dataclass(frozen=True)
class SmtpEmailSender:
    """SMTP implementation for production magic-link delivery."""

    host: str
    port: int
    from_address: str
    from_name: str = "LotFile"
    username: str = ""
    password: str = ""
    use_starttls: bool = True
    use_ssl: bool = False
    timeout_seconds: int = 10

    def send_magic_link(self, recipient: str, magic_link: str, expires_at: datetime) -> None:
        if not self.host.strip() or not self.from_address.strip():
            raise EmailConfigurationError("SMTP_HOST and SMTP_FROM must be configured")
        if bool(self.username) != bool(self.password):
            raise EmailConfigurationError("SMTP_USERNAME and SMTP_PASSWORD must be set together")

        message = EmailMessage()
        message["Subject"] = "Your LotFile sign-in link"
        message["From"] = (
            formataddr((self.from_name, self.from_address))
            if self.from_name
            else self.from_address
        )
        message["To"] = recipient
        message.set_content(
            "\n".join(
                [
                    "Use this one-time link to sign in to LotFile:",
                    "",
                    magic_link,
                    "",
                    f"This link expires at {expires_at.isoformat()}.",
                    "If you did not request this, you can ignore this email.",
                ]
            )
        )

        smtp_cls = smtplib.SMTP_SSL if self.use_ssl else smtplib.SMTP
        try:
            with smtp_cls(self.host, self.port, timeout=self.timeout_seconds) as smtp:
                if self.use_starttls and not self.use_ssl:
                    smtp.starttls()
                if self.username:
                    smtp.login(self.username, self.password)
                smtp.send_message(message)
        except smtplib.SMTPException as exc:
            raise EmailDeliveryError("SMTP delivery failed") from exc
        except OSError as exc:
            raise EmailDeliveryError("SMTP connection failed") from exc
