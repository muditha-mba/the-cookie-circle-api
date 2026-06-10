"""Add admin_role for super-admin vs clerk-admin access.

Revision ID: 028_admin_role
Revises: 027_user_token_version
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "028_admin_role"
down_revision: Union[str, None] = "027_user_token_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

admin_role_enum = sa.Enum(
    "super_admin",
    "clerk_admin",
    name="admin_role",
)


def upgrade() -> None:
    admin_role_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column("admin_role", admin_role_enum, nullable=True),
    )
    op.execute(
        "UPDATE users SET admin_role = 'super_admin' WHERE role = 'ADMIN'",
    )


def downgrade() -> None:
    op.drop_column("users", "admin_role")
    admin_role_enum.drop(op.get_bind(), checkfirst=True)
