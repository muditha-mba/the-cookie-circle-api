"""Add address column to suppliers.

Revision ID: 046_supplier_address
Revises: 045_webxpay_payment_sessions
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "046_supplier_address"
down_revision: Union[str, None] = "045_webxpay_payment_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("suppliers", sa.Column("address", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("suppliers", "address")
