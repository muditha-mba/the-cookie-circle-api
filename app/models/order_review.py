"""Customer order reviews with per-item sentiment and tags."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.order import Order
    from app.models.order_review_item import OrderReviewItem


class OrderReview(Base, TimestampMixin):
    """One review per delivered order from a customer."""

    __tablename__ = "order_reviews"
    __table_args__ = (
        UniqueConstraint("customer_id", "order_id", name="uq_order_reviews_customer_order"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_order_reviews_rating"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    order_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer: Mapped["Customer"] = relationship("Customer", back_populates="order_reviews")
    order: Mapped["Order"] = relationship("Order", back_populates="order_review")
    items: Mapped[list["OrderReviewItem"]] = relationship(
        "OrderReviewItem",
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="OrderReviewItem.product_name_snapshot",
    )
