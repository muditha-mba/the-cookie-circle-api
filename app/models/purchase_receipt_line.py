"""Purchase receipt line SQLAlchemy model."""

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.inventory_lot import InventoryLot
    from app.models.product_item import ProductItem
    from app.models.purchase_receipt import PurchaseReceipt


class PurchaseReceiptLine(Base, TimestampMixin):
    """Line item on a purchase receipt."""

    __tablename__ = "purchase_receipt_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    purchase_receipt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("purchase_receipts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("product_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    purchase_receipt: Mapped["PurchaseReceipt"] = relationship(
        "PurchaseReceipt",
        back_populates="lines",
    )
    product_item: Mapped["ProductItem"] = relationship("ProductItem")
    inventory_lot: Mapped["InventoryLot | None"] = relationship(
        "InventoryLot",
        back_populates="purchase_receipt_line",
        uselist=False,
    )
