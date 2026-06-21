"""Collection data access repository."""

import uuid
from math import ceil

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.collection import Collection
from app.models.product_category import ProductCategory
from app.models.collection_item_line import CollectionItemLine
from app.models.collection_package import CollectionPackage
from app.models.collection_product_line import CollectionProductLine
from app.models.product_item import ProductItem
from app.models.labour_charge import LabourCharge
from app.models.product import Product
from app.models.product_recipe_line import ProductRecipeLine
from app.models.tax_charge import TaxCharge
from app.models.utility_charge import UtilityCharge
from app.utils.search import ilike_contains


class CollectionRepository:
    """Repository for collection persistence."""

    SORTABLE_COLUMNS = {
        "name": Collection.name,
        "package": CollectionPackage.name,
        "created_at": Collection.created_at,
        "is_active": Collection.is_active,
        "package_size": Collection.package_size,
        "package_fee": Collection.package_fee,
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def _detail_options(self):
        product_costing = (
            selectinload(Product.recipe_lines).joinedload(ProductRecipeLine.product_item),
            selectinload(Product.utility_charges),
            selectinload(Product.labour_charges),
            selectinload(Product.tax_charges),
        )
        return (
            selectinload(Collection.product_lines)
            .joinedload(CollectionProductLine.product)
            .options(*product_costing),
            selectinload(Collection.item_lines)
            .joinedload(CollectionItemLine.product_item)
            .joinedload(ProductItem.item_type),
            selectinload(Collection.utility_charges),
            selectinload(Collection.labour_charges),
            selectinload(Collection.tax_charges),
            selectinload(Collection.package),
            selectinload(Collection.allowed_categories),
        )

    def get_for_costing_by_ids(self, ids: list[uuid.UUID]) -> list[Collection]:
        if not ids:
            return []
        stmt = (
            select(Collection)
            .options(*self._detail_options())
            .where(Collection.id.in_(ids))
        )
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, collection_id: uuid.UUID) -> Collection | None:
        stmt = (
            select(Collection)
            .options(*self._detail_options())
            .where(Collection.id == collection_id)
        )
        return self.db.scalar(stmt)

    def get_by_name(self, name: str) -> Collection | None:
        stmt = select(Collection).where(func.lower(Collection.name) == name.strip().lower())
        return self.db.scalar(stmt)

    def create(self, collection: Collection) -> Collection:
        self.db.add(collection)
        self.db.flush()
        return self.get_by_id(collection.id)  # type: ignore[return-value]

    def delete(self, collection: Collection) -> None:
        self.db.delete(collection)

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_order: str,
        package_id: uuid.UUID | None,
    ) -> tuple[list[Collection], int]:
        stmt = select(Collection).outerjoin(Collection.package)
        count_stmt = select(func.count()).select_from(Collection).outerjoin(Collection.package)

        if search:
            pattern, escape = ilike_contains(search)
            filter_clause = or_(
                Collection.name.ilike(pattern, escape=escape),
                Collection.description.ilike(pattern, escape=escape),
            )
            stmt = stmt.where(filter_clause)
            count_stmt = count_stmt.where(filter_clause)

        if package_id is not None:
            stmt = stmt.where(Collection.package_id == package_id)
            count_stmt = count_stmt.where(Collection.package_id == package_id)

        total = int(self.db.scalar(count_stmt) or 0)
        sort_column = self.SORTABLE_COLUMNS.get(sort_by, Collection.created_at)
        order = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        stmt = (
            stmt.options(
                selectinload(Collection.package),
                selectinload(Collection.allowed_categories),
            )
            .order_by(order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        return list(self.db.scalars(stmt).unique().all()), total

    @staticmethod
    def total_pages(total: int, page_size: int) -> int:
        if total == 0:
            return 0
        return ceil(total / page_size)

    def get_products_by_ids(self, ids: list[uuid.UUID]) -> list[Product]:
        if not ids:
            return []
        stmt = select(Product).where(Product.id.in_(ids))
        return list(self.db.scalars(stmt).all())

    def get_utility_charges_by_ids(self, ids: list[uuid.UUID]) -> list[UtilityCharge]:
        if not ids:
            return []
        stmt = select(UtilityCharge).where(UtilityCharge.id.in_(ids))
        return list(self.db.scalars(stmt).all())

    def get_labour_charges_by_ids(self, ids: list[uuid.UUID]) -> list[LabourCharge]:
        if not ids:
            return []
        stmt = select(LabourCharge).where(LabourCharge.id.in_(ids))
        return list(self.db.scalars(stmt).all())

    def get_tax_charges_by_ids(self, ids: list[uuid.UUID]) -> list[TaxCharge]:
        if not ids:
            return []
        stmt = select(TaxCharge).where(TaxCharge.id.in_(ids))
        return list(self.db.scalars(stmt).all())