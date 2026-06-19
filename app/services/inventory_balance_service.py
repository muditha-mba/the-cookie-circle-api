"""Inventory balance queries."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import NotFoundError
from app.models.inventory_lot import InventoryLot
from app.models.product_item import ProductItem
from app.repositories.consumption_proposal_repository import ConsumptionProposalRepository
from app.repositories.inventory_lot_repository import InventoryLotRepository
from app.repositories.product_item_repository import ProductItemRepository
from app.schemas.inventory import (
    InventoryAlertResponse,
    InventoryBalanceDetailResponse,
    InventoryBalanceResponse,
    InventoryLotSummary,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.product_item import ProductItemTypeSummary

QTY_PRECISION = Decimal("0.0001")


class InventoryBalanceService:
    """On-hand balances and stock alerts."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.items = ProductItemRepository(db)
        self.lots = InventoryLotRepository(db)

    def list_balances(
        self,
        params: PaginationParams,
        *,
        low_stock_only: bool = False,
    ) -> PaginatedResponse[InventoryBalanceResponse]:
        items, total = self._list_tracked_items(
            page=params.page,
            page_size=params.page_size,
            search=params.search,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        balances = [self._to_balance_response(item) for item in items]
        if low_stock_only:
            balances = [balance for balance in balances if balance.is_low_stock]
            total = len(balances)
        return PaginatedResponse(
            items=balances,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=self.items.total_pages(total, params.page_size),
        )

    def get_balance(self, product_item_id: uuid.UUID) -> InventoryBalanceDetailResponse:
        item = self.items.get_by_id(product_item_id)
        if not item:
            raise NotFoundError("Product item not found")
        if not item.track_inventory:
            raise NotFoundError("Inventory tracking is not enabled for this product item")

        balance = self._to_balance_response(item)
        active_lots = self.lots.list_fefo_for_item(product_item_id)
        return InventoryBalanceDetailResponse(
            **balance.model_dump(),
            lots=[InventoryLotSummary.model_validate(lot) for lot in active_lots],
        )

    def get_alerts(self, *, expiring_within_days: int = 7) -> InventoryAlertResponse:
        low_stock_count = 0
        items, _ = self._list_tracked_items(page=1, page_size=10_000, search=None, sort_by="name", sort_order="asc")
        for item in items:
            balance = self._to_balance_response(item)
            if balance.is_low_stock:
                low_stock_count += 1

        cutoff = date.today() + timedelta(days=expiring_within_days)
        expiring_stmt = (
            select(func.count())
            .select_from(InventoryLot)
            .where(InventoryLot.is_active.is_(True))
            .where(InventoryLot.quantity_on_hand > 0)
            .where(InventoryLot.expires_at.is_not(None))
            .where(InventoryLot.expires_at <= cutoff)
        )
        expiring_soon_count = int(self.db.scalar(expiring_stmt) or 0)

        return InventoryAlertResponse(
            low_stock_count=low_stock_count,
            expiring_soon_count=expiring_soon_count,
            pending_consumption_count=ConsumptionProposalRepository(self.db).count_pending(),
        )

    def sum_on_hand(self, product_item_id: uuid.UUID) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(InventoryLot.quantity_on_hand), 0))
            .where(InventoryLot.product_item_id == product_item_id)
            .where(InventoryLot.is_active.is_(True))
        )
        return Decimal(str(self.db.scalar(stmt) or 0)).quantize(QTY_PRECISION)

    def _to_balance_response(self, item: ProductItem) -> InventoryBalanceResponse:
        on_hand = self.sum_on_hand(item.id)
        nearest_expiry = self._nearest_expiry(item.id)
        is_low_stock = False
        if item.reorder_level is not None and on_hand <= item.reorder_level:
            is_low_stock = True

        return InventoryBalanceResponse(
            product_item_id=item.id,
            product_item_name=item.name,
            item_type=ProductItemTypeSummary.model_validate(item.item_type),
            unit=item.reorder_unit or item.purchase_unit,
            quantity_on_hand=on_hand,
            reorder_level=item.reorder_level,
            reorder_unit=item.reorder_unit,
            is_low_stock=is_low_stock,
            nearest_expiry=nearest_expiry,
        )

    def _nearest_expiry(self, product_item_id: uuid.UUID) -> date | None:
        stmt = (
            select(InventoryLot.expires_at)
            .where(InventoryLot.product_item_id == product_item_id)
            .where(InventoryLot.is_active.is_(True))
            .where(InventoryLot.quantity_on_hand > 0)
            .where(InventoryLot.expires_at.is_not(None))
            .order_by(InventoryLot.expires_at.asc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def _list_tracked_items(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[ProductItem], int]:
        items, total = self.items.list_paginated(
            page=page,
            page_size=page_size,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            track_inventory_only=True,
        )
        return items, total
