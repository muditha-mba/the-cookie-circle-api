"""Email service abstractions."""

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal


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
        whatsapp_url: str | None = None,
    ) -> None:
        """Send an order confirmation email after checkout."""
