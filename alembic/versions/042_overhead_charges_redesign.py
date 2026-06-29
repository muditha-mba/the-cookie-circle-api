"""Overhead charges redesign: utility/labour to monthly bills, tax to order-level.

Changes:
- Drop product_utility_charges, product_labour_charges, product_tax_charges
- Drop collection_utility_charges, collection_labour_charges, collection_tax_charges
- Drop amount/charge_type/applicability from utility_charges and labour_charges
- Drop applicability from tax_charges (keep charge_type + amount for order-level tax)
- Create utility_bill_entries and labour_bill_entries (monthly overhead records)
- Add total_tax_snapshot and tax_lines_snapshot to orders

Revision ID: 042_overhead_charges_redesign
Revises: 041_reconcile_lot_balances
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "042_overhead_charges_redesign"
down_revision: Union[str, None] = "041_reconcile_lot_balances"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop all charge association tables
    op.drop_table("product_utility_charges")
    op.drop_table("product_labour_charges")
    op.drop_table("product_tax_charges")
    op.drop_table("collection_utility_charges")
    op.drop_table("collection_labour_charges")
    op.drop_table("collection_tax_charges")

    # 2. Simplify utility_charges: remove per-unit cost fields
    op.drop_column("utility_charges", "charge_type")
    op.drop_column("utility_charges", "amount")
    op.drop_column("utility_charges", "applicability")

    # 3. Simplify labour_charges: same
    op.drop_column("labour_charges", "charge_type")
    op.drop_column("labour_charges", "amount")
    op.drop_column("labour_charges", "applicability")

    # 4. Simplify tax_charges: remove applicability (keep charge_type + amount for order calc)
    op.drop_column("tax_charges", "applicability")

    # 5. Create utility_bill_entries
    op.create_table(
        "utility_bill_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("utility_charge_id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("month", sa.SmallInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["utility_charge_id"],
            ["utility_charges.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("utility_charge_id", "year", "month", name="uq_utility_bill_per_month"),
        sa.CheckConstraint("year >= 2020 AND year <= 2100", name="ck_utility_bill_year"),
        sa.CheckConstraint("month >= 1 AND month <= 12", name="ck_utility_bill_month"),
        sa.CheckConstraint("amount >= 0", name="ck_utility_bill_amount"),
    )
    op.create_index("ix_utility_bill_entries_charge_id", "utility_bill_entries", ["utility_charge_id"])

    # 6. Create labour_bill_entries
    op.create_table(
        "labour_bill_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("labour_charge_id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("month", sa.SmallInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["labour_charge_id"],
            ["labour_charges.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("labour_charge_id", "year", "month", name="uq_labour_bill_per_month"),
        sa.CheckConstraint("year >= 2020 AND year <= 2100", name="ck_labour_bill_year"),
        sa.CheckConstraint("month >= 1 AND month <= 12", name="ck_labour_bill_month"),
        sa.CheckConstraint("amount >= 0", name="ck_labour_bill_amount"),
    )
    op.create_index("ix_labour_bill_entries_charge_id", "labour_bill_entries", ["labour_charge_id"])

    # 7. Add tax snapshot columns to orders
    op.add_column(
        "orders",
        sa.Column(
            "total_tax_snapshot",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "tax_lines_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )

    # Existing orders: total_revenue already excludes tax (no tax was applied before)
    # total_tax_snapshot = 0, tax_lines_snapshot = [] — correct defaults above


def downgrade() -> None:
    # Restore order columns
    op.drop_column("orders", "tax_lines_snapshot")
    op.drop_column("orders", "total_tax_snapshot")

    # Drop new bill entry tables
    op.drop_table("labour_bill_entries")
    op.drop_table("utility_bill_entries")

    # Restore tax_charges applicability (best-effort, data lost)
    charge_applicability_enum = postgresql.ENUM(
        "product", "collection", "both", name="chargeapplicability", create_type=False
    )
    op.add_column(
        "tax_charges",
        sa.Column("applicability", charge_applicability_enum, nullable=True),
    )
    op.execute("UPDATE tax_charges SET applicability = 'both'")
    op.alter_column("tax_charges", "applicability", nullable=False)

    # Restore utility_charges columns (data lost)
    charge_type_enum = postgresql.ENUM("fixed", "percentage", name="chargetype", create_type=False)
    for table in ("utility_charges", "labour_charges"):
        op.add_column(table, sa.Column("charge_type", charge_type_enum, nullable=True))
        op.add_column(table, sa.Column("amount", sa.Numeric(12, 4), nullable=True))
        op.add_column(
            table,
            sa.Column("applicability", charge_applicability_enum, nullable=True),
        )
        op.execute(f"UPDATE {table} SET charge_type='fixed', amount=0, applicability='both'")
        op.alter_column(table, "charge_type", nullable=False)
        op.alter_column(table, "amount", nullable=False)
        op.alter_column(table, "applicability", nullable=False)

    # Restore association tables (empty)
    op.create_table(
        "product_utility_charges",
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("utility_charge_id", sa.Uuid(), sa.ForeignKey("utility_charges.id", ondelete="RESTRICT"), primary_key=True),
    )
    op.create_table(
        "product_labour_charges",
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("labour_charge_id", sa.Uuid(), sa.ForeignKey("labour_charges.id", ondelete="RESTRICT"), primary_key=True),
    )
    op.create_table(
        "product_tax_charges",
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tax_charge_id", sa.Uuid(), sa.ForeignKey("tax_charges.id", ondelete="RESTRICT"), primary_key=True),
    )
    op.create_table(
        "collection_utility_charges",
        sa.Column("collection_id", sa.Uuid(), sa.ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("utility_charge_id", sa.Uuid(), sa.ForeignKey("utility_charges.id", ondelete="RESTRICT"), primary_key=True),
    )
    op.create_table(
        "collection_labour_charges",
        sa.Column("collection_id", sa.Uuid(), sa.ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("labour_charge_id", sa.Uuid(), sa.ForeignKey("labour_charges.id", ondelete="RESTRICT"), primary_key=True),
    )
    op.create_table(
        "collection_tax_charges",
        sa.Column("collection_id", sa.Uuid(), sa.ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tax_charge_id", sa.Uuid(), sa.ForeignKey("tax_charges.id", ondelete="RESTRICT"), primary_key=True),
    )
