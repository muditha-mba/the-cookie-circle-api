"""Order lifecycle, fulfillment, delivery, and payment analytics."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import OrderSource, OrderStatus, PaymentMethod, PaymentStatus
from app.repositories.analytics_repository import (
    ONLINE_ORDER_SOURCES,
    AnalyticsRepository,
)
from app.schemas.analytics import (
    AnalyticsKpiMetric,
    AnalyticsQueryParams,
    OrderAnalyticsInsightItem,
    OrderAnalyticsInsightsResponse,
    OrderAnalyticsKpiResponse,
    OrderAnalyticsPerformanceResponse,
    OrderAnalyticsPerformanceRow,
    OrderDistributionItem,
    OrderDistributionResponse,
    OrderTrendPoint,
    OrderTrendSeriesResponse,
    TopOrderRow,
    TopOrdersResponse,
    TrendSeriesResponse,
)
from app.services.analytics._common import date_range_response, safe_divide
from app.services.analytics.analytics_revenue_service import AnalyticsRevenueService
from app.utils.analytics_date_range import resolve_analytics_date_range

MONEY = Decimal("0.01")

STATUS_BUCKETS: tuple[tuple[str, str], ...] = (
    (OrderStatus.PENDING.value, "Pending"),
    (OrderStatus.CONFIRMED.value, "Confirmed"),
    (OrderStatus.PREPARING.value, "Preparing"),
    (OrderStatus.READY.value, "Ready"),
    (OrderStatus.DELIVERED.value, "Delivered"),
    (OrderStatus.CANCELLED.value, "Cancelled"),
)

PAYMENT_STATUS_BUCKETS: tuple[tuple[str, str], ...] = (
    (PaymentStatus.PENDING.value, "Pending"),
    (PaymentStatus.PAID.value, "Paid"),
    (PaymentStatus.FAILED.value, "Failed"),
    (PaymentStatus.REFUNDED.value, "Refunded"),
)

PAYMENT_METHOD_BUCKETS: tuple[tuple[str, str], ...] = (
    (PaymentMethod.CASH_ON_DELIVERY.value, "COD"),
    (PaymentMethod.BANK_TRANSFER.value, "Bank Transfer"),
    (PaymentMethod.MANUAL.value, "Cash"),
    (PaymentMethod.STRIPE.value, "Stripe"),
)

SOURCE_BUCKETS: tuple[tuple[str, str], ...] = (
    ("manual", "Manual"),
    ("phone", "Phone"),
    ("walk_in", "Walk In"),
    ("online", "Online"),
)


def _kpi_metric(value: Decimal) -> AnalyticsKpiMetric:
    return AnalyticsKpiMetric(value=value)


def _payment_method_label(method: str) -> str:
    labels = dict(PAYMENT_METHOD_BUCKETS)
    return labels.get(method, "Other")


def _source_group_key(source: str) -> str:
    if source in ONLINE_ORDER_SOURCES:
        return "online"
    if source in {bucket[0] for bucket in SOURCE_BUCKETS}:
        return source
    return "other"


def _normalize_distribution(
    rows: list[tuple[str, int]],
    buckets: tuple[tuple[str, str], ...],
) -> list[OrderDistributionItem]:
    counts = dict(rows)
    return [
        OrderDistributionItem(key=key, label=label, count=int(counts.get(key, 0)))
        for key, label in buckets
    ]


def _group_source_distribution(
    rows: list[tuple[str, int]],
) -> list[OrderDistributionItem]:
    grouped: dict[str, int] = {key: 0 for key, _ in SOURCE_BUCKETS}
    for source, count in rows:
        key = _source_group_key(source)
        if key in grouped:
            grouped[key] += count
    return [
        OrderDistributionItem(key=key, label=label, count=grouped[key])
        for key, label in SOURCE_BUCKETS
    ]


class AnalyticsOrderService:
    """Order trends, distributions, and operational performance."""

    def __init__(self, db: Session) -> None:
        self.repo = AnalyticsRepository(db)
        self.revenue = AnalyticsRevenueService(db)

    def get_order_trends(self, params: AnalyticsQueryParams) -> TrendSeriesResponse:
        return self.revenue.get_order_trends(params)

    def get_top_profitable_orders(self, params: AnalyticsQueryParams) -> TopOrdersResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        orders = self.repo.fetch_top_orders(date_range, limit=params.limit)
        return TopOrdersResponse(
            date_range=date_range_response(date_range),
            items=[
                TopOrderRow(
                    order_id=order.id,
                    order_number=order.order_number,
                    customer_name=(
                        f"{order.customer.first_name} {order.customer.last_name}".strip()
                    ),
                    total_revenue_snapshot=order.total_revenue_snapshot,
                    total_profit_snapshot=order.total_profit_snapshot,
                    margin_percentage_snapshot=order.margin_percentage_snapshot,
                    scheduled_delivery_date=order.scheduled_delivery_date,
                    created_at=order.created_at,
                )
                for order in orders
            ],
        )

    def get_kpis(self, params: AnalyticsQueryParams) -> OrderAnalyticsKpiResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        agg = self.repo.fetch_order_kpi_aggregate(date_range)
        fulfilment_denominator = agg.total_orders - agg.cancelled_orders
        fulfillment_rate = safe_divide(
            Decimal(agg.completed_orders * 100),
            fulfilment_denominator,
        )
        delivery_success = safe_divide(
            Decimal(agg.completed_orders * 100),
            agg.total_orders,
        )
        average_order_value = safe_divide(agg.total_revenue, agg.total_orders)
        average_delivery_fee = safe_divide(agg.total_delivery_fees, agg.total_orders)

        return OrderAnalyticsKpiResponse(
            date_range=date_range_response(date_range),
            total_orders=_kpi_metric(Decimal(agg.total_orders)),
            completed_orders=_kpi_metric(Decimal(agg.completed_orders)),
            average_order_value=_kpi_metric(average_order_value),
            fulfillment_rate=_kpi_metric(fulfillment_rate),
            delivery_success_rate=_kpi_metric(delivery_success),
            average_delivery_fee=_kpi_metric(average_delivery_fee),
        )

    def get_insights(self, params: AnalyticsQueryParams) -> OrderAnalyticsInsightsResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )

        top_area = self.repo.fetch_top_delivery_area(date_range)
        top_payment = self.repo.fetch_top_payment_method(date_range)
        top_source_raw = self.repo.fetch_top_order_source_raw(date_range)
        fastest = self.repo.fetch_fastest_fulfilled_order(date_range)
        highest = self.repo.fetch_highest_value_order(date_range)
        largest_batch = self.repo.fetch_largest_delivery_batch(date_range)

        top_source_label = None
        top_source_count = 0
        if top_source_raw:
            key = _source_group_key(top_source_raw[0])
            top_source_label = dict(SOURCE_BUCKETS).get(key, top_source_raw[0].replace("_", " ").title())
            grouped = _group_source_distribution(self.repo.fetch_order_source_distribution(date_range))
            top_source_count = next(
                (item.count for item in grouped if item.key == key),
                top_source_raw[1],
            )

        fastest_duration: str | None = None
        if fastest and fastest.delivered_at and fastest.created_at:
            delta = fastest.delivered_at - fastest.created_at
            hours = int(delta.total_seconds() // 3600)
            minutes = int((delta.total_seconds() % 3600) // 60)
            fastest_duration = f"{hours}h {minutes}m" if hours else f"{minutes}m"

        items = [
            OrderAnalyticsInsightItem(
                id="most_popular_delivery_area",
                title="Most Popular Delivery Area",
                name=top_area[0] if top_area else None,
                metric_label="Orders",
                metric_value=str(top_area[1]) if top_area else "—",
            ),
            OrderAnalyticsInsightItem(
                id="most_used_payment_method",
                title="Most Used Payment Method",
                name=_payment_method_label(top_payment[0]) if top_payment else None,
                metric_label="Orders",
                metric_value=str(top_payment[1]) if top_payment else "—",
            ),
            OrderAnalyticsInsightItem(
                id="most_used_order_source",
                title="Most Used Order Source",
                name=top_source_label,
                metric_label="Orders",
                metric_value=str(top_source_count) if top_source_label else "—",
            ),
            OrderAnalyticsInsightItem(
                id="fastest_fulfilled_order",
                title="Fastest Fulfilled Order",
                name=fastest.order_number if fastest else None,
                metric_label="Fulfillment time",
                metric_value=fastest_duration or "—",
            ),
            OrderAnalyticsInsightItem(
                id="highest_value_order",
                title="Highest Value Order",
                name=highest.order_number if highest else None,
                metric_label="Revenue",
                metric_value=(
                    f"Rs {highest.total_revenue_snapshot:,.2f}" if highest else "—"
                ),
            ),
            OrderAnalyticsInsightItem(
                id="largest_delivery_batch",
                title="Largest Delivery Batch",
                name=largest_batch[0].isoformat() if largest_batch else None,
                metric_label="Orders",
                metric_value=str(largest_batch[1]) if largest_batch else "—",
            ),
        ]
        return OrderAnalyticsInsightsResponse(
            date_range=date_range_response(date_range),
            items=items,
        )

    def get_status_distribution(
        self,
        params: AnalyticsQueryParams,
    ) -> OrderDistributionResponse:
        return self._distribution(params, self.repo.fetch_order_status_distribution, STATUS_BUCKETS)

    def get_payment_status_distribution(
        self,
        params: AnalyticsQueryParams,
    ) -> OrderDistributionResponse:
        return self._distribution(
            params,
            self.repo.fetch_order_payment_status_distribution,
            PAYMENT_STATUS_BUCKETS,
        )

    def get_payment_method_distribution(
        self,
        params: AnalyticsQueryParams,
    ) -> OrderDistributionResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        rows = self.repo.fetch_order_payment_method_distribution(date_range)
        counts_by_method = dict(rows)
        items = [
            OrderDistributionItem(
                key=key,
                label=label,
                count=int(counts_by_method.get(key, 0)),
            )
            for key, label in PAYMENT_METHOD_BUCKETS
        ]
        return OrderDistributionResponse(
            date_range=date_range_response(date_range),
            items=items,
        )

    def get_order_source_distribution(
        self,
        params: AnalyticsQueryParams,
    ) -> OrderDistributionResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        rows = self.repo.fetch_order_source_distribution(date_range)
        return OrderDistributionResponse(
            date_range=date_range_response(date_range),
            items=_group_source_distribution(rows),
        )

    def get_delivery_area_distribution(
        self,
        params: AnalyticsQueryParams,
    ) -> OrderDistributionResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        rows = self.repo.fetch_order_delivery_area_distribution(
            date_range,
            limit=params.limit,
        )
        return OrderDistributionResponse(
            date_range=date_range_response(date_range),
            items=[
                OrderDistributionItem(key=name, label=name, count=count)
                for name, count in rows
            ],
        )

    def get_fulfillment_trends(
        self,
        params: AnalyticsQueryParams,
    ) -> OrderTrendSeriesResponse:
        return self._trend_series(params, self.repo.fetch_order_fulfillment_trends)

    def get_delivery_trends(self, params: AnalyticsQueryParams) -> OrderTrendSeriesResponse:
        return self._trend_series(params, self.repo.fetch_order_delivery_trends)

    def get_performance(
        self,
        params: AnalyticsQueryParams,
    ) -> OrderAnalyticsPerformanceResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        orders = self.repo.fetch_order_performance(date_range, limit=params.limit)
        return OrderAnalyticsPerformanceResponse(
            date_range=date_range_response(date_range),
            items=[self._performance_row(order) for order in orders],
        )

    def _distribution(
        self,
        params: AnalyticsQueryParams,
        fetcher,
        buckets: tuple[tuple[str, str], ...],
    ) -> OrderDistributionResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        rows = fetcher(date_range)
        return OrderDistributionResponse(
            date_range=date_range_response(date_range),
            items=_normalize_distribution(rows, buckets),
        )

    def _trend_series(
        self,
        params: AnalyticsQueryParams,
        fetcher,
    ) -> OrderTrendSeriesResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        rows = fetcher(date_range, params.granularity)
        return OrderTrendSeriesResponse(
            date_range=date_range_response(date_range),
            granularity=params.granularity,
            points=[
                OrderTrendPoint(period_start=period, count=count)
                for period, count in rows
            ],
        )

    @staticmethod
    def _performance_row(order) -> OrderAnalyticsPerformanceRow:
        customer_name = f"{order.customer.first_name} {order.customer.last_name}".strip()
        area_name = order.delivery_area.name if order.delivery_area else None
        return OrderAnalyticsPerformanceRow(
            order_id=order.id,
            order_number=order.order_number,
            customer_id=order.customer_id,
            customer_name=customer_name,
            total_revenue_snapshot=order.total_revenue_snapshot,
            total_profit_snapshot=order.total_profit_snapshot,
            delivery_fee_snapshot=order.delivery_fee_snapshot,
            payment_method=order.payment_method,
            payment_status=order.payment_status,
            status=order.status,
            delivery_area_name=area_name,
            scheduled_delivery_date=order.scheduled_delivery_date,
            created_at=order.created_at,
        )
