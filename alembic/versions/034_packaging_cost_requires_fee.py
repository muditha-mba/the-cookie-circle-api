"""Only charge packaging materials cost when a package fee applies.

Revision ID: 034_packaging_cost_requires_fee
Revises: 033_order_packaging_snapshots
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "034_packaging_cost_requires_fee"
down_revision: Union[str, None] = "033_order_packaging_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE order_collection_lines
            SET packaging_cost_snapshot = 0
            WHERE COALESCE(package_fee_snapshot, 0) = 0
            """
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE orders o
            SET
              packaging_cost_snapshot = COALESCE(sub.new_packaging, 0),
              total_cost_snapshot = o.total_cost_snapshot
                - o.packaging_cost_snapshot
                + COALESCE(sub.new_packaging, 0),
              total_profit_snapshot = o.total_revenue_snapshot
                - (
                  o.total_cost_snapshot
                  - o.packaging_cost_snapshot
                  + COALESCE(sub.new_packaging, 0)
                ),
              margin_percentage_snapshot = CASE
                WHEN o.total_revenue_snapshot > 0 THEN ROUND(
                  (
                    (
                      o.total_revenue_snapshot
                      - (
                        o.total_cost_snapshot
                        - o.packaging_cost_snapshot
                        + COALESCE(sub.new_packaging, 0)
                      )
                    )
                    / o.total_revenue_snapshot
                  ) * 100,
                  2
                )
                ELSE 0
              END
            FROM (
                SELECT
                    ocl.order_id,
                    ROUND(
                        COALESCE(SUM(ocl.packaging_cost_snapshot * ocl.quantity), 0),
                        2
                    ) AS new_packaging
                FROM order_collection_lines ocl
                GROUP BY ocl.order_id
            ) sub
            WHERE o.id = sub.order_id
            """
        ),
    )


def downgrade() -> None:
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
            SET
              packaging_cost_snapshot = COALESCE(sub.new_packaging, 0),
              total_cost_snapshot = o.total_cost_snapshot
                - o.packaging_cost_snapshot
                + COALESCE(sub.new_packaging, 0),
              total_profit_snapshot = o.total_revenue_snapshot
                - (
                  o.total_cost_snapshot
                  - o.packaging_cost_snapshot
                  + COALESCE(sub.new_packaging, 0)
                ),
              margin_percentage_snapshot = CASE
                WHEN o.total_revenue_snapshot > 0 THEN ROUND(
                  (
                    (
                      o.total_revenue_snapshot
                      - (
                        o.total_cost_snapshot
                        - o.packaging_cost_snapshot
                        + COALESCE(sub.new_packaging, 0)
                      )
                    )
                    / o.total_revenue_snapshot
                  ) * 100,
                  2
                )
                ELSE 0
              END
            FROM (
                SELECT
                    ocl.order_id,
                    ROUND(
                        COALESCE(SUM(ocl.packaging_cost_snapshot * ocl.quantity), 0),
                        2
                    ) AS new_packaging
                FROM order_collection_lines ocl
                GROUP BY ocl.order_id
            ) sub
            WHERE o.id = sub.order_id
            """
        ),
    )
