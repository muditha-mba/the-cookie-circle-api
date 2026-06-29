"""Order status timeline event model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import OrderStatus
from app.database.base import Base
from app.models.enum_columns import order_status_enum
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.order import Order


class OrderStatusEvent(Base, TimestampMixin):
    """Historical order status change for admin timeline."""

    __tablename__ = "order_status_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[OrderStatus] = mapped_column(
        order_status_enum,
        nullable=False,
    )

    order: Mapped["Order"] = relationship("Order", back_populates="status_events")
