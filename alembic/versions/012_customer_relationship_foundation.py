"""Customer relationship foundation (CRM).

Revision ID: 012_customer_crm
Revises: 011_procurement_foundation
Create Date: 2026-06-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012_customer_crm"
down_revision: Union[str, None] = "011_procurement_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

marketing_source = postgresql.ENUM(
    "instagram",
    "facebook",
    "whatsapp",
    "referral",
    "google",
    "walk_in",
    "other",
    name="marketing_source",
    create_type=False,
)

communication_type = postgresql.ENUM(
    "phone_call",
    "whatsapp",
    "email",
    "manual_follow_up",
    name="communication_type",
    create_type=False,
)


def upgrade() -> None:
    marketing_source.create(op.get_bind(), checkfirst=True)
    communication_type.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "customers",
        sa.Column("marketing_source", marketing_source, nullable=True),
    )
    op.create_index("ix_customers_marketing_source", "customers", ["marketing_source"])

    op.create_table(
        "customer_notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_notes_customer_id", "customer_notes", ["customer_id"])

    op.create_table(
        "customer_communications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("communication_type", communication_type, nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customer_communications_customer_id",
        "customer_communications",
        ["customer_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_customer_communications_customer_id", table_name="customer_communications")
    op.drop_table("customer_communications")
    op.drop_index("ix_customer_notes_customer_id", table_name="customer_notes")
    op.drop_table("customer_notes")
    op.drop_index("ix_customers_marketing_source", table_name="customers")
    op.drop_column("customers", "marketing_source")
    communication_type.drop(op.get_bind(), checkfirst=True)
    marketing_source.drop(op.get_bind(), checkfirst=True)
