"""Customer insights and list aggregation queries."""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from math import ceil

from sqlalchemy import asc, case, desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.enums import CustomerSegment, MarketingSource, OrderStatus
from app.models.customer import Customer
from app.models.order import Order
from app.models.order_collection_line import OrderCollectionLine
from app.models.order_product_line import OrderProductLine
from app.services.customer_segmentation import (
    CRM_EXCLUDED_ORDER_STATUSES,
    CustomerOrderMetrics,
    CustomerSegmentationConfig,
)
from app.utils.search import ilike_contains

MONEY_PRECISION = Decimal("0.01")


@dataclass(frozen=True)
class CustomerListRow:
    """Customer with calculated CRM metrics for list views."""

    customer: Customer
    total_orders: int
    lifetime_spend: Decimal
    last_order_date: date | None
    first_order_date: date | None
    segment: CustomerSegment | None


class CustomerInsightsRepository:
    """Read-only aggregations for customer relationship data."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _excluded_statuses(self) -> list[str]:
        return [status.value for status in CRM_EXCLUDED_ORDER_STATUSES]

    def _order_stats_subquery(self):
        return (
            select(
                Order.customer_id.label("customer_id"),
                func.count(Order.id).label("total_orders"),
                func.coalesce(func.sum(Order.total_revenue_snapshot), 0).label("lifetime_spend"),
                func.max(Order.scheduled_delivery_date).label("last_order_date"),
                func.min(Order.created_at).label("first_order_at"),
            )
            .where(Order.status.notin_(self._excluded_statuses()))
            .group_by(Order.customer_id)
            .subquery()
        )

    def _segment_expression(
        self,
        stats,
        customer_created_at_col,
        config: CustomerSegmentationConfig,
    ):
        total_orders = func.coalesce(stats.c.total_orders, 0)
        lifetime_spend = func.coalesce(stats.c.lifetime_spend, 0)
        last_order_date = stats.c.last_order_date
        days_since_created = func.current_date() - func.date(customer_created_at_col)
        days_since_last_order = func.current_date() - last_order_date

        return case(
            (
                (total_orders == 0) & (days_since_created >= config.inactive_days),
                CustomerSegment.INACTIVE.value,
            ),
            (
                (total_orders > 0)
                & (last_order_date.isnot(None))
                & (days_since_last_order >= config.inactive_days),
                CustomerSegment.INACTIVE.value,
            ),
            (
                lifetime_spend >= config.vip_lifetime_spend_threshold,
                CustomerSegment.VIP.value,
            ),
            (
                total_orders >= config.returning_min_orders,
                CustomerSegment.RETURNING.value,
            ),
            (
                total_orders == config.new_order_count,
                CustomerSegment.NEW.value,
            ),
            else_=None,
        )

    def get_metrics_for_customer(self, customer: Customer) -> CustomerOrderMetrics:
        stmt = select(
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_revenue_snapshot), 0),
            func.max(Order.scheduled_delivery_date),
            func.min(Order.created_at),
        ).where(
            Order.customer_id == customer.id,
            Order.status.notin_(self._excluded_statuses()),
        )
        row = self.db.execute(stmt).one()
        first_order_at = row[3]
        return CustomerOrderMetrics(
            total_orders=int(row[0] or 0),
            lifetime_spend=Decimal(row[1] or 0).quantize(MONEY_PRECISION),
            last_order_date=row[2],
            first_order_date=first_order_at.date() if first_order_at else None,
            customer_created_at=customer.created_at,
        )

    def get_favourite_product_name(self, customer_id: uuid.UUID) -> str | None:
        stmt = (
            select(
                OrderProductLine.product_name_snapshot,
                func.sum(OrderProductLine.quantity).label("qty"),
            )
            .join(Order, OrderProductLine.order_id == Order.id)
            .where(
                Order.customer_id == customer_id,
                Order.status.notin_(self._excluded_statuses()),
            )
            .group_by(OrderProductLine.product_name_snapshot)
            .order_by(desc("qty"))
            .limit(1)
        )
        row = self.db.execute(stmt).first()
        return row[0] if row else None

    def get_favourite_collection_name(self, customer_id: uuid.UUID) -> str | None:
        stmt = (
            select(
                OrderCollectionLine.collection_name_snapshot,
                func.sum(OrderCollectionLine.quantity).label("qty"),
            )
            .join(Order, OrderCollectionLine.order_id == Order.id)
            .where(
                Order.customer_id == customer_id,
                Order.status.notin_(self._excluded_statuses()),
            )
            .group_by(OrderCollectionLine.collection_name_snapshot)
            .order_by(desc("qty"))
            .limit(1)
        )
        row = self.db.execute(stmt).first()
        return row[0] if row else None

    def list_orders_for_customer(
        self,
        customer_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[Order]:
        stmt = (
            select(Order)
            .where(
                Order.customer_id == customer_id,
                Order.status.notin_(self._excluded_statuses()),
            )
            .order_by(Order.scheduled_delivery_date.desc(), Order.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def list_customers_with_metrics(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_order: str,
        segment: CustomerSegment | None,
        marketing_source: MarketingSource | None,
        min_order_count: int | None,
        max_order_count: int | None,
        min_lifetime_spend: Decimal | None,
        max_lifetime_spend: Decimal | None,
        config: CustomerSegmentationConfig,
    ) -> tuple[list[CustomerListRow], int]:
        stats = self._order_stats_subquery()
        segment_expr = self._segment_expression(stats, Customer.created_at, config)

        stmt = select(
            Customer,
            func.coalesce(stats.c.total_orders, 0),
            func.coalesce(stats.c.lifetime_spend, 0),
            stats.c.last_order_date,
            stats.c.first_order_at,
            segment_expr.label("segment"),
        ).outerjoin(stats, Customer.id == stats.c.customer_id)

        count_stmt = select(func.count()).select_from(Customer).outerjoin(
            stats,
            Customer.id == stats.c.customer_id,
        )

        filters = []
        if search:
            pattern, escape = ilike_contains(search)
            filters.append(
                or_(
                    Customer.first_name.ilike(pattern, escape=escape),
                    Customer.last_name.ilike(pattern, escape=escape),
                    Customer.email.ilike(pattern, escape=escape),
                    Customer.phone.ilike(pattern, escape=escape),
                ),
            )
        if marketing_source is not None:
            filters.append(Customer.marketing_source == marketing_source)
        if min_order_count is not None:
            filters.append(func.coalesce(stats.c.total_orders, 0) >= min_order_count)
        if max_order_count is not None:
            filters.append(func.coalesce(stats.c.total_orders, 0) <= max_order_count)
        if min_lifetime_spend is not None:
            filters.append(func.coalesce(stats.c.lifetime_spend, 0) >= min_lifetime_spend)
        if max_lifetime_spend is not None:
            filters.append(func.coalesce(stats.c.lifetime_spend, 0) <= max_lifetime_spend)
        if segment is not None:
            filters.append(segment_expr == segment.value)

        for filter_clause in filters:
            stmt = stmt.where(filter_clause)
            count_stmt = count_stmt.where(filter_clause)

        total = int(self.db.scalar(count_stmt) or 0)

        sort_map = {
            "first_name": Customer.first_name,
            "last_name": Customer.last_name,
            "email": Customer.email,
            "created_at": Customer.created_at,
            "is_active": Customer.is_active,
            "lifetime_spend": func.coalesce(stats.c.lifetime_spend, 0),
            "order_count": func.coalesce(stats.c.total_orders, 0),
            "last_order_date": stats.c.last_order_date,
        }
        sort_column = sort_map.get(sort_by, Customer.created_at)
        order = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        stmt = stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)

        rows = self.db.execute(stmt).all()
        result_rows: list[CustomerListRow] = []
        for row in rows:
            customer = row[0]
            total_orders = int(row[1] or 0)
            lifetime_spend = Decimal(row[2] or 0).quantize(MONEY_PRECISION)
            last_order_date = row[3]
            first_order_at = row[4]
            segment_value = row[5]
            calculated_segment = (
                CustomerSegment(segment_value) if segment_value else None
            )
            result_rows.append(
                CustomerListRow(
                    customer=customer,
                    total_orders=total_orders,
                    lifetime_spend=lifetime_spend,
                    last_order_date=last_order_date,
                    first_order_date=first_order_at.date() if first_order_at else None,
                    segment=calculated_segment,
                ),
            )

        return result_rows, total

    @staticmethod
    def total_pages(total: int, page_size: int) -> int:
        if total == 0:
            return 0
        return ceil(total / page_size)