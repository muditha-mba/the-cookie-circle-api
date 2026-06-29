"""Delivery area SQLAlchemy model."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.order import Order


class DeliveryArea(Base, TimestampMixin):
    """Geographic or operational delivery zone with optional fee override."""

    __tablename__ = "delivery_areas"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_fee_override: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    pickup_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="true")

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="delivery_area")
