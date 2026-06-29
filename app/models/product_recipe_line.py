"""Product recipe line SQLAlchemy model."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.product_item import ProductItem


class ProductRecipeLine(Base, TimestampMixin):
    """Quantity of a product item used in a product recipe."""

    __tablename__ = "product_recipe_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("product_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="recipe_lines")
    product_item: Mapped["ProductItem"] = relationship("ProductItem")
