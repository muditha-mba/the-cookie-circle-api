"""SMTP email delivery for staging and production."""

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.services.email.base import EmailService

logger = logging.getLogger(__name__)


class SmtpEmailService(EmailService):
    """Send transactional email through SMTP."""

    def _send(self, *, to_email: str, subject: str, body: str) -> None:
        if not settings.smtp_host or not settings.smtp_from_email:
            raise RuntimeError("SMTP is not fully configured")

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.smtp_from_email
        message["To"] = to_email
        message.set_content(body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)

        logger.info("SMTP email sent to %s (%s)", to_email, subject)

    def send_verification_email(
        self,
        *,
        to_email: str,
        verification_url: str,
        dev_verification_url: str | None = None,
    ) -> None:
        body = (
            "Welcome to The Cookie Circle.\n\n"
            "Please verify your email address using the link below:\n"
            f"{verification_url}\n\n"
            "If you did not create an account, you can ignore this email."
        )
        self._send(
            to_email=to_email,
            subject="Verify your Cookie Circle account",
            body=body,
        )

    def send_password_reset_email(self, *, to_email: str, reset_url: str) -> None:
        body = (
            "We received a request to reset your Cookie Circle password.\n\n"
            f"Reset your password using the link below:\n{reset_url}\n\n"
            "If you did not request this, you can ignore this email."
        )
        self._send(
            to_email=to_email,
            subject="Reset your Cookie Circle password",
            body=body,
        )
