"""Add collection package category enum field.

Revision ID: 013_collection_package_category
Revises: 012_customer_crm
Create Date: 2026-06-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_collection_package_category"
down_revision: Union[str, None] = "012_customer_crm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "collections",
        sa.Column(
            "package_category",
            sa.Enum(
                "SPECIAL_EDITION",
                "MIX_AND_MATCH",
                "BUTTER_COLLECTION",
                name="collection_package_category",
                native_enum=False,
            ),
            nullable=False,
            server_default="SPECIAL_EDITION",
        ),
    )
    op.create_index("ix_collections_package_category", "collections", ["package_category"])

    op.execute(
        """
        UPDATE collections
        SET package_category = CASE
            WHEN name IN ('The Signature Circle', 'The Golden Circle', 'The Grand Circle')
                THEN 'SPECIAL_EDITION'
            WHEN name IN ('The Little Circle', 'The Family Circle', 'The Party Circle')
                THEN 'MIX_AND_MATCH'
            WHEN name IN ('The Tea Circle', 'The Warm Circle', 'The Gathering Circle')
                THEN 'BUTTER_COLLECTION'
            ELSE 'SPECIAL_EDITION'
        END
        """
    )


def downgrade() -> None:
    op.drop_index("ix_collections_package_category", table_name="collections")
    op.drop_column("collections", "package_category")
    sa.Enum(
        "SPECIAL_EDITION",
        "MIX_AND_MATCH",
        "BUTTER_COLLECTION",
        name="collection_package_category",
        native_enum=False,
    ).drop(op.get_bind(), checkfirst=True)
