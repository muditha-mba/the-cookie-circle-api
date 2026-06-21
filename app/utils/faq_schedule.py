"""Resolve schedule-sensitive FAQ answers from business settings."""

from __future__ import annotations

from app.utils.delivery_schedule import DeliveryScheduleCopy


def resolve_schedule_faq_answer(
    *,
    question: str,
    stored_answer: str,
    copy: DeliveryScheduleCopy,
) -> str:
    """Return a dynamic answer for known delivery-schedule FAQs."""
    normalized = question.strip().lower()

    if normalized == "when is your delivery day?":
        return (
            f"We deliver on {copy.delivery_day_label}. Orders are prepared on Friday "
            "in small handcrafted batches, so every cookie reaches you fresh for the weekend."
        )

    if normalized == "what is the order cutoff for this week's batch?":
        return copy.explanation

    if normalized == "can i choose my delivery date?":
        return (
            f"Your delivery is assigned to the next available {copy.delivery_day_label} batch "
            "based on when you order. The suggested delivery date is shown during checkout."
        )

    if normalized == "are your cookies made fresh?":
        return (
            "Every batch is handcrafted to order. We do not hold large ready-made stock — "
            f"cookies are baked fresh in small weekly batches for {copy.delivery_day_label} delivery."
        )

    return stored_answer
