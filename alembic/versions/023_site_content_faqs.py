"""Add FAQs table for client site content.

Revision ID: 023_site_content_faqs
Revises: 022_granular_delivery_areas
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "023_site_content_faqs"
down_revision: Union[str, None] = "022_granular_delivery_areas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "faqs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.String(length=300), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
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
    )


def downgrade() -> None:
    op.drop_table("faqs")
