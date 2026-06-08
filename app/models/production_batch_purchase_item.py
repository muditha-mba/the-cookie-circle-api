"""Purchase planning line for a production batch."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import PurchasePlanningStatus
from app.database.base import Base
from app.models.base import TimestampMixin
from app.models.enum_columns import purchase_planning_status_enum

if TYPE_CHECKING:
    from app.models.product_item import ProductItem
    from app.models.production_batch import ProductionBatch


class ProductionBatchPurchaseItem(Base, TimestampMixin):
    """Planning status for a product item required on a production batch."""

    __tablename__ = "production_batch_purchase_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    production_batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("production_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("product_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    purchase_status: Mapped[PurchasePlanningStatus] = mapped_column(
        purchase_planning_status_enum,
        nullable=False,
        default=PurchasePlanningStatus.NOT_PLANNED,
    )

    production_batch: Mapped["ProductionBatch"] = relationship(
        "ProductionBatch",
        back_populates="purchase_items",
    )
    product_item: Mapped["ProductItem"] = relationship("ProductItem")
