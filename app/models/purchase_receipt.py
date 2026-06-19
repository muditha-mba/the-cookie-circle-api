"""Purchase receipt SQLAlchemy model."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import PurchaseReceiptStatus
from app.database.base import Base
from app.models.base import TimestampMixin
from app.models.enum_columns import purchase_receipt_status_enum

if TYPE_CHECKING:
    from app.models.purchase_receipt_line import PurchaseReceiptLine
    from app.models.supplier import Supplier
    from app.models.user import User


class PurchaseReceipt(Base, TimestampMixin):
    """Supplier purchase receipt with optional bill attachment."""

    __tablename__ = "purchase_receipts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    bill_asset_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    bill_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bill_extension: Mapped[str | None] = mapped_column(String(20), nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    status: Mapped[PurchaseReceiptStatus] = mapped_column(
        purchase_receipt_status_enum,
        nullable=False,
        default=PurchaseReceiptStatus.DRAFT,
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    supplier: Mapped["Supplier"] = relationship("Supplier")
    lines: Mapped[list["PurchaseReceiptLine"]] = relationship(
        "PurchaseReceiptLine",
        back_populates="purchase_receipt",
        cascade="all, delete-orphan",
    )
    created_by: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    confirmed_by: Mapped["User | None"] = relationship("User", foreign_keys=[confirmed_by_user_id])
