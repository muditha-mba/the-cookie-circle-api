"""Add billing address snapshots to orders.

Revision ID: 018_order_billing_address
Revises: 017_selection_snapshots
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "018_order_billing_address"
down_revision: Union[str, None] = "017_selection_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "billing_same_as_shipping",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "orders",
        sa.Column("billing_address_line_1", sa.String(255), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("billing_address_line_2", sa.String(255), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("billing_city", sa.String(100), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("billing_postal_code", sa.String(20), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("billing_landmark", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orders", "billing_landmark")
    op.drop_column("orders", "billing_postal_code")
    op.drop_column("orders", "billing_city")
    op.drop_column("orders", "billing_address_line_2")
    op.drop_column("orders", "billing_address_line_1")
    op.drop_column("orders", "billing_same_as_shipping")
