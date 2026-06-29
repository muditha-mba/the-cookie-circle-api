"""Operational dashboard service."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import OrderStatus
from app.models.order import Order
from app.repositories.analytics_repository import ANALYTICS_EXCLUDED, ORDER_ANALYTICS_EXCLUDED, AnalyticsRepository
from app.schemas.dashboard import (
    DashboardOperationalAlert,
    DashboardOverviewResponse,
    DashboardRecentOrderRow,
    DashboardTodaySnapshotResponse,
    DashboardUpcomingDeliveryRow,
    DashboardUpcomingProductionResponse,
)
from app.schemas.pagination import PaginationParams
from app.services.analytics.analytics_production_ux_service import AnalyticsProductionUxService
from app.services.order_service import OrderService
from app.services.production_planning_service import ProductionPlanningService

MONEY = Decimal("0.01")
QTY = Decimal("0.0001")


class DashboardService:
    """Operational dashboard composition from existing order/production services."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.analytics = AnalyticsRepository(db)
        self.production_ux = AnalyticsProductionUxService(db)
        self.orders = OrderService(db)
        self.production = ProductionPlanningService(db)

    def get_overview(self) -> DashboardOverviewResponse:
        today = datetime.now(timezone.utc).date()
        tomorrow = today + timedelta(days=1)

        today_snapshot = self._today_snapshot(today)
        upcoming_production = self._upcoming_production()
        upcoming_deliveries = self._upcoming_deliveries(today)
        recent_orders = self._recent_orders()
        alerts = self._alerts(today, tomorrow, upcoming_production)

        return DashboardOverviewResponse(
            today_snapshot=today_snapshot,
            upcoming_production=upcoming_production,
            upcoming_deliveries=upcoming_deliveries,
            recent_orders=recent_orders,
            operational_alerts=alerts,
        )

    def _today_snapshot(self, today) -> DashboardTodaySnapshotResponse:
        created_filter = (
            Order.created_at >= datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc),
            Order.created_at < datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc),
            Order.status.notin_(ORDER_ANALYTICS_EXCLUDED),
        )
        scheduled_filter = (
            Order.scheduled_delivery_date == today,
            Order.status.notin_(ANALYTICS_EXCLUDED),
        )

        orders_today_stmt = select(func.count(Order.id)).where(*created_filter)
        revenue_today_stmt = select(func.coalesce(func.sum(Order.total_revenue_snapshot), 0)).where(*created_filter)
        deliveries_today_stmt = select(func.count(Order.id)).where(*scheduled_filter)

        product_units = Decimal("0")
        if self.analytics.count_upcoming_delivery_orders(today):
            demand = self.production.get_product_demand(today)
            product_units = sum((line.quantity for line in demand.items), Decimal("0"))

        return DashboardTodaySnapshotResponse(
            orders_today=int(self.db.scalar(orders_today_stmt) or 0),
            revenue_today=Decimal(self.db.scalar(revenue_today_stmt) or 0).quantize(MONEY),
            deliveries_today=int(self.db.scalar(deliveries_today_stmt) or 0),
            production_units_scheduled_today=Decimal(product_units).quantize(QTY),
        )

    def _upcoming_production(self) -> DashboardUpcomingProductionResponse:
        upcoming = self.production_ux.get_upcoming_demand()
        if not upcoming.has_upcoming_batch:
            return DashboardUpcomingProductionResponse()
        return DashboardUpcomingProductionResponse(
            has_upcoming_batch=True,
            delivery_date=upcoming.delivery_date,
            orders=upcoming.order_count,
            collections=upcoming.collection_count,
            product_units=upcoming.product_count,
            top_ingredients=[
                f"{line.item_name} ({line.quantity.normalize()} {line.unit})"
                for line in upcoming.top_ingredients[:3]
            ],
        )

    def _upcoming_deliveries(self, today) -> list[DashboardUpcomingDeliveryRow]:
        rows = self.analytics.fetch_upcoming_delivery_schedule(today, limit=7)
        return [
            DashboardUpcomingDeliveryRow(delivery_date=delivery_date, order_count=order_count)
            for delivery_date, order_count in rows
        ]

    def _recent_orders(self) -> list[DashboardRecentOrderRow]:
        page = self.orders.list(
            PaginationParams(page=1, page_size=10, sort_by="created_at", sort_order="desc"),
        )
        return [
            DashboardRecentOrderRow(
                order_id=row.id,
                order_number=row.order_number,
                customer_id=row.customer_id,
                customer_name=row.customer_name,
                delivery_date=row.scheduled_delivery_date,
                total_revenue_snapshot=row.total_revenue_snapshot,
                status=row.status,
            )
            for row in page.items
        ]

    def _alerts(
        self,
        today,
        tomorrow,
        upcoming_production: DashboardUpcomingProductionResponse,
    ) -> list[DashboardOperationalAlert]:
        awaiting_confirmation = self.analytics.count_orders_by_status((OrderStatus.PENDING,))
        deliveries_tomorrow_stmt = select(func.count(Order.id)).where(
            Order.scheduled_delivery_date == tomorrow,
            Order.status.notin_(ANALYTICS_EXCLUDED),
        )
        deliveries_tomorrow = int(self.db.scalar(deliveries_tomorrow_stmt) or 0)

        alerts = [
            DashboardOperationalAlert(
                id="orders_awaiting_confirmation",
                title="Orders awaiting confirmation",
                message="Orders are pending and need confirmation.",
                count=awaiting_confirmation,
            ),
            DashboardOperationalAlert(
                id="deliveries_tomorrow",
                title="Deliveries tomorrow",
                message=f"Orders scheduled for {tomorrow.isoformat()}.",
                count=deliveries_tomorrow,
            ),
        ]
        if upcoming_production.has_upcoming_batch and upcoming_production.delivery_date:
            alerts.append(
                DashboardOperationalAlert(
                    id="upcoming_production_batch",
                    title="Upcoming production batch",
                    message=f"Next production batch on {upcoming_production.delivery_date.isoformat()}.",
                    count=upcoming_production.orders,
                ),
            )
        return alerts
