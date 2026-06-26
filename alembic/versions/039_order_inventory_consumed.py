"""Order inventory consumption tracking columns.

Revision ID: 039_order_inventory_consumed
Revises: 038_consumption_proposals
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "039_order_inventory_consumed"
down_revision: Union[str, None] = "038_consumption_proposals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("inventory_consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("inventory_consumption_proposal_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_orders_inventory_consumption_proposal_id",
        "orders",
        "inventory_consumption_proposals",
        ["inventory_consumption_proposal_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_orders_inventory_consumption_proposal_id",
        "orders",
        ["inventory_consumption_proposal_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_orders_inventory_consumption_proposal_id", table_name="orders")
    op.drop_constraint("fk_orders_inventory_consumption_proposal_id", "orders", type_="foreignkey")
    op.drop_column("orders", "inventory_consumption_proposal_id")
    op.drop_column("orders", "inventory_consumed_at")
