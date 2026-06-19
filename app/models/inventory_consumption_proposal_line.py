"""Consumption proposal line SQLAlchemy model."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ConsumptionDemandType
from app.database.base import Base
from app.models.base import TimestampMixin
from app.models.enum_columns import consumption_demand_type_enum

if TYPE_CHECKING:
    from app.models.inventory_consumption_proposal import InventoryConsumptionProposal
    from app.models.inventory_consumption_proposal_lot_allocation import (
        InventoryConsumptionProposalLotAllocation,
    )
    from app.models.product_item import ProductItem


class InventoryConsumptionProposalLine(Base, TimestampMixin):
    """Aggregated demand line on a consumption proposal."""

    __tablename__ = "inventory_consumption_proposal_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventory_consumption_proposals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("product_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    demand_type: Mapped[ConsumptionDemandType] = mapped_column(
        consumption_demand_type_enum,
        nullable=False,
    )
    quantity_proposed: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    quantity_approved: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity_on_hand_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    track_inventory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_shortfall: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    proposal: Mapped["InventoryConsumptionProposal"] = relationship(
        "InventoryConsumptionProposal",
        back_populates="lines",
    )
    product_item: Mapped["ProductItem"] = relationship("ProductItem")
    lot_allocations: Mapped[list["InventoryConsumptionProposalLotAllocation"]] = relationship(
        "InventoryConsumptionProposalLotAllocation",
        back_populates="proposal_line",
        cascade="all, delete-orphan",
    )
