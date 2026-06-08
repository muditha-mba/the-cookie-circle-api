"""Business settings, customers, and orders foundation.

Revision ID: 008_business_orders
Revises: 007_collection_packaging
Create Date: 2026-06-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008_business_orders"
down_revision: Union[str, None] = "007_collection_packaging"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

customer_source = postgresql.ENUM(
    "registered",
    "guest",
    "manual",
    name="customer_source",
    create_type=False,
)
order_source = postgresql.ENUM(
    "website",
    "whatsapp",
    "instagram",
    "facebook",
    "manual",
    name="order_source",
    create_type=False,
)
payment_method = postgresql.ENUM(
    "cash_on_delivery",
    "bank_transfer",
    "stripe",
    "manual",
    name="payment_method",
    create_type=False,
)
payment_status = postgresql.ENUM(
    "pending",
    "paid",
    "failed",
    "refunded",
    name="payment_status",
    create_type=False,
)
order_status = postgresql.ENUM(
    "draft",
    "pending",
    "confirmed",
    "preparing",
    "ready",
    "delivered",
    "cancelled",
    name="order_status",
    create_type=False,
)


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "collections",
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.create_table(
        "business_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key"),
    )

    customer_source.create(op.get_bind(), checkfirst=True)
    order_source.create(op.get_bind(), checkfirst=True)
    payment_method.create(op.get_bind(), checkfirst=True)
    payment_status.create(op.get_bind(), checkfirst=True)
    order_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("source", customer_source, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_customers_email", "customers", ["email"])
    op.create_index("ix_customers_phone", "customers", ["phone"])

    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.String(length=50), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("source", order_source, nullable=False),
        sa.Column("payment_method", payment_method, nullable=False),
        sa.Column("payment_status", payment_status, nullable=False),
        sa.Column("status", order_status, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("delivery_date", sa.Date(), nullable=False),
        sa.Column("delivery_fee_snapshot", sa.Numeric(12, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("profit_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("margin_percentage", sa.Numeric(8, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_number"),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_orders_delivery_date", "orders", ["delivery_date"])
    op.create_index("ix_orders_order_number", "orders", ["order_number"])

    op.create_table(
        "order_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("collection_name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("collection_price_snapshot", sa.Numeric(12, 2), nullable=False),
        sa.Column("collection_cost_snapshot", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_lines_collection_id", "order_lines", ["collection_id"])
    op.create_index("ix_order_lines_order_id", "order_lines", ["order_id"])

    op.create_table(
        "order_status_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("status", order_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_status_events_order_id", "order_status_events", ["order_id"])

    settings = sa.table(
        "business_settings",
        sa.column("key", sa.String),
        sa.column("value", sa.Text),
    )
    op.bulk_insert(
        settings,
        [
            {"key": "delivery_fee", "value": "0.00"},
            {"key": "order_cutoff_day", "value": "thursday"},
            {"key": "delivery_day", "value": "saturday"},
            {"key": "business_phone", "value": ""},
            {"key": "business_email", "value": ""},
            {"key": "stripe_enabled", "value": "false"},
            {"key": "bank_transfer_enabled", "value": "true"},
            {"key": "cod_enabled", "value": "true"},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_order_status_events_order_id", table_name="order_status_events")
    op.drop_table("order_status_events")
    op.drop_index("ix_order_lines_order_id", table_name="order_lines")
    op.drop_index("ix_order_lines_collection_id", table_name="order_lines")
    op.drop_table("order_lines")
    op.drop_index("ix_orders_order_number", table_name="orders")
    op.drop_index("ix_orders_delivery_date", table_name="orders")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_customers_phone", table_name="customers")
    op.drop_index("ix_customers_email", table_name="customers")
    op.drop_table("customers")
    op.drop_table("business_settings")

    order_status.drop(op.get_bind(), checkfirst=True)
    payment_status.drop(op.get_bind(), checkfirst=True)
    payment_method.drop(op.get_bind(), checkfirst=True)
    order_source.drop(op.get_bind(), checkfirst=True)
    customer_source.drop(op.get_bind(), checkfirst=True)

    op.drop_column("collections", "is_public")
    op.drop_column("products", "is_public")
