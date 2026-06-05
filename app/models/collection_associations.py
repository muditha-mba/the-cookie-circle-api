"""Collection ↔ global charge association tables."""

from sqlalchemy import Column, ForeignKey, Table, Uuid

from app.database.base import Base

collection_utility_charges = Table(
    "collection_utility_charges",
    Base.metadata,
    Column(
        "collection_id",
        Uuid(as_uuid=True),
        ForeignKey("collections.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "utility_charge_id",
        Uuid(as_uuid=True),
        ForeignKey("utility_charges.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
)

collection_labour_charges = Table(
    "collection_labour_charges",
    Base.metadata,
    Column(
        "collection_id",
        Uuid(as_uuid=True),
        ForeignKey("collections.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "labour_charge_id",
        Uuid(as_uuid=True),
        ForeignKey("labour_charges.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
)

collection_allowed_categories = Table(
    "collection_allowed_categories",
    Base.metadata,
    Column(
        "collection_id",
        Uuid(as_uuid=True),
        ForeignKey("collections.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "product_category_id",
        Uuid(as_uuid=True),
        ForeignKey("product_categories.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
)

collection_tax_charges = Table(
    "collection_tax_charges",
    Base.metadata,
    Column(
        "collection_id",
        Uuid(as_uuid=True),
        ForeignKey("collections.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tax_charge_id",
        Uuid(as_uuid=True),
        ForeignKey("tax_charges.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
)
