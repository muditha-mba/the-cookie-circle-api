"""Email service factory."""

import logging
from functools import lru_cache

from app.core.config import settings
from app.services.email.base import EmailService
from app.services.email.console import ConsoleEmailService
from app.services.email.resend import ResendEmailService
from app.services.email.smtp import SmtpEmailService

logger = logging.getLogger(__name__)


@lru_cache
def get_email_service() -> EmailService:
    """Return the configured email service implementation."""
    provider = settings.email_provider

    if provider == "resend":
        if (settings.resend_api_key or "").strip() and (settings.email_from or "").strip():
            return ResendEmailService()
        logger.warning(
            "EMAIL_PROVIDER=resend but RESEND_API_KEY or EMAIL_FROM is missing; "
            "falling back to console email delivery",
        )
        return ConsoleEmailService()

    if provider == "smtp":
        return SmtpEmailService()

    return ConsoleEmailService()
