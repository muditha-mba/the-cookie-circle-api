"""Inventory consumption proposal SQLAlchemy model."""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ConsumptionProposalStatus
from app.database.base import Base
from app.models.base import TimestampMixin
from app.models.enum_columns import consumption_proposal_status_enum

if TYPE_CHECKING:
    from app.models.inventory_consumption_proposal_line import InventoryConsumptionProposalLine
    from app.models.inventory_consumption_proposal_order import InventoryConsumptionProposalOrder
    from app.models.user import User


class InventoryConsumptionProposal(Base, TimestampMixin):
    """Pending or completed stock consumption review for delivered orders."""

    __tablename__ = "inventory_consumption_proposals"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    delivery_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[ConsumptionProposalStatus] = mapped_column(
        consumption_proposal_status_enum,
        nullable=False,
        default=ConsumptionProposalStatus.PENDING_REVIEW,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lines: Mapped[list["InventoryConsumptionProposalLine"]] = relationship(
        "InventoryConsumptionProposalLine",
        back_populates="proposal",
        cascade="all, delete-orphan",
    )
    proposal_orders: Mapped[list["InventoryConsumptionProposalOrder"]] = relationship(
        "InventoryConsumptionProposalOrder",
        back_populates="proposal",
        cascade="all, delete-orphan",
    )
    reviewed_by: Mapped["User | None"] = relationship("User", foreign_keys=[reviewed_by_user_id])
