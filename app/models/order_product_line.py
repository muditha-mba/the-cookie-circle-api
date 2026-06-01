"""Order product line SQLAlchemy model with snapshots."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.product import Product


class OrderProductLine(Base, TimestampMixin):
    """Product line on an order with frozen pricing, cost, and profit per unit."""

    __tablename__ = "order_product_lines"

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
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    product_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    product_selling_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    product_cost_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    product_profit_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="product_lines")
    product: Mapped["Product"] = relationship("Product")
