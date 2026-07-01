"""Resend transactional email delivery."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

import httpx

from app.core.config import settings
from app.services.email.base import EmailService
from app.services.email.templates import (
    EmailContent,
    build_internal_order_notification_email,
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
        scheduled_delivery_date: date,
        total_amount: Decimal,
        whatsapp_url: str | None = None,
        order_details_message: str | None = None,
        whatsapp_open_url: str | None = None,
        premium_packaging_notice: str | None = None,
        products_subtotal: Decimal | None = None,
        collections_subtotal: Decimal | None = None,
        delivery_fee: Decimal | None = None,
        discount_amount: Decimal | None = None,
        discount_label: str | None = None,
        tax_lines: list[tuple[str, Decimal]] | None = None,
        confirmation_intro: str | None = None,
        bank_name: str | None = None,
        bank_account_name: str | None = None,
        bank_account_number: str | None = None,
        bank_branch: str | None = None,
        bank_transfer_instructions: str | None = None,
    ) -> None:
        content = build_order_confirmation_email(
            first_name=first_name,
            order_number=order_number,
            order_type_label=order_type_label,
            scheduled_delivery_date=scheduled_delivery_date,
            total_amount=total_amount,
            whatsapp_url=whatsapp_url,
            order_details_message=order_details_message,
            whatsapp_open_url=whatsapp_open_url,
            premium_packaging_notice=premium_packaging_notice,
            products_subtotal=products_subtotal,
            collections_subtotal=collections_subtotal,
            delivery_fee=delivery_fee,
            discount_amount=discount_amount,
            discount_label=discount_label,
            tax_lines=tax_lines,
            confirmation_intro=confirmation_intro,
            bank_name=bank_name,
            bank_account_name=bank_account_name,
            bank_account_number=bank_account_number,
            bank_branch=bank_branch,
            bank_transfer_instructions=bank_transfer_instructions,
        )
        self._send(to_email=to_email, content=content)

    def send_internal_order_notification_email(
        self,
        *,
        to_email: str,
        order_number: str,
        order_source_label: str,
        order_type_label: str,
        customer_name: str,
        customer_email: str | None,
        customer_phone: str | None,
        scheduled_delivery_date: date,
        total_amount: Decimal,
        admin_order_url: str,
        products_subtotal: Decimal | None = None,
        collections_subtotal: Decimal | None = None,
        package_fee_revenue: Decimal | None = None,
        delivery_fee: Decimal | None = None,
        discount_amount: Decimal | None = None,
        discount_label: str | None = None,
        tax_lines: list[tuple[str, Decimal]] | None = None,
        notification_intro: str | None = None,
        notification_headline: str | None = None,
        notification_eyebrow: str | None = None,
    ) -> None:
        content = build_internal_order_notification_email(
            order_number=order_number,
            order_source_label=order_source_label,
            order_type_label=order_type_label,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            scheduled_delivery_date=scheduled_delivery_date,
            total_amount=total_amount,
            admin_order_url=admin_order_url,
            products_subtotal=products_subtotal,
            collections_subtotal=collections_subtotal,
            package_fee_revenue=package_fee_revenue,
            delivery_fee=delivery_fee,
            discount_amount=discount_amount,
            discount_label=discount_label,
            tax_lines=tax_lines,
            notification_intro=notification_intro,
            notification_headline=notification_headline,
            notification_eyebrow=notification_eyebrow,
        )
        self._send(to_email=to_email, content=content)
