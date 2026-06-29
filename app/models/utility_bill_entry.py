"""Utility bill entry SQLAlchemy model — monthly actual cost record."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, SmallInteger, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.utility_charge import UtilityCharge


class UtilityBillEntry(Base, TimestampMixin):
    """Actual monthly bill amount for a utility type."""

    __tablename__ = "utility_bill_entries"
    __table_args__ = (
        UniqueConstraint("utility_charge_id", "year", "month", name="uq_utility_bill_per_month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    utility_charge_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("utility_charges.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    utility_charge: Mapped["UtilityCharge"] = relationship(
        "UtilityCharge",
        back_populates="bill_entries",
    )
