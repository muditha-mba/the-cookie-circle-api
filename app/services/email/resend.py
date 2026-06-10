"""Resend transactional email delivery."""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings
from app.services.email.base import EmailService
from app.services.email.templates import (
    EmailContent,
    build_order_confirmation_email,
    build_password_reset_email,
    build_verification_email,
    build_welcome_email,
)

logger = logging.getLogger(__name__)

_RESEND_API_URL = "https://api.resend.com/emails"


class ResendEmailService(EmailService):
    """Send branded transactional email through Resend."""

    def _send(self, *, to_email: str, content: EmailContent) -> None:
        api_key = (settings.resend_api_key or "").strip()
        from_address = (settings.email_from or "").strip()
        if not api_key or not from_address:
            raise RuntimeError("Resend is not fully configured")

        payload: dict[str, object] = {
            "from": from_address,
            "to": [to_email],
            "subject": content.subject,
            "html": content.html,
            "text": content.text,
        }
        reply_to = (settings.email_reply_to or "").strip()
        if reply_to:
            payload["reply_to"] = reply_to

        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                _RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()

        logger.info("Resend email sent to %s (%s)", to_email, content.subject)

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
        self._send(to_email=to_email, content=content)

    def send_password_reset_email(self, *, to_email: str, reset_url: str) -> None:
        content = build_password_reset_email(to_email=to_email, reset_url=reset_url)
        self._send(to_email=to_email, content=content)

    def send_welcome_email(self, *, to_email: str, first_name: str | None) -> None:
        content = build_welcome_email(first_name=first_name)
        self._send(to_email=to_email, content=content)

    def send_order_confirmation_email(
        self,
        *,
        to_email: str,
        first_name: str,
        order_number: str,
        order_type_label: str,
        scheduled_delivery_date,
        total_amount,
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
        self._send(to_email=to_email, content=content)
