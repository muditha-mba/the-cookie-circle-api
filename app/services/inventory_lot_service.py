"""Inventory lot listing."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.repositories.inventory_lot_repository import InventoryLotRepository
from app.schemas.inventory import InventoryLotSummary
from app.schemas.pagination import PaginatedResponse, PaginationParams


class InventoryLotService:
    """List and retrieve inventory lots."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.lots = InventoryLotRepository(db)

    def get(self, lot_id: uuid.UUID) -> InventoryLotSummary:
        lot = self.lots.get_by_id(lot_id)
        if not lot:
            raise NotFoundError("Inventory lot not found")
        return InventoryLotSummary.model_validate(lot)

    def list(
        self,
        params: PaginationParams,
        *,
        product_item_id: uuid.UUID | None = None,
        expiring_before: date | None = None,
    ) -> PaginatedResponse[InventoryLotSummary]:
        rows, total = self.lots.list_paginated(
            page=params.page,
            page_size=params.page_size,
            search=params.search,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
            product_item_id=product_item_id,
            expiring_before=expiring_before,
        )
        return PaginatedResponse(
            items=[InventoryLotSummary.model_validate(row) for row in rows],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=self.lots.total_pages(total, params.page_size),
        )
