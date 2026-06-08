"""Development console email service."""

import logging

from app.services.email.base import EmailService

logger = logging.getLogger(__name__)


class ConsoleEmailService(EmailService):
    """Log email content to the console — development only."""

    def send_verification_email(
        self,
        *,
        to_email: str,
        verification_url: str,
        dev_verification_url: str | None = None,
    ) -> None:
        dev_block = ""
        if dev_verification_url:
            dev_block = (
                f"\nDev shortcut (reusable): {dev_verification_url}\n"
                "Use this link anytime until email is connected — no inbox needed."
            )
        logger.info(
            "\n"
            "══════════════════════════════════════════════════════════\n"
            "EMAIL VERIFICATION (development)\n"
            "To: %s\n"
            "One-time link: %s%s"
            "══════════════════════════════════════════════════════════",
            to_email,
            verification_url,
            dev_block,
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
