"""Production analytics UX helpers — delegates to ProductionPlanningService only."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsQueryParams,
    ProductionDemandPreviewLine,
    ProductionOutOfRangeHintResponse,
    UpcomingProductionDemandResponse,
)
from app.services.analytics.analytics_production_date_range import (
    resolve_production_analytics_date_range,
)
from app.services.production_planning_service import ProductionPlanningService

PREVIEW_LIMIT = 5
QTY = Decimal("0.0001")


class AnalyticsProductionUxService:
    """Read-only production analytics UX data without changing aggregation logic."""

    def __init__(self, db: Session) -> None:
        self.repo = AnalyticsRepository(db)
        self.production = ProductionPlanningService(db)

    def get_upcoming_demand(self) -> UpcomingProductionDemandResponse:
        today = datetime.now(timezone.utc).date()
        delivery_date = self.repo.fetch_next_delivery_date_on_or_after(today)
        if delivery_date is None:
            return UpcomingProductionDemandResponse()

        return self._build_upcoming_response(delivery_date)

    def get_out_of_range_hint(
        self,
        params: AnalyticsQueryParams,
    ) -> ProductionOutOfRangeHintResponse:
        date_range = resolve_production_analytics_date_range(self.repo, params)
        next_date = self.repo.fetch_next_delivery_date_after(date_range.end_date)
        if next_date is None:
            return ProductionOutOfRangeHintResponse()

        summary = self.production.get_order_summary(next_date)
        return ProductionOutOfRangeHintResponse(
            has_upcoming_outside_range=True,
            delivery_date=next_date,
            order_count=summary.total_orders,
            collection_count=summary.total_collections_ordered.quantize(QTY),
            product_count=summary.total_products_ordered.quantize(QTY),
        )

    def _build_upcoming_response(
        self,
        delivery_date,
    ) -> UpcomingProductionDemandResponse:
        summary = self.production.get_order_summary(delivery_date)
        product_demand = self.production.get_product_demand(delivery_date)
        product_count = sum(
            (line.quantity for line in product_demand.items),
            Decimal("0"),
        )

        ingredient_lines = sorted(
            self.production.get_ingredient_demand(delivery_date),
            key=lambda line: line.quantity,
            reverse=True,
        )[:PREVIEW_LIMIT]
        packaging_lines = sorted(
            self.production.get_packaging_demand(delivery_date),
            key=lambda line: line.quantity,
            reverse=True,
        )[:PREVIEW_LIMIT]

        return UpcomingProductionDemandResponse(
            has_upcoming_batch=True,
            delivery_date=delivery_date,
            order_count=summary.total_orders,
            collection_count=summary.total_collections_ordered.quantize(QTY),
            product_count=product_count.quantize(QTY),
            top_ingredients=[
                ProductionDemandPreviewLine(
                    item_name=line.product_item_name,
                    quantity=line.quantity.quantize(QTY),
                    unit=line.unit,
                )
                for line in ingredient_lines
            ],
            top_packaging=[
                ProductionDemandPreviewLine(
                    item_name=line.product_item_name,
                    quantity=line.quantity.quantize(QTY),
                    unit=line.unit,
                )
                for line in packaging_lines
            ],
        )
