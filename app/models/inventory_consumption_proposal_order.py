"""Consumption proposal order link SQLAlchemy model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.inventory_consumption_proposal import InventoryConsumptionProposal
    from app.models.order import Order


class InventoryConsumptionProposalOrder(Base, TimestampMixin):
    """Order included in a consumption proposal."""

    __tablename__ = "inventory_consumption_proposal_orders"

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
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )

    proposal: Mapped["InventoryConsumptionProposal"] = relationship(
        "InventoryConsumptionProposal",
        back_populates="proposal_orders",
    )
    order: Mapped["Order"] = relationship("Order")
