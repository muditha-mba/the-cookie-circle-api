"""Shared analytics helpers."""

from datetime import date, timedelta
from decimal import Decimal

from app.schemas.analytics import AnalyticsDateRangeResponse
from app.utils.analytics_date_range import AnalyticsDateRange


def date_range_response(date_range: AnalyticsDateRange) -> AnalyticsDateRangeResponse:
    return AnalyticsDateRangeResponse(
        preset=date_range.preset,
        start_date=date_range.start_date,
        end_date=date_range.end_date,
    )


def snapshot_margin_percentage(revenue: Decimal, profit: Decimal) -> Decimal:
    """Profit margin % from immutable snapshot revenue and profit."""
    if revenue <= 0:
        return Decimal("0.00")
    return (profit / revenue * Decimal("100")).quantize(Decimal("0.01"))


def safe_divide(numerator: Decimal, denominator: int | Decimal) -> Decimal:
    if not denominator:
        return Decimal("0.00")
    return (numerator / Decimal(denominator)).quantize(Decimal("0.01"))


def to_optional_date(value: object | None) -> date | None:
    if value is None:
        return None
    if hasattr(value, "date"):
        return value.date()  # type: ignore[union-attr]
    if isinstance(value, date):
        return value
    return None


def previous_period(date_range: AnalyticsDateRange) -> AnalyticsDateRange:
    """Equivalent previous window for period-over-period comparisons."""
    days = (date_range.end_date - date_range.start_date).days + 1
    prev_end = date_range.start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    return AnalyticsDateRange(
        start_date=prev_start,
        end_date=prev_end,
        preset=date_range.preset,
    )


def trend_delta_percentage(
    current_value: Decimal,
    previous_value: Decimal,
) -> tuple[Decimal | None, str | None]:
    """Return trend percentage and direction (up/down/flat)."""
    if previous_value == 0:
        if current_value == 0:
            return Decimal("0.00"), "flat"
        return None, None
    pct = ((current_value - previous_value) / previous_value * Decimal("100")).quantize(
        Decimal("0.01"),
    )
    if pct > 0:
        return pct, "up"
    if pct < 0:
        return abs(pct), "down"
    return Decimal("0.00"), "flat"
