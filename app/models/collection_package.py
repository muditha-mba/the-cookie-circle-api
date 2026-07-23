"""Collection package SQLAlchemy model."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.collection import Collection


class CollectionPackage(Base, TimestampMixin):
    """Managed package definition for customer-facing collection groupings.

    Business UI name: Collection (Butter / Mix / Special).
    """

    __tablename__ = "collection_packages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    badge_tone: Mapped[str] = mapped_column(String(32), nullable=False, default="violet")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    min_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    max_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30,
        server_default="30",
    )
    packaging_fee_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="flat",
        server_default="flat",
    )
    packaging_fee_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
    )

    collections: Mapped[list["Collection"]] = relationship(
        "Collection",
        back_populates="package",
    )
