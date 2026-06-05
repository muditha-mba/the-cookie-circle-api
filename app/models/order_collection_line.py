"""Order collection line SQLAlchemy model with snapshots."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.collection import Collection
    from app.models.order import Order
    from app.models.order_collection_line_selection import OrderCollectionLineSelection


class OrderCollectionLine(Base, TimestampMixin):
    """Collection line on an order with frozen pricing, cost, and profit per unit."""

    __tablename__ = "order_collection_lines"

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
    collection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("collections.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    collection_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    collection_selling_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    collection_cost_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    collection_profit_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="collection_lines")
    collection: Mapped["Collection"] = relationship("Collection")
    selections: Mapped[list["OrderCollectionLineSelection"]] = relationship(
        "OrderCollectionLineSelection",
        back_populates="order_collection_line",
        cascade="all, delete-orphan",
        order_by="OrderCollectionLineSelection.created_at",
    )
