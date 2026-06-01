"""Procurement and purchase planning foundation.

Revision ID: 011_procurement_foundation
Revises: 010_order_profit_snapshots
Create Date: 2026-06-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011_procurement_foundation"
down_revision: Union[str, None] = "010_order_profit_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

production_batch_status = postgresql.ENUM(
    "draft",
    "planning",
    "ready",
    name="production_batch_status",
    create_type=False,
)

purchase_planning_status = postgresql.ENUM(
    "not_planned",
    "planned",
    "ordered",
    name="purchase_planning_status",
    create_type=False,
)


def upgrade() -> None:
    production_batch_status.create(op.get_bind(), checkfirst=True)
    purchase_planning_status.create(op.get_bind(), checkfirst=True)

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "suppliers" not in existing_tables:
        op.create_table(
            "suppliers",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("supplier_name", sa.String(length=200), nullable=False),
            sa.Column("contact_person", sa.String(length=200), nullable=True),
            sa.Column("email", sa.String(length=320), nullable=True),
            sa.Column("phone", sa.String(length=50), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("supplier_name", name="uq_suppliers_supplier_name"),
        )
        op.create_index("ix_suppliers_supplier_name", "suppliers", ["supplier_name"])

    product_item_columns = {c["name"] for c in inspector.get_columns("product_items")}
    if "primary_supplier_id" not in product_item_columns:
        op.add_column(
            "product_items",
            sa.Column("primary_supplier_id", sa.Uuid(), nullable=True),
        )
        op.create_foreign_key(
            "fk_product_items_primary_supplier_id",
            "product_items",
            "suppliers",
            ["primary_supplier_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(
            "ix_product_items_primary_supplier_id",
            "product_items",
            ["primary_supplier_id"],
        )

    if "production_batches" not in existing_tables:
        op.create_table(
            "production_batches",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("delivery_date", sa.Date(), nullable=False),
            sa.Column(
                "status",
                production_batch_status,
                nullable=False,
                server_default="draft",
            ),
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
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("delivery_date", name="uq_production_batches_delivery_date"),
        )
        op.create_index(
            "ix_production_batches_delivery_date",
            "production_batches",
            ["delivery_date"],
        )

    if "production_batch_purchase_items" not in existing_tables:
        op.create_table(
            "production_batch_purchase_items",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("production_batch_id", sa.Uuid(), nullable=False),
            sa.Column("product_item_id", sa.Uuid(), nullable=False),
            sa.Column(
                "purchase_status",
                purchase_planning_status,
                nullable=False,
                server_default="not_planned",
            ),
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
                ["production_batch_id"],
                ["production_batches.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["product_item_id"],
                ["product_items.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "production_batch_id",
                "product_item_id",
                name="uq_batch_purchase_item_batch_product",
            ),
        )
        op.create_index(
            "ix_production_batch_purchase_items_batch_id",
            "production_batch_purchase_items",
            ["production_batch_id"],
        )


def downgrade() -> None:
    op.drop_index(
        "ix_production_batch_purchase_items_batch_id",
        table_name="production_batch_purchase_items",
    )
    op.drop_table("production_batch_purchase_items")
    op.drop_index("ix_production_batches_delivery_date", table_name="production_batches")
    op.drop_table("production_batches")
    op.drop_index("ix_product_items_primary_supplier_id", table_name="product_items")
    op.drop_constraint(
        "fk_product_items_primary_supplier_id",
        "product_items",
        type_="foreignkey",
    )
    op.drop_column("product_items", "primary_supplier_id")
    op.drop_index("ix_suppliers_supplier_name", table_name="suppliers")
    op.drop_table("suppliers")
    purchase_planning_status.drop(op.get_bind(), checkfirst=True)
    production_batch_status.drop(op.get_bind(), checkfirst=True)
