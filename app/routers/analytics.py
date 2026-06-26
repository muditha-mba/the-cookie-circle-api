"""Analytics foundation routes (metrics only — no dashboard UI)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.admin import (
    get_analytics_collection_service,
    get_analytics_customer_service,
    get_analytics_executive_service,
    get_analytics_export_service,
    get_analytics_kpi_service,
    get_analytics_operations_service,
    get_analytics_order_service,
    get_analytics_overview_service,
    get_analytics_product_service,
    get_analytics_production_service,
    get_analytics_production_ux_service,
    get_analytics_revenue_service,
    get_current_admin_user,
    get_overhead_analytics_service,
)
from app.services.overhead_analytics_service import OverheadAnalyticsService
from app.dependencies.permissions import require_super_admin
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    AnalyticsQueryParams,
    BatchVolumeTrendsResponse,
    CollectionPackageAnalyticsInsightsResponse,
    CollectionPackageAnalyticsKpisResponse,
    CollectionPackageAnalyticsPerformanceResponse,
    CoreKpiResponse,
    CollectionAnalyticsInsightsResponse,
    CollectionAnalyticsKpiResponse,
    CollectionTrendSeriesResponse,
    CustomerAnalyticsInsightsResponse,
    CustomerAnalyticsKpiResponse,
    CustomerAnalyticsListResponse,
    CustomerGrowthResponse,
    CustomerSegmentSummaryResponse,
    ExecutiveOperationsSnapshotResponse,
    ExecutiveOverviewHighlightsResponse,
    ExecutiveOverviewKpisResponse,
    ExecutiveRevenueContributionResponse,
    IngredientDemandTrendsResponse,
    MarketingSourcePerformanceResponse,
    OrderAnalyticsInsightsResponse,
    OrderAnalyticsKpiResponse,
    OrderCustomerBehaviourResponse,
    OrderDeliveryAreaPerformanceResponse,
    OrderLifecycleTrendResponse,
    OrderPaymentMethodPerformanceResponse,
    OperationsAlertsResponse,
    OperationsAnalyticsKpiResponse,
    OperationsBusinessHealthResponse,
    OperationsDeliveryOverviewResponse,
    OperationsPaymentOverviewResponse,
    OperationsUpcomingWorkloadResponse,
    OrderAnalyticsPerformanceResponse,
    OrderDistributionResponse,
    OrderTrendSeriesResponse,
    PackagingDemandTrendsResponse,
    ProductionAnalyticsInsightsResponse,
    ProductionAnalyticsKpiResponse,
    ProductionDemandListResponse,
    ProductionOutOfRangeHintResponse,
    ProductionVolumeResponse,
    UpcomingProductionDemandResponse,
    ProductAnalyticsInsightsResponse,
    ProductAnalyticsKpiResponse,
    RankedCollectionsResponse,
    RankedProductsResponse,
    TopOrdersResponse,
    TrendSeriesResponse,
)
from app.services.analytics.analytics_collection_service import AnalyticsCollectionService
from app.services.analytics.analytics_customer_service import AnalyticsCustomerService
from app.services.analytics.analytics_executive_service import AnalyticsExecutiveService
from app.services.analytics.analytics_export_service import AnalyticsExportService
from app.services.analytics.analytics_kpi_service import AnalyticsKpiService
from app.services.analytics.analytics_operations_service import AnalyticsOperationsService
from app.services.analytics.analytics_order_service import AnalyticsOrderService
from app.services.analytics.analytics_overview_service import AnalyticsOverviewService
from app.services.analytics.analytics_product_service import AnalyticsProductService
from app.services.analytics.analytics_production_service import AnalyticsProductionService
from app.services.analytics.analytics_production_ux_service import AnalyticsProductionUxService
from app.services.analytics.analytics_revenue_service import AnalyticsRevenueService

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
    dependencies=[Depends(get_current_admin_user), Depends(require_super_admin)],
)


@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOverviewService, Depends(get_analytics_overview_service)],
) -> AnalyticsOverviewResponse:
    """Analytics module categories and active date range."""
    return service.get_overview(params)


@router.get("/kpis", response_model=CoreKpiResponse)
def get_core_kpis(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsKpiService, Depends(get_analytics_kpi_service)],
) -> CoreKpiResponse:
    """Core business KPIs from order snapshots."""
    return service.get_core_kpis(params)


@router.get("/revenue/trends", response_model=TrendSeriesResponse)
def get_revenue_trends(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsRevenueService, Depends(get_analytics_revenue_service)],
) -> TrendSeriesResponse:
    return service.get_revenue_trends(params)


@router.get("/profit/trends", response_model=TrendSeriesResponse)
def get_profit_trends(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsRevenueService, Depends(get_analytics_revenue_service)],
) -> TrendSeriesResponse:
    return service.get_profit_trends(params)


@router.get("/orders/kpis", response_model=OrderAnalyticsKpiResponse)
def get_order_analytics_kpis(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOrderService, Depends(get_analytics_order_service)],
) -> OrderAnalyticsKpiResponse:
    return service.get_kpis(params)


@router.get("/orders/insights", response_model=OrderAnalyticsInsightsResponse)
def get_order_analytics_insights(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOrderService, Depends(get_analytics_order_service)],
) -> OrderAnalyticsInsightsResponse:
    return service.get_insights(params)


@router.get("/orders/status-distribution", response_model=OrderDistributionResponse)
def get_order_status_distribution(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOrderService, Depends(get_analytics_order_service)],
) -> OrderDistributionResponse:
    return service.get_status_distribution(params)


@router.get("/orders/payment-status-distribution", response_model=OrderDistributionResponse)
def get_order_payment_status_distribution(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOrderService, Depends(get_analytics_order_service)],
) -> OrderDistributionResponse:
    return service.get_payment_status_distribution(params)


@router.get("/orders/payment-method-distribution", response_model=OrderDistributionResponse)
def get_order_payment_method_distribution(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOrderService, Depends(get_analytics_order_service)],
) -> OrderDistributionResponse:
    return service.get_payment_method_distribution(params)


@router.get("/orders/order-source-distribution", response_model=OrderDistributionResponse)
def get_order_order_source_distribution(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOrderService, Depends(get_analytics_order_service)],
) -> OrderDistributionResponse:
    return service.get_order_source_distribution(params)


@router.get("/orders/order-type-distribution", response_model=OrderDistributionResponse)
def get_order_type_distribution(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOrderService, Depends(get_analytics_order_service)],
) -> OrderDistributionResponse:
    return service.get_order_type_distribution(params)


@router.get("/orders/delivery-area-distribution", response_model=OrderDistributionResponse)
def get_order_delivery_area_distribution(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOrderService, Depends(get_analytics_order_service)],
) -> OrderDistributionResponse:
    return service.get_delivery_area_distribution(params)


@router.get("/orders/fulfillment-trends", response_model=OrderTrendSeriesResponse)
def get_order_fulfillment_trends(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOrderService, Depends(get_analytics_order_service)],
) -> OrderTrendSeriesResponse:
    return service.get_fulfillment_trends(params)


@router.get("/orders/delivery-trends", response_model=OrderTrendSeriesResponse)
def get_order_delivery_trends(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOrderService, Depends(get_analytics_order_service)],
) -> OrderTrendSeriesResponse:
    return service.get_delivery_trends(params)


@router.get("/orders/lifecycle-trends", response_model=OrderLifecycleTrendResponse)
def get_order_lifecycle_trends(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOrderService, Depends(get_analytics_order_service)],
) -> OrderLifecycleTrendResponse:
    return service.get_lifecycle_trends(params)


@router.get("/orders/delivery-area-performance", response_model=OrderDeliveryAreaPerformanceResponse)
def get_order_delivery_area_performance(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOrderService, Depends(get_analytics_order_service)],
) -> OrderDeliveryAreaPerformanceResponse:
    return service.get_delivery_area_performance(params)


@router.get("/orders/payment-method-performance", response_model=OrderPaymentMethodPerformanceResponse)
def get_order_payment_method_performance(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOrderService, Depends(get_analytics_order_service)],
) -> OrderPaymentMethodPerformanceResponse:
    return service.get_payment_method_performance(params)


@router.get("/orders/customer-behaviour", response_model=OrderCustomerBehaviourResponse)
def get_order_customer_behaviour(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOrderService, Depends(get_analytics_order_service)],
) -> OrderCustomerBehaviourResponse:
    return service.get_customer_behaviour(params)


@router.get("/orders/performance", response_model=OrderAnalyticsPerformanceResponse)
def get_order_analytics_performance(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOrderService, Depends(get_analytics_order_service)],
) -> OrderAnalyticsPerformanceResponse:
    return service.get_performance(params)


@router.get("/orders/trends", response_model=TrendSeriesResponse)
def get_order_trends(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOrderService, Depends(get_analytics_order_service)],
) -> TrendSeriesResponse:
    return service.get_order_trends(params)


@router.get("/orders/top-profitable", response_model=TopOrdersResponse)
def get_top_profitable_orders(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOrderService, Depends(get_analytics_order_service)],
) -> TopOrdersResponse:
    return service.get_top_profitable_orders(params)


@router.get("/products/most-ordered", response_model=RankedProductsResponse)
def get_most_ordered_products(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsProductService, Depends(get_analytics_product_service)],
) -> RankedProductsResponse:
    return service.get_most_ordered(params)


@router.get("/products/most-profitable", response_model=RankedProductsResponse)
def get_most_profitable_products(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsProductService, Depends(get_analytics_product_service)],
) -> RankedProductsResponse:
    return service.get_most_profitable(params)


@router.get("/products/least-ordered", response_model=RankedProductsResponse)
def get_least_ordered_products(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsProductService, Depends(get_analytics_product_service)],
) -> RankedProductsResponse:
    return service.get_least_ordered(params)


@router.get("/products/kpis", response_model=ProductAnalyticsKpiResponse)
def get_product_analytics_kpis(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsProductService, Depends(get_analytics_product_service)],
) -> ProductAnalyticsKpiResponse:
    return service.get_kpis(params)


@router.get("/products/insights", response_model=ProductAnalyticsInsightsResponse)
def get_product_analytics_insights(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsProductService, Depends(get_analytics_product_service)],
) -> ProductAnalyticsInsightsResponse:
    return service.get_insights(params)


@router.get("/products/performance", response_model=RankedProductsResponse)
def get_product_performance(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsProductService, Depends(get_analytics_product_service)],
) -> RankedProductsResponse:
    """Full product performance rows for dashboard tables."""
    return service.get_performance(params)


@router.get("/collections/kpis", response_model=CollectionAnalyticsKpiResponse)
def get_collection_analytics_kpis(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCollectionService, Depends(get_analytics_collection_service)],
) -> CollectionAnalyticsKpiResponse:
    return service.get_kpis(params)


@router.get("/collections/insights", response_model=CollectionAnalyticsInsightsResponse)
def get_collection_analytics_insights(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCollectionService, Depends(get_analytics_collection_service)],
) -> CollectionAnalyticsInsightsResponse:
    return service.get_insights(params)


@router.get("/collections/revenue-trends", response_model=CollectionTrendSeriesResponse)
def get_collection_revenue_trends(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCollectionService, Depends(get_analytics_collection_service)],
) -> CollectionTrendSeriesResponse:
    return service.get_revenue_trends(params)


@router.get("/collections/profit-trends", response_model=CollectionTrendSeriesResponse)
def get_collection_profit_trends(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCollectionService, Depends(get_analytics_collection_service)],
) -> CollectionTrendSeriesResponse:
    return service.get_profit_trends(params)


@router.get("/collections/order-trends", response_model=CollectionTrendSeriesResponse)
def get_collection_order_trends(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCollectionService, Depends(get_analytics_collection_service)],
) -> CollectionTrendSeriesResponse:
    return service.get_order_trends(params)


@router.get("/collections/top-revenue", response_model=RankedCollectionsResponse)
def get_top_revenue_collections(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCollectionService, Depends(get_analytics_collection_service)],
) -> RankedCollectionsResponse:
    return service.get_top_revenue(params)


@router.get("/collections/top-profit", response_model=RankedCollectionsResponse)
def get_top_profit_collections(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCollectionService, Depends(get_analytics_collection_service)],
) -> RankedCollectionsResponse:
    return service.get_top_profit(params)


@router.get("/collections/top-margin", response_model=RankedCollectionsResponse)
def get_top_margin_collections(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCollectionService, Depends(get_analytics_collection_service)],
) -> RankedCollectionsResponse:
    return service.get_top_margin(params)


@router.get("/collections/top-volume", response_model=RankedCollectionsResponse)
def get_top_volume_collections(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCollectionService, Depends(get_analytics_collection_service)],
) -> RankedCollectionsResponse:
    return service.get_top_volume(params)


@router.get("/collections/most-ordered", response_model=RankedCollectionsResponse)
def get_most_ordered_collections(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCollectionService, Depends(get_analytics_collection_service)],
) -> RankedCollectionsResponse:
    return service.get_most_ordered(params)


@router.get("/collections/most-profitable", response_model=RankedCollectionsResponse)
def get_most_profitable_collections(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCollectionService, Depends(get_analytics_collection_service)],
) -> RankedCollectionsResponse:
    return service.get_most_profitable(params)


@router.get("/collections/performance", response_model=RankedCollectionsResponse)
def get_collection_performance(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCollectionService, Depends(get_analytics_collection_service)],
) -> RankedCollectionsResponse:
    """Full collection performance rows for dashboard tables."""
    return service.get_performance(params)


@router.get("/collections/packages/kpis", response_model=CollectionPackageAnalyticsKpisResponse)
def get_collection_package_kpis(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCollectionService, Depends(get_analytics_collection_service)],
) -> CollectionPackageAnalyticsKpisResponse:
    return service.get_package_kpis(params)


@router.get(
    "/collections/packages/insights",
    response_model=CollectionPackageAnalyticsInsightsResponse,
)
def get_collection_package_insights(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCollectionService, Depends(get_analytics_collection_service)],
) -> CollectionPackageAnalyticsInsightsResponse:
    return service.get_package_insights(params)


@router.get(
    "/collections/packages/performance",
    response_model=CollectionPackageAnalyticsPerformanceResponse,
)
def get_collection_package_performance(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCollectionService, Depends(get_analytics_collection_service)],
) -> CollectionPackageAnalyticsPerformanceResponse:
    return service.get_package_performance(params)


@router.get("/customers/kpis", response_model=CustomerAnalyticsKpiResponse)
def get_customer_analytics_kpis(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCustomerService, Depends(get_analytics_customer_service)],
) -> CustomerAnalyticsKpiResponse:
    return service.get_kpis(params)


@router.get("/customers/insights", response_model=CustomerAnalyticsInsightsResponse)
def get_customer_analytics_insights(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCustomerService, Depends(get_analytics_customer_service)],
) -> CustomerAnalyticsInsightsResponse:
    return service.get_insights(params)


@router.get("/customers/performance", response_model=CustomerAnalyticsListResponse)
def get_customer_performance(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCustomerService, Depends(get_analytics_customer_service)],
) -> CustomerAnalyticsListResponse:
    return service.get_performance(params)


@router.get("/customers/growth", response_model=CustomerGrowthResponse)
def get_customer_growth(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCustomerService, Depends(get_analytics_customer_service)],
) -> CustomerGrowthResponse:
    return service.get_customer_growth(params)


@router.get("/customers/segments", response_model=CustomerSegmentSummaryResponse)
def get_customer_segments(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCustomerService, Depends(get_analytics_customer_service)],
) -> CustomerSegmentSummaryResponse:
    return service.get_segment_summary(params)


@router.get("/customers/marketing-sources", response_model=MarketingSourcePerformanceResponse)
def get_marketing_source_performance(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsCustomerService, Depends(get_analytics_customer_service)],
) -> MarketingSourcePerformanceResponse:
    return service.get_marketing_source_performance(params)


@router.get("/production/upcoming", response_model=UpcomingProductionDemandResponse)
def get_upcoming_production_demand(
    service: Annotated[AnalyticsProductionUxService, Depends(get_analytics_production_ux_service)],
) -> UpcomingProductionDemandResponse:
    return service.get_upcoming_demand()


@router.get("/production/out-of-range-hint", response_model=ProductionOutOfRangeHintResponse)
def get_production_out_of_range_hint(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsProductionUxService, Depends(get_analytics_production_ux_service)],
) -> ProductionOutOfRangeHintResponse:
    return service.get_out_of_range_hint(params)


@router.get("/production/kpis", response_model=ProductionAnalyticsKpiResponse)
def get_production_analytics_kpis(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsProductionService, Depends(get_analytics_production_service)],
) -> ProductionAnalyticsKpiResponse:
    return service.get_kpis(params)


@router.get("/production/insights", response_model=ProductionAnalyticsInsightsResponse)
def get_production_analytics_insights(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsProductionService, Depends(get_analytics_production_service)],
) -> ProductionAnalyticsInsightsResponse:
    return service.get_insights(params)


@router.get("/production/ingredients/summary", response_model=ProductionDemandListResponse)
def get_production_ingredient_summary(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsProductionService, Depends(get_analytics_production_service)],
) -> ProductionDemandListResponse:
    return service.get_ingredient_summary(params)


@router.get("/production/packaging/summary", response_model=ProductionDemandListResponse)
def get_production_packaging_summary(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsProductionService, Depends(get_analytics_production_service)],
) -> ProductionDemandListResponse:
    return service.get_packaging_summary(params)


@router.get("/production/volume", response_model=ProductionVolumeResponse)
def get_production_volume(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsProductionService, Depends(get_analytics_production_service)],
) -> ProductionVolumeResponse:
    return service.get_production_volume(params)


@router.get("/production/batch-trends", response_model=BatchVolumeTrendsResponse)
def get_batch_volume_trends(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsProductionService, Depends(get_analytics_production_service)],
) -> BatchVolumeTrendsResponse:
    return service.get_batch_volume_trends(params)


@router.get("/production/ingredient-trends", response_model=IngredientDemandTrendsResponse)
def get_ingredient_demand_trends(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsProductionService, Depends(get_analytics_production_service)],
) -> IngredientDemandTrendsResponse:
    return service.get_ingredient_demand_trends(params)


@router.get("/production/packaging-trends", response_model=PackagingDemandTrendsResponse)
def get_packaging_demand_trends(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsProductionService, Depends(get_analytics_production_service)],
) -> PackagingDemandTrendsResponse:
    return service.get_packaging_demand_trends(params)


@router.get("/operations/kpis", response_model=OperationsAnalyticsKpiResponse)
def get_operations_analytics_kpis(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOperationsService, Depends(get_analytics_operations_service)],
) -> OperationsAnalyticsKpiResponse:
    return service.get_kpis(params)


@router.get("/operations/alerts", response_model=OperationsAlertsResponse)
def get_operations_analytics_alerts(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOperationsService, Depends(get_analytics_operations_service)],
) -> OperationsAlertsResponse:
    return service.get_alerts(params)


@router.get("/operations/upcoming-workload", response_model=OperationsUpcomingWorkloadResponse)
def get_operations_upcoming_workload(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOperationsService, Depends(get_analytics_operations_service)],
) -> OperationsUpcomingWorkloadResponse:
    return service.get_upcoming_workload(params)


@router.get("/operations/delivery-overview", response_model=OperationsDeliveryOverviewResponse)
def get_operations_delivery_overview(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOperationsService, Depends(get_analytics_operations_service)],
) -> OperationsDeliveryOverviewResponse:
    return service.get_delivery_overview(params)


@router.get("/operations/payment-overview", response_model=OperationsPaymentOverviewResponse)
def get_operations_payment_overview(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOperationsService, Depends(get_analytics_operations_service)],
) -> OperationsPaymentOverviewResponse:
    return service.get_payment_overview(params)


@router.get("/operations/business-health", response_model=OperationsBusinessHealthResponse)
def get_operations_business_health(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsOperationsService, Depends(get_analytics_operations_service)],
) -> OperationsBusinessHealthResponse:
    return service.get_business_health(params)


@router.get("/executive/kpis", response_model=ExecutiveOverviewKpisResponse)
def get_executive_kpis(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsExecutiveService, Depends(get_analytics_executive_service)],
) -> ExecutiveOverviewKpisResponse:
    return service.get_kpis(params)


@router.get("/executive/highlights", response_model=ExecutiveOverviewHighlightsResponse)
def get_executive_highlights(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsExecutiveService, Depends(get_analytics_executive_service)],
) -> ExecutiveOverviewHighlightsResponse:
    return service.get_highlights(params)


@router.get("/executive/revenue-contribution", response_model=ExecutiveRevenueContributionResponse)
def get_executive_revenue_contribution(
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsExecutiveService, Depends(get_analytics_executive_service)],
) -> ExecutiveRevenueContributionResponse:
    return service.get_revenue_contribution(params)


@router.get("/executive/operations-snapshot", response_model=ExecutiveOperationsSnapshotResponse)
def get_executive_operations_snapshot(
    service: Annotated[AnalyticsExecutiveService, Depends(get_analytics_executive_service)],
) -> ExecutiveOperationsSnapshotResponse:
    return service.get_operations_snapshot()


@router.get("/export/{scope}")
def export_analytics_scope_csv(
    scope: str,
    params: Annotated[AnalyticsQueryParams, Depends()],
    service: Annotated[AnalyticsExportService, Depends(get_analytics_export_service)],
) -> Response:
    filename, csv_content = service.build_csv(scope, params)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── Overhead Analytics ────────────────────────────────────────────────────────


@router.get("/overhead/kpis")
def get_overhead_kpis(
    year: Annotated[int, Query(ge=2020, le=2100)] = 2026,
    service: Annotated[OverheadAnalyticsService, Depends(get_overhead_analytics_service)] = ...,
    _: Annotated[object, Depends(require_super_admin)] = ...,
) -> dict:
    return service.get_kpis(year)


@router.get("/overhead/monthly-breakdown")
def get_overhead_monthly_breakdown(
    year: Annotated[int, Query(ge=2020, le=2100)] = 2026,
    service: Annotated[OverheadAnalyticsService, Depends(get_overhead_analytics_service)] = ...,
    _: Annotated[object, Depends(require_super_admin)] = ...,
) -> list[dict]:
    return service.get_monthly_breakdown(year)


@router.get("/overhead/category-breakdown")
def get_overhead_category_breakdown(
    year: Annotated[int, Query(ge=2020, le=2100)] = 2026,
    service: Annotated[OverheadAnalyticsService, Depends(get_overhead_analytics_service)] = ...,
    _: Annotated[object, Depends(require_super_admin)] = ...,
) -> list[dict]:
    return service.get_category_breakdown(year)


# ─── Discount Analytics ────────────────────────────────────────────────────────


@router.get("/discounts/kpis")
def get_discount_kpis(
    params: Annotated[AnalyticsQueryParams, Depends()],
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[object, Depends(require_super_admin)] = ...,
) -> dict:
    from app.services.analytics.analytics_discount_service import DiscountAnalyticsService
    return DiscountAnalyticsService(db).get_kpis(params)


@router.get("/discounts/monthly-trends")
def get_discount_monthly_trends(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[object, Depends(require_super_admin)] = ...,
) -> list[dict]:
    from app.services.analytics.analytics_discount_service import DiscountAnalyticsService
    return DiscountAnalyticsService(db).get_monthly_trends()


@router.get("/discounts/rule-performance")
def get_discount_rule_performance(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[object, Depends(require_super_admin)] = ...,
) -> list[dict]:
    from app.services.analytics.analytics_discount_service import DiscountAnalyticsService
    return DiscountAnalyticsService(db).get_rule_performance()
