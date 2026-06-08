"""Global utility, labour, and tax charge tables.

Revision ID: 003_global_cost_foundation
Revises: 002_product_items_foundation
Create Date: 2026-06-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_global_cost_foundation"
down_revision: Union[str, None] = "002_product_items_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

charge_type_enum = postgresql.ENUM(
    "fixed",
    "percentage",
    name="charge_type",
    create_type=False,
)


def _charge_table(name: str) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("charge_type", charge_type_enum, nullable=False),
        sa.Column("amount", sa.Numeric(12, 4), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.UniqueConstraint("name"),
    )
    op.create_index(f"ix_{name}_name", name, ["name"], unique=True)


def upgrade() -> None:
    charge_type_enum.create(op.get_bind(), checkfirst=True)
    _charge_table("utility_charges")
    _charge_table("labour_charges")
    _charge_table("tax_charges")


def downgrade() -> None:
    op.drop_index("ix_tax_charges_name", table_name="tax_charges")
    op.drop_table("tax_charges")
    op.drop_index("ix_labour_charges_name", table_name="labour_charges")
    op.drop_table("labour_charges")
    op.drop_index("ix_utility_charges_name", table_name="utility_charges")
    op.drop_table("utility_charges")
    charge_type_enum.drop(op.get_bind(), checkfirst=True)
