"""Discount & Promotions — Phase 1 foundation.

Changes:
- Create discount_rules table
- Create customer_discount_grants table (with partial unique index for one active grant per customer)
- Create customer_discount_overrides table
- Create discount_audit_events table
- Create promotion_slides table
- Add discount + gross_revenue snapshot columns to orders
- Backfill orders: discount_amount_snapshot=0, gross_revenue_snapshot=total_revenue_snapshot

Revision ID: 043_discount_and_promotions_foundation
Revises: 042_overhead_charges_redesign
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "043_discounts_phase1"
down_revision: Union[str, None] = "042_overhead_charges_redesign"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. PostgreSQL enum types ─────────────────────────────────────────────
    op.execute(
        "CREATE TYPE discount_rule_type AS ENUM ('order_frequency_in_window')"
    )
    op.execute(
        "CREATE TYPE discount_type AS ENUM ('fixed', 'percentage')"
    )
    op.execute(
        "CREATE TYPE discount_grant_status AS ENUM ('active', 'used', 'expired', 'revoked')"
    )
    op.execute(
        "CREATE TYPE discount_source AS ENUM ('rule', 'manual')"
    )
    op.execute(
        "CREATE TYPE discount_audit_event_type AS ENUM "
        "('rule_evaluated', 'granted', 'used', 'expired', 'revoked', 'override_set')"
    )

    # ── 2. discount_rules ────────────────────────────────────────────────────
    op.create_table(
        "discount_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "rule_type",
            postgresql.ENUM(
                "order_frequency_in_window",
                name="discount_rule_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "config",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("priority", sa.SmallInteger, nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
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
    )
    op.create_index("ix_discount_rules_name", "discount_rules", ["name"], unique=True)
    op.create_index("ix_discount_rules_rule_type", "discount_rules", ["rule_type"])

    # ── 3. customer_discount_grants ──────────────────────────────────────────
    op.create_table(
        "customer_discount_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "discount_rule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("discount_rules.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "discount_type",
            postgresql.ENUM("fixed", "percentage", name="discount_type", create_type=False),
            nullable=False,
        ),
        sa.Column("discount_value", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "source",
            postgresql.ENUM("rule", "manual", name="discount_source", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active", "used", "expired", "revoked",
                name="discount_grant_status",
                create_type=False,
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("eligibility_reason", sa.Text, nullable=True),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "used_on_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "revoked_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("revoke_reason", sa.Text, nullable=True),
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
    )
    op.create_index(
        "ix_customer_discount_grants_customer_id",
        "customer_discount_grants",
        ["customer_id"],
    )
    op.create_index(
        "ix_customer_discount_grants_discount_rule_id",
        "customer_discount_grants",
        ["discount_rule_id"],
    )
    op.create_index(
        "ix_customer_discount_grants_status",
        "customer_discount_grants",
        ["status"],
    )
    op.create_index(
        "ix_customer_discount_grants_used_on_order_id",
        "customer_discount_grants",
        ["used_on_order_id"],
    )
    # Partial unique index: only one active grant per customer
    op.execute(
        """
        CREATE UNIQUE INDEX uq_one_active_grant_per_customer
        ON customer_discount_grants (customer_id)
        WHERE status = 'active'
        """
    )

    # ── 4. customer_discount_overrides ───────────────────────────────────────
    op.create_table(
        "customer_discount_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("discounts_enabled", sa.Boolean, nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column(
            "admin_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_customer_discount_overrides_customer_id",
        "customer_discount_overrides",
        ["customer_id"],
        unique=True,
    )

    # ── 5. discount_audit_events ─────────────────────────────────────────────
    op.create_table(
        "discount_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "event_type",
            postgresql.ENUM(
                "rule_evaluated", "granted", "used", "expired", "revoked", "override_set",
                name="discount_audit_event_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "customer_discount_grant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customer_discount_grants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "discount_rule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("discount_rules.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "admin_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "payload",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_discount_audit_events_event_type",
        "discount_audit_events",
        ["event_type"],
    )
    op.create_index(
        "ix_discount_audit_events_customer_id",
        "discount_audit_events",
        ["customer_id"],
    )
    op.create_index(
        "ix_discount_audit_events_customer_discount_grant_id",
        "discount_audit_events",
        ["customer_discount_grant_id"],
    )
    op.create_index(
        "ix_discount_audit_events_discount_rule_id",
        "discount_audit_events",
        ["discount_rule_id"],
    )
    op.create_index(
        "ix_discount_audit_events_order_id",
        "discount_audit_events",
        ["order_id"],
    )

    # ── 6. promotion_slides ──────────────────────────────────────────────────
    op.create_table(
        "promotion_slides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("image_url", sa.String(2000), nullable=False),
        sa.Column("cta_text", sa.String(100), nullable=True),
        sa.Column("cta_destination", sa.String(500), nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
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
    )

    # ── 7. New order snapshot columns ────────────────────────────────────────
    op.add_column(
        "orders",
        sa.Column(
            "pre_discount_subtotal_snapshot",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "discount_amount_snapshot",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "discount_type_snapshot",
            sa.String(20),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "discount_value_snapshot",
            sa.Numeric(12, 2),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "discount_source_snapshot",
            sa.String(20),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "discount_rule_id_snapshot",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "customer_discount_grant_id_snapshot",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "gross_revenue_snapshot",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )

    # ── 8. Backfill existing orders ──────────────────────────────────────────
    # discount_amount_snapshot already defaults to 0 via server_default
    # pre_discount_subtotal_snapshot = products + collections (no discount existed before)
    op.execute(
        """
        UPDATE orders
        SET
            pre_discount_subtotal_snapshot = products_subtotal_snapshot + collections_subtotal_snapshot,
            gross_revenue_snapshot = total_revenue_snapshot
        """
    )


def downgrade() -> None:
    # Remove order columns
    op.drop_column("orders", "gross_revenue_snapshot")
    op.drop_column("orders", "customer_discount_grant_id_snapshot")
    op.drop_column("orders", "discount_rule_id_snapshot")
    op.drop_column("orders", "discount_source_snapshot")
    op.drop_column("orders", "discount_value_snapshot")
    op.drop_column("orders", "discount_type_snapshot")
    op.drop_column("orders", "discount_amount_snapshot")
    op.drop_column("orders", "pre_discount_subtotal_snapshot")

    # Drop tables (reverse order due to FKs)
    op.drop_table("promotion_slides")
    op.drop_table("discount_audit_events")
    op.drop_table("customer_discount_overrides")
    op.drop_table("customer_discount_grants")
    op.drop_table("discount_rules")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS discount_audit_event_type")
    op.execute("DROP TYPE IF EXISTS discount_source")
    op.execute("DROP TYPE IF EXISTS discount_grant_status")
    op.execute("DROP TYPE IF EXISTS discount_type")
    op.execute("DROP TYPE IF EXISTS discount_rule_type")
