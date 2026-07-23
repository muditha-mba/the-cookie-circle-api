"""Email service abstractions."""

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from app.services.email.order_summary import OrderEmailSummary


class EmailService(ABC):
    """Abstract email service for transactional customer communications."""

    @abstractmethod
    def send_verification_email(
        self,
        *,
        to_email: str,
        verification_url: str,
        dev_verification_url: str | None = None,
    ) -> None:
        """Send an email verification link."""

    @abstractmethod
    def send_password_reset_email(self, *, to_email: str, reset_url: str) -> None:
        """Send a password reset link."""

    @abstractmethod
    def send_welcome_email(self, *, to_email: str, first_name: str | None) -> None:
        """Send a welcome email after successful verification."""

    @abstractmethod
    def send_order_confirmation_email(
        self,
        *,
        to_email: str,
        first_name: str,
        order_number: str,
        order_type_label: str,
        scheduled_delivery_date: date,
        total_amount: Decimal,
        order_summary: OrderEmailSummary | None = None,
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
        """Send an order confirmation email after checkout."""

    @abstractmethod
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
        """Notify the business inbox that a new order was created."""
