"""Flexible collection ordering: min/max qty and packaging fee on collection_packages.

Revision ID: 047_flexible_collection_ordering
Revises: 046_supplier_address
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "047_flexible_collection_ordering"
down_revision: Union[str, None] = "046_supplier_address"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "collection_packages",
        sa.Column("min_quantity", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "collection_packages",
        sa.Column("max_quantity", sa.Integer(), nullable=False, server_default="30"),
    )
    op.add_column(
        "collection_packages",
        sa.Column(
            "packaging_fee_mode",
            sa.String(length=32),
            nullable=False,
            server_default="flat",
        ),
    )
    op.add_column(
        "collection_packages",
        sa.Column(
            "packaging_fee_amount",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )

    # Seed Special Edition packaging fee from existing collection.package_fee when present.
    op.execute(
        """
        UPDATE collection_packages AS cp
        SET packaging_fee_amount = COALESCE(
            (
                SELECT MAX(c.package_fee)
                FROM collections AS c
                WHERE c.package_id = cp.id
                  AND c.package_fee > 0
            ),
            0
        ),
        packaging_fee_mode = 'flat'
        WHERE cp.code = 'SPECIAL_EDITION'
        """
    )

    # Sensible defaults for Mix / Butter ranges (overrideable in admin).
    op.execute(
        """
        UPDATE collection_packages
        SET min_quantity = 4, max_quantity = 30
        WHERE code IN ('MIX_AND_MATCH', 'BUTTER_COLLECTION')
        """
    )
    op.execute(
        """
        UPDATE collection_packages
        SET min_quantity = 6, max_quantity = 24
        WHERE code = 'SPECIAL_EDITION'
        """
    )


def downgrade() -> None:
    op.drop_column("collection_packages", "packaging_fee_amount")
    op.drop_column("collection_packages", "packaging_fee_mode")
    op.drop_column("collection_packages", "max_quantity")
    op.drop_column("collection_packages", "min_quantity")
