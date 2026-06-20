"""Analytics module overview and category metadata."""

from sqlalchemy.orm import Session

from app.schemas.analytics import AnalyticsCategory, AnalyticsOverviewResponse, AnalyticsQueryParams
from app.services.analytics._common import date_range_response
from app.utils.analytics_date_range import resolve_analytics_date_range

ANALYTICS_CATEGORIES: tuple[AnalyticsCategory, ...] = (
    AnalyticsCategory(
        id="revenue",
        title="Revenue Analytics",
        description="Revenue, profit, and order trends from financial snapshots.",
        endpoint_prefix="/api/v1/analytics/revenue",
    ),
    AnalyticsCategory(
        id="orders",
        title="Order Analytics",
        description="Fulfillment, delivery, payment, and operational order performance.",
        endpoint_prefix="/api/v1/analytics/orders",
    ),
    AnalyticsCategory(
        id="products",
        title="Product Analytics",
        description="Most and least ordered products by snapshot data.",
        endpoint_prefix="/api/v1/analytics/products",
    ),
    AnalyticsCategory(
        id="collections",
        title="Collection Analytics",
        description="Collection demand and profitability rankings.",
        endpoint_prefix="/api/v1/analytics/collections",
    ),
    AnalyticsCategory(
        id="customers",
        title="Customer Analytics",
        description="Growth, segments, and marketing source performance.",
        endpoint_prefix="/api/v1/analytics/customers",
    ),
    AnalyticsCategory(
        id="production",
        title="Production Analytics",
        description="Batch volume and ingredient/packaging demand trends.",
        endpoint_prefix="/api/v1/analytics/production",
    ),
    AnalyticsCategory(
        id="operations",
        title="Operations Analytics",
        description="Executive KPIs, alerts, workload, and business health overview.",
        endpoint_prefix="/api/v1/analytics/operations",
    ),
    AnalyticsCategory(
        id="overhead",
        title="Overhead Analytics",
        description="Utility and labour monthly bills, operating profit after overhead, and spend by category.",
        endpoint_prefix="/api/v1/analytics/overhead",
    ),
)


class AnalyticsOverviewService:
    """Analytics landing metadata for admin and future dashboards."""

    def __init__(self, _db: Session) -> None:
        pass

    def get_overview(self, params: AnalyticsQueryParams) -> AnalyticsOverviewResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        return AnalyticsOverviewResponse(
            date_range=date_range_response(date_range),
            categories=list(ANALYTICS_CATEGORIES),
        )
