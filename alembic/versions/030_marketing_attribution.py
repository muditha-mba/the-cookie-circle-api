"""Extend marketing sources and store first-touch attribution metadata.

Revision ID: 030_marketing_attribution
Revises: 029_admin_activity_logs
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "030_marketing_attribution"
down_revision: Union[str, None] = "029_admin_activity_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_MARKETING_SOURCES = (
    "tiktok",
    "linkedin",
    "youtube",
    "twitter",
    "pinterest",
    "email",
)


def upgrade() -> None:
    for value in _NEW_MARKETING_SOURCES:
        op.execute(sa.text(f"ALTER TYPE marketing_source ADD VALUE IF NOT EXISTS '{value}'"))

    op.add_column(
        "customers",
        sa.Column("marketing_attribution", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("customers", "marketing_attribution")
    # PostgreSQL enums cannot remove values safely without recreating the type.
