"""Email service factory."""

from functools import lru_cache

from app.services.email.base import EmailService
from app.services.email.console import ConsoleEmailService


@lru_cache
def get_email_service() -> EmailService:
    """Return the configured email service implementation."""
    return ConsoleEmailService()
