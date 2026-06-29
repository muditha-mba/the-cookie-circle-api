"""Safe email delivery helpers — failures must not break core flows."""

from __future__ import annotations

import logging
from collections.abc import Callable

from app.services.email.base import EmailService

logger = logging.getLogger(__name__)


def send_email_safely(action: Callable[[], None], *, context: str) -> None:
    """Execute an email send and log failures without raising."""
    try:
        action()
    except Exception:
        logger.exception("Failed to send email (%s)", context)
