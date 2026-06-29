"""Production analytics date range resolution (historical and forward-looking presets)."""

from datetime import datetime, timedelta, timezone

from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import AnalyticsQueryParams
from app.utils.analytics_date_range import (
    AnalyticsDatePreset,
    AnalyticsDateRange,
    resolve_analytics_date_range,
)

FORWARD_PRESETS = frozenset(
    {
        AnalyticsDatePreset.NEXT_BATCH,
        AnalyticsDatePreset.NEXT_7_DAYS,
        AnalyticsDatePreset.NEXT_30_DAYS,
    },
)


def resolve_production_analytics_date_range(
    repo: AnalyticsRepository,
    params: AnalyticsQueryParams,
) -> AnalyticsDateRange:
    """Resolve date range for production analytics, including forward delivery presets."""
    preset = params.preset
    today = datetime.now(timezone.utc).date()

    if preset == AnalyticsDatePreset.NEXT_BATCH:
        next_date = repo.fetch_next_delivery_date_on_or_after(today)
        batch_date = next_date or today
        return AnalyticsDateRange(batch_date, batch_date, preset)

    if preset == AnalyticsDatePreset.NEXT_7_DAYS:
        return AnalyticsDateRange(today, today + timedelta(days=6), preset)

    if preset == AnalyticsDatePreset.NEXT_30_DAYS:
        return AnalyticsDateRange(today, today + timedelta(days=29), preset)

    return resolve_analytics_date_range(
        preset=preset,
        start_date=params.start_date,
        end_date=params.end_date,
    )
