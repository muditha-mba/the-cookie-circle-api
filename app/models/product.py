"""Product SQLAlchemy model."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin
from app.models.product_associations import (
    product_labour_charges,
    product_tax_charges,
    product_utility_charges,
)

if TYPE_CHECKING:
    from app.models.labour_charge import LabourCharge
    from app.models.product_category import ProductCategory
    from app.models.product_recipe_line import ProductRecipeLine
    from app.models.tax_charge import TaxCharge
    from app.models.utility_charge import UtilityCharge


class Product(Base, TimestampMixin):
    """Sellable product with recipe-based costing.

    Future: global charges may gain ``applicability`` (PRODUCT | COLLECTION | BOTH)
    to filter which charges can attach at product vs collection level.
    """

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    buffer_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
    )
    yield_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    production_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="true")
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("product_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    category: Mapped["ProductCategory"] = relationship("ProductCategory", back_populates="products")
    recipe_lines: Mapped[list["ProductRecipeLine"]] = relationship(
        "ProductRecipeLine",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductRecipeLine.created_at",
    )
    utility_charges: Mapped[list["UtilityCharge"]] = relationship(
        "UtilityCharge",
        secondary=product_utility_charges,
    )
    labour_charges: Mapped[list["LabourCharge"]] = relationship(
        "LabourCharge",
        secondary=product_labour_charges,
    )
    tax_charges: Mapped[list["TaxCharge"]] = relationship(
        "TaxCharge",
        secondary=product_tax_charges,
    )
