"""Many-to-many association tables linking products to global charges."""

from sqlalchemy import Column, ForeignKey, Table, Uuid

from app.database.base import Base

product_utility_charges = Table(
    "product_utility_charges",
    Base.metadata,
    Column(
        "product_id",
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "utility_charge_id",
        Uuid(as_uuid=True),
        ForeignKey("utility_charges.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
)

product_labour_charges = Table(
    "product_labour_charges",
    Base.metadata,
    Column(
        "product_id",
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "labour_charge_id",
        Uuid(as_uuid=True),
        ForeignKey("labour_charges.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
)

product_tax_charges = Table(
    "product_tax_charges",
    Base.metadata,
    Column(
        "product_id",
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tax_charge_id",
        Uuid(as_uuid=True),
        ForeignKey("tax_charges.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
)
