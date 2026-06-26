"""Human-readable Decimal formatting helpers."""

from __future__ import annotations

from decimal import Decimal


def format_decimal_for_display(value: Decimal) -> str:
    """Format a Decimal for user-facing text without scientific notation."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text
