"""Purchase receipt file attachment SQLAlchemy model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.purchase_receipt import PurchaseReceipt


class PurchaseReceiptAttachment(Base, TimestampMixin):
    """Supplier receipt image or PDF stored in S3."""

    __tablename__ = "purchase_receipt_attachments"

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
    asset_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    extension: Mapped[str] = mapped_column(String(20), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    purchase_receipt: Mapped["PurchaseReceipt"] = relationship(
        "PurchaseReceipt",
        back_populates="attachments",
    )
