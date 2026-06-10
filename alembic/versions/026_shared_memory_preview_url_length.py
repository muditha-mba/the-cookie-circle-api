"""Increase shared memory preview image URL length for CDN links.

Revision ID: 026_sm_preview_url
Revises: 025_shared_memories
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "026_sm_preview_url"
down_revision: Union[str, None] = "025_shared_memories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "shared_memories",
        "preview_image_url",
        existing_type=sa.String(length=500),
        type_=sa.String(length=2000),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "shared_memories",
        "preview_image_url",
        existing_type=sa.String(length=2000),
        type_=sa.String(length=500),
        existing_nullable=False,
    )
