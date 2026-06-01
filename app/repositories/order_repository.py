"""Order data access repository."""

import uuid
from math import ceil

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.collection import Collection
from app.models.customer import Customer
from app.models.order import Order
from app.models.order_collection_line import OrderCollectionLine
from app.models.order_product_line import OrderProductLine
from app.models.order_status_event import OrderStatusEvent


class OrderRepository:
    """Repository for order persistence."""

    SORTABLE_COLUMNS = {
        "order_number": Order.order_number,
        "requested_delivery_date": Order.requested_delivery_date,
        "scheduled_delivery_date": Order.scheduled_delivery_date,
        "created_at": Order.created_at,
        "total_revenue_snapshot": Order.total_revenue_snapshot,
        "total_profit_snapshot": Order.total_profit_snapshot,
        "revenue": Order.total_revenue_snapshot,
        "profit": Order.total_profit_snapshot,
        "status": Order.status,
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def _detail_options(self):
        return (
            selectinload(Order.customer).joinedload(Customer.user),
            selectinload(Order.delivery_area),
            selectinload(Order.product_lines).joinedload(OrderProductLine.product),
            selectinload(Order.collection_lines).joinedload(OrderCollectionLine.collection),
            selectinload(Order.status_events),
        )

    def get_by_id(self, order_id: uuid.UUID) -> Order | None:
        stmt = select(Order).options(*self._detail_options()).where(Order.id == order_id)
        return self.db.scalar(stmt)

    def create(self, order: Order) -> Order:
        self.db.add(order)
        self.db.flush()
        return self.get_by_id(order.id)  # type: ignore[return-value]

    def delete(self, order: Order) -> None:
        self.db.delete(order)

    def count_orders_for_prefix(self, prefix: str) -> int:
        stmt = select(func.count()).select_from(Order).where(Order.order_number.like(f"{prefix}%"))
        return int(self.db.scalar(stmt) or 0)

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[Order], int]:
        stmt = select(Order).options(selectinload(Order.customer))
        count_stmt = select(func.count()).select_from(Order)

        if search:
            pattern = f"%{search.strip()}%"
            filter_clause = or_(
                Order.order_number.ilike(pattern),
                Order.customer_notes.ilike(pattern),
                Order.internal_notes.ilike(pattern),
                Order.delivery_contact_name.ilike(pattern),
            )
            stmt = stmt.where(filter_clause)
            count_stmt = count_stmt.where(filter_clause)

        total = int(self.db.scalar(count_stmt) or 0)
        sort_column = self.SORTABLE_COLUMNS.get(sort_by, Order.created_at)
        order = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        stmt = stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)

        return list(self.db.scalars(stmt).unique().all()), total

    def fetch_top_profitable_orders(self, *, limit: int) -> list[Order]:
        stmt = (
            select(Order)
            .order_by(desc(Order.total_profit_snapshot))
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def fetch_most_profitable_products_sold(self, *, limit: int) -> list[dict[str, object]]:
        revenue = func.sum(
            OrderProductLine.product_selling_price_snapshot * OrderProductLine.quantity,
        ).label("revenue_snapshot")
        cost = func.sum(
            OrderProductLine.product_cost_snapshot * OrderProductLine.quantity,
        ).label("cost_snapshot")
        profit = func.sum(
            OrderProductLine.product_profit_snapshot * OrderProductLine.quantity,
        ).label("profit_snapshot")
        units = func.sum(OrderProductLine.quantity).label("units_sold")

        stmt = (
            select(
                OrderProductLine.product_id,
                OrderProductLine.product_name_snapshot,
                units,
                revenue,
                cost,
                profit,
            )
            .group_by(
                OrderProductLine.product_id,
                OrderProductLine.product_name_snapshot,
            )
            .order_by(desc(profit))
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "product_id": row.product_id,
                "product_name_snapshot": row.product_name_snapshot,
                "units_sold": row.units_sold,
                "revenue_snapshot": row.revenue_snapshot,
                "cost_snapshot": row.cost_snapshot,
                "profit_snapshot": row.profit_snapshot,
            }
            for row in rows
        ]

    def fetch_most_profitable_collections_sold(self, *, limit: int) -> list[dict[str, object]]:
        revenue = func.sum(
            OrderCollectionLine.collection_selling_price_snapshot * OrderCollectionLine.quantity,
        ).label("revenue_snapshot")
        cost = func.sum(
            OrderCollectionLine.collection_cost_snapshot * OrderCollectionLine.quantity,
        ).label("cost_snapshot")
        profit = func.sum(
            OrderCollectionLine.collection_profit_snapshot * OrderCollectionLine.quantity,
        ).label("profit_snapshot")
        units = func.sum(OrderCollectionLine.quantity).label("units_sold")

        stmt = (
            select(
                OrderCollectionLine.collection_id,
                OrderCollectionLine.collection_name_snapshot,
                units,
                revenue,
                cost,
                profit,
            )
            .group_by(
                OrderCollectionLine.collection_id,
                OrderCollectionLine.collection_name_snapshot,
            )
            .order_by(desc(profit))
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "collection_id": row.collection_id,
                "collection_name_snapshot": row.collection_name_snapshot,
                "units_sold": row.units_sold,
                "revenue_snapshot": row.revenue_snapshot,
                "cost_snapshot": row.cost_snapshot,
                "profit_snapshot": row.profit_snapshot,
            }
            for row in rows
        ]

    def get_collections_by_ids(self, ids: list[uuid.UUID]) -> list[Collection]:
        if not ids:
            return []
        stmt = select(Collection).where(Collection.id.in_(ids))
        return list(self.db.scalars(stmt).all())

    @staticmethod
    def total_pages(total: int, page_size: int) -> int:
        if total == 0:
            return 0
        return ceil(total / page_size)
