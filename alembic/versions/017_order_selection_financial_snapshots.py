"""Per-cookie and package fee snapshots on order collection lines.

Revision ID: 017_selection_snapshots
Revises: 016_package_builder
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "017_selection_snapshots"
down_revision: Union[str, None] = "016_package_builder"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "order_collection_lines",
        sa.Column("package_fee_snapshot", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "order_collection_line_selections",
        sa.Column("product_selling_price_snapshot", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "order_collection_line_selections",
        sa.Column("product_cost_snapshot", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "order_collection_line_selections",
        sa.Column("product_profit_snapshot", sa.Numeric(12, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("order_collection_line_selections", "product_profit_snapshot")
    op.drop_column("order_collection_line_selections", "product_cost_snapshot")
    op.drop_column("order_collection_line_selections", "product_selling_price_snapshot")
    op.drop_column("order_collection_lines", "package_fee_snapshot")
