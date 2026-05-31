"""Email service abstractions."""

from abc import ABC, abstractmethod


class EmailService(ABC):
    """Abstract email service for verification and password reset flows."""

    @abstractmethod
    def send_verification_email(self, *, to_email: str, verification_url: str) -> None:
        """Send an email verification link."""

    @abstractmethod
    def send_password_reset_email(self, *, to_email: str, reset_url: str) -> None:
        """Send a password reset link."""
