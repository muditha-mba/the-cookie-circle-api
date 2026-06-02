"""Analytics API schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import (
    CustomerSegment,
    MarketingSource,
    OrderSource,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.utils.analytics_date_range import AnalyticsDatePreset, TrendGranularity


class AnalyticsQueryParams(BaseModel):
    """Shared date range parameters for analytics endpoints."""

    preset: AnalyticsDatePreset | None = None
    start_date: date | None = None
    end_date: date | None = None
    granularity: TrendGranularity = TrendGranularity.DAY
    limit: int = Field(default=10, ge=1, le=100)


class AnalyticsDateRangeResponse(BaseModel):
    preset: AnalyticsDatePreset | None
    start_date: date
    end_date: date


class AnalyticsCategory(BaseModel):
    """Navigation category for future dashboard sections."""

    id: str
    title: str
    description: str
    endpoint_prefix: str


class AnalyticsOverviewResponse(BaseModel):
    """Analytics module metadata for admin landing."""

    date_range: AnalyticsDateRangeResponse
    categories: list[AnalyticsCategory]


class CoreKpiResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    total_revenue: Decimal
    total_profit: Decimal
    total_orders: int
    total_customers: int
    average_order_value: Decimal
    repeat_customer_rate: Decimal
    customer_lifetime_value: Decimal
    profit_margin_percentage: Decimal


class TrendDataPoint(BaseModel):
    period_start: date
    revenue: Decimal
    profit: Decimal
    order_count: int


class TrendSeriesResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    granularity: TrendGranularity
    points: list[TrendDataPoint]


class ProductAnalyticsRow(BaseModel):
    product_id: UUID
    name: str
    units_sold: Decimal
    revenue_snapshot: Decimal
    cost_snapshot: Decimal
    profit_snapshot: Decimal
    average_margin_percentage: Decimal
    last_sold_date: date | None = None


class CollectionAnalyticsRow(BaseModel):
    collection_id: UUID
    name: str
    units_sold: Decimal
    revenue_snapshot: Decimal
    cost_snapshot: Decimal
    profit_snapshot: Decimal
    average_margin_percentage: Decimal
    average_selling_price: Decimal
    last_sold_date: date | None = None


class CollectionKpiMetric(BaseModel):
    """KPI value with optional period-over-period trend (reserved for future use)."""

    value: Decimal
    trend_percentage: Decimal | None = None
    trend_direction: str | None = None


class CollectionAnalyticsKpiResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    total_collection_revenue: CollectionKpiMetric
    total_collection_profit: CollectionKpiMetric
    collections_sold: CollectionKpiMetric
    average_collection_order_value: CollectionKpiMetric
    average_collection_margin_percentage: CollectionKpiMetric
    active_collections_sold: CollectionKpiMetric


class CollectionAnalyticsInsightItem(BaseModel):
    id: str
    title: str
    name: str | None
    metric_label: str
    metric_value: str


class CollectionAnalyticsInsightsResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    items: list[CollectionAnalyticsInsightItem]


class CollectionTrendDataPoint(BaseModel):
    period_start: date
    revenue: Decimal
    profit: Decimal
    units_sold: Decimal
    order_count: int


class CollectionTrendSeriesResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    granularity: TrendGranularity
    points: list[CollectionTrendDataPoint]


class ProductAnalyticsKpiResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    most_ordered_product_name: str | None
    most_profitable_product_name: str | None
    most_ordered_collection_name: str | None
    most_profitable_collection_name: str | None
    total_products_sold: Decimal
    total_collections_sold: Decimal


class ProductAnalyticsInsightItem(BaseModel):
    id: str
    title: str
    entity_type: str
    name: str | None
    metric_label: str
    metric_value: str


class ProductAnalyticsInsightsResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    items: list[ProductAnalyticsInsightItem]


class RankedProductsResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    items: list[ProductAnalyticsRow]


class RankedCollectionsResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    items: list[CollectionAnalyticsRow]


class CustomerGrowthPoint(BaseModel):
    period_start: date
    new_customers: int


class CustomerGrowthResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    granularity: TrendGranularity
    total_new_customers: int
    points: list[CustomerGrowthPoint]


class CustomerSegmentCount(BaseModel):
    segment: CustomerSegment
    count: int


class CustomerSegmentSummaryResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    active_customers: int
    segments: list[CustomerSegmentCount]


class CustomerAnalyticsKpiResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    total_customers: int
    new_customers: int
    returning_customers: int
    vip_customers: int
    inactive_customers: int
    average_customer_lifetime_value: Decimal


class CustomerAnalyticsRow(BaseModel):
    customer_id: UUID
    customer_name: str
    total_orders: int
    lifetime_spend: Decimal
    average_order_value: Decimal
    last_order_date: date | None
    segment: CustomerSegment | None
    marketing_source: MarketingSource | None


class CustomerAnalyticsListResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    items: list[CustomerAnalyticsRow]


class CustomerAnalyticsInsightItem(BaseModel):
    id: str
    title: str
    name: str | None
    metric_label: str
    metric_value: str


class CustomerAnalyticsInsightsResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    items: list[CustomerAnalyticsInsightItem]


class MarketingSourcePerformanceRow(BaseModel):
    marketing_source: MarketingSource | None
    label: str
    customer_count: int
    order_count: int
    revenue_snapshot: Decimal
    profit_snapshot: Decimal


class MarketingSourcePerformanceResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    items: list[MarketingSourcePerformanceRow]


class ProductionVolumePoint(BaseModel):
    period_start: date
    total_products: Decimal
    total_collections: Decimal
    order_count: int


class ProductionVolumeResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    granularity: TrendGranularity
    points: list[ProductionVolumePoint]


class DemandTrendPoint(BaseModel):
    period_start: date
    item_name: str
    quantity: Decimal
    unit: str
    estimated_cost: Decimal


class IngredientDemandTrendsResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    granularity: TrendGranularity
    points: list[DemandTrendPoint]


class PackagingDemandTrendsResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    granularity: TrendGranularity
    points: list[DemandTrendPoint]


class BatchVolumePoint(BaseModel):
    delivery_date: date
    order_count: int
    total_revenue_snapshot: Decimal


class BatchVolumeTrendsResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    points: list[BatchVolumePoint]


class ProductionDemandItemRow(BaseModel):
    product_item_id: UUID
    item_name: str
    total_quantity: Decimal
    unit: str
    estimated_cost: Decimal
    last_used_date: date | None = None


class ProductionDemandListResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    items: list[ProductionDemandItemRow]


class ProductionAnalyticsKpiResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    total_products_produced: Decimal
    total_collections_produced: Decimal
    total_ingredient_consumption_cost: Decimal
    total_packaging_consumption_cost: Decimal
    total_production_batches: int
    average_batch_size: Decimal


class ProductionAnalyticsInsightItem(BaseModel):
    id: str
    title: str
    name: str | None
    metric_label: str
    metric_value: str


class ProductionAnalyticsInsightsResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    items: list[ProductionAnalyticsInsightItem]


class ProductionDemandPreviewLine(BaseModel):
    item_name: str
    quantity: Decimal
    unit: str


class ProductionOutOfRangeHintResponse(BaseModel):
    """Upcoming delivery outside the selected analytics window."""

    has_upcoming_outside_range: bool = False
    delivery_date: date | None = None
    order_count: int = 0
    collection_count: Decimal = Decimal("0")
    product_count: Decimal = Decimal("0")


class UpcomingProductionDemandResponse(BaseModel):
    """Next scheduled production batch (from ProductionPlanningService)."""

    has_upcoming_batch: bool = False
    delivery_date: date | None = None
    order_count: int = 0
    collection_count: Decimal = Decimal("0")
    product_count: Decimal = Decimal("0")
    top_ingredients: list[ProductionDemandPreviewLine] = []
    top_packaging: list[ProductionDemandPreviewLine] = []


class TopOrderRow(BaseModel):
    order_id: UUID
    order_number: str
    customer_name: str
    total_revenue_snapshot: Decimal
    total_profit_snapshot: Decimal
    margin_percentage_snapshot: Decimal
    scheduled_delivery_date: date
    created_at: datetime


class TopOrdersResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    items: list[TopOrderRow]


class AnalyticsKpiMetric(BaseModel):
    """Shared KPI value with optional trend fields for future period comparisons."""

    value: Decimal
    trend_percentage: Decimal | None = None
    trend_direction: str | None = None


class OrderAnalyticsKpiResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    total_orders: AnalyticsKpiMetric
    completed_orders: AnalyticsKpiMetric
    average_order_value: AnalyticsKpiMetric
    fulfillment_rate: AnalyticsKpiMetric
    delivery_success_rate: AnalyticsKpiMetric
    average_delivery_fee: AnalyticsKpiMetric


class OrderAnalyticsInsightItem(BaseModel):
    id: str
    title: str
    name: str | None
    metric_label: str
    metric_value: str


class OrderAnalyticsInsightsResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    items: list[OrderAnalyticsInsightItem]


class OrderDistributionItem(BaseModel):
    """Reusable count bucket for operations and order analytics dashboards."""

    key: str
    label: str
    count: int


class OrderDistributionResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    items: list[OrderDistributionItem]


class OrderTrendPoint(BaseModel):
    period_start: date
    count: int


class OrderTrendSeriesResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    granularity: TrendGranularity
    points: list[OrderTrendPoint]


class OrderAnalyticsPerformanceRow(BaseModel):
    order_id: UUID
    order_number: str
    customer_id: UUID
    customer_name: str
    total_revenue_snapshot: Decimal
    total_profit_snapshot: Decimal
    delivery_fee_snapshot: Decimal
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    status: OrderStatus
    delivery_area_name: str | None
    scheduled_delivery_date: date
    created_at: datetime


class OrderAnalyticsPerformanceResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    items: list[OrderAnalyticsPerformanceRow]


class OperationsAnalyticsKpiResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    revenue_this_period: AnalyticsKpiMetric
    profit_this_period: AnalyticsKpiMetric
    orders_this_period: AnalyticsKpiMetric
    upcoming_deliveries: AnalyticsKpiMetric
    active_customers: AnalyticsKpiMetric
    production_workload: AnalyticsKpiMetric


class OperationsAlertItem(BaseModel):
    """Operational alert for executive dashboard — reusable by future modules."""

    id: str
    severity: str
    title: str
    message: str
    count: int
    metric_label: str | None = None


class OperationsAlertsResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    items: list[OperationsAlertItem]


class OperationsProductRequirementLine(BaseModel):
    product_name: str
    quantity: Decimal


class OperationsUpcomingWorkloadResponse(BaseModel):
    has_upcoming_batch: bool = False
    delivery_date: date | None = None
    orders_scheduled: int = 0
    collections_scheduled: Decimal = Decimal("0")
    products_required: list[OperationsProductRequirementLine] = []
    top_ingredients: list[ProductionDemandPreviewLine] = []
    top_packaging: list[ProductionDemandPreviewLine] = []


class OperationsDeliveryFeeByAreaRow(BaseModel):
    area_name: str
    order_count: int
    delivery_fee_revenue: Decimal


class OperationsUpcomingDeliveryRow(BaseModel):
    delivery_date: date
    order_count: int


class OperationsDeliveryOverviewResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    deliveries_by_area: list[OrderDistributionItem]
    upcoming_by_date: list[OperationsUpcomingDeliveryRow]
    delivery_fee_by_area: list[OperationsDeliveryFeeByAreaRow]


class OperationsPaymentOverviewResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    payment_methods: list[OrderDistributionItem]
    payment_statuses: list[OrderDistributionItem]
    outstanding_payment_value: Decimal
    paid_revenue: Decimal
    unpaid_revenue: Decimal


class OperationsBusinessHealthItem(BaseModel):
    id: str
    title: str
    name: str | None
    metric_label: str
    metric_value: str


class OperationsExecutiveSummaryRow(BaseModel):
    category: str
    name: str
    primary_metric: str
    secondary_metric: str | None = None


class OperationsBusinessHealthResponse(BaseModel):
    date_range: AnalyticsDateRangeResponse
    highlights: list[OperationsBusinessHealthItem]
    summary_rows: list[OperationsExecutiveSummaryRow]
