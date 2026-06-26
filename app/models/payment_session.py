"""WebXPay payment session model."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import PaymentMethod, PaymentSessionStatus
from app.database.base import Base
from app.models.base import TimestampMixin
from app.models.enum_columns import payment_method_enum, payment_session_status_enum

if TYPE_CHECKING:
    from app.models.order import Order


class PaymentSession(Base, TimestampMixin):
    """
    Tracks a single WebXPay payment attempt for an order.

    Lifecycle: initiated → redirected → completed | failed | expired | tampered

    One order may have multiple sessions if earlier attempts failed or expired.
    Only one session per order may be in initiated or redirected state at a time —
    enforced at the service layer, not by a DB constraint, to allow expired-session
    detection on new checkout attempts.

    The idempotency_key (sha256 of order_id + order_number + amount) prevents
    duplicate sessions from being created if a checkout request is retried.
    """

    __tablename__ = "payment_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Deterministic key: sha256(f"{order_id}|{order_number}|{amount}").
    # UNIQUE ensures only one session is ever created for a given order + amount
    # combination, even under concurrent or retried checkout requests.
    idempotency_key: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    status: Mapped[PaymentSessionStatus] = mapped_column(
        payment_session_status_enum,
        nullable=False,
        default=PaymentSessionStatus.INITIATED,
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(
        payment_method_enum,
        nullable=False,
    )
    # Immutable snapshot of the order amount at session creation time.
    # Used to detect tampering: return handler verifies WebXPay's reported
    # amount matches this value exactly.
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="LKR")

    # WebXPay's own transaction reference — set on successful return callback.
    # UNIQUE constraint prevents duplicate processing of the same gateway event.
    gateway_reference: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
    )

    # Stores the non-sensitive fields sent to WebXPay (encrypted payment blob
    # excluded — it contains no secret but its storage adds no audit value).
    raw_request_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Raw POST fields received from WebXPay return callback.
    # Stored for reconciliation and audit. The decrypted plaintext is stored
    # rather than the encrypted blob. Never includes secret_key.
    raw_callback_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Human-readable failure context. Never exposed to customers.
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # IP address of the browser at checkout time — for audit trail.
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    initiated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    redirected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    order: Mapped["Order"] = relationship("Order", back_populates="payment_sessions")
