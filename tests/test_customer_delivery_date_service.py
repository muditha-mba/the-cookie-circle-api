"""Tests for customer weekly/catering delivery date rules."""

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from app.core.enums import OrderType
from app.services.customer_delivery_date_service import CustomerDeliveryDateService

TZ = ZoneInfo("Asia/Colombo")


def _dt(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=TZ).astimezone(UTC)


def test_monday_before_cutoff_targets_upcoming_saturday():
    order_at = _dt(2026, 6, 1, 10)  # Monday
    assert CustomerDeliveryDateService.calculate_weekly_delivery_date(order_at) == date(2026, 6, 6)


def test_wednesday_before_cutoff_targets_upcoming_saturday():
    order_at = _dt(2026, 6, 3, 22)  # Wednesday 10 PM
    assert CustomerDeliveryDateService.calculate_weekly_delivery_date(order_at) == date(2026, 6, 6)


def test_thursday_after_cutoff_targets_following_saturday():
    order_at = _dt(2026, 6, 4, 9)  # Thursday
    assert CustomerDeliveryDateService.calculate_weekly_delivery_date(order_at) == date(2026, 6, 13)


def test_sunday_after_cutoff_targets_next_saturday():
    order_at = _dt(2026, 6, 7, 12)  # Sunday
    assert CustomerDeliveryDateService.calculate_weekly_delivery_date(order_at) == date(2026, 6, 13)


def test_catering_earliest_date_is_three_days_ahead():
    from_date = date(2026, 6, 1)
    assert CustomerDeliveryDateService.calculate_catering_earliest_date(from_date) == date(2026, 6, 4)


def test_resolve_weekly_ignores_requested_date():
    resolved = CustomerDeliveryDateService.resolve_delivery_date(
        order_type=OrderType.WEEKLY_DELIVERY,
        requested_date=None,
        order_at=_dt(2026, 6, 1, 10),
    )
    assert resolved == date(2026, 6, 6)
