"""Add FAQ section visibility setting.

Revision ID: 031_faqs_section_enabled
Revises: 030_marketing_attribution
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "031_faqs_section_enabled"
down_revision: Union[str, None] = "030_marketing_attribution"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO business_settings (key, value, created_at, updated_at)
            VALUES ('faqs_enabled', 'true', now(), now())
            ON CONFLICT (key) DO NOTHING
            """
        ),
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM business_settings WHERE key = 'faqs_enabled'"),
    )
