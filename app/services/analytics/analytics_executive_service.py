"""Executive analytics overview orchestration."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import OrderStatus
from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsKpiMetric,
    AnalyticsQueryParams,
    ExecutiveOperationsSnapshotResponse,
    ExecutiveOverviewHighlightsResponse,
    ExecutiveOverviewKpisResponse,
    ExecutiveRevenueContributionItem,
    ExecutiveRevenueContributionResponse,
)
from app.services.analytics._common import (
    date_range_response,
    previous_period,
    safe_divide,
    trend_delta_percentage,
)
from app.services.analytics.analytics_collection_service import AnalyticsCollectionService
from app.services.analytics.analytics_customer_service import AnalyticsCustomerService
from app.services.analytics.analytics_kpi_service import AnalyticsKpiService
from app.services.analytics.analytics_production_ux_service import AnalyticsProductionUxService
from app.services.analytics.analytics_product_service import AnalyticsProductService
from app.utils.analytics_date_range import resolve_analytics_date_range


def _metric(value: Decimal, previous: Decimal) -> AnalyticsKpiMetric:
    trend_pct, trend_dir = trend_delta_percentage(value, previous)
    return AnalyticsKpiMetric(
        value=value,
        trend_percentage=trend_pct,
        trend_direction=trend_dir,
    )


class AnalyticsExecutiveService:
    """Executive overview dashboard data source."""

    def __init__(self, db: Session) -> None:
        self.repo = AnalyticsRepository(db)
        self.core = AnalyticsKpiService(db)
        self.products = AnalyticsProductService(db)
        self.collections = AnalyticsCollectionService(db)
        self.customers = AnalyticsCustomerService(db)
        self.production_ux = AnalyticsProductionUxService(db)

    def get_kpis(self, params: AnalyticsQueryParams) -> ExecutiveOverviewKpisResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        prev_range = previous_period(date_range)
        current = self.repo.fetch_core_kpis(date_range)
        prev = self.repo.fetch_core_kpis(prev_range)
        current_aov = safe_divide(current.total_revenue, current.total_orders)
        prev_aov = safe_divide(prev.total_revenue, prev.total_orders)
        current_margin = safe_divide(current.total_profit * Decimal("100"), current.total_revenue)
        prev_margin = safe_divide(prev.total_profit * Decimal("100"), prev.total_revenue)
        return ExecutiveOverviewKpisResponse(
            date_range=date_range_response(date_range),
            total_revenue=_metric(current.total_revenue, prev.total_revenue),
            total_profit=_metric(current.total_profit, prev.total_profit),
            total_orders=_metric(Decimal(current.total_orders), Decimal(prev.total_orders)),
            total_customers=_metric(
                Decimal(current.total_customers),
                Decimal(prev.total_customers),
            ),
            average_order_value=_metric(current_aov, prev_aov),
            average_margin_percentage=_metric(current_margin, prev_margin),
        )

    def get_highlights(self, params: AnalyticsQueryParams) -> ExecutiveOverviewHighlightsResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        product = self.products.get_most_ordered(params).items
        collection = self.collections.get_most_ordered(params).items
        packages = self.repo.fetch_collection_package_performance(date_range)
        customer_insight = self.customers.get_insights(params)
        top_customer = next(
            (i for i in customer_insight.items if i.id == "most_valuable_customer"),
            None,
        )
        delivery_areas = self.repo.fetch_delivery_area_performance(date_range, limit=1)
        payment = self.repo.fetch_top_payment_method(date_range)
        return ExecutiveOverviewHighlightsResponse(
            date_range=date_range_response(date_range),
            top_product=product[0].name if product else None,
            top_collection=collection[0].name if collection else None,
            top_package=str(packages[0]["package_name"]) if packages else None,
            top_customer=top_customer.name if top_customer else None,
            highest_revenue_delivery_area=(
                str(delivery_areas[0]["area_name"]) if delivery_areas else None
            ),
            most_used_payment_method=str(payment[0]).replace("_", " ").title() if payment else None,
        )

    def get_revenue_contribution(
        self,
        params: AnalyticsQueryParams,
    ) -> ExecutiveRevenueContributionResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        product_value, collection_value, delivery_fees = self.repo.fetch_revenue_contribution(
            date_range,
        )
        return ExecutiveRevenueContributionResponse(
            date_range=date_range_response(date_range),
            items=[
                ExecutiveRevenueContributionItem(name="Products", value=product_value),
                ExecutiveRevenueContributionItem(name="Collections", value=collection_value),
                ExecutiveRevenueContributionItem(name="Delivery Fees", value=delivery_fees),
            ],
        )

    def get_operations_snapshot(
        self,
    ) -> ExecutiveOperationsSnapshotResponse:
        today = datetime.now(timezone.utc).date()
        upcoming = self.production_ux.get_upcoming_demand()
        return ExecutiveOperationsSnapshotResponse(
            upcoming_production_batch=upcoming.delivery_date if upcoming.has_upcoming_batch else None,
            upcoming_orders=upcoming.order_count if upcoming.has_upcoming_batch else 0,
            orders_awaiting_preparation=self.repo.count_orders_by_status(
                (OrderStatus.CONFIRMED, OrderStatus.PREPARING),
            ),
            orders_awaiting_delivery=self.repo.count_orders_by_status((OrderStatus.READY,)),
        )
