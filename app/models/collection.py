"""Collection SQLAlchemy model — configurable package template."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin
from app.models.collection_associations import collection_allowed_categories

if TYPE_CHECKING:
    from app.models.collection_item_line import CollectionItemLine
    from app.models.collection_package import CollectionPackage
    from app.models.collection_product_line import CollectionProductLine
    from app.models.product_category import ProductCategory


class Collection(Base, TimestampMixin):
    """Customer-facing package template with dynamic cookie composition."""

    __tablename__ = "collections"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    package_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("collection_packages.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    package_size: Mapped[int] = mapped_column(Integer, nullable=False)
    package_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="true")

    package: Mapped["CollectionPackage"] = relationship(
        "CollectionPackage",
        back_populates="collections",
    )
    allowed_categories: Mapped[list["ProductCategory"]] = relationship(
        "ProductCategory",
        secondary=collection_allowed_categories,
    )

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
