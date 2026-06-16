"""Order packaging fee revenue and materials cost snapshots.

Revision ID: 033_order_packaging_snapshots
Revises: 032_order_delivery_cost_snapshot
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "033_order_packaging_snapshots"
down_revision: Union[str, None] = "032_order_delivery_cost_snapshot"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "package_fee_revenue_snapshot",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "packaging_cost_snapshot",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "order_collection_lines",
        sa.Column(
            "packaging_cost_snapshot",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE order_collection_lines ocl
            SET packaging_cost_snapshot = COALESCE(sub.unit_cost, 0)
            FROM (
                SELECT
                    ocl2.id AS line_id,
                    ROUND(
                        COALESCE(
                            SUM(
                                cil.quantity
                                * ROUND(
                                    pi.purchase_price / NULLIF(pi.purchase_quantity, 0),
                                    4
                                )
                            ),
                            0
                        ),
                        2
                    ) AS unit_cost
                FROM order_collection_lines ocl2
                JOIN collections c ON c.id = ocl2.collection_id
                LEFT JOIN collection_item_lines cil ON cil.collection_id = c.id
                LEFT JOIN product_items pi ON pi.id = cil.product_item_id
                GROUP BY ocl2.id
            ) sub
            WHERE ocl.id = sub.line_id
            """
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE orders o
            SET package_fee_revenue_snapshot = COALESCE(line_totals.fee_revenue, 0)
            FROM (
                SELECT
                    ocl.order_id,
                    ROUND(
                        COALESCE(
                            SUM(COALESCE(ocl.package_fee_snapshot, 0) * ocl.quantity),
                            0
                        ),
                        2
                    ) AS fee_revenue
                FROM order_collection_lines ocl
                GROUP BY ocl.order_id
            ) line_totals
            WHERE o.id = line_totals.order_id
            """
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE orders o
            SET packaging_cost_snapshot = COALESCE(line_totals.packaging_cost, 0)
            FROM (
                SELECT
                    ocl.order_id,
                    ROUND(
                        COALESCE(SUM(ocl.packaging_cost_snapshot * ocl.quantity), 0),
                        2
                    ) AS packaging_cost
                FROM order_collection_lines ocl
                GROUP BY ocl.order_id
            ) line_totals
            WHERE o.id = line_totals.order_id
            """
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE orders
            SET
              total_cost_snapshot = total_cost_snapshot + packaging_cost_snapshot,
              total_profit_snapshot = total_revenue_snapshot
                - (total_cost_snapshot + packaging_cost_snapshot),
              margin_percentage_snapshot = CASE
                WHEN total_revenue_snapshot > 0 THEN ROUND(
                  (
                    (total_revenue_snapshot - (total_cost_snapshot + packaging_cost_snapshot))
                    / total_revenue_snapshot
                  ) * 100,
                  2
                )
                ELSE 0
              END
            WHERE packaging_cost_snapshot > 0
            """
        ),
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE orders
            SET
              total_cost_snapshot = total_cost_snapshot - packaging_cost_snapshot,
              total_profit_snapshot = total_revenue_snapshot
                - (total_cost_snapshot - packaging_cost_snapshot),
              margin_percentage_snapshot = CASE
                WHEN total_revenue_snapshot > 0 THEN ROUND(
                  (
                    (total_revenue_snapshot - (total_cost_snapshot - packaging_cost_snapshot))
                    / total_revenue_snapshot
                  ) * 100,
                  2
                )
                ELSE 0
              END
            WHERE packaging_cost_snapshot > 0
            """
        ),
    )
    op.drop_column("order_collection_lines", "packaging_cost_snapshot")
    op.drop_column("orders", "packaging_cost_snapshot")
    op.drop_column("orders", "package_fee_revenue_snapshot")
