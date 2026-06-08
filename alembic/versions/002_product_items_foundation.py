"""Product item types and product items tables.

Revision ID: 002_product_items_foundation
Revises: 001_auth_foundation
Create Date: 2026-06-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_product_items_foundation"
down_revision: Union[str, None] = "001_auth_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_item_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
    op.create_index(
        "ix_product_item_types_name",
        "product_item_types",
        ["name"],
        unique=True,
    )

    op.create_table(
        "product_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("item_type_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("purchase_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("purchase_quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("purchase_unit", sa.String(length=50), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["item_type_id"],
            ["product_item_types.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_items_item_type_id", "product_items", ["item_type_id"])
    op.create_index("ix_product_items_name", "product_items", ["name"])


def downgrade() -> None:
    op.drop_index("ix_product_items_name", table_name="product_items")
    op.drop_index("ix_product_items_item_type_id", table_name="product_items")
    op.drop_table("product_items")
    op.drop_index("ix_product_item_types_name", table_name="product_item_types")
    op.drop_table("product_item_types")
