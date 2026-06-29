"""Collection package SQLAlchemy model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.collection import Collection


class CollectionPackage(Base, TimestampMixin):
    """Managed package definition for customer-facing collection groupings."""

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

    collections: Mapped[list["Collection"]] = relationship(
        "Collection",
        back_populates="package",
    )
