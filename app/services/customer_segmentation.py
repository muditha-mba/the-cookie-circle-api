"""Configurable customer segment calculation (analytics-ready)."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from app.core.enums import CustomerSegment, OrderStatus

CRM_EXCLUDED_ORDER_STATUSES = frozenset({OrderStatus.DRAFT, OrderStatus.CANCELLED})


@dataclass(frozen=True)
class CustomerSegmentationConfig:
    """Thresholds for system-calculated customer segments."""

    vip_lifetime_spend_threshold: Decimal = Decimal("50000.00")
    inactive_days: int = 90
    returning_min_orders: int = 2
    new_order_count: int = 1


@dataclass(frozen=True)
class CustomerOrderMetrics:
    """Order aggregates used for segmentation and insights."""

    total_orders: int
    lifetime_spend: Decimal
    last_order_date: date | None
    first_order_date: date | None
    customer_created_at: datetime


def calculate_customer_segment(
    metrics: CustomerOrderMetrics,
    *,
    config: CustomerSegmentationConfig | None = None,
    reference_date: date | None = None,
) -> CustomerSegment | None:
    """Derive the primary customer segment from order metrics."""
    cfg = config or CustomerSegmentationConfig()
    today = reference_date or datetime.now(timezone.utc).date()

    days_since_last_order = _days_since(metrics.last_order_date, today)
    days_since_created = _days_since(metrics.customer_created_at.date(), today)

    if metrics.total_orders == 0:
        if days_since_created >= cfg.inactive_days:
            return CustomerSegment.INACTIVE
        return None

    if days_since_last_order is not None and days_since_last_order >= cfg.inactive_days:
        return CustomerSegment.INACTIVE

    if metrics.lifetime_spend >= cfg.vip_lifetime_spend_threshold:
        return CustomerSegment.VIP

    if metrics.total_orders >= cfg.returning_min_orders:
        return CustomerSegment.RETURNING

    if metrics.total_orders == cfg.new_order_count:
        return CustomerSegment.NEW

    return None


def _days_since(value: date | None, today: date) -> int | None:
    if value is None:
        return None
    return (today - value).days
