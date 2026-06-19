"""Inventory lot data access."""

import uuid
from datetime import date
from math import ceil

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.inventory_lot import InventoryLot
from app.models.product_item import ProductItem
from app.utils.search import ilike_contains


class InventoryLotRepository:
    """Repository for inventory lot persistence."""

    SORTABLE_COLUMNS = {
        "lot_code": InventoryLot.lot_code,
        "received_at": InventoryLot.received_at,
        "expires_at": InventoryLot.expires_at,
        "quantity_on_hand": InventoryLot.quantity_on_hand,
        "created_at": InventoryLot.created_at,
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, lot_id: uuid.UUID) -> InventoryLot | None:
        stmt = (
            select(InventoryLot)
            .options(
                joinedload(InventoryLot.product_item).joinedload(ProductItem.item_type),
            )
            .where(InventoryLot.id == lot_id)
        )
        return self.db.scalar(stmt)

    def create(self, lot: InventoryLot) -> InventoryLot:
        self.db.add(lot)
        self.db.flush()
        return lot

    def list_fefo_for_item(
        self,
        product_item_id: uuid.UUID,
        *,
        active_only: bool = True,
    ) -> list[InventoryLot]:
        stmt = (
            select(InventoryLot)
            .where(InventoryLot.product_item_id == product_item_id)
            .where(InventoryLot.quantity_on_hand > 0)
            .order_by(
                InventoryLot.expires_at.asc().nulls_last(),
                InventoryLot.received_at.asc(),
            )
        )
        if active_only:
            stmt = stmt.where(InventoryLot.is_active.is_(True))
        return list(self.db.scalars(stmt).all())

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_order: str,
        product_item_id: uuid.UUID | None = None,
        expiring_before: date | None = None,
        active_only: bool = True,
    ) -> tuple[list[InventoryLot], int]:
        stmt = select(InventoryLot).options(
            joinedload(InventoryLot.product_item).joinedload(ProductItem.item_type),
        )
        count_stmt = select(func.count()).select_from(InventoryLot)

        if product_item_id is not None:
            stmt = stmt.where(InventoryLot.product_item_id == product_item_id)
            count_stmt = count_stmt.where(InventoryLot.product_item_id == product_item_id)

        if active_only:
            stmt = stmt.where(InventoryLot.is_active.is_(True))
            count_stmt = count_stmt.where(InventoryLot.is_active.is_(True))

        if expiring_before is not None:
            expiry_filter = (
                InventoryLot.expires_at.is_not(None),
                InventoryLot.expires_at <= expiring_before,
                InventoryLot.quantity_on_hand > 0,
            )
            stmt = stmt.where(*expiry_filter)
            count_stmt = count_stmt.where(*expiry_filter)

        if search:
            pattern, escape = ilike_contains(search)
            search_filter = or_(
                InventoryLot.lot_code.ilike(pattern, escape=escape),
                ProductItem.name.ilike(pattern, escape=escape),
            )
            stmt = stmt.join(ProductItem).where(search_filter)
            count_stmt = count_stmt.join(ProductItem).where(search_filter)

        total = int(self.db.scalar(count_stmt) or 0)
        sort_column = self.SORTABLE_COLUMNS.get(sort_by, InventoryLot.received_at)
        order = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        stmt = stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)
        return list(self.db.scalars(stmt).unique().all()), total

    @staticmethod
    def total_pages(total: int, page_size: int) -> int:
        if total == 0:
            return 0
        return ceil(total / page_size)
