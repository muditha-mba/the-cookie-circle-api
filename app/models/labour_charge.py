"""Labour charge SQLAlchemy model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.labour_bill_entry import LabourBillEntry


class LabourCharge(Base, TimestampMixin):
    """Monthly labour overhead definition (preparation, packaging, administration, etc.)."""

    __tablename__ = "labour_charges"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    bill_entries: Mapped[list["LabourBillEntry"]] = relationship(
        "LabourBillEntry",
        back_populates="labour_charge",
        cascade="all, delete-orphan",
        order_by="(LabourBillEntry.year.desc(), LabourBillEntry.month.desc())",
    )
