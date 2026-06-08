"""Operational dashboard schemas."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.core.enums import OrderStatus


class DashboardTodaySnapshotResponse(BaseModel):
    orders_today: int
    revenue_today: Decimal
    deliveries_today: int
    production_units_scheduled_today: Decimal


class DashboardUpcomingProductionResponse(BaseModel):
    has_upcoming_batch: bool = False
    delivery_date: date | None = None
    orders: int = 0
    collections: Decimal = Decimal("0")
    product_units: Decimal = Decimal("0")
    top_ingredients: list[str] = []


class DashboardUpcomingDeliveryRow(BaseModel):
    delivery_date: date
    order_count: int


class DashboardRecentOrderRow(BaseModel):
    order_id: UUID
    order_number: str
    customer_id: UUID
    customer_name: str
    delivery_date: date
    total_revenue_snapshot: Decimal
    status: OrderStatus


class DashboardOperationalAlert(BaseModel):
    id: str
    title: str
    message: str
    count: int


class DashboardOverviewResponse(BaseModel):
    today_snapshot: DashboardTodaySnapshotResponse
    upcoming_production: DashboardUpcomingProductionResponse
    upcoming_deliveries: list[DashboardUpcomingDeliveryRow]
    recent_orders: list[DashboardRecentOrderRow]
    operational_alerts: list[DashboardOperationalAlert]
