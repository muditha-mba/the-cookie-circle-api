"""CustomerDiscountGrant SQLAlchemy model."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import DiscountGrantStatus, DiscountSource, DiscountType
from app.database.base import Base
from app.models.base import TimestampMixin
from app.models.enum_columns import (
    discount_grant_status_enum,
    discount_source_enum,
    discount_type_enum,
)


class CustomerDiscountGrant(Base, TimestampMixin):
    """A discount grant issued to a customer — consumed on their next order."""

    __tablename__ = "customer_discount_grants"

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
    discount_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("discount_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    discount_type: Mapped[DiscountType] = mapped_column(
        discount_type_enum,
        nullable=False,
    )
    discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    source: Mapped[DiscountSource] = mapped_column(discount_source_enum, nullable=False)
    status: Mapped[DiscountGrantStatus] = mapped_column(
        discount_grant_status_enum,
        nullable=False,
        default=DiscountGrantStatus.ACTIVE,
        index=True,
    )
    eligibility_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_on_order_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
