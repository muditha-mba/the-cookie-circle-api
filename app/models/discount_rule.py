"""DiscountRule SQLAlchemy model."""

import uuid
from typing import Any

from sqlalchemy import Boolean, SmallInteger, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import DiscountRuleType
from app.database.base import Base
from app.models.base import TimestampMixin
from app.models.enum_columns import discount_rule_type_enum


class DiscountRule(Base, TimestampMixin):
    """Admin-configured rule that triggers automatic discount grants."""

    __tablename__ = "discount_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_type: Mapped[DiscountRuleType] = mapped_column(
        discount_rule_type_enum,
        nullable=False,
        index=True,
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="'{}'",
    )
    priority: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=100,
        server_default="100",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
