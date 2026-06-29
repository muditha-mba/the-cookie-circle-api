"""Inventory movement data access."""

import uuid
from math import ceil

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import InventoryMovementType
from app.models.inventory_lot import InventoryLot
from app.models.inventory_movement import InventoryMovement
from app.models.product_item import ProductItem


class InventoryMovementRepository:
    """Repository for inventory movement persistence."""

    SORTABLE_COLUMNS = {
        "created_at": InventoryMovement.created_at,
        "movement_type": InventoryMovement.movement_type,
        "quantity_change": InventoryMovement.quantity_change,
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, movement: InventoryMovement) -> InventoryMovement:
        self.db.add(movement)
        self.db.flush()
        return movement

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
        product_item_id: uuid.UUID | None = None,
        lot_id: uuid.UUID | None = None,
        movement_type: InventoryMovementType | None = None,
    ) -> tuple[list[InventoryMovement], int]:
        stmt = (
            select(InventoryMovement)
            .options(
                joinedload(InventoryMovement.lot)
                .joinedload(InventoryLot.product_item)
                .joinedload(ProductItem.item_type),
            )
        )
        count_stmt = select(func.count()).select_from(InventoryMovement)

        if lot_id is not None:
            stmt = stmt.where(InventoryMovement.lot_id == lot_id)
            count_stmt = count_stmt.where(InventoryMovement.lot_id == lot_id)

        if product_item_id is not None:
            stmt = stmt.join(InventoryLot).where(InventoryLot.product_item_id == product_item_id)
            count_stmt = count_stmt.join(InventoryLot).where(
                InventoryLot.product_item_id == product_item_id,
            )

        if movement_type is not None:
            stmt = stmt.where(InventoryMovement.movement_type == movement_type)
            count_stmt = count_stmt.where(InventoryMovement.movement_type == movement_type)

        total = int(self.db.scalar(count_stmt) or 0)
        sort_column = self.SORTABLE_COLUMNS.get(sort_by, InventoryMovement.created_at)
        order = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        stmt = stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)
        return list(self.db.scalars(stmt).unique().all()), total

    @staticmethod
    def total_pages(total: int, page_size: int) -> int:
        if total == 0:
            return 0
        return ceil(total / page_size)
