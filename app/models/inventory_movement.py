"""Inventory movement SQLAlchemy model."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import InventoryMovementReferenceType, InventoryMovementType
from app.database.base import Base
from app.models.base import TimestampMixin
from app.models.enum_columns import (
    inventory_movement_reference_type_enum,
    inventory_movement_type_enum,
)

if TYPE_CHECKING:
    from app.models.inventory_lot import InventoryLot
    from app.models.user import User


class InventoryMovement(Base, TimestampMixin):
    """Immutable inventory ledger entry."""

    __tablename__ = "inventory_movements"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    lot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventory_lots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    movement_type: Mapped[InventoryMovementType] = mapped_column(
        inventory_movement_type_enum,
        nullable=False,
        index=True,
    )
    quantity_change: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_type: Mapped[InventoryMovementReferenceType] = mapped_column(
        inventory_movement_reference_type_enum,
        nullable=False,
    )
    reference_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    lot: Mapped["InventoryLot"] = relationship(
        "InventoryLot",
        back_populates="movements",
    )
    created_by: Mapped["User | None"] = relationship("User")
