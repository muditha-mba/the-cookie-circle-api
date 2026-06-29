"""Analytics service layer."""

from app.services.analytics.analytics_collection_service import AnalyticsCollectionService
from app.services.analytics.analytics_customer_service import AnalyticsCustomerService
from app.services.analytics.analytics_kpi_service import AnalyticsKpiService
from app.services.analytics.analytics_order_service import AnalyticsOrderService
from app.services.analytics.analytics_product_service import AnalyticsProductService
from app.services.analytics.analytics_production_service import AnalyticsProductionService
from app.services.analytics.analytics_revenue_service import AnalyticsRevenueService

__all__ = [
    "AnalyticsCollectionService",
    "AnalyticsCustomerService",
    "AnalyticsKpiService",
    "AnalyticsOrderService",
    "AnalyticsProductService",
    "AnalyticsProductionService",
    "AnalyticsRevenueService",
]
