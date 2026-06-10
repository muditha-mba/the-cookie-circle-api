"""Development console email service."""

import logging
from datetime import date
from decimal import Decimal

from app.services.email.base import EmailService
from app.services.email.templates import (
    build_order_confirmation_email,
    build_password_reset_email,
    build_verification_email,
    build_welcome_email,
)

logger = logging.getLogger(__name__)


class ConsoleEmailService(EmailService):
    """Log rendered email content to the console — development fallback."""

    @staticmethod
    def _log(content, *, banner: str, to_email: str) -> None:
        logger.info(
            "\n"
            "══════════════════════════════════════════════════════════\n"
            "%s\n"
            "To: %s\n"
            "Subject: %s\n"
            "---- TEXT ----\n"
            "%s\n"
            "══════════════════════════════════════════════════════════",
            banner,
            to_email,
            content.subject,
            content.text,
        )

    def send_verification_email(
        self,
        *,
        to_email: str,
        verification_url: str,
        dev_verification_url: str | None = None,
    ) -> None:
        content = build_verification_email(
            to_email=to_email,
            verification_url=verification_url,
            dev_verification_url=dev_verification_url,
        )
        self._log(content, banner="EMAIL VERIFICATION (development)", to_email=to_email)

    def send_password_reset_email(self, *, to_email: str, reset_url: str) -> None:
        content = build_password_reset_email(to_email=to_email, reset_url=reset_url)
        self._log(content, banner="PASSWORD RESET (development)", to_email=to_email)

    def send_welcome_email(self, *, to_email: str, first_name: str | None) -> None:
        content = build_welcome_email(first_name=first_name)
        self._log(content, banner="WELCOME EMAIL (development)", to_email=to_email)

    def send_order_confirmation_email(
        self,
        *,
        to_email: str,
        first_name: str,
        order_number: str,
        order_type_label: str,
        scheduled_delivery_date: date,
        total_amount: Decimal,
        whatsapp_url: str | None = None,
    ) -> None:
        content = build_order_confirmation_email(
            first_name=first_name,
            order_number=order_number,
            order_type_label=order_type_label,
            scheduled_delivery_date=scheduled_delivery_date,
            total_amount=total_amount,
            whatsapp_url=whatsapp_url,
        )
        self._log(content, banner="ORDER CONFIRMATION (development)", to_email=to_email)
