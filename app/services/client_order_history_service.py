"""Customer-facing order history (no internal financial data)."""

import uuid
from decimal import Decimal

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import OrderStatus, OrderType
from app.core.exceptions import NotFoundError
from app.models.customer import Customer
from app.models.order import Order
from app.models.order_collection_line import OrderCollectionLine
from app.models.order_product_line import OrderProductLine
from app.repositories.order_repository import OrderRepository
from app.schemas.client_account import (
    ClientAccountOrderCollectionLine,
    ClientAccountOrderCookieLine,
    ClientAccountOrderDetailResponse,
    ClientAccountOrderProductLine,
    ClientAccountOrderSummary,
)
from app.schemas.pagination import PaginatedResponse


class ClientOrderHistoryService:
    """Authenticated customer order list and detail."""

    SORTABLE_COLUMNS = {
        "created_at": Order.created_at,
        "scheduled_delivery_date": Order.scheduled_delivery_date,
        "order_number": Order.order_number,
        "total": Order.total_revenue_snapshot,
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.orders = OrderRepository(db)

    def list_orders(
        self,
        customer: Customer,
        *,
        page: int,
        page_size: int,
        search: str | None,
        status: OrderStatus | None,
        order_type: OrderType | None,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[ClientAccountOrderSummary], int]:
        stmt = (
            select(Order)
            .options(selectinload(Order.delivery_area))
            .where(Order.customer_id == customer.id)
        )
        count_stmt = select(func.count()).select_from(Order).where(Order.customer_id == customer.id)

        if search:
            pattern = f"%{search.strip()}%"
            clause = or_(Order.order_number.ilike(pattern))
            stmt = stmt.where(clause)
            count_stmt = count_stmt.where(clause)
        if status:
            stmt = stmt.where(Order.status == status)
            count_stmt = count_stmt.where(Order.status == status)
        if order_type:
            stmt = stmt.where(Order.order_type == order_type)
            count_stmt = count_stmt.where(Order.order_type == order_type)

        total = int(self.db.scalar(count_stmt) or 0)
        sort_column = self.SORTABLE_COLUMNS.get(sort_by, Order.created_at)
        order = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        rows = list(
            self.db.scalars(
                stmt.order_by(order).offset((page - 1) * page_size).limit(page_size),
            ).all(),
        )

        return [self._to_summary(row) for row in rows], total

    def list_orders_paginated(
        self,
        customer: Customer,
        *,
        page: int,
        page_size: int,
        search: str | None,
        status: OrderStatus | None,
        order_type: OrderType | None,
        sort_by: str,
        sort_order: str,
    ) -> PaginatedResponse[ClientAccountOrderSummary]:
        items, total = self.list_orders(
            customer,
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            order_type=order_type,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=self.orders.total_pages(total, page_size),
        )

    def get_order_detail(
        self,
        customer: Customer,
        order_id: uuid.UUID,
    ) -> ClientAccountOrderDetailResponse:
        order = self.orders.get_by_id(order_id)
        if not order or order.customer_id != customer.id:
            raise NotFoundError("Order not found")

        collection_lines: list[ClientAccountOrderCollectionLine] = []
        for line in order.collection_lines:
            cookies = [
                ClientAccountOrderCookieLine(
                    product_id=selection.product_id,
                    product_name=selection.product_name_snapshot,
                    quantity=selection.quantity,
                )
                for selection in line.selections
            ]
            collection_lines.append(
                ClientAccountOrderCollectionLine(
                    collection_name=line.collection_name_snapshot,
                    quantity=line.quantity,
                    cookies=cookies,
                ),
            )

        product_lines = [
            ClientAccountOrderProductLine(
                product_id=line.product_id,
                product_name=line.product_name_snapshot,
                quantity=line.quantity,
            )
            for line in order.product_lines
        ]

        return ClientAccountOrderDetailResponse(
            id=order.id,
            order_number=order.order_number,
            order_type=order.order_type,
            status=order.status,
            event_name=order.event_name,
            payment_method=order.payment_method,
            delivery_area_name=self._delivery_area_display_name(order),
            scheduled_delivery_date=order.scheduled_delivery_date,
            created_at=order.created_at,
            products_subtotal=order.products_subtotal_snapshot,
            collections_subtotal=order.collections_subtotal_snapshot,
            delivery_fee=order.delivery_fee_snapshot,
            total=order.total_revenue_snapshot,
            delivery_address_line_1=order.delivery_address_line_1,
            delivery_address_line_2=order.delivery_address_line_2,
            delivery_city=order.delivery_city,
            delivery_postal_code=order.delivery_postal_code,
            delivery_landmark=order.delivery_landmark,
            delivery_latitude=order.delivery_latitude,
            delivery_longitude=order.delivery_longitude,
            collection_lines=collection_lines,
            product_lines=product_lines,
        )

    def _delivery_area_display_name(self, order: Order) -> str | None:
        if order.delivery_area and order.delivery_area.name:
            return order.delivery_area.name
        if order.delivery_city and order.delivery_city.strip():
            return order.delivery_city.strip()
        if order.delivery_area:
            return order.delivery_area.name
        return None

    def _to_summary(self, order: Order) -> ClientAccountOrderSummary:
        return ClientAccountOrderSummary(
            id=order.id,
            order_number=order.order_number,
            order_type=order.order_type,
            status=order.status,
            scheduled_delivery_date=order.scheduled_delivery_date,
            delivery_area_name=self._delivery_area_display_name(order),
            total=order.total_revenue_snapshot,
            created_at=order.created_at,
        )
