"""Customer SQLAlchemy model."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import CustomerSource, MarketingSource
from app.database.base import Base
from app.models.enum_columns import customer_source_enum, marketing_source_enum
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.customer_address import CustomerAddress
    from app.models.customer_communication import CustomerCommunication
    from app.models.customer_note import CustomerNote
    from app.models.order import Order
    from app.models.order_review import OrderReview
    from app.models.user import User


class Customer(Base, TimestampMixin):
    """Customer profile for registered, guest, and manual customers."""

    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    phone_secondary: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address_line_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    landmark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[CustomerSource] = mapped_column(
        customer_source_enum,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    marketing_source: Mapped[MarketingSource | None] = mapped_column(
        marketing_source_enum,
        nullable=True,
        index=True,
    )
    marketing_attribution_json: Mapped[dict[str, Any] | None] = mapped_column(
        "marketing_attribution",
        JSONB,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User | None"] = relationship("User")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="customer")
    crm_notes: Mapped[list["CustomerNote"]] = relationship(
        "CustomerNote",
        back_populates="customer",
        cascade="all, delete-orphan",
        order_by="CustomerNote.created_at.desc()",
    )
    communications: Mapped[list["CustomerCommunication"]] = relationship(
        "CustomerCommunication",
        back_populates="customer",
        cascade="all, delete-orphan",
        order_by="CustomerCommunication.created_at.desc()",
    )
    saved_addresses: Mapped[list["CustomerAddress"]] = relationship(
        "CustomerAddress",
        back_populates="customer",
        cascade="all, delete-orphan",
        order_by="CustomerAddress.is_default.desc(), CustomerAddress.created_at.desc()",
    )
    order_reviews: Mapped[list["OrderReview"]] = relationship(
        "OrderReview",
        back_populates="customer",
        cascade="all, delete-orphan",
        order_by="OrderReview.created_at.desc()",
    )
