"""Add shared memories table and section visibility setting.

Revision ID: 025_shared_memories
Revises: 024_faq_categories
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "025_shared_memories"
down_revision: Union[str, None] = "024_faq_categories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shared_memories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), server_default="", nullable=False),
        sa.Column("preview_image_url", sa.String(length=500), nullable=False),
        sa.Column("post_url", sa.String(length=500), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shared_memories_platform"), "shared_memories", ["platform"], unique=False)

    op.execute(
        sa.text(
            """
            INSERT INTO business_settings (key, value, created_at, updated_at)
            VALUES ('shared_memories_enabled', 'false', now(), now())
            ON CONFLICT (key) DO NOTHING
            """
        ),
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM business_settings WHERE key = 'shared_memories_enabled'"),
    )
    op.drop_index(op.f("ix_shared_memories_platform"), table_name="shared_memories")
    op.drop_table("shared_memories")
