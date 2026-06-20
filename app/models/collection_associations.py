"""Collection ↔ global charge association tables."""

from sqlalchemy import Column, ForeignKey, Table, Uuid

from app.database.base import Base

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
