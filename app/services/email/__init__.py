"""Email service factory."""

from functools import lru_cache

from app.core.config import settings
from app.services.email.base import EmailService
from app.services.email.console import ConsoleEmailService
from app.services.email.smtp import SmtpEmailService


@lru_cache
def get_email_service() -> EmailService:
    """Return the configured email service implementation."""
    if settings.email_provider == "smtp":
        return SmtpEmailService()
    return ConsoleEmailService()
