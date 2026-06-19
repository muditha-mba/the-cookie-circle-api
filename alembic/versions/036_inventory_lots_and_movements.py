"""Inventory lots and movement ledger.

Revision ID: 036_inventory_lots_and_movements
Revises: 035_product_item_inventory_flags
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "036_inventory_lots_and_movements"
down_revision: Union[str, None] = "035_product_item_inventory_flags"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

inventory_movement_type = postgresql.ENUM(
    "receipt",
    "adjustment",
    "waste",
    "consumption",
    name="inventory_movement_type",
    create_type=False,
)

inventory_movement_reference_type = postgresql.ENUM(
    "purchase_receipt",
    "manual",
    "consumption_proposal",
    name="inventory_movement_reference_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    inventory_movement_type.create(bind, checkfirst=True)
    inventory_movement_reference_type.create(bind, checkfirst=True)

    for value in ("inventory_lot", "inventory_movement", "purchase_receipt"):
        op.execute(sa.text(f"ALTER TYPE activity_resource_type ADD VALUE IF NOT EXISTS '{value}'"))

    op.create_table(
        "inventory_lots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_item_id", sa.Uuid(), nullable=False),
        sa.Column("lot_code", sa.String(length=100), nullable=False),
        sa.Column("quantity_on_hand", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("purchase_receipt_line_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["product_item_id"], ["product_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_lots_product_item_id", "inventory_lots", ["product_item_id"])
    op.create_index("ix_inventory_lots_lot_code", "inventory_lots", ["lot_code"])
    op.create_index("ix_inventory_lots_expires_at", "inventory_lots", ["expires_at"])

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=False),
        sa.Column("movement_type", inventory_movement_type, nullable=False),
        sa.Column("quantity_change", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("reference_type", inventory_movement_reference_type, nullable=False),
        sa.Column("reference_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["lot_id"], ["inventory_lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_movements_lot_id", "inventory_movements", ["lot_id"])
    op.create_index("ix_inventory_movements_movement_type", "inventory_movements", ["movement_type"])
    op.create_index("ix_inventory_movements_reference_id", "inventory_movements", ["reference_id"])


def downgrade() -> None:
    op.drop_table("inventory_movements")
    op.drop_table("inventory_lots")
    inventory_movement_reference_type.drop(op.get_bind(), checkfirst=True)
    inventory_movement_type.drop(op.get_bind(), checkfirst=True)
