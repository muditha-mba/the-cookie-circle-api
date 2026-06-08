"""Order operations foundation: delivery areas, order lines split, delivery info.

Revision ID: 009_order_operations
Revises: 008_business_orders
Create Date: 2026-06-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_order_operations"
down_revision: Union[str, None] = "008_business_orders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE order_source ADD VALUE IF NOT EXISTS 'walk_in'")
    op.execute("ALTER TYPE order_source ADD VALUE IF NOT EXISTS 'phone'")

    op.create_table(
        "delivery_areas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("delivery_fee_override", sa.Numeric(12, 2), nullable=True),
        sa.Column("pickup_only", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_delivery_areas_name", "delivery_areas", ["name"])

    op.add_column("customers", sa.Column("address_line_1", sa.String(length=255), nullable=True))
    op.add_column("customers", sa.Column("address_line_2", sa.String(length=255), nullable=True))
    op.add_column("customers", sa.Column("city", sa.String(length=100), nullable=True))
    op.add_column("customers", sa.Column("postal_code", sa.String(length=20), nullable=True))
    op.add_column("customers", sa.Column("landmark", sa.String(length=255), nullable=True))

    op.add_column("orders", sa.Column("delivery_area_id", sa.Uuid(), nullable=True))
    op.add_column("orders", sa.Column("customer_notes", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("internal_notes", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("requested_delivery_date", sa.Date(), nullable=True))
    op.add_column("orders", sa.Column("scheduled_delivery_date", sa.Date(), nullable=True))
    op.add_column("orders", sa.Column("delivery_contact_name", sa.String(length=200), nullable=True))
    op.add_column("orders", sa.Column("delivery_phone_primary", sa.String(length=50), nullable=True))
    op.add_column("orders", sa.Column("delivery_phone_secondary", sa.String(length=50), nullable=True))
    op.add_column("orders", sa.Column("delivery_address_line_1", sa.String(length=255), nullable=True))
    op.add_column("orders", sa.Column("delivery_address_line_2", sa.String(length=255), nullable=True))
    op.add_column("orders", sa.Column("delivery_city", sa.String(length=100), nullable=True))
    op.add_column("orders", sa.Column("delivery_postal_code", sa.String(length=20), nullable=True))
    op.add_column("orders", sa.Column("delivery_landmark", sa.String(length=255), nullable=True))
    op.add_column("orders", sa.Column("delivery_notes", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("delivery_latitude", sa.Numeric(10, 7), nullable=True))
    op.add_column("orders", sa.Column("delivery_longitude", sa.Numeric(10, 7), nullable=True))
    op.add_column(
        "orders",
        sa.Column("products_subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "orders",
        sa.Column("collections_subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.add_column("orders", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("preparing_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        """
        UPDATE orders
        SET internal_notes = notes,
            requested_delivery_date = delivery_date,
            scheduled_delivery_date = delivery_date,
            collections_subtotal = subtotal,
            products_subtotal = 0
        """
    )

    op.drop_column("orders", "notes")
    op.drop_column("orders", "delivery_date")
    op.drop_index("ix_orders_delivery_date", table_name="orders", if_exists=True)

    op.alter_column("orders", "requested_delivery_date", nullable=False)
    op.alter_column("orders", "scheduled_delivery_date", nullable=False)

    op.create_foreign_key(
        "fk_orders_delivery_area_id",
        "orders",
        "delivery_areas",
        ["delivery_area_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_orders_delivery_area_id", "orders", ["delivery_area_id"])
    op.create_index("ix_orders_requested_delivery_date", "orders", ["requested_delivery_date"])
    op.create_index("ix_orders_scheduled_delivery_date", "orders", ["scheduled_delivery_date"])

    op.rename_table("order_lines", "order_collection_lines")
    op.drop_index("ix_order_lines_order_id", table_name="order_collection_lines")
    op.drop_index("ix_order_lines_collection_id", table_name="order_collection_lines")
    op.create_index(
        "ix_order_collection_lines_order_id",
        "order_collection_lines",
        ["order_id"],
    )
    op.create_index(
        "ix_order_collection_lines_collection_id",
        "order_collection_lines",
        ["collection_id"],
    )

    op.create_table(
        "order_product_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("product_name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("product_price_snapshot", sa.Numeric(12, 2), nullable=False),
        sa.Column("product_cost_snapshot", sa.Numeric(12, 2), nullable=False),
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
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_product_lines_order_id", "order_product_lines", ["order_id"])
    op.create_index("ix_order_product_lines_product_id", "order_product_lines", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_order_product_lines_product_id", table_name="order_product_lines")
    op.drop_index("ix_order_product_lines_order_id", table_name="order_product_lines")
    op.drop_table("order_product_lines")

    op.drop_index("ix_order_collection_lines_collection_id", table_name="order_collection_lines")
    op.drop_index("ix_order_collection_lines_order_id", table_name="order_collection_lines")
    op.rename_table("order_collection_lines", "order_lines")
    op.create_index("ix_order_lines_order_id", "order_lines", ["order_id"])
    op.create_index("ix_order_lines_collection_id", "order_lines", ["collection_id"])

    op.add_column("orders", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("delivery_date", sa.Date(), nullable=True))
    op.execute(
        """
        UPDATE orders
        SET notes = internal_notes,
            delivery_date = scheduled_delivery_date
        """
    )
    op.drop_column("orders", "cancelled_at")
    op.drop_column("orders", "delivered_at")
    op.drop_column("orders", "ready_at")
    op.drop_column("orders", "preparing_at")
    op.drop_column("orders", "confirmed_at")
    op.drop_column("orders", "collections_subtotal")
    op.drop_column("orders", "products_subtotal")
    op.drop_column("orders", "delivery_longitude")
    op.drop_column("orders", "delivery_latitude")
    op.drop_column("orders", "delivery_notes")
    op.drop_column("orders", "delivery_landmark")
    op.drop_column("orders", "delivery_postal_code")
    op.drop_column("orders", "delivery_city")
    op.drop_column("orders", "delivery_address_line_2")
    op.drop_column("orders", "delivery_address_line_1")
    op.drop_column("orders", "delivery_phone_secondary")
    op.drop_column("orders", "delivery_phone_primary")
    op.drop_column("orders", "delivery_contact_name")
    op.drop_column("orders", "scheduled_delivery_date")
    op.drop_column("orders", "requested_delivery_date")
    op.drop_column("orders", "internal_notes")
    op.drop_column("orders", "customer_notes")
    op.drop_constraint("fk_orders_delivery_area_id", "orders", type_="foreignkey")
    op.drop_index("ix_orders_scheduled_delivery_date", table_name="orders")
    op.drop_index("ix_orders_requested_delivery_date", table_name="orders")
    op.drop_index("ix_orders_delivery_area_id", table_name="orders")
    op.drop_column("orders", "delivery_area_id")
    op.alter_column("orders", "delivery_date", nullable=False)
    op.create_index("ix_orders_delivery_date", "orders", ["delivery_date"])

    op.drop_column("customers", "landmark")
    op.drop_column("customers", "postal_code")
    op.drop_column("customers", "city")
    op.drop_column("customers", "address_line_2")
    op.drop_column("customers", "address_line_1")

    op.drop_index("ix_delivery_areas_name", table_name="delivery_areas")
    op.drop_table("delivery_areas")
