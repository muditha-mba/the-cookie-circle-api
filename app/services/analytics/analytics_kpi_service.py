"""Core KPI analytics from order snapshots."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import AnalyticsQueryParams, CoreKpiResponse
from app.services.analytics._common import date_range_response, safe_divide
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

        repeat_rate = safe_divide(
            Decimal(agg.repeat_customers) * 100,
            agg.total_customers,
        )
        clv = safe_divide(agg.total_revenue, agg.total_customers)
        aov = safe_divide(agg.total_revenue, agg.total_orders)
        margin = safe_divide(agg.total_profit * 100, agg.total_revenue)

        return CoreKpiResponse(
            date_range=date_range_response(date_range),
            total_revenue=agg.total_revenue,
            total_profit=agg.total_profit,
            total_orders=agg.total_orders,
            total_customers=agg.total_customers,
            average_order_value=aov,
            repeat_customer_rate=repeat_rate,
            customer_lifetime_value=clv,
            profit_margin_percentage=margin,
        )
