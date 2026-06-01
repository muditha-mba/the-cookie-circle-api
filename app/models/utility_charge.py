"""Utility charge SQLAlchemy model."""

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import ChargeApplicability, ChargeType
from app.database.base import Base
from app.models.base import TimestampMixin
from app.models.charge_columns import charge_applicability_enum, charge_type_enum


class UtilityCharge(Base, TimestampMixin):
    """Business-wide utility cost definition."""

    __tablename__ = "utility_charges"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    charge_type: Mapped[ChargeType] = mapped_column(charge_type_enum, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    applicability: Mapped[ChargeApplicability] = mapped_column(
        charge_applicability_enum,
        nullable=False,
        default=ChargeApplicability.BOTH,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
