"""Reusable CSV export generation for analytics datasets."""

import csv
import io
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.schemas.analytics import AnalyticsQueryParams
from app.services.analytics.analytics_collection_service import AnalyticsCollectionService
from app.services.analytics.analytics_customer_service import AnalyticsCustomerService
from app.services.analytics.analytics_order_service import AnalyticsOrderService
from app.services.analytics.analytics_product_service import AnalyticsProductService
from app.services.analytics.analytics_production_service import AnalyticsProductionService
from app.services.analytics.analytics_revenue_service import AnalyticsRevenueService


class AnalyticsExportService:
    """Exports analytics tabular datasets as CSV."""

    def __init__(self, db: Session) -> None:
        self.revenue = AnalyticsRevenueService(db)
        self.products = AnalyticsProductService(db)
        self.collections = AnalyticsCollectionService(db)
        self.customers = AnalyticsCustomerService(db)
        self.production = AnalyticsProductionService(db)
        self.orders = AnalyticsOrderService(db)

    def build_csv(self, scope: str, params: AnalyticsQueryParams) -> tuple[str, str]:
        rows = self._rows_for_scope(scope, params)
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()) if rows else ["message"])
        writer.writeheader()
        if rows:
            writer.writerows(rows)
        else:
            writer.writerow({"message": "No data"})
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"analytics-{scope}-{stamp}.csv", buffer.getvalue()

    def _rows_for_scope(self, scope: str, params: AnalyticsQueryParams) -> list[dict[str, object]]:
        if scope == "revenue":
            return [point.model_dump() for point in self.revenue.get_revenue_trends(params).points]
        if scope == "products":
            return [row.model_dump() for row in self.products.get_performance(params).items]
        if scope == "collections":
            return [row.model_dump() for row in self.collections.get_performance(params).items]
        if scope == "packages":
            return [row.model_dump() for row in self.collections.get_package_performance(params).items]
        if scope == "customers":
            return [row.model_dump() for row in self.customers.get_performance(params).items]
        if scope == "orders":
            return [row.model_dump() for row in self.orders.get_performance(params).items]
        if scope == "production-ingredients":
            return [row.model_dump() for row in self.production.get_ingredient_summary(params).items]
        if scope == "production-packaging":
            return [row.model_dump() for row in self.production.get_packaging_summary(params).items]
        return []
