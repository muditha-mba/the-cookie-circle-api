"""Compare production demand against on-hand inventory."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.product_item_repository import ProductItemRepository
from app.schemas.inventory_readiness import InventoryReadinessLine, InventoryReadinessResponse
from app.services.inventory_balance_service import InventoryBalanceService
from app.services.production_planning_service import ProductionPlanningService

QTY_PRECISION = Decimal("0.0001")


class InventoryReadinessService:
    """Need vs on-hand for a production delivery date."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.production = ProductionPlanningService(db)
        self.balances = InventoryBalanceService(db)
        self.items = ProductItemRepository(db)

    def get_readiness(self, delivery_date: date) -> InventoryReadinessResponse:
        lines = self._build_lines(delivery_date)
        shortfall_count = sum(1 for line in lines if line.is_short)
        tracked_item_count = sum(1 for line in lines if line.track_inventory)
        return InventoryReadinessResponse(
            delivery_date=delivery_date,
            lines=lines,
            shortfall_count=shortfall_count,
            tracked_item_count=tracked_item_count,
        )

    def count_shortfalls(self, delivery_date: date) -> int:
        return sum(1 for line in self._build_lines(delivery_date) if line.is_short)

    def _build_lines(self, delivery_date: date) -> list[InventoryReadinessLine]:
        ingredient_demand = self.production.get_ingredient_demand(delivery_date)
        packaging_demand = self.production.get_packaging_demand(delivery_date)

        merged_qty: dict[uuid.UUID, Decimal] = defaultdict(lambda: Decimal("0"))
        names: dict[uuid.UUID, str] = {}
        units: dict[uuid.UUID, str] = {}

        for row in ingredient_demand:
            merged_qty[row.product_item_id] += row.quantity
            names[row.product_item_id] = row.product_item_name
            units[row.product_item_id] = row.unit

        for row in packaging_demand:
            merged_qty[row.product_item_id] += row.quantity
            names[row.product_item_id] = row.product_item_name
            units[row.product_item_id] = row.unit

        lines: list[InventoryReadinessLine] = []
        for item_id in sorted(merged_qty.keys(), key=lambda i: names.get(i, "").lower()):
            quantity_needed = merged_qty[item_id].quantize(QTY_PRECISION)
            if quantity_needed <= 0:
                continue

            item = self.items.get_by_id(item_id)
            track_inventory = bool(item and item.track_inventory)
            on_hand = (
                self.balances.sum_on_hand(item_id).quantize(QTY_PRECISION)
                if track_inventory
                else Decimal("0")
            )
            gap = (quantity_needed - on_hand).quantize(QTY_PRECISION)
            lines.append(
                InventoryReadinessLine(
                    product_item_id=item_id,
                    product_item_name=names[item_id],
                    quantity_needed=quantity_needed,
                    unit=units[item_id],
                    quantity_on_hand=on_hand,
                    quantity_gap=gap,
                    track_inventory=track_inventory,
                    is_short=track_inventory and gap > 0,
                ),
            )

        return lines
