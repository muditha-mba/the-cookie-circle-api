"""Customer ordering experience foundation.

Revision ID: 015_customer_ordering
Revises: 014_collection_pkg_mgmt
Create Date: 2026-06-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "015_customer_ordering"
down_revision: Union[str, None] = "014_collection_pkg_mgmt"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

order_type_enum = postgresql.ENUM(
    "weekly_delivery",
    "catering",
    name="order_type",
    create_type=False,
)

collection_selection_mode_enum = postgresql.ENUM(
    "fixed",
    "flexible",
    "premium_limited",
    name="collection_selection_mode",
    create_type=False,
)


def upgrade() -> None:
    op.execute("ALTER TYPE order_source ADD VALUE IF NOT EXISTS 'admin'")

    order_type_enum.create(op.get_bind(), checkfirst=True)
    collection_selection_mode_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "products",
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        """
        UPDATE products
        SET is_premium = true
        WHERE name IN (
            'Double Chocolate Chip Cookie',
            'Double Chocolate White Chip Cookie',
            'Fruit & Nut Chocolate Chip Cookie',
            'Mixed Nut Chocolate Chip Cookie',
            'Cashew Chocolate Chip Cookie',
            'Cashew Butter Cookie'
        )
        """
    )

    op.add_column(
        "collections",
        sa.Column(
            "selection_mode",
            collection_selection_mode_enum,
            nullable=False,
            server_default="fixed",
        ),
    )
    op.add_column(
        "collections",
        sa.Column("max_premium_cookies", sa.Integer(), nullable=True),
    )
    op.add_column(
        "collections",
        sa.Column("cookie_slot_count", sa.Integer(), nullable=True),
    )

    op.execute(
        """
        UPDATE collections c
        SET
            selection_mode = CASE cp.code
                WHEN 'SPECIAL_EDITION' THEN 'flexible'
                WHEN 'MIX_AND_MATCH' THEN 'premium_limited'
                WHEN 'BUTTER_COLLECTION' THEN 'fixed'
                ELSE 'fixed'
            END::collection_selection_mode,
            cookie_slot_count = CASE c.name
                WHEN 'The Signature Circle' THEN 6
                WHEN 'The Golden Circle' THEN 14
                WHEN 'The Grand Circle' THEN 18
                WHEN 'The Little Circle' THEN 6
                WHEN 'The Family Circle' THEN 12
                WHEN 'The Party Circle' THEN 20
                WHEN 'The Tea Circle' THEN 10
                WHEN 'The Warm Circle' THEN 20
                WHEN 'The Gathering Circle' THEN 30
                ELSE NULL
            END,
            max_premium_cookies = CASE c.name
                WHEN 'The Little Circle' THEN 1
                WHEN 'The Family Circle' THEN 2
                WHEN 'The Party Circle' THEN 4
                ELSE NULL
            END
        FROM collection_packages cp
        WHERE c.package_id = cp.id
        """
    )

    op.add_column(
        "orders",
        sa.Column(
            "order_type",
            order_type_enum,
            nullable=False,
            server_default="weekly_delivery",
        ),
    )
    op.add_column("orders", sa.Column("event_name", sa.String(length=200), nullable=True))
    op.create_index("ix_orders_order_type", "orders", ["order_type"])

    op.create_table(
        "order_collection_line_selections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_collection_line_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("product_name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("is_premium_snapshot", sa.Boolean(), nullable=False, server_default=sa.false()),
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
        sa.ForeignKeyConstraint(
            ["order_collection_line_id"],
            ["order_collection_lines.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_order_collection_line_selections_line_id",
        "order_collection_line_selections",
        ["order_collection_line_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_order_collection_line_selections_line_id",
        table_name="order_collection_line_selections",
    )
    op.drop_table("order_collection_line_selections")
    op.drop_index("ix_orders_order_type", table_name="orders")
    op.drop_column("orders", "event_name")
    op.drop_column("orders", "order_type")
    op.drop_column("collections", "cookie_slot_count")
    op.drop_column("collections", "max_premium_cookies")
    op.drop_column("collections", "selection_mode")
    op.drop_column("products", "is_premium")
    collection_selection_mode_enum.drop(op.get_bind(), checkfirst=True)
    order_type_enum.drop(op.get_bind(), checkfirst=True)
