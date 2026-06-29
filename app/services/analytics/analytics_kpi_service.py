"""Core KPI analytics from order snapshots."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import AnalyticsQueryParams, CoreKpiResponse
from app.services.analytics._common import (
    date_range_response,
    previous_period,
    safe_divide,
    trend_delta_percentage,
)
from app.utils.analytics_date_range import resolve_analytics_date_range


class AnalyticsKpiService:
    """Reusable core business KPI calculations."""

    def __init__(self, db: Session) -> None:
        self.repo = AnalyticsRepository(db)

    def get_core_kpis(self, params: AnalyticsQueryParams) -> CoreKpiResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        agg = self.repo.fetch_core_kpis(date_range)
        prev = self.repo.fetch_core_kpis(previous_period(date_range))

        repeat_rate = safe_divide(
            Decimal(agg.repeat_customers) * 100,
            agg.total_customers,
        )
        prev_repeat_rate = safe_divide(
            Decimal(prev.repeat_customers) * 100,
            prev.total_customers,
        )
        clv = safe_divide(agg.total_revenue, agg.total_customers)
        prev_clv = safe_divide(prev.total_revenue, prev.total_customers)
        aov = safe_divide(agg.total_revenue, agg.total_orders)
        prev_aov = safe_divide(prev.total_revenue, prev.total_orders)
        margin = safe_divide(agg.total_profit * 100, agg.total_revenue)
        prev_margin = safe_divide(prev.total_profit * 100, prev.total_revenue)

        def metric(current: Decimal, previous: Decimal):
            trend_pct, trend_dir = trend_delta_percentage(current, previous)
            return {
                "value": current,
                "trend_percentage": trend_pct,
                "trend_direction": trend_dir,
            }

        return CoreKpiResponse(
            date_range=date_range_response(date_range),
            total_revenue=metric(agg.total_revenue, prev.total_revenue),
            total_profit=metric(agg.total_profit, prev.total_profit),
            total_orders=metric(Decimal(agg.total_orders), Decimal(prev.total_orders)),
            total_customers=metric(Decimal(agg.total_customers), Decimal(prev.total_customers)),
            average_order_value=metric(aov, prev_aov),
            repeat_customer_rate=metric(repeat_rate, prev_repeat_rate),
            customer_lifetime_value=metric(clv, prev_clv),
            profit_margin_percentage=metric(margin, prev_margin),
        )
