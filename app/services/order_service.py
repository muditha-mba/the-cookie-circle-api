"""Order business logic."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import OrderStatus
from app.core.exceptions import NotFoundError, ValidationError
from app.models.delivery_area import DeliveryArea
from app.models.order import Order
from app.models.order_collection_line import OrderCollectionLine
from app.models.order_product_line import OrderProductLine
from app.models.order_status_event import OrderStatusEvent
from app.repositories.customer_repository import CustomerRepository
from app.repositories.delivery_area_repository import DeliveryAreaRepository
from app.repositories.order_repository import OrderRepository
from app.schemas.delivery_area import DeliveryAreaSummary
from app.schemas.order import (
    OrderCollectionLineInput,
    OrderCollectionLineResponse,
    OrderCreate,
    OrderCustomerSummary,
    OrderDetailResponse,
    OrderFinancialPerformance,
    OrderLifecycleTimestamps,
    OrderPreviewRequest,
    OrderPreviewResponse,
    OrderProductLineInput,
    OrderProductLineResponse,
    OrderStatusEventResponse,
    OrderSummaryResponse,
    OrderUpdate,
)
from app.schemas.order_profitability import TopProfitableOrderRow
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.business_setting_service import BusinessSettingService
from app.services.delivery_fee_service import resolve_delivery_fee
from app.services.delivery_schedule_service import DeliveryScheduleService
from app.services.order_profitability_service import OrderProfitabilityService
from app.services.product_cost_service import _money

_STATUS_TIMESTAMP_FIELDS: dict[OrderStatus, str] = {
    OrderStatus.CONFIRMED: "confirmed_at",
    OrderStatus.PREPARING: "preparing_at",
    OrderStatus.READY: "ready_at",
    OrderStatus.DELIVERED: "delivered_at",
    OrderStatus.CANCELLED: "cancelled_at",
}


class OrderService:
    """Handles order CRUD; profitability snapshots via OrderProfitabilityService."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.customers = CustomerRepository(db)
        self.delivery_areas = DeliveryAreaRepository(db)
        self.business_settings = BusinessSettingService(db)
        self.profitability = OrderProfitabilityService(db)

    def create(self, payload: OrderCreate) -> OrderDetailResponse:
        customer = self.customers.get_by_id(payload.customer_id)
        if not customer:
            raise NotFoundError("Customer not found")
        if not customer.is_active:
            raise ValidationError("Customer is inactive")

        settings = self.business_settings.get_settings()
        delivery_area = self._get_delivery_area(payload.delivery_area_id)
        delivery_fee = resolve_delivery_fee(settings, delivery_area)
        scheduled_delivery_date = DeliveryScheduleService.calculate_delivery_date(
            order_date=date.today(),
            cutoff_day=settings.order_cutoff_day,
            delivery_day=settings.delivery_day,
        )

        snapshot_result = self.profitability.build_order_snapshots(
            product_lines=payload.product_lines,
            collection_lines=payload.collection_lines,
            delivery_fee=delivery_fee,
        )

        order = Order(
            order_number=self._generate_order_number(),
            customer_id=customer.id,
            delivery_area_id=delivery_area.id if delivery_area else None,
            source=payload.source,
            payment_method=payload.payment_method,
            payment_status=payload.payment_status,
            status=payload.status,
            customer_notes=payload.customer_notes,
            internal_notes=payload.internal_notes,
            requested_delivery_date=payload.requested_delivery_date,
            scheduled_delivery_date=scheduled_delivery_date,
            **self._delivery_field_values(payload),
        )
        self.profitability.apply_snapshots_to_order(order, snapshot_result)
        order.product_lines = snapshot_result.product_lines
        order.collection_lines = snapshot_result.collection_lines
        order.status_events = [OrderStatusEvent(status=payload.status)]
        self._apply_lifecycle_timestamp(order, payload.status)

        self.orders.create(order)
        self.db.commit()
        loaded = self.orders.get_by_id(order.id)
        assert loaded is not None
        return self._to_detail(loaded)

    def get(self, order_id: uuid.UUID) -> OrderDetailResponse:
        order = self.orders.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")
        return self._to_detail(order)

    def list(self, params: PaginationParams) -> PaginatedResponse[OrderSummaryResponse]:
        items, total = self.orders.list_paginated(
            page=params.page,
            page_size=params.page_size,
            search=params.search,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        summaries = [
            OrderSummaryResponse(
                id=order.id,
                order_number=order.order_number,
                customer_id=order.customer_id,
                customer_name=f"{order.customer.first_name} {order.customer.last_name}",
                source=order.source,
                payment_method=order.payment_method,
                payment_status=order.payment_status,
                status=order.status,
                requested_delivery_date=order.requested_delivery_date,
                scheduled_delivery_date=order.scheduled_delivery_date,
                total_revenue_snapshot=order.total_revenue_snapshot,
                total_profit_snapshot=order.total_profit_snapshot,
                created_at=order.created_at,
            )
            for order in items
        ]
        return PaginatedResponse(
            items=summaries,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=self.orders.total_pages(total, params.page_size),
        )

    def update(self, order_id: uuid.UUID, payload: OrderUpdate) -> OrderDetailResponse:
        order = self.orders.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")

        if not payload.model_dump(exclude_unset=True):
            raise ValidationError("No fields provided to update")

        previous_status = order.status
        settings = self.business_settings.get_settings()
        delivery_area_changed = "delivery_area_id" in payload.model_fields_set

        if delivery_area_changed:
            delivery_area = self._get_delivery_area(payload.delivery_area_id)
            order.delivery_area_id = delivery_area.id if delivery_area else None
            if payload.product_lines is None and payload.collection_lines is None:
                fee = resolve_delivery_fee(settings, delivery_area)
                self.profitability.apply_delivery_fee_snapshot(order, fee)

        if payload.source is not None:
            order.source = payload.source
        if payload.payment_method is not None:
            order.payment_method = payload.payment_method
        if payload.payment_status is not None:
            order.payment_status = payload.payment_status
        if payload.customer_notes is not None:
            order.customer_notes = payload.customer_notes
        if payload.internal_notes is not None:
            order.internal_notes = payload.internal_notes
        if payload.requested_delivery_date is not None:
            order.requested_delivery_date = payload.requested_delivery_date
        if payload.scheduled_delivery_date is not None:
            order.scheduled_delivery_date = payload.scheduled_delivery_date

        for key, value in self._delivery_field_values(payload).items():
            setattr(order, key, value)

        lines_updated = payload.product_lines is not None or payload.collection_lines is not None
        if lines_updated:
            product_inputs = (
                payload.product_lines
                if payload.product_lines is not None
                else [
                    OrderProductLineInput(product_id=line.product_id, quantity=line.quantity)
                    for line in order.product_lines
                ]
            )
            collection_inputs = (
                payload.collection_lines
                if payload.collection_lines is not None
                else [
                    OrderCollectionLineInput(collection_id=line.collection_id, quantity=line.quantity)
                    for line in order.collection_lines
                ]
            )

            delivery_area = None
            if order.delivery_area_id:
                delivery_area = self.delivery_areas.get_by_id(order.delivery_area_id)
            delivery_fee = order.delivery_fee_snapshot
            if delivery_area_changed:
                delivery_fee = resolve_delivery_fee(settings, delivery_area)

            snapshot_result = self.profitability.build_order_snapshots(
                product_lines=product_inputs,
                collection_lines=collection_inputs,
                delivery_fee=delivery_fee,
            )
            order.product_lines.clear()
            order.collection_lines.clear()
            self.db.flush()
            order.product_lines = snapshot_result.product_lines
            order.collection_lines = snapshot_result.collection_lines
            self.profitability.apply_snapshots_to_order(order, snapshot_result)

        if payload.status is not None:
            order.status = payload.status

        if payload.status is not None and payload.status != previous_status:
            order.status_events.append(OrderStatusEvent(status=payload.status))
            self._apply_lifecycle_timestamp(order, payload.status)

        self.db.add(order)
        self.db.commit()
        loaded = self.orders.get_by_id(order.id)
        assert loaded is not None
        return self._to_detail(loaded)

    def delete(self, order_id: uuid.UUID) -> None:
        order = self.orders.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")
        self.orders.delete(order)
        self.db.commit()

    def preview(self, payload: OrderPreviewRequest) -> OrderPreviewResponse:
        settings = self.business_settings.get_settings()
        delivery_area = self._get_delivery_area(payload.delivery_area_id)
        delivery_fee = resolve_delivery_fee(settings, delivery_area)
        snapshot_result = self.profitability.build_order_snapshots(
            product_lines=payload.product_lines,
            collection_lines=payload.collection_lines,
            delivery_fee=delivery_fee,
        )
        financials = snapshot_result.financials
        return OrderPreviewResponse(
            products_subtotal_snapshot=financials.products_subtotal_snapshot,
            collections_subtotal_snapshot=financials.collections_subtotal_snapshot,
            delivery_fee_snapshot=financials.delivery_fee_snapshot,
            total_revenue_snapshot=financials.total_revenue_snapshot,
            total_cost_snapshot=financials.total_cost_snapshot,
            total_profit_snapshot=financials.total_profit_snapshot,
            margin_percentage_snapshot=financials.margin_percentage_snapshot,
            product_lines=[
                self._product_line_to_response(line) for line in snapshot_result.product_lines
            ],
            collection_lines=[
                self._collection_line_to_response(line) for line in snapshot_result.collection_lines
            ],
        )

    def get_top_profitable_orders(self, *, limit: int = 10) -> list[TopProfitableOrderRow]:
        return self.profitability.get_top_profitable_orders(limit=limit)

    def _get_delivery_area(self, area_id: uuid.UUID | None) -> DeliveryArea | None:
        if area_id is None:
            return None
        area = self.delivery_areas.get_by_id(area_id)
        if not area:
            raise NotFoundError("Delivery area not found")
        if not area.is_active:
            raise ValidationError("Delivery area is inactive")
        return area

    @staticmethod
    def _apply_lifecycle_timestamp(order: Order, status: OrderStatus) -> None:
        field = _STATUS_TIMESTAMP_FIELDS.get(status)
        if field and getattr(order, field) is None:
            setattr(order, field, datetime.now(UTC))

    @staticmethod
    def _delivery_field_values(payload: OrderCreate | OrderUpdate) -> dict[str, object]:
        keys = (
            "delivery_contact_name",
            "delivery_phone_primary",
            "delivery_phone_secondary",
            "delivery_address_line_1",
            "delivery_address_line_2",
            "delivery_city",
            "delivery_postal_code",
            "delivery_landmark",
            "delivery_notes",
            "delivery_latitude",
            "delivery_longitude",
        )
        if isinstance(payload, OrderUpdate):
            return {k: getattr(payload, k) for k in keys if k in payload.model_fields_set}
        return {k: getattr(payload, k) for k in keys}

    def _generate_order_number(self) -> str:
        today = date.today().strftime("%Y%m%d")
        prefix = f"ORD-{today}-"
        count = self.orders.count_orders_for_prefix(prefix) + 1
        return f"{prefix}{count:04d}"

    @staticmethod
    def _product_line_to_response(line: OrderProductLine) -> OrderProductLineResponse:
        return OrderProductLineResponse(
            id=line.id or uuid.uuid4(),
            product_id=line.product_id,
            quantity=line.quantity,
            product_name_snapshot=line.product_name_snapshot,
            product_selling_price_snapshot=line.product_selling_price_snapshot,
            product_cost_snapshot=line.product_cost_snapshot,
            product_profit_snapshot=line.product_profit_snapshot,
            line_revenue_snapshot=_money(line.product_selling_price_snapshot * line.quantity),
            line_cost_snapshot=_money(line.product_cost_snapshot * line.quantity),
            line_profit_snapshot=_money(line.product_profit_snapshot * line.quantity),
        )

    @staticmethod
    def _collection_line_to_response(line: OrderCollectionLine) -> OrderCollectionLineResponse:
        return OrderCollectionLineResponse(
            id=line.id or uuid.uuid4(),
            collection_id=line.collection_id,
            quantity=line.quantity,
            collection_name_snapshot=line.collection_name_snapshot,
            collection_selling_price_snapshot=line.collection_selling_price_snapshot,
            collection_cost_snapshot=line.collection_cost_snapshot,
            collection_profit_snapshot=line.collection_profit_snapshot,
            line_revenue_snapshot=_money(line.collection_selling_price_snapshot * line.quantity),
            line_cost_snapshot=_money(line.collection_cost_snapshot * line.quantity),
            line_profit_snapshot=_money(line.collection_profit_snapshot * line.quantity),
        )

    def _to_detail(self, order: Order) -> OrderDetailResponse:
        customer = order.customer
        delivery_area = order.delivery_area
        return OrderDetailResponse(
            id=order.id,
            order_number=order.order_number,
            customer=OrderCustomerSummary(
                id=customer.id,
                first_name=customer.first_name,
                last_name=customer.last_name,
                email=customer.email,
                phone=customer.phone,
                address_line_1=customer.address_line_1,
                address_line_2=customer.address_line_2,
                city=customer.city,
                postal_code=customer.postal_code,
                landmark=customer.landmark,
            ),
            delivery_area=(
                DeliveryAreaSummary.model_validate(delivery_area) if delivery_area else None
            ),
            source=order.source,
            payment_method=order.payment_method,
            payment_status=order.payment_status,
            status=order.status,
            customer_notes=order.customer_notes,
            internal_notes=order.internal_notes,
            requested_delivery_date=order.requested_delivery_date,
            scheduled_delivery_date=order.scheduled_delivery_date,
            delivery_contact_name=order.delivery_contact_name,
            delivery_phone_primary=order.delivery_phone_primary,
            delivery_phone_secondary=order.delivery_phone_secondary,
            delivery_address_line_1=order.delivery_address_line_1,
            delivery_address_line_2=order.delivery_address_line_2,
            delivery_city=order.delivery_city,
            delivery_postal_code=order.delivery_postal_code,
            delivery_landmark=order.delivery_landmark,
            delivery_notes=order.delivery_notes,
            delivery_latitude=order.delivery_latitude,
            delivery_longitude=order.delivery_longitude,
            financial_performance=OrderFinancialPerformance(
                snapshot=self.profitability.financial_snapshot_from_order(order),
                is_historical_snapshot=True,
            ),
            product_lines=[self._product_line_to_response(line) for line in order.product_lines],
            collection_lines=[
                self._collection_line_to_response(line) for line in order.collection_lines
            ],
            status_timeline=[
                OrderStatusEventResponse.model_validate(event) for event in order.status_events
            ],
            lifecycle=OrderLifecycleTimestamps(
                confirmed_at=order.confirmed_at,
                preparing_at=order.preparing_at,
                ready_at=order.ready_at,
                delivered_at=order.delivered_at,
                cancelled_at=order.cancelled_at,
            ),
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
