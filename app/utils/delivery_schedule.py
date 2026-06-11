"""Delivery schedule copy and config derived from business settings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from app.core.enums import Weekday
from app.utils.weekday import weekday_to_index


@dataclass(frozen=True, slots=True)
class DeliveryScheduleConfig:
    """Weekly batch cutoff and delivery weekdays."""

    cutoff_day: Weekday
    delivery_day: Weekday
    cutoff_time: time = time(23, 59, 59)

    @property
    def cutoff_weekday_index(self) -> int:
        return weekday_to_index(self.cutoff_day)

    @property
    def delivery_weekday_index(self) -> int:
        return weekday_to_index(self.delivery_day)


@dataclass(frozen=True, slots=True)
class DeliveryScheduleCopy:
    """Human-readable delivery schedule messaging for UI and email."""

    order_cutoff_day: Weekday
    delivery_day: Weekday
    order_cutoff_day_label: str
    delivery_day_label: str
    explanation: str
    reserve_before_message: str
    preorder_note: str
    order_before_message: str
    cutoff_period_label: str
    cutoff_timing_note: str
    fresh_delivery_message: str


def weekday_label(day: Weekday) -> str:
    """Return a display label such as Thursday."""
    return day.value.capitalize()


def build_delivery_schedule_config(
    *,
    cutoff_day: Weekday,
    delivery_day: Weekday,
) -> DeliveryScheduleConfig:
    return DeliveryScheduleConfig(cutoff_day=cutoff_day, delivery_day=delivery_day)


def build_delivery_schedule_copy(
    *,
    cutoff_day: Weekday,
    delivery_day: Weekday,
) -> DeliveryScheduleCopy:
    cutoff = weekday_label(cutoff_day)
    delivery = weekday_label(delivery_day)
    explanation = (
        f"Orders placed on or before {cutoff} evening are included in the "
        f"upcoming {delivery} delivery batch. Orders placed after {cutoff} "
        f"evening are scheduled for the following {delivery}."
    )
    reserve_before_message = f"Reserve before {cutoff} evening"
    return DeliveryScheduleCopy(
        order_cutoff_day=cutoff_day,
        delivery_day=delivery_day,
        order_cutoff_day_label=cutoff,
        delivery_day_label=delivery,
        explanation=explanation,
        reserve_before_message=reserve_before_message,
        preorder_note=(
            f"Preorders throughout the week · {reserve_before_message}"
        ),
        order_before_message=f"Order before {cutoff} evening",
        cutoff_period_label=f"{cutoff} Evening",
        cutoff_timing_note=(
            f"Before {cutoff} for this {delivery}. After that, next week's batch"
        ),
        fresh_delivery_message=f"Fresh {delivery} delivery",
    )
