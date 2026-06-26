"""Consumption proposals and related tables.

Revision ID: 038_consumption_proposals
Revises: 037_purchase_receipts
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "038_consumption_proposals"
down_revision: Union[str, None] = "037_purchase_receipts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

consumption_proposal_status = postgresql.ENUM(
    "pending_review",
    "approved",
    "dismissed",
    name="consumption_proposal_status",
    create_type=False,
)

consumption_demand_type = postgresql.ENUM(
    "ingredient",
    "packaging",
    name="consumption_demand_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    consumption_proposal_status.create(bind, checkfirst=True)
    consumption_demand_type.create(bind, checkfirst=True)

    op.execute(
        sa.text(
            "ALTER TYPE activity_resource_type ADD VALUE IF NOT EXISTS 'consumption_proposal'",
        ),
    )

    op.create_table(
        "inventory_consumption_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("delivery_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            consumption_proposal_status,
            nullable=False,
            server_default="pending_review",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inventory_consumption_proposals_delivery_date",
        "inventory_consumption_proposals",
        ["delivery_date"],
    )
    op.create_index(
        "ix_inventory_consumption_proposals_status",
        "inventory_consumption_proposals",
        ["status"],
    )

    op.create_table(
        "inventory_consumption_proposal_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("product_item_id", sa.Uuid(), nullable=False),
        sa.Column("demand_type", consumption_demand_type, nullable=False),
        sa.Column("quantity_proposed", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("quantity_approved", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("quantity_on_hand_snapshot", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("track_inventory", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("has_shortfall", sa.Boolean(), nullable=False, server_default="false"),
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
            ["proposal_id"],
            ["inventory_consumption_proposals.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["product_item_id"], ["product_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inventory_consumption_proposal_lines_proposal_id",
        "inventory_consumption_proposal_lines",
        ["proposal_id"],
    )
    op.create_index(
        "ix_inventory_consumption_proposal_lines_product_item_id",
        "inventory_consumption_proposal_lines",
        ["product_item_id"],
    )

    op.create_table(
        "inventory_consumption_proposal_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
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
            ["proposal_id"],
            ["inventory_consumption_proposals.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_consumption_proposal_orders_order_id"),
    )
    op.create_index(
        "ix_inventory_consumption_proposal_orders_proposal_id",
        "inventory_consumption_proposal_orders",
        ["proposal_id"],
    )

    op.create_table(
        "inventory_consumption_proposal_lot_allocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_line_id", sa.Uuid(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=False),
        sa.Column("lot_code", sa.String(length=100), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=False),
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
            ["proposal_line_id"],
            ["inventory_consumption_proposal_lines.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["lot_id"], ["inventory_lots.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_consumption_proposal_lot_allocations_line_id",
        "inventory_consumption_proposal_lot_allocations",
        ["proposal_line_id"],
    )


def downgrade() -> None:
    op.drop_table("inventory_consumption_proposal_lot_allocations")
    op.drop_table("inventory_consumption_proposal_orders")
    op.drop_table("inventory_consumption_proposal_lines")
    op.drop_table("inventory_consumption_proposals")
    consumption_demand_type.drop(op.get_bind(), checkfirst=True)
    consumption_proposal_status.drop(op.get_bind(), checkfirst=True)
