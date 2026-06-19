"""FEFO lot allocation for consumption proposals."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.inventory_lot_repository import InventoryLotRepository

QTY_PRECISION = Decimal("0.0001")


@dataclass(frozen=True)
class FefoLotAllocation:
    lot_id: uuid.UUID
    lot_code: str
    quantity: Decimal
    unit: str
    expires_at: date | None


@dataclass(frozen=True)
class FefoAllocationResult:
    allocations: list[FefoLotAllocation]
    shortfall: Decimal


class FefoAllocationService:
    """Allocate quantity across lots first-expiry-first-out."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.lots = InventoryLotRepository(db)

    def allocate(
        self,
        *,
        product_item_id: uuid.UUID,
        quantity: Decimal,
        unit: str,
    ) -> FefoAllocationResult:
        if quantity <= 0:
            return FefoAllocationResult(allocations=[], shortfall=Decimal("0"))

        remaining = quantity.quantize(QTY_PRECISION)
        allocations: list[FefoLotAllocation] = []

        for lot in self.lots.list_fefo_for_item(product_item_id):
            if remaining <= 0:
                break
            if lot.unit != unit:
                continue
            take = min(lot.quantity_on_hand, remaining).quantize(QTY_PRECISION)
            if take <= 0:
                continue
            allocations.append(
                FefoLotAllocation(
                    lot_id=lot.id,
                    lot_code=lot.lot_code,
                    quantity=take,
                    unit=lot.unit,
                    expires_at=lot.expires_at,
                ),
            )
            remaining -= take

        return FefoAllocationResult(
            allocations=allocations,
            shortfall=max(remaining, Decimal("0")).quantize(QTY_PRECISION),
        )
