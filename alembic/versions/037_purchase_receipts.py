"""Purchase receipts and link lots to receipt lines.

Revision ID: 037_purchase_receipts
Revises: 036_inventory_lots_and_movements
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "037_purchase_receipts"
down_revision: Union[str, None] = "036_inventory_lots_and_movements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

purchase_receipt_status = postgresql.ENUM(
    "draft",
    "confirmed",
    name="purchase_receipt_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    purchase_receipt_status.create(bind, checkfirst=True)

    op.create_table(
        "purchase_receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("receipt_date", sa.Date(), nullable=False),
        sa.Column("reference_number", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("bill_asset_id", sa.Uuid(), nullable=True),
        sa.Column("bill_content_type", sa.String(length=100), nullable=True),
        sa.Column("bill_extension", sa.String(length=20), nullable=True),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("status", purchase_receipt_status, nullable=False, server_default="draft"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by_user_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["confirmed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_receipts_supplier_id", "purchase_receipts", ["supplier_id"])
    op.create_index("ix_purchase_receipts_receipt_date", "purchase_receipts", ["receipt_date"])
    op.create_index("ix_purchase_receipts_status", "purchase_receipts", ["status"])

    op.create_table(
        "purchase_receipt_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("purchase_receipt_id", sa.Uuid(), nullable=False),
        sa.Column("product_item_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("unit_cost", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("line_total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("expires_at", sa.Date(), nullable=True),
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
        sa.ForeignKeyConstraint(["product_item_id"], ["product_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_purchase_receipt_lines_purchase_receipt_id",
        "purchase_receipt_lines",
        ["purchase_receipt_id"],
    )
    op.create_index(
        "ix_purchase_receipt_lines_product_item_id",
        "purchase_receipt_lines",
        ["product_item_id"],
    )

    op.create_foreign_key(
        "fk_inventory_lots_purchase_receipt_line_id",
        "inventory_lots",
        "purchase_receipt_lines",
        ["purchase_receipt_line_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_inventory_lots_purchase_receipt_line_id",
        "inventory_lots",
        ["purchase_receipt_line_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_constraint("fk_inventory_lots_purchase_receipt_line_id", "inventory_lots", type_="foreignkey")
    op.drop_index("ix_inventory_lots_purchase_receipt_line_id", table_name="inventory_lots")
    op.drop_table("purchase_receipt_lines")
    op.drop_table("purchase_receipts")
    purchase_receipt_status.drop(op.get_bind(), checkfirst=True)
