"""Reusable analytics date range resolution."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum

from app.core.exceptions import ValidationError


class AnalyticsDatePreset(str, Enum):
    """Predefined analytics reporting windows."""

    TODAY = "today"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    LAST_12_MONTHS = "last_12_months"
    NEXT_BATCH = "next_batch"
    NEXT_7_DAYS = "next_7_days"
    NEXT_30_DAYS = "next_30_days"
    CUSTOM = "custom"


class TrendGranularity(str, Enum):
    """Time bucket size for trend series."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass(frozen=True)
class AnalyticsDateRange:
    """Inclusive calendar date range for analytics queries."""

    start_date: date
    end_date: date
    preset: AnalyticsDatePreset | None = None

    @property
    def start_datetime(self) -> datetime:
        return datetime.combine(self.start_date, datetime.min.time(), tzinfo=timezone.utc)

    @property
    def end_datetime_exclusive(self) -> datetime:
        """Start of the day after end_date for half-open interval filtering."""
        return datetime.combine(
            self.end_date + timedelta(days=1),
            datetime.min.time(),
            tzinfo=timezone.utc,
        )


def resolve_analytics_date_range(
    *,
    preset: AnalyticsDatePreset | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    reference_date: date | None = None,
) -> AnalyticsDateRange:
    """Resolve preset or custom dates into an inclusive range."""
    today = reference_date or datetime.now(timezone.utc).date()

    if preset is None and start_date is None and end_date is None:
        preset = AnalyticsDatePreset.LAST_30_DAYS

    if preset and preset != AnalyticsDatePreset.CUSTOM:
        if preset == AnalyticsDatePreset.TODAY:
            return AnalyticsDateRange(today, today, preset)
        if preset == AnalyticsDatePreset.LAST_7_DAYS:
            return AnalyticsDateRange(today - timedelta(days=6), today, preset)
        if preset == AnalyticsDatePreset.LAST_30_DAYS:
            return AnalyticsDateRange(today - timedelta(days=29), today, preset)
        if preset == AnalyticsDatePreset.LAST_90_DAYS:
            return AnalyticsDateRange(today - timedelta(days=89), today, preset)
        if preset == AnalyticsDatePreset.LAST_12_MONTHS:
            return AnalyticsDateRange(today - timedelta(days=364), today, preset)

    if start_date is None or end_date is None:
        raise ValidationError(
            "Custom analytics range requires both start_date and end_date",
        )
    if start_date > end_date:
        raise ValidationError("start_date must be on or before end_date")

    return AnalyticsDateRange(
        start_date,
        end_date,
        preset or AnalyticsDatePreset.CUSTOM,
    )
