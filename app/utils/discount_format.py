"""Discount display helpers for customer-facing copy."""

from __future__ import annotations

from decimal import Decimal

from app.utils.decimal_format import format_decimal_for_display


def format_discount_label(
    discount_type: str | None,
    discount_value: Decimal | None,
    *,
    fallback: str = "Discount",
) -> str:
    if discount_type == "percentage" and discount_value is not None:
        return f"Discount ({format_decimal_for_display(discount_value)}%)"
    return fallback
