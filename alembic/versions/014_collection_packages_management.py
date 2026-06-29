"""Introduce managed collection packages.

Revision ID: 014_collection_pkg_mgmt
Revises: 013_collection_package_category
Create Date: 2026-06-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014_collection_pkg_mgmt"
down_revision: Union[str, None] = "013_collection_package_category"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "collection_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("badge_tone", sa.String(length=32), nullable=False, server_default="violet"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_collection_packages_code", "collection_packages", ["code"], unique=True)
    op.create_index("ix_collection_packages_name", "collection_packages", ["name"], unique=True)

    op.execute(
        """
        INSERT INTO collection_packages (id, code, name, description, badge_tone, is_active)
        VALUES
            ('b7be0f1a-0d3b-4f9d-abf1-7d5ec3b50331', 'SPECIAL_EDITION', 'Special Edition', 'Premium and curated gift collections.', 'violet', true),
            ('993e3b84-3cc8-4265-a1a1-b865857f7452', 'MIX_AND_MATCH', 'Mix & Match', 'Flexible mixed bundles with premium limits.', 'blue', true),
            ('a087f684-f9e1-4e87-9d7f-64cbf9d7f9cc', 'BUTTER_COLLECTION', 'Butter Collection', 'Tea-time butter cookie focused bundles.', 'amber', true)
        ON CONFLICT (code) DO NOTHING
        """
    )

    op.add_column("collections", sa.Column("package_id", sa.Uuid(), nullable=True))
    op.execute(
        """
        UPDATE collections c
        SET package_id = cp.id
        FROM collection_packages cp
        WHERE cp.code = c.package_category
        """
    )
    op.alter_column("collections", "package_id", nullable=False)
    op.create_index("ix_collections_package_id", "collections", ["package_id"])
    op.create_foreign_key(
        "fk_collections_package_id",
        "collections",
        "collection_packages",
        ["package_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_index("ix_collections_package_category", table_name="collections")
    op.drop_column("collections", "package_category")
    sa.Enum(
        "SPECIAL_EDITION",
        "MIX_AND_MATCH",
        "BUTTER_COLLECTION",
        name="collection_package_category",
        native_enum=False,
    ).drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    package_category = postgresql.ENUM(
        "SPECIAL_EDITION",
        "MIX_AND_MATCH",
        "BUTTER_COLLECTION",
        name="collection_package_category",
        create_type=False,
    )
    package_category.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "collections",
        sa.Column(
            "package_category",
            package_category,
            nullable=False,
            server_default="SPECIAL_EDITION",
        ),
    )
    op.create_index("ix_collections_package_category", "collections", ["package_category"])
    op.execute(
        """
        UPDATE collections c
        SET package_category = COALESCE(cp.code, 'SPECIAL_EDITION')
        FROM collection_packages cp
        WHERE c.package_id = cp.id
        """
    )

    op.drop_constraint("fk_collections_package_id", "collections", type_="foreignkey")
    op.drop_index("ix_collections_package_id", table_name="collections")
    op.drop_column("collections", "package_id")

    op.drop_index("ix_collection_packages_name", table_name="collection_packages")
    op.drop_index("ix_collection_packages_code", table_name="collection_packages")
    op.drop_table("collection_packages")
