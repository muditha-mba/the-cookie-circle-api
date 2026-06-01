"""Order profitability immutable snapshot columns.

Revision ID: 010_order_profit_snapshots
Revises: 009_order_operations
Create Date: 2026-06-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_order_profit_snapshots"
down_revision: Union[str, None] = "009_order_operations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Order header financial snapshots ---
    op.alter_column(
        "orders",
        "products_subtotal",
        new_column_name="products_subtotal_snapshot",
    )
    op.alter_column(
        "orders",
        "collections_subtotal",
        new_column_name="collections_subtotal_snapshot",
    )
    op.alter_column("orders", "total_amount", new_column_name="total_revenue_snapshot")
    op.alter_column("orders", "total_cost", new_column_name="total_cost_snapshot")
    op.alter_column("orders", "profit_amount", new_column_name="total_profit_snapshot")
    op.alter_column(
        "orders",
        "margin_percentage",
        new_column_name="margin_percentage_snapshot",
    )
    op.drop_column("orders", "subtotal")

    # --- Product line snapshots ---
    op.alter_column(
        "order_product_lines",
        "product_price_snapshot",
        new_column_name="product_selling_price_snapshot",
    )
    op.add_column(
        "order_product_lines",
        sa.Column("product_profit_snapshot", sa.Numeric(12, 2), nullable=True),
    )
    op.execute(
        """
        UPDATE order_product_lines
        SET product_profit_snapshot = product_selling_price_snapshot - product_cost_snapshot
        """
    )
    op.alter_column("order_product_lines", "product_profit_snapshot", nullable=False)

    # --- Collection line snapshots ---
    op.alter_column(
        "order_collection_lines",
        "collection_price_snapshot",
        new_column_name="collection_selling_price_snapshot",
    )
    op.add_column(
        "order_collection_lines",
        sa.Column("collection_profit_snapshot", sa.Numeric(12, 2), nullable=True),
    )
    op.execute(
        """
        UPDATE order_collection_lines
        SET collection_profit_snapshot = collection_selling_price_snapshot - collection_cost_snapshot
        """
    )
    op.alter_column("order_collection_lines", "collection_profit_snapshot", nullable=False)


def downgrade() -> None:
    op.drop_column("order_collection_lines", "collection_profit_snapshot")
    op.alter_column(
        "order_collection_lines",
        "collection_selling_price_snapshot",
        new_column_name="collection_price_snapshot",
    )

    op.drop_column("order_product_lines", "product_profit_snapshot")
    op.alter_column(
        "order_product_lines",
        "product_selling_price_snapshot",
        new_column_name="product_price_snapshot",
    )

    op.add_column(
        "orders",
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=True),
    )
    op.execute(
        """
        UPDATE orders
        SET subtotal = products_subtotal_snapshot + collections_subtotal_snapshot
        """
    )
    op.alter_column("orders", "subtotal", nullable=False)

    op.alter_column(
        "orders",
        "margin_percentage_snapshot",
        new_column_name="margin_percentage",
    )
    op.alter_column("orders", "total_profit_snapshot", new_column_name="profit_amount")
    op.alter_column("orders", "total_cost_snapshot", new_column_name="total_cost")
    op.alter_column("orders", "total_revenue_snapshot", new_column_name="total_amount")
    op.alter_column(
        "orders",
        "collections_subtotal_snapshot",
        new_column_name="collections_subtotal",
    )
    op.alter_column(
        "orders",
        "products_subtotal_snapshot",
        new_column_name="products_subtotal",
    )
