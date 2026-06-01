"""Collection SQLAlchemy model."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin
from app.models.collection_associations import (
    collection_labour_charges,
    collection_tax_charges,
    collection_utility_charges,
)

if TYPE_CHECKING:
    from app.models.collection_item_line import CollectionItemLine
    from app.models.collection_product_line import CollectionProductLine
    from app.models.labour_charge import LabourCharge
    from app.models.tax_charge import TaxCharge
    from app.models.utility_charge import UtilityCharge


class Collection(Base, TimestampMixin):
    """Customer-facing product bundle with aggregated costing."""

    __tablename__ = "collections"

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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="true")

    product_lines: Mapped[list["CollectionProductLine"]] = relationship(
        "CollectionProductLine",
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="CollectionProductLine.created_at",
    )
    item_lines: Mapped[list["CollectionItemLine"]] = relationship(
        "CollectionItemLine",
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="CollectionItemLine.created_at",
    )
    utility_charges: Mapped[list["UtilityCharge"]] = relationship(
        "UtilityCharge",
        secondary=collection_utility_charges,
    )
    labour_charges: Mapped[list["LabourCharge"]] = relationship(
        "LabourCharge",
        secondary=collection_labour_charges,
    )
    tax_charges: Mapped[list["TaxCharge"]] = relationship(
        "TaxCharge",
        secondary=collection_tax_charges,
    )
