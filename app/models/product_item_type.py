"""Product item type SQLAlchemy model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.product_item import ProductItem


class ProductItemType(Base, TimestampMixin):
    """Category of resources used in costing (ingredient, packaging, etc.)."""

    __tablename__ = "product_item_types"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    product_items: Mapped[list["ProductItem"]] = relationship(
        "ProductItem",
        back_populates="item_type",
    )
