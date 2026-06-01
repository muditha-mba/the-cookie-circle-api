"""Charge applicability and collections foundation.

Revision ID: 006_collections_foundation
Revises: 005_product_production
Create Date: 2026-06-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_collections_foundation"
down_revision: Union[str, None] = "005_product_production"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

charge_applicability_enum = postgresql.ENUM(
    "product",
    "collection",
    "both",
    name="charge_applicability",
    create_type=False,
)


def upgrade() -> None:
    charge_applicability_enum.create(op.get_bind(), checkfirst=True)

    for table in ("utility_charges", "labour_charges", "tax_charges"):
        op.add_column(
            table,
            sa.Column(
                "applicability",
                charge_applicability_enum,
                nullable=False,
                server_default="both",
            ),
        )

    op.execute(
        "UPDATE utility_charges SET applicability = 'product' WHERE name = 'Electricity'",
    )
    op.execute(
        "UPDATE labour_charges SET applicability = 'product' WHERE name = 'Preparation Labour'",
    )
    op.execute(
        "UPDATE labour_charges SET applicability = 'collection' WHERE name = 'Packaging Labour'",
    )
    op.execute(
        "UPDATE tax_charges SET applicability = 'both' WHERE name IN ('VAT', 'Marketplace Fee')",
    )

    op.create_table(
        "collections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("selling_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("buffer_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
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
    op.create_index("ix_collections_name", "collections", ["name"], unique=True)

    op.create_table(
        "collection_product_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
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
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collection_id", "product_id", name="uq_collection_product"),
    )
    op.create_index(
        "ix_collection_product_lines_collection_id",
        "collection_product_lines",
        ["collection_id"],
    )
    op.create_index(
        "ix_collection_product_lines_product_id",
        "collection_product_lines",
        ["product_id"],
    )

    op.create_table(
        "collection_utility_charges",
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("utility_charge_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["utility_charge_id"], ["utility_charges.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("collection_id", "utility_charge_id"),
    )

    op.create_table(
        "collection_labour_charges",
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("labour_charge_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["labour_charge_id"], ["labour_charges.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("collection_id", "labour_charge_id"),
    )

    op.create_table(
        "collection_tax_charges",
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("tax_charge_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tax_charge_id"], ["tax_charges.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("collection_id", "tax_charge_id"),
    )


def downgrade() -> None:
    op.drop_table("collection_tax_charges")
    op.drop_table("collection_labour_charges")
    op.drop_table("collection_utility_charges")
    op.drop_index("ix_collection_product_lines_product_id", table_name="collection_product_lines")
    op.drop_index(
        "ix_collection_product_lines_collection_id",
        table_name="collection_product_lines",
    )
    op.drop_table("collection_product_lines")
    op.drop_index("ix_collections_name", table_name="collections")
    op.drop_table("collections")

    for table in ("tax_charges", "labour_charges", "utility_charges"):
        op.drop_column(table, "applicability")

    charge_applicability_enum.drop(op.get_bind(), checkfirst=True)
