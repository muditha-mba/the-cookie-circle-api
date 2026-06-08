"""Immutable cookie selections within an order collection line."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.order_collection_line import OrderCollectionLine
    from app.models.product import Product


class OrderCollectionLineSelection(Base, TimestampMixin):
    """Customer-chosen cookies for a collection line at order time."""

    __tablename__ = "order_collection_line_selections"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    order_collection_line_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("order_collection_lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    product_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    is_premium_snapshot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    product_selling_price_snapshot: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    product_cost_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    product_profit_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    order_collection_line: Mapped["OrderCollectionLine"] = relationship(
        "OrderCollectionLine",
        back_populates="selections",
    )
    product: Mapped["Product"] = relationship("Product")
