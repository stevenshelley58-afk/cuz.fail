from __future__ import annotations

from datetime import UTC, datetime
from email.message import EmailMessage

from draftcheck.domain.identity.email import SmtpEmailSender
import draftcheck.domain.identity.email as email_module


def test_smtp_email_sender_sends_magic_link(monkeypatch) -> None:
    sent_messages: list[EmailMessage] = []
    actions: list[str] = []

    class FakeSmtp:
        def __init__(self, host: str, port: int, *, timeout: int) -> None:
            actions.append(f"connect:{host}:{port}:{timeout}")

        def __enter__(self) -> "FakeSmtp":
            return self

        def __exit__(self, *_args) -> None:
            actions.append("close")

        def starttls(self) -> None:
            actions.append("starttls")

        def login(self, username: str, password: str) -> None:
            actions.append(f"login:{username}:{password}")

        def send_message(self, message: EmailMessage) -> None:
            sent_messages.append(message)

    monkeypatch.setattr(email_module.smtplib, "SMTP", FakeSmtp)

    sender = SmtpEmailSender(
        host="smtp.example.test",
        port=587,
        username="smtp-user",
        password="smtp-pass",
        from_address="no-reply@app.cuz.fail",
        timeout_seconds=7,
    )
    sender.send_magic_link(
        "owner@example.test",
        "https://app.cuz.fail/auth/magic-link/verify?token=fixed",
        datetime(2026, 6, 8, 12, 0, tzinfo=UTC),
    )

    assert actions == [
        "connect:smtp.example.test:587:7",
        "starttls",
        "login:smtp-user:smtp-pass",
        "close",
    ]
    assert len(sent_messages) == 1
    message = sent_messages[0]
    assert message["Subject"] == "Your LotFile sign-in link"
    assert message["To"] == "owner@example.test"
    assert message["From"] == "LotFile <no-reply@app.cuz.fail>"
    assert "https://app.cuz.fail/auth/magic-link/verify?token=fixed" in message.get_content()
