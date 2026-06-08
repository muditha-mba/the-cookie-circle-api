"""Collection package data access repository."""

import uuid
from math import ceil

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.collection import Collection
from app.models.collection_package import CollectionPackage


class CollectionPackageRepository:
    """Repository for collection package persistence."""

    SORTABLE_COLUMNS = {
        "name": CollectionPackage.name,
        "code": CollectionPackage.code,
        "badge_tone": CollectionPackage.badge_tone,
        "is_active": CollectionPackage.is_active,
        "created_at": CollectionPackage.created_at,
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, package_id: uuid.UUID) -> CollectionPackage | None:
        stmt = select(CollectionPackage).where(CollectionPackage.id == package_id)
        return self.db.scalar(stmt)

    def get_by_code(self, code: str) -> CollectionPackage | None:
        stmt = select(CollectionPackage).where(func.upper(CollectionPackage.code) == code.strip().upper())
        return self.db.scalar(stmt)

    def get_by_name(self, name: str) -> CollectionPackage | None:
        stmt = select(CollectionPackage).where(func.lower(CollectionPackage.name) == name.strip().lower())
        return self.db.scalar(stmt)

    def create(self, package: CollectionPackage) -> CollectionPackage:
        self.db.add(package)
        self.db.flush()
        return package

    def delete(self, package: CollectionPackage) -> None:
        self.db.delete(package)

    def count_collections_for_package(self, package_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Collection).where(Collection.package_id == package_id)
        return int(self.db.scalar(stmt) or 0)

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[CollectionPackage], int]:
        stmt = select(CollectionPackage)
        count_stmt = select(func.count()).select_from(CollectionPackage)

        if search:
            pattern = f"%{search.strip()}%"
            filter_clause = or_(
                CollectionPackage.name.ilike(pattern),
                CollectionPackage.code.ilike(pattern),
                CollectionPackage.description.ilike(pattern),
            )
            stmt = stmt.where(filter_clause)
            count_stmt = count_stmt.where(filter_clause)

        total = int(self.db.scalar(count_stmt) or 0)
        sort_column = self.SORTABLE_COLUMNS.get(sort_by, CollectionPackage.created_at)
        order = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        stmt = stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)
        return list(self.db.scalars(stmt).all()), total

    @staticmethod
    def total_pages(total: int, page_size: int) -> int:
        if total == 0:
            return 0
        return ceil(total / page_size)
