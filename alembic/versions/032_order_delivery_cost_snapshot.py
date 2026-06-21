"""Add delivery cost snapshot and backfill order profitability.

Revision ID: 032_order_delivery_cost_snapshot
Revises: 031_faqs_section_enabled
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "032_order_delivery_cost_snapshot"
down_revision: Union[str, None] = "031_faqs_section_enabled"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "delivery_cost_snapshot",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )

    # Non-pickup delivery areas: estimated delivery cost equals charged fee.
    op.execute(
        sa.text(
            """
            UPDATE orders o
            SET delivery_cost_snapshot = o.delivery_fee_snapshot
            FROM delivery_areas da
            WHERE o.delivery_area_id = da.id
              AND da.pickup_only = false
              AND o.delivery_fee_snapshot > 0
            """
        ),
    )

    # Orders with a delivery fee but no linked area (legacy edge cases).
    op.execute(
        sa.text(
            """
            UPDATE orders
            SET delivery_cost_snapshot = delivery_fee_snapshot
            WHERE delivery_area_id IS NULL
              AND delivery_fee_snapshot > 0
            """
        ),
    )

    # Fold delivery cost into stored totals for affected orders.
    op.execute(
        sa.text(
            """
            UPDATE orders
            SET
              total_cost_snapshot = total_cost_snapshot + delivery_cost_snapshot,
              total_profit_snapshot = total_revenue_snapshot
                - (total_cost_snapshot + delivery_cost_snapshot),
              margin_percentage_snapshot = CASE
                WHEN total_revenue_snapshot > 0 THEN ROUND(
                  (
                    (total_revenue_snapshot - (total_cost_snapshot + delivery_cost_snapshot))
                    / total_revenue_snapshot
                  ) * 100,
                  2
                )
                ELSE 0
              END
            WHERE delivery_cost_snapshot > 0
            """
        ),
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE orders
            SET
              total_cost_snapshot = total_cost_snapshot - delivery_cost_snapshot,
              total_profit_snapshot = total_revenue_snapshot
                - (total_cost_snapshot - delivery_cost_snapshot),
              margin_percentage_snapshot = CASE
                WHEN total_revenue_snapshot > 0 THEN ROUND(
                  (
                    (total_revenue_snapshot - (total_cost_snapshot - delivery_cost_snapshot))
                    / total_revenue_snapshot
                  ) * 100,
                  2
                )
                ELSE 0
              END
            WHERE delivery_cost_snapshot > 0
            """
        ),
    )
    op.drop_column("orders", "delivery_cost_snapshot")
