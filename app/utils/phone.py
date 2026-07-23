"""Shared phone-number validation for client-facing APIs."""

from __future__ import annotations

import re

# ITU E.164 maximum (digits including country code).
PHONE_MAX_DIGITS = 15
# Digits plus light formatting (+, spaces, dashes, parentheses).
PHONE_MAX_INPUT_LENGTH = 20

_PHONE_ALLOWED = re.compile(r"^[+\d\s().-]+$")
_PHONE_INVALID_MESSAGE = (
    "Enter a valid phone number using digits only "
    "(e.g. 0771234567 or +94771234567)."
)
_PHONE_TOO_LONG_MESSAGE = (
    "Phone number cannot exceed 15 digits (international maximum)."
)


def validate_phone_number(value: str) -> str:
    """Validate and normalize a required phone number."""
    stripped = value.strip()
    if not stripped:
        raise ValueError("Phone number is required.")
    if len(stripped) > PHONE_MAX_INPUT_LENGTH:
        raise ValueError(_PHONE_TOO_LONG_MESSAGE)
    if not _PHONE_ALLOWED.fullmatch(stripped):
        raise ValueError(_PHONE_INVALID_MESSAGE)
    if "+" in stripped[1:]:
        raise ValueError(_PHONE_INVALID_MESSAGE)

    digits = re.sub(r"\D", "", stripped)
    if len(digits) > PHONE_MAX_DIGITS:
        raise ValueError(_PHONE_TOO_LONG_MESSAGE)
    if len(digits) < 9:
        raise ValueError(_PHONE_INVALID_MESSAGE)
    return stripped


def validate_optional_phone(value: str | None) -> str | None:
    """Validate an optional phone; blank values become None."""
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return validate_phone_number(stripped)
