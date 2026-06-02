"""Operations analytics orchestration — composes existing analytics services."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import OrderStatus, PurchasePlanningStatus
from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsKpiMetric,
    AnalyticsQueryParams,
    OperationsAlertItem,
    OperationsAlertsResponse,
    OperationsAnalyticsKpiResponse,
    OperationsBusinessHealthItem,
    OperationsBusinessHealthResponse,
    OperationsDeliveryFeeByAreaRow,
    OperationsDeliveryOverviewResponse,
    OperationsExecutiveSummaryRow,
    OperationsPaymentOverviewResponse,
    OperationsProductRequirementLine,
    OperationsUpcomingDeliveryRow,
    OperationsUpcomingWorkloadResponse,
)
from app.services.analytics._common import date_range_response
from app.services.analytics.analytics_collection_service import AnalyticsCollectionService
from app.services.analytics.analytics_customer_service import AnalyticsCustomerService
from app.services.analytics.analytics_kpi_service import AnalyticsKpiService
from app.services.analytics.analytics_order_service import AnalyticsOrderService
from app.services.analytics.analytics_product_service import AnalyticsProductService
from app.services.analytics.analytics_production_ux_service import AnalyticsProductionUxService
from app.services.production_planning_service import ProductionPlanningService
from app.services.purchase_planning_service import PurchasePlanningService
from app.utils.analytics_date_range import resolve_analytics_date_range

QTY = Decimal("0.0001")
UPCOMING_SCHEDULE_LIMIT = 14
PRODUCT_REQUIREMENT_LIMIT = 20


def _metric(value: Decimal) -> AnalyticsKpiMetric:
    return AnalyticsKpiMetric(value=value)


class AnalyticsOperationsService:
    """Executive operations dashboard — orchestrates domain analytics services."""

    def __init__(self, db: Session) -> None:
        self.repo = AnalyticsRepository(db)
        self.core_kpis = AnalyticsKpiService(db)
        self.orders = AnalyticsOrderService(db)
        self.customers = AnalyticsCustomerService(db)
        self.products = AnalyticsProductService(db)
        self.collections = AnalyticsCollectionService(db)
        self.production_ux = AnalyticsProductionUxService(db)
        self.production_planning = ProductionPlanningService(db)
        self.purchase_planning = PurchasePlanningService(db)

    def get_kpis(self, params: AnalyticsQueryParams) -> OperationsAnalyticsKpiResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        core = self.core_kpis.get_core_kpis(params)
        segments = self.customers.get_segment_summary(params)
        today = datetime.now(timezone.utc).date()
        upcoming_count = self.repo.count_upcoming_delivery_orders(today)
        upcoming = self.production_ux.get_upcoming_demand()
        workload_units = Decimal("0")
        if upcoming.has_upcoming_batch:
            workload_units = (
                Decimal(upcoming.order_count)
                + upcoming.collection_count
                + upcoming.product_count
            )

        return OperationsAnalyticsKpiResponse(
            date_range=date_range_response(date_range),
            revenue_this_period=_metric(core.total_revenue),
            profit_this_period=_metric(core.total_profit),
            orders_this_period=_metric(Decimal(core.total_orders)),
            upcoming_deliveries=_metric(Decimal(upcoming_count)),
            active_customers=_metric(Decimal(segments.active_customers)),
            production_workload=_metric(workload_units),
        )

    def get_alerts(self, params: AnalyticsQueryParams) -> OperationsAlertsResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        items: list[OperationsAlertItem] = []

        pending = self.repo.count_orders_by_status((OrderStatus.PENDING,))
        if pending:
            items.append(
                OperationsAlertItem(
                    id="orders_awaiting_confirmation",
                    severity="warning",
                    title="Orders awaiting confirmation",
                    message="Orders are pending confirmation before production can proceed.",
                    count=pending,
                    metric_label="Orders",
                ),
            )

        preparing_queue = self.repo.count_orders_by_status(
            (OrderStatus.CONFIRMED, OrderStatus.PREPARING),
        )
        if preparing_queue:
            items.append(
                OperationsAlertItem(
                    id="orders_awaiting_preparation",
                    severity="info",
                    title="Orders awaiting preparation",
                    message="Confirmed orders still need preparation or are in progress.",
                    count=preparing_queue,
                    metric_label="Orders",
                ),
            )

        awaiting_delivery = self.repo.count_orders_by_status((OrderStatus.READY,))
        if awaiting_delivery:
            items.append(
                OperationsAlertItem(
                    id="orders_awaiting_delivery",
                    severity="warning",
                    title="Orders awaiting delivery",
                    message="Orders are ready and waiting to be delivered.",
                    count=awaiting_delivery,
                    metric_label="Orders",
                ),
            )

        today = datetime.now(timezone.utc).date()
        for delivery_date, order_count in self.repo.fetch_upcoming_delivery_schedule(
            today,
            limit=5,
        ):
            if order_count <= 0:
                continue
            lines = self.purchase_planning.get_purchase_plan_lines(delivery_date)
            if not lines:
                continue
            not_planned = sum(
                1
                for line in lines
                if line.purchase_status == PurchasePlanningStatus.NOT_PLANNED
            )
            if not_planned == len(lines):
                items.append(
                    OperationsAlertItem(
                        id=f"purchase_not_planned_{delivery_date.isoformat()}",
                        severity="warning",
                        title="Purchase planning needed",
                        message=(
                            f"Delivery batch on {delivery_date.isoformat()} has no purchase "
                            "items marked as planned."
                        ),
                        count=not_planned,
                        metric_label="Items",
                    ),
                )
            unassigned = sum(1 for line in lines if line.supplier is None)
            if unassigned:
                items.append(
                    OperationsAlertItem(
                        id=f"unassigned_suppliers_{delivery_date.isoformat()}",
                        severity="info",
                        title="Unassigned suppliers",
                        message=(
                            f"{unassigned} purchase items for {delivery_date.isoformat()} "
                            "have no primary supplier."
                        ),
                        count=unassigned,
                        metric_label="Items",
                    ),
                )

        high_value_pending = self.repo.count_high_value_pending_orders()
        if high_value_pending:
            items.append(
                OperationsAlertItem(
                    id="high_value_pending_orders",
                    severity="warning",
                    title="High-value pending orders",
                    message="Pending or confirmed orders exceed the high-value threshold.",
                    count=high_value_pending,
                    metric_label="Orders",
                ),
            )

        return OperationsAlertsResponse(
            date_range=date_range_response(date_range),
            items=items,
        )

    def get_upcoming_workload(
        self,
        params: AnalyticsQueryParams,
    ) -> OperationsUpcomingWorkloadResponse:
        _ = params
        upcoming = self.production_ux.get_upcoming_demand()
        if not upcoming.has_upcoming_batch or not upcoming.delivery_date:
            return OperationsUpcomingWorkloadResponse()

        product_demand = self.production_planning.get_product_demand(upcoming.delivery_date)
        limit = min(PRODUCT_REQUIREMENT_LIMIT, len(product_demand.items))

        return OperationsUpcomingWorkloadResponse(
            has_upcoming_batch=True,
            delivery_date=upcoming.delivery_date,
            orders_scheduled=upcoming.order_count,
            collections_scheduled=upcoming.collection_count,
            products_required=[
                OperationsProductRequirementLine(
                    product_name=line.product_name,
                    quantity=line.quantity.quantize(QTY),
                )
                for line in product_demand.items[:limit]
            ],
            top_ingredients=upcoming.top_ingredients,
            top_packaging=upcoming.top_packaging,
        )

    def get_delivery_overview(
        self,
        params: AnalyticsQueryParams,
    ) -> OperationsDeliveryOverviewResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        area_dist = self.orders.get_delivery_area_distribution(params)
        today = datetime.now(timezone.utc).date()
        upcoming_rows = self.repo.fetch_upcoming_delivery_schedule(
            today,
            limit=UPCOMING_SCHEDULE_LIMIT,
        )
        fee_rows = self.repo.fetch_delivery_fee_revenue_by_area(
            date_range,
            limit=params.limit,
        )

        return OperationsDeliveryOverviewResponse(
            date_range=date_range_response(date_range),
            deliveries_by_area=area_dist.items,
            upcoming_by_date=[
                OperationsUpcomingDeliveryRow(
                    delivery_date=delivery_date,
                    order_count=count,
                )
                for delivery_date, count in upcoming_rows
            ],
            delivery_fee_by_area=[
                OperationsDeliveryFeeByAreaRow(
                    area_name=name,
                    order_count=count,
                    delivery_fee_revenue=fee,
                )
                for name, count, fee in fee_rows
            ],
        )

    def get_payment_overview(
        self,
        params: AnalyticsQueryParams,
    ) -> OperationsPaymentOverviewResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        methods = self.orders.get_payment_method_distribution(params)
        statuses = self.orders.get_payment_status_distribution(params)
        paid, unpaid, outstanding = self.repo.fetch_payment_revenue_split(date_range)

        return OperationsPaymentOverviewResponse(
            date_range=date_range_response(date_range),
            payment_methods=methods.items,
            payment_statuses=statuses.items,
            outstanding_payment_value=outstanding,
            paid_revenue=paid,
            unpaid_revenue=unpaid,
        )

    def get_business_health(
        self,
        params: AnalyticsQueryParams,
    ) -> OperationsBusinessHealthResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )

        collection_insights = self.collections.get_insights(params)
        product_insights = self.products.get_insights(params)
        customer_insights = self.customers.get_insights(params)
        upcoming = self.production_ux.get_upcoming_demand()

        collection_map = {item.id: item for item in collection_insights.items}
        product_map = {item.id: item for item in product_insights.items}
        customer_map = {item.id: item for item in customer_insights.items}

        highlights = [
            self._health_from_insight(
                collection_map,
                "most_ordered_collection",
                "Best selling collection",
            ),
            self._health_from_insight(
                product_map,
                "fastest_moving_product",
                "Best selling product",
            ),
            self._health_from_insight(
                customer_map,
                "most_valuable_customer",
                "Most valuable customer",
            ),
            self._health_from_insight(
                collection_map,
                "highest_profit_collection",
                "Most profitable collection",
            ),
            self._health_from_insight(
                product_map,
                "highest_profit_product",
                "Most profitable product",
            ),
            self._largest_upcoming_batch_health(upcoming),
        ]

        summary_rows = [
            OperationsExecutiveSummaryRow(
                category=item.title,
                name=item.name or "—",
                primary_metric=item.metric_value,
                secondary_metric=item.metric_label,
            )
            for item in highlights
        ]

        return OperationsBusinessHealthResponse(
            date_range=date_range_response(date_range),
            highlights=highlights,
            summary_rows=summary_rows,
        )

    @staticmethod
    def _health_from_insight(
        source: dict[str, object],
        insight_id: str,
        title: str,
    ) -> OperationsBusinessHealthItem:
        item = source.get(insight_id)
        if item is None:
            return OperationsBusinessHealthItem(
                id=insight_id,
                title=title,
                name=None,
                metric_label="—",
                metric_value="—",
            )
        return OperationsBusinessHealthItem(
            id=insight_id,
            title=title,
            name=getattr(item, "name", None),
            metric_label=getattr(item, "metric_label", "—"),
            metric_value=getattr(item, "metric_value", "—"),
        )

    @staticmethod
    def _largest_upcoming_batch_health(upcoming) -> OperationsBusinessHealthItem:
        if not upcoming.has_upcoming_batch or not upcoming.delivery_date:
            return OperationsBusinessHealthItem(
                id="largest_upcoming_batch",
                title="Largest upcoming batch",
                name=None,
                metric_label="Orders",
                metric_value="—",
            )
        return OperationsBusinessHealthItem(
            id="largest_upcoming_batch",
            title="Largest upcoming batch",
            name=upcoming.delivery_date.isoformat(),
            metric_label="Orders scheduled",
            metric_value=str(upcoming.order_count),
        )
