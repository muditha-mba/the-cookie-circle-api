"""Product production fields: yield quantity and production notes.

Revision ID: 005_product_production
Revises: 004_products_foundation
Create Date: 2026-06-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_product_production"
down_revision: Union[str, None] = "004_products_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "yield_quantity",
            sa.Numeric(12, 4),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "products",
        sa.Column("production_notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("products", "production_notes")
    op.drop_column("products", "yield_quantity")
