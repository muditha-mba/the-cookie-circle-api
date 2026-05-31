"""Development console email service."""

import logging

from app.services.email.base import EmailService

logger = logging.getLogger(__name__)


class ConsoleEmailService(EmailService):
    """Log email content to the console — development only."""

    def send_verification_email(self, *, to_email: str, verification_url: str) -> None:
        logger.info(
            "\n"
            "══════════════════════════════════════════════════════════\n"
            "EMAIL VERIFICATION (development)\n"
            "To: %s\n"
            "Link: %s\n"
            "══════════════════════════════════════════════════════════",
            to_email,
            verification_url,
        )

    def send_password_reset_email(self, *, to_email: str, reset_url: str) -> None:
        logger.info(
            "\n"
            "══════════════════════════════════════════════════════════\n"
            "PASSWORD RESET (development)\n"
            "To: %s\n"
            "Link: %s\n"
            "══════════════════════════════════════════════════════════",
            to_email,
            reset_url,
        )
