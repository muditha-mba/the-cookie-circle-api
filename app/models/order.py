"""Order SQLAlchemy model."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import OrderSource, OrderStatus, PaymentMethod, PaymentStatus
from app.database.base import Base
from app.models.enum_columns import (
    order_source_enum,
    order_status_enum,
    payment_method_enum,
    payment_status_enum,
)
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.delivery_area import DeliveryArea
    from app.models.order_collection_line import OrderCollectionLine
    from app.models.order_product_line import OrderProductLine
    from app.models.order_status_event import OrderStatusEvent


class Order(Base, TimestampMixin):
    """Customer order with immutable financial snapshots captured at placement."""

    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    delivery_area_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("delivery_areas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source: Mapped[OrderSource] = mapped_column(order_source_enum, nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(payment_method_enum, nullable=False)
    payment_status: Mapped[PaymentStatus] = mapped_column(
        payment_status_enum,
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    status: Mapped[OrderStatus] = mapped_column(
        order_status_enum,
        nullable=False,
        default=OrderStatus.PENDING,
    )
    customer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_delivery_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    scheduled_delivery_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    delivery_contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    delivery_phone_primary: Mapped[str | None] = mapped_column(String(50), nullable=True)
    delivery_phone_secondary: Mapped[str | None] = mapped_column(String(50), nullable=True)
    delivery_address_line_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    delivery_postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    delivery_landmark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    delivery_longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    products_subtotal_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default="0",
    )
    collections_subtotal_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default="0",
    )
    delivery_fee_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_revenue_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_cost_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_profit_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    margin_percentage_snapshot: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    preparing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    delivery_area: Mapped["DeliveryArea | None"] = relationship("DeliveryArea", back_populates="orders")
    product_lines: Mapped[list["OrderProductLine"]] = relationship(
        "OrderProductLine",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderProductLine.created_at",
    )
    collection_lines: Mapped[list["OrderCollectionLine"]] = relationship(
        "OrderCollectionLine",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderCollectionLine.created_at",
    )
    status_events: Mapped[list["OrderStatusEvent"]] = relationship(
        "OrderStatusEvent",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusEvent.created_at",
    )
