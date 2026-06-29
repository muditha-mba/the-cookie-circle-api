"""Revenue, profit, and order trend analytics."""

from sqlalchemy.orm import Session

from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import AnalyticsQueryParams, TrendDataPoint, TrendSeriesResponse
from app.services.analytics._common import date_range_response
from app.utils.analytics_date_range import resolve_analytics_date_range


class AnalyticsRevenueService:
    """Revenue and profit trend series from order snapshots."""

    def __init__(self, db: Session) -> None:
        self.repo = AnalyticsRepository(db)

    def get_revenue_trends(self, params: AnalyticsQueryParams) -> TrendSeriesResponse:
        return self._trends(params)

    def get_profit_trends(self, params: AnalyticsQueryParams) -> TrendSeriesResponse:
        return self._trends(params)

    def get_order_trends(self, params: AnalyticsQueryParams) -> TrendSeriesResponse:
        return self._trends(params)

    def _trends(self, params: AnalyticsQueryParams) -> TrendSeriesResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        rows = self.repo.fetch_order_trends(date_range, params.granularity)
        return TrendSeriesResponse(
            date_range=date_range_response(date_range),
            granularity=params.granularity,
            points=[
                TrendDataPoint(
                    period_start=period,
                    revenue=revenue,
                    profit=profit,
                    order_count=count,
                )
                for period, revenue, profit, count in rows
            ],
        )
