"""Replace per-product reviews with order-level reviews.

Revision ID: 020_order_reviews
Revises: 019_customer_account
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "020_order_reviews"
down_revision: Union[str, None] = "019_customer_account"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

review_item_sentiment = postgresql.ENUM(
    "positive",
    "negative",
    name="review_item_sentiment",
    create_type=False,
)


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS product_reviews")

    review_item_sentiment.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "order_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("order_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id", "order_id", name="uq_order_reviews_customer_order"),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_order_reviews_rating"),
    )
    op.create_index("ix_order_reviews_customer_id", "order_reviews", ["customer_id"])
    op.create_index("ix_order_reviews_order_id", "order_reviews", ["order_id"])

    op.create_table(
        "order_review_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_review_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("product_name_snapshot", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("sentiment", review_item_sentiment, nullable=False),
        sa.Column("item_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["order_review_id"], ["order_reviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "order_review_id",
            "product_id",
            name="uq_order_review_items_review_product",
        ),
    )
    op.create_index(
        "ix_order_review_items_order_review_id",
        "order_review_items",
        ["order_review_id"],
    )
    op.create_index("ix_order_review_items_product_id", "order_review_items", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_order_review_items_product_id", table_name="order_review_items")
    op.drop_index("ix_order_review_items_order_review_id", table_name="order_review_items")
    op.drop_table("order_review_items")
    op.drop_index("ix_order_reviews_order_id", table_name="order_reviews")
    op.drop_index("ix_order_reviews_customer_id", table_name="order_reviews")
    op.drop_table("order_reviews")
    review_item_sentiment.drop(op.get_bind(), checkfirst=True)

    op.create_table(
        "product_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("product_name_snapshot", sa.String(200), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=True),
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
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "customer_id",
            "order_id",
            "product_id",
            name="uq_product_reviews_customer_order_product",
        ),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_product_reviews_rating"),
    )
    op.create_index("ix_product_reviews_customer_id", "product_reviews", ["customer_id"])
    op.create_index("ix_product_reviews_order_id", "product_reviews", ["order_id"])
    op.create_index("ix_product_reviews_product_id", "product_reviews", ["product_id"])
