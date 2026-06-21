"""Payments pre-integration: remove Stripe placeholders and add online payment settings.

Revision ID: 044_payments_pre_integration
Revises: 043_discounts_phase1
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "044_payments_pre_integration"
down_revision: Union[str, None] = "043_discounts_phase1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_PAYMENT_METHODS = ("online_card", "online_bank_debit")
_NEW_SETTINGS: tuple[tuple[str, str], ...] = (
    ("online_card_enabled", "false"),
    ("online_bank_debit_enabled", "false"),
    ("bank_name", ""),
    ("bank_account_name", ""),
    ("bank_account_number", ""),
    ("bank_branch", ""),
    (
        "bank_transfer_instructions",
        "Use your order number as the payment reference. "
        "We will confirm your order after we verify the transfer.",
    ),
)


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE orders SET payment_method = 'manual' "
            "WHERE payment_method::text = 'stripe'",
        ),
    )
    op.execute(sa.text("DELETE FROM business_settings WHERE key = 'stripe_enabled'"))

    for value in _NEW_PAYMENT_METHODS:
        op.execute(
            sa.text(f"ALTER TYPE payment_method ADD VALUE IF NOT EXISTS '{value}'"),
        )

    settings_table = sa.table(
        "business_settings",
        sa.column("key", sa.String),
        sa.column("value", sa.String),
    )
    op.bulk_insert(
        settings_table,
        [{"key": key, "value": value} for key, value in _NEW_SETTINGS],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM business_settings WHERE key IN ("
            "'online_card_enabled', 'online_bank_debit_enabled', "
            "'bank_name', 'bank_account_name', 'bank_account_number', "
            "'bank_branch', 'bank_transfer_instructions'"
            ")",
        ),
    )
    op.bulk_insert(
        sa.table(
            "business_settings",
            sa.column("key", sa.String),
            sa.column("value", sa.String),
        ),
        [{"key": "stripe_enabled", "value": "false"}],
    )
