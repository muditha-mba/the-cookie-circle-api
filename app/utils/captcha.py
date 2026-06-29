"""Optional Cloudflare Turnstile verification."""

import logging

import httpx

from app.core.config import settings
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def verify_captcha_token(token: str | None, *, remote_ip: str | None = None) -> None:
    """Verify a Turnstile token when CAPTCHA is required."""
    if not settings.captcha_required:
        return

    secret = (settings.turnstile_secret_key or "").strip()
    if not secret:
        if settings.is_production:
            raise ValidationError("CAPTCHA is not configured")
        return

    if not token or not token.strip():
        raise ValidationError("CAPTCHA verification is required")

    payload: dict[str, str] = {
        "secret": secret,
        "response": token.strip(),
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(TURNSTILE_VERIFY_URL, data=payload)
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPError as exc:
        logger.exception("Turnstile verification request failed")
        raise ValidationError("CAPTCHA verification failed") from exc

    if not result.get("success"):
        logger.warning("Turnstile verification rejected: %s", result.get("error-codes"))
        raise ValidationError("CAPTCHA verification failed")
