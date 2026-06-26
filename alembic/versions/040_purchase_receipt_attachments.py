"""Purchase receipt attachments table and legacy bill migration.

Revision ID: 040_purchase_receipt_attachments
Revises: 039_order_inventory_consumed
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "040_purchase_receipt_attachments"
down_revision: Union[str, None] = "039_order_inventory_consumed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "purchase_receipt_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("purchase_receipt_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("extension", sa.String(length=20), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["purchase_receipt_id"],
            ["purchase_receipts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_purchase_receipt_attachments_purchase_receipt_id",
        "purchase_receipt_attachments",
        ["purchase_receipt_id"],
    )

    op.execute(
        """
        INSERT INTO purchase_receipt_attachments (
            id,
            purchase_receipt_id,
            asset_id,
            content_type,
            extension,
            file_name,
            sort_order,
            created_at,
            updated_at
        )
        SELECT
            gen_random_uuid(),
            id,
            bill_asset_id,
            COALESCE(bill_content_type, 'application/octet-stream'),
            bill_extension,
            'Supplier bill',
            0,
            created_at,
            updated_at
        FROM purchase_receipts
        WHERE bill_asset_id IS NOT NULL
          AND bill_extension IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_purchase_receipt_attachments_purchase_receipt_id",
        table_name="purchase_receipt_attachments",
    )
    op.drop_table("purchase_receipt_attachments")
