"""Customer communication log SQLAlchemy model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import CommunicationType
from app.database.base import Base
from app.models.base import TimestampMixin
from app.models.enum_columns import communication_type_enum

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.user import User


class CustomerCommunication(Base, TimestampMixin):
    """Internal log of staff contact with a customer."""

    __tablename__ = "customer_communications"

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
    communication_type: Mapped[CommunicationType] = mapped_column(
        communication_type_enum,
        nullable=False,
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    customer: Mapped["Customer"] = relationship("Customer", back_populates="communications")
    created_by: Mapped["User"] = relationship("User")
