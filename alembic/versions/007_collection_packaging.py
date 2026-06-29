"""Collection packaging item lines.

Revision ID: 007_collection_packaging
Revises: 006_collections_foundation
Create Date: 2026-06-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_collection_packaging"
down_revision: Union[str, None] = "006_collections_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "collection_item_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("product_item_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["product_item_id"], ["product_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "collection_id",
            "product_item_id",
            name="uq_collection_item_line",
        ),
    )
    op.create_index(
        "ix_collection_item_lines_collection_id",
        "collection_item_lines",
        ["collection_id"],
    )
    op.create_index(
        "ix_collection_item_lines_product_item_id",
        "collection_item_lines",
        ["product_item_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_collection_item_lines_product_item_id", table_name="collection_item_lines")
    op.drop_index("ix_collection_item_lines_collection_id", table_name="collection_item_lines")
    op.drop_table("collection_item_lines")
