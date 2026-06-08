"""Per-item feedback within an order review."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ReviewItemSentiment
from app.database.base import Base
from app.models.enum_columns import review_item_sentiment_enum

if TYPE_CHECKING:
    from app.models.order_review import OrderReview
    from app.models.product import Product


class OrderReviewItem(Base):
    """Thumbs and tags for a single product in an order review."""

    __tablename__ = "order_review_items"
    __table_args__ = (
        UniqueConstraint("order_review_id", "product_id", name="uq_order_review_items_review_product"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    order_review_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("order_reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    product_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    sentiment: Mapped[ReviewItemSentiment] = mapped_column(
        review_item_sentiment_enum,
        nullable=False,
    )
    item_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    review: Mapped["OrderReview"] = relationship("OrderReview", back_populates="items")
    product: Mapped["Product"] = relationship("Product")
