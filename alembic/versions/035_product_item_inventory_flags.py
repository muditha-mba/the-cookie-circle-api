"""Product item inventory tracking flags.

Revision ID: 035_product_item_inventory_flags
Revises: 034_packaging_cost_requires_fee
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "035_product_item_inventory_flags"
down_revision: Union[str, None] = "034_packaging_cost_requires_fee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "product_items",
        sa.Column("track_inventory", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "product_items",
        sa.Column("reorder_level", sa.Numeric(precision=12, scale=4), nullable=True),
    )
    op.add_column(
        "product_items",
        sa.Column("reorder_unit", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("product_items", "reorder_unit")
    op.drop_column("product_items", "reorder_level")
    op.drop_column("product_items", "track_inventory")
