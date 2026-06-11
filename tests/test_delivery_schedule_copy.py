"""Delivery schedule messaging tests."""

from app.core.enums import Weekday
from app.utils.delivery_schedule import build_delivery_schedule_copy


def test_build_delivery_schedule_copy_uses_weekday_labels() -> None:
    copy = build_delivery_schedule_copy(
        cutoff_day=Weekday.THURSDAY,
        delivery_day=Weekday.SATURDAY,
    )
    assert copy.order_cutoff_day_label == "Thursday"
    assert copy.delivery_day_label == "Saturday"
    assert "Thursday evening" in copy.explanation
    assert "Saturday" in copy.explanation
    assert copy.reserve_before_message == "Reserve before Thursday evening"
