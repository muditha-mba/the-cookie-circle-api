"""Production batch SQLAlchemy model."""

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ProductionBatchStatus
from app.database.base import Base
from app.models.base import TimestampMixin
from app.models.enum_columns import production_batch_status_enum

if TYPE_CHECKING:
    from app.models.production_batch_purchase_item import ProductionBatchPurchaseItem


class ProductionBatch(Base, TimestampMixin):
    """Saved production planning work for a delivery date."""

    __tablename__ = "production_batches"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    delivery_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)
    status: Mapped[ProductionBatchStatus] = mapped_column(
        production_batch_status_enum,
        nullable=False,
        default=ProductionBatchStatus.DRAFT,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    purchase_items: Mapped[list["ProductionBatchPurchaseItem"]] = relationship(
        "ProductionBatchPurchaseItem",
        back_populates="production_batch",
        cascade="all, delete-orphan",
    )
