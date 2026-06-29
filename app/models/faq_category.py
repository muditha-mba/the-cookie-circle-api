"""FAQ category SQLAlchemy model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.faq import Faq


class FaqCategory(Base, TimestampMixin):
    """Grouping for customer-facing FAQs."""

    __tablename__ = "faq_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="true")

    faqs: Mapped[list["Faq"]] = relationship("Faq", back_populates="category")
