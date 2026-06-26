"""Inventory lot SQLAlchemy model."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.inventory_movement import InventoryMovement
    from app.models.product_item import ProductItem
    from app.models.purchase_receipt_line import PurchaseReceiptLine


class InventoryLot(Base, TimestampMixin):
    """A quantity of a product item received together with optional expiry."""

    __tablename__ = "inventory_lots"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    product_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("product_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    lot_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    quantity_on_hand: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    purchase_receipt_line_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("purchase_receipt_lines.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="true")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    product_item: Mapped["ProductItem"] = relationship(
        "ProductItem",
        back_populates="inventory_lots",
    )
    purchase_receipt_line: Mapped["PurchaseReceiptLine | None"] = relationship(
        "PurchaseReceiptLine",
        back_populates="inventory_lot",
    )
    movements: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement",
        back_populates="lot",
    )
