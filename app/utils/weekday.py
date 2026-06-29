"""Weekday helpers for delivery scheduling."""

from datetime import date, timedelta

from app.core.enums import Weekday


def weekday_to_index(day: Weekday) -> int:
    """Map Weekday enum to Python weekday (Monday=0)."""
    mapping = {
        Weekday.MONDAY: 0,
        Weekday.TUESDAY: 1,
        Weekday.WEDNESDAY: 2,
        Weekday.THURSDAY: 3,
        Weekday.FRIDAY: 4,
        Weekday.SATURDAY: 5,
        Weekday.SUNDAY: 6,
    }
    return mapping[day]


def parse_weekday(value: str) -> Weekday:
    """Parse a weekday string into the enum."""
    normalized = value.strip().lower()
    for day in Weekday:
        if day.value == normalized:
            return day
    raise ValueError(f"Invalid weekday: {value}")
