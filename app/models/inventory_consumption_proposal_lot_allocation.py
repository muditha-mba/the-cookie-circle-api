"""FEFO lot allocation preview for a consumption proposal line."""

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.inventory_consumption_proposal_line import InventoryConsumptionProposalLine
    from app.models.inventory_lot import InventoryLot


class InventoryConsumptionProposalLotAllocation(Base, TimestampMixin):
    """Preview of which lots will be consumed when a proposal is approved."""

    __tablename__ = "inventory_consumption_proposal_lot_allocations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    proposal_line_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventory_consumption_proposal_lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventory_lots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    lot_code: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    proposal_line: Mapped["InventoryConsumptionProposalLine"] = relationship(
        "InventoryConsumptionProposalLine",
        back_populates="lot_allocations",
    )
    lot: Mapped["InventoryLot"] = relationship("InventoryLot")
