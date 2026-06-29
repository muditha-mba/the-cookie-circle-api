"""Package builder foundation — dynamic package pricing and product categories.

Revision ID: 016_package_builder
Revises: 015_customer_ordering
Create Date: 2026-06-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016_package_builder"
down_revision: Union[str, None] = "015_customer_ordering"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_product_categories_code", "product_categories", ["code"])
    op.create_index("ix_product_categories_name", "product_categories", ["name"])

    op.execute(
        """
        INSERT INTO product_categories (id, code, name, sort_order, is_active)
        VALUES
            ('a1000001-0000-4000-8000-000000000001', 'CHOCOLATE', 'Chocolate', 1, true),
            ('a1000001-0000-4000-8000-000000000002', 'KIDS_FAVOURITES', 'Kids Favourites', 2, true),
            ('a1000001-0000-4000-8000-000000000003', 'HEALTHY', 'Healthy', 3, true),
            ('a1000001-0000-4000-8000-000000000004', 'NUTTY', 'Nutty', 4, true),
            ('a1000001-0000-4000-8000-000000000005', 'BUTTER', 'Butter', 5, true)
        """
    )

    op.add_column(
        "products",
        sa.Column("category_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_products_category_id",
        "products",
        "product_categories",
        ["category_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_products_category_id", "products", ["category_id"])

    op.execute(
        """
        UPDATE products SET category_id = 'a1000001-0000-4000-8000-000000000001'
        WHERE name IN (
            'Classic Chocolate Chip Cookie',
            'White Chocolate Chip Cookie',
            'Double Chocolate Chip Cookie',
            'Double Chocolate White Chip Cookie'
        )
        """
    )
    op.execute(
        """
        UPDATE products SET category_id = 'a1000001-0000-4000-8000-000000000002'
        WHERE name IN (
            'Unicorn Cookie',
            'Smarties Cookie',
            'White & Dark Chocolate Chip Cookie'
        )
        """
    )
    op.execute(
        """
        UPDATE products SET category_id = 'a1000001-0000-4000-8000-000000000003'
        WHERE name IN (
            'Sugar Free Chocolate Chip Cookie',
            'Sugar Free Date Cookie'
        )
        """
    )
    op.execute(
        """
        UPDATE products SET category_id = 'a1000001-0000-4000-8000-000000000004'
        WHERE name IN (
            'Fruit & Nut Chocolate Chip Cookie',
            'Mixed Nut Chocolate Chip Cookie',
            'Cashew Chocolate Chip Cookie'
        )
        """
    )
    op.execute(
        """
        UPDATE products SET category_id = 'a1000001-0000-4000-8000-000000000005'
        WHERE name IN (
            'Classic Butter Cookie',
            'Cashew Butter Cookie'
        )
        """
    )
    op.alter_column("products", "category_id", nullable=False)

    op.add_column(
        "collections",
        sa.Column("package_size", sa.Integer(), nullable=True),
    )
    op.add_column(
        "collections",
        sa.Column(
            "package_fee",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )

    op.execute(
        """
        UPDATE collections c
        SET package_size = CASE c.name
            WHEN 'The Signature Circle' THEN 6
            WHEN 'The Golden Circle' THEN 10
            WHEN 'The Grand Circle' THEN 14
            WHEN 'The Little Circle' THEN 4
            WHEN 'The Family Circle' THEN 8
            WHEN 'The Party Circle' THEN 12
            WHEN 'The Tea Circle' THEN 8
            WHEN 'The Warm Circle' THEN 14
            WHEN 'The Gathering Circle' THEN 20
            ELSE COALESCE(c.cookie_slot_count, 1)
        END
        """
    )
    op.execute(
        """
        UPDATE collections c
        SET package_fee = CASE cp.code
            WHEN 'SPECIAL_EDITION' THEN 350
            ELSE 0
        END
        FROM collection_packages cp
        WHERE c.package_id = cp.id
        """
    )
    op.alter_column("collections", "package_size", nullable=False)

    op.create_table(
        "collection_allowed_categories",
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("product_category_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["product_category_id"],
            ["product_categories.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("collection_id", "product_category_id"),
    )

    op.execute(
        """
        INSERT INTO collection_allowed_categories (collection_id, product_category_id)
        SELECT c.id, pc.id
        FROM collections c
        JOIN collection_packages cp ON cp.id = c.package_id
        CROSS JOIN product_categories pc
        WHERE cp.code IN ('SPECIAL_EDITION', 'MIX_AND_MATCH')
          AND pc.code IN ('CHOCOLATE', 'KIDS_FAVOURITES', 'HEALTHY', 'NUTTY')
        """
    )
    op.execute(
        """
        INSERT INTO collection_allowed_categories (collection_id, product_category_id)
        SELECT c.id, pc.id
        FROM collections c
        JOIN collection_packages cp ON cp.id = c.package_id
        CROSS JOIN product_categories pc
        WHERE cp.code = 'BUTTER_COLLECTION'
          AND pc.code = 'BUTTER'
        """
    )

    op.drop_column("collections", "selling_price")
    op.drop_column("collections", "buffer_amount")
    op.drop_column("collections", "selection_mode")
    op.drop_column("collections", "max_premium_cookies")
    op.drop_column("collections", "cookie_slot_count")

    op.execute("DROP TYPE IF EXISTS collection_selection_mode")


def downgrade() -> None:
    raise NotImplementedError("Package builder migration cannot be safely downgraded.")
