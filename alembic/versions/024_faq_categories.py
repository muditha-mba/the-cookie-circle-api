"""Add FAQ categories and group FAQs by category.

Revision ID: 024_faq_categories
Revises: 023_site_content_faqs
"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "024_faq_categories"
down_revision: Union[str, None] = "023_site_content_faqs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CATEGORIES: tuple[tuple[str, int], ...] = (
    ("Orders & Payment", 0),
    ("Weekend Delivery", 1),
    ("Collections & Customisation", 2),
    ("Ingredients & Freshness", 3),
    ("Gifting & Catering", 4),
)

# (category_name, sort_order, question, answer)
SEED_FAQS: tuple[tuple[str, int, str, str], ...] = (
    (
        "Orders & Payment",
        0,
        "How can I place an order?",
        "Browse our collections or Build Your Circle on the website, add your selections to the cart, and complete checkout. After placing your order, you will be guided to send your order details via WhatsApp so our team can confirm it.",
    ),
    (
        "Orders & Payment",
        1,
        "What payment methods do you accept?",
        "We currently accept cash on delivery and bank transfer. Card payments will be introduced when our online payment gateway is live. Your available options are shown at checkout.",
    ),
    (
        "Orders & Payment",
        2,
        "Do you offer cash on delivery?",
        "Yes. Cash on delivery is available for eligible delivery areas. Please place your order through the website first so we can prepare your batch accurately.",
    ),
    (
        "Orders & Payment",
        3,
        "Can I order without creating an account?",
        "Yes. Guest checkout is available. If you create an account, you can save addresses, track orders, and enjoy a smoother experience for future weekend batches.",
    ),
    (
        "Weekend Delivery",
        0,
        "When is your delivery day?",
        "We deliver on Saturday. Orders are prepared on Friday in small handcrafted batches, so every cookie reaches you fresh for the weekend.",
    ),
    (
        "Weekend Delivery",
        1,
        "What is the order cutoff for this week's batch?",
        "Orders placed on or before Thursday evening are included in the upcoming Saturday delivery batch. Orders placed after the cutoff are scheduled for the following week.",
    ),
    (
        "Weekend Delivery",
        2,
        "Which areas do you deliver to?",
        "We deliver across selected localities around Kandy. Available delivery areas and fees are shown during checkout when you choose your delivery location.",
    ),
    (
        "Weekend Delivery",
        3,
        "How much is delivery?",
        "Delivery fees depend on your area. The exact fee for your location is calculated at checkout before you confirm your order.",
    ),
    (
        "Weekend Delivery",
        4,
        "Can I choose my delivery date?",
        "Your delivery is assigned to the next available Saturday batch based on when you order. The suggested delivery date is shown during checkout.",
    ),
    (
        "Collections & Customisation",
        0,
        "What is the difference between Signature Collections and Build Your Circle?",
        "Signature Collections are curated luxury bundles designed as complete gifting experiences. Build Your Circle lets you mix and match cookie flavours within a bundle size — ideal for families and personalised weekend orders.",
    ),
    (
        "Collections & Customisation",
        1,
        "Can I choose the flavours in my box?",
        "Yes, with Build Your Circle collections. Signature Collections are curated as fixed bundles to preserve their editorial presentation and gifting experience.",
    ),
    (
        "Collections & Customisation",
        2,
        "Do you sell individual cookies?",
        "Our website is collection-focused, designed around curated bundles and weekend batches. Individual flavours are available within Build Your Circle and selected collection formats.",
    ),
    (
        "Ingredients & Freshness",
        0,
        "Are your cookies made fresh?",
        "Every batch is handcrafted to order. We do not hold large ready-made stock — cookies are baked fresh in small weekly batches for Saturday delivery.",
    ),
    (
        "Ingredients & Freshness",
        1,
        "Do you use preservatives?",
        "No. Our cookies are made with quality ingredients in small batches. We focus on freshness, craftsmanship, and flavour — not mass-production shelf life.",
    ),
    (
        "Ingredients & Freshness",
        2,
        "Where can I see ingredients for each cookie?",
        "Ingredient details are available on individual product pages in our cookie catalogue. If you have allergies or dietary concerns, please contact us before ordering.",
    ),
    (
        "Gifting & Catering",
        0,
        "Can I order cookies as a gift?",
        "Absolutely. Our Signature Collections are designed for gifting. Include your message and delivery details at checkout, and we will handle your order with care.",
    ),
    (
        "Gifting & Catering",
        1,
        "Do you offer catering for events?",
        "Yes. We offer catering packages for celebrations, gatherings, and special occasions. Visit our Catering section or contact us to discuss your event requirements.",
    ),
    (
        "Gifting & Catering",
        2,
        "How do I get help with a large or custom order?",
        "For catering enquiries or special requests, contact us by phone or email. We are happy to guide you on quantities, collections, and delivery timing.",
    ),
)


def upgrade() -> None:
    op.create_table(
        "faq_categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
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
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_faq_categories_name", "faq_categories", ["name"], unique=True)

    op.add_column("faqs", sa.Column("category_id", sa.Uuid(), nullable=True))

    connection = op.get_bind()
    category_ids: dict[str, uuid.UUID] = {}
    for name, sort_order in CATEGORIES:
        category_id = uuid.uuid4()
        category_ids[name] = category_id
        connection.execute(
            sa.text(
                """
                INSERT INTO faq_categories (id, name, sort_order, is_active)
                VALUES (:id, :name, :sort_order, true)
                """,
            ),
            {"id": category_id, "name": name, "sort_order": sort_order},
        )

    fallback_category_id = next(iter(category_ids.values()))
    connection.execute(
        sa.text("UPDATE faqs SET category_id = :category_id WHERE category_id IS NULL"),
        {"category_id": fallback_category_id},
    )

    for category_name, sort_order, question, answer in SEED_FAQS:
        connection.execute(
            sa.text(
                """
                INSERT INTO faqs (id, category_id, question, answer, sort_order, is_active)
                VALUES (:id, :category_id, :question, :answer, :sort_order, true)
                """,
            ),
            {
                "id": uuid.uuid4(),
                "category_id": category_ids[category_name],
                "question": question,
                "answer": answer,
                "sort_order": sort_order,
            },
        )

    op.alter_column("faqs", "category_id", nullable=False)
    op.create_foreign_key(
        "fk_faqs_category_id",
        "faqs",
        "faq_categories",
        ["category_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_faqs_category_id", "faqs", ["category_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_faqs_category_id", table_name="faqs")
    op.drop_constraint("fk_faqs_category_id", "faqs", type_="foreignkey")
    op.drop_column("faqs", "category_id")
    op.drop_index("ix_faq_categories_name", table_name="faq_categories")
    op.drop_table("faq_categories")
