"""Reconcile lot on-hand balances from movement history.

Revision ID: 041_reconcile_lot_balances
Revises: 040_purchase_receipt_attachments
"""

from typing import Sequence, Union

from alembic import op

revision: str = "041_reconcile_lot_balances"
down_revision: Union[str, None] = "040_purchase_receipt_attachments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Purchase receipt confirm previously seeded lot quantity then added a receipt
    # movement, doubling on-hand. Movement sums are the source of truth.
    op.execute(
        """
        UPDATE inventory_lots AS lot
        SET
            quantity_on_hand = COALESCE(movement_totals.total_change, 0),
            is_active = COALESCE(movement_totals.total_change, 0) > 0
        FROM (
            SELECT
                lot_id,
                SUM(quantity_change) AS total_change
            FROM inventory_movements
            GROUP BY lot_id
        ) AS movement_totals
        WHERE lot.id = movement_totals.lot_id
          AND lot.quantity_on_hand IS DISTINCT FROM COALESCE(movement_totals.total_change, 0)
        """,
    )


def downgrade() -> None:
    # Data repair is not reversible.
    pass
