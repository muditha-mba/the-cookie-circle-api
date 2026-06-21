"""Development console email service."""

import logging
from datetime import date
from decimal import Decimal

from app.services.email.base import EmailService
from app.services.email.templates import (
    build_internal_order_notification_email,
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
        premium_packaging_notice: str | None = None,
        products_subtotal: Decimal | None = None,
        collections_subtotal: Decimal | None = None,
        delivery_fee: Decimal | None = None,
        discount_amount: Decimal | None = None,
        discount_label: str | None = None,
        tax_lines: list[tuple[str, Decimal]] | None = None,
    ) -> None:
        content = build_order_confirmation_email(
            first_name=first_name,
            order_number=order_number,
            order_type_label=order_type_label,
            scheduled_delivery_date=scheduled_delivery_date,
            total_amount=total_amount,
            whatsapp_url=whatsapp_url,
            premium_packaging_notice=premium_packaging_notice,
            products_subtotal=products_subtotal,
            collections_subtotal=collections_subtotal,
            delivery_fee=delivery_fee,
            discount_amount=discount_amount,
            discount_label=discount_label,
            tax_lines=tax_lines,
        )
        self._log(content, banner="ORDER CONFIRMATION (development)", to_email=to_email)

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
        )
        self._log(content, banner="INTERNAL ORDER ALERT (development)", to_email=to_email)
