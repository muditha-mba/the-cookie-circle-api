"""Supplier SQLAlchemy model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.product_item import ProductItem


class Supplier(Base, TimestampMixin):
    """Vendor that supplies product items."""

    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    supplier_name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    contact_person: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="true")

    product_items: Mapped[list["ProductItem"]] = relationship(
        "ProductItem",
        back_populates="primary_supplier",
    )
