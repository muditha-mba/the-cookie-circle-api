"""Products, recipe lines, and charge associations.

Revision ID: 004_products_foundation
Revises: 003_global_cost_foundation
Create Date: 2026-06-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_products_foundation"
down_revision: Union[str, None] = "003_global_cost_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("selling_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("buffer_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
    op.create_index("ix_products_name", "products", ["name"], unique=True)

    op.create_table(
        "product_recipe_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("product_item_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
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
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_item_id"], ["product_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "product_item_id", name="uq_product_recipe_item"),
    )
    op.create_index("ix_product_recipe_lines_product_id", "product_recipe_lines", ["product_id"])
    op.create_index(
        "ix_product_recipe_lines_product_item_id",
        "product_recipe_lines",
        ["product_item_id"],
    )

    op.create_table(
        "product_utility_charges",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("utility_charge_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["utility_charge_id"], ["utility_charges.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("product_id", "utility_charge_id"),
    )

    op.create_table(
        "product_labour_charges",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("labour_charge_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["labour_charge_id"], ["labour_charges.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("product_id", "labour_charge_id"),
    )

    op.create_table(
        "product_tax_charges",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("tax_charge_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tax_charge_id"], ["tax_charges.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("product_id", "tax_charge_id"),
    )


def downgrade() -> None:
    op.drop_table("product_tax_charges")
    op.drop_table("product_labour_charges")
    op.drop_table("product_utility_charges")
    op.drop_index("ix_product_recipe_lines_product_item_id", table_name="product_recipe_lines")
    op.drop_index("ix_product_recipe_lines_product_id", table_name="product_recipe_lines")
    op.drop_table("product_recipe_lines")
    op.drop_index("ix_products_name", table_name="products")
    op.drop_table("products")
