"""Add admin_activity_logs for super-admin audit trail.

Revision ID: 029_admin_activity_logs
Revises: 028_admin_role
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "029_admin_activity_logs"
down_revision: Union[str, None] = "028_admin_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

activity_action_enum = postgresql.ENUM(
    "created",
    "updated",
    "deleted",
    "exported",
    "login",
    "login_failed",
    "logout",
    "logout_all",
    name="activity_action",
    create_type=False,
)

activity_resource_type_enum = postgresql.ENUM(
    "order",
    "product",
    "customer",
    "collection",
    "collection_package",
    "product_item",
    "product_item_type",
    "product_category",
    "supplier",
    "delivery_area",
    "utility_charge",
    "labour_charge",
    "tax_charge",
    "business_settings",
    "faq",
    "faq_category",
    "shared_memory",
    "review",
    "production",
    "analytics",
    "dashboard",
    "auth",
    "user",
    "system",
    name="activity_resource_type",
    create_type=False,
)

client_device_type_enum = postgresql.ENUM(
    "desktop",
    "mobile",
    "tablet",
    "bot",
    "unknown",
    name="client_device_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    activity_action_enum.create(bind, checkfirst=True)
    activity_resource_type_enum.create(bind, checkfirst=True)
    client_device_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "admin_activity_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("actor_email", sa.String(length=320), nullable=True),
        sa.Column("actor_admin_role", sa.String(length=32), nullable=True),
        sa.Column("action", activity_action_enum, nullable=False),
        sa.Column("resource_type", activity_resource_type_enum, nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=True),
        sa.Column("resource_label", sa.String(length=255), nullable=True),
        sa.Column("http_method", sa.String(length=10), nullable=True),
        sa.Column("path", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("browser_name", sa.String(length=64), nullable=True),
        sa.Column("browser_version", sa.String(length=32), nullable=True),
        sa.Column("os_name", sa.String(length=64), nullable=True),
        sa.Column("os_version", sa.String(length=32), nullable=True),
        sa.Column("device_type", client_device_type_enum, nullable=False, server_default="unknown"),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_activity_logs_actor_user_id", "admin_activity_logs", ["actor_user_id"])
    op.create_index("ix_admin_activity_logs_action", "admin_activity_logs", ["action"])
    op.create_index("ix_admin_activity_logs_resource_type", "admin_activity_logs", ["resource_type"])
    op.create_index("ix_admin_activity_logs_created_at", "admin_activity_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_admin_activity_logs_created_at", table_name="admin_activity_logs")
    op.drop_index("ix_admin_activity_logs_resource_type", table_name="admin_activity_logs")
    op.drop_index("ix_admin_activity_logs_action", table_name="admin_activity_logs")
    op.drop_index("ix_admin_activity_logs_actor_user_id", table_name="admin_activity_logs")
    op.drop_table("admin_activity_logs")
    bind = op.get_bind()
    client_device_type_enum.drop(bind, checkfirst=True)
    activity_resource_type_enum.drop(bind, checkfirst=True)
    activity_action_enum.drop(bind, checkfirst=True)
