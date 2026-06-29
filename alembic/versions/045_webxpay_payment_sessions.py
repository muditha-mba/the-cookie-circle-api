"""WebXPay payment sessions table.

Revision ID: 045_webxpay_payment_sessions
Revises: 044_payments_pre_integration
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "045_webxpay_payment_sessions"
down_revision: Union[str, None] = "044_payments_pre_integration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATUS_VALUES = (
    "initiated",
    "redirected",
    "completed",
    "failed",
    "expired",
    "tampered",
)

payment_session_status_enum = postgresql.ENUM(
    *_STATUS_VALUES,
    name="payment_session_status",
    create_type=False,
)

payment_method_enum = postgresql.ENUM(
    name="payment_method",
    create_type=False,
)


def upgrade() -> None:
    # Idempotent — safe if a previous attempt created the type but failed on create_table.
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "CREATE TYPE payment_session_status AS ENUM ("
            + ", ".join(f"'{v}'" for v in _STATUS_VALUES)
            + "); "
            "EXCEPTION WHEN duplicate_object THEN NULL; "
            "END $$;"
        )
    )

    op.create_table(
        "payment_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column(
            "status",
            payment_session_status_enum,
            nullable=False,
            server_default="initiated",
        ),
        sa.Column("payment_method", payment_method_enum, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="LKR"),
        sa.Column("gateway_reference", sa.String(100), nullable=True),
        sa.Column("raw_request_payload", sa.JSON, nullable=True),
        sa.Column("raw_callback_payload", sa.JSON, nullable=True),
        sa.Column("failure_reason", sa.Text, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("initiated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("redirected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "ix_payment_sessions_order_id",
        "payment_sessions",
        ["order_id"],
    )
    op.create_index(
        "ix_payment_sessions_idempotency_key",
        "payment_sessions",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_payment_sessions_gateway_reference",
        "payment_sessions",
        ["gateway_reference"],
        unique=True,
        postgresql_where=sa.text("gateway_reference IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_payment_sessions_gateway_reference",
        table_name="payment_sessions",
    )
    op.drop_index(
        "ix_payment_sessions_idempotency_key",
        table_name="payment_sessions",
    )
    op.drop_index(
        "ix_payment_sessions_order_id",
        table_name="payment_sessions",
    )
    op.drop_table("payment_sessions")
    op.execute(sa.text("DROP TYPE IF EXISTS payment_session_status"))
