"""Inventory movement business logic."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import (
    ActivityAction,
    ActivityResourceType,
    InventoryMovementReferenceType,
    InventoryMovementType,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.models.inventory_lot import InventoryLot
from app.models.inventory_movement import InventoryMovement
from app.repositories.inventory_lot_repository import InventoryLotRepository
from app.repositories.inventory_movement_repository import InventoryMovementRepository
from app.schemas.inventory import (
    InventoryAdjustmentCreate,
    InventoryMovementResponse,
    InventoryWasteCreate,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.activity_log_service import ActivityLogService

QTY_PRECISION = Decimal("0.0001")


class InventoryMovementService:
    """Record adjustments, waste, and query movement history."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.lots = InventoryLotRepository(db)
        self.movements = InventoryMovementRepository(db)
        self.activity = ActivityLogService(db)

    def list_movements(
        self,
        params: PaginationParams,
        *,
        product_item_id: uuid.UUID | None = None,
        lot_id: uuid.UUID | None = None,
        movement_type: InventoryMovementType | None = None,
    ) -> PaginatedResponse[InventoryMovementResponse]:
        rows, total = self.movements.list_paginated(
            page=params.page,
            page_size=params.page_size,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
            product_item_id=product_item_id,
            lot_id=lot_id,
            movement_type=movement_type,
        )
        return PaginatedResponse(
            items=[self._to_response(row) for row in rows],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=self.movements.total_pages(total, params.page_size),
        )

    def adjust(
        self,
        payload: InventoryAdjustmentCreate,
        *,
        user_id: uuid.UUID,
    ) -> InventoryMovementResponse:
        if payload.quantity_change == 0:
            raise ValidationError("Adjustment quantity cannot be zero")

        lot = self.lots.get_by_id(payload.lot_id)
        if not lot:
            raise NotFoundError("Inventory lot not found")
        if not lot.is_active:
            raise ValidationError("Cannot adjust an inactive lot")

        movement = self._apply_quantity_change(
            lot=lot,
            quantity_change=payload.quantity_change,
            movement_type=InventoryMovementType.ADJUSTMENT,
            reference_type=InventoryMovementReferenceType.MANUAL,
            reference_id=None,
            notes=payload.notes,
            user_id=user_id,
        )
        self.db.commit()
        self.activity.record(
            action=ActivityAction.UPDATED,
            resource_type=ActivityResourceType.INVENTORY_MOVEMENT,
            actor_user_id=user_id,
            resource_id=movement.id,
            resource_label=f"Inventory adjustment ({lot.lot_code})",
            commit=True,
        )
        return self._to_response(movement)

    def record_waste(
        self,
        payload: InventoryWasteCreate,
        *,
        user_id: uuid.UUID,
    ) -> InventoryMovementResponse:
        lot = self.lots.get_by_id(payload.lot_id)
        if not lot:
            raise NotFoundError("Inventory lot not found")
        if not lot.is_active:
            raise ValidationError("Cannot record waste on an inactive lot")

        quantity_change = (-payload.quantity).quantize(QTY_PRECISION)
        movement = self._apply_quantity_change(
            lot=lot,
            quantity_change=quantity_change,
            movement_type=InventoryMovementType.WASTE,
            reference_type=InventoryMovementReferenceType.MANUAL,
            reference_id=None,
            notes=payload.notes,
            user_id=user_id,
        )
        self.db.commit()
        self.activity.record(
            action=ActivityAction.UPDATED,
            resource_type=ActivityResourceType.INVENTORY_MOVEMENT,
            actor_user_id=user_id,
            resource_id=movement.id,
            resource_label=f"Inventory waste ({lot.lot_code})",
            commit=True,
        )
        return self._to_response(movement)

    def record_receipt_movement(
        self,
        *,
        lot: InventoryLot,
        quantity: Decimal,
        reference_id: uuid.UUID,
        user_id: uuid.UUID | None,
        notes: str | None = None,
    ) -> InventoryMovement:
        return self._apply_quantity_change(
            lot=lot,
            quantity_change=quantity.quantize(QTY_PRECISION),
            movement_type=InventoryMovementType.RECEIPT,
            reference_type=InventoryMovementReferenceType.PURCHASE_RECEIPT,
            reference_id=reference_id,
            notes=notes,
            user_id=user_id,
        )

    def record_consumption_movement(
        self,
        *,
        lot: InventoryLot,
        quantity: Decimal,
        reference_id: uuid.UUID,
        user_id: uuid.UUID | None,
        notes: str | None = None,
    ) -> InventoryMovement:
        quantity_change = (-quantity).quantize(QTY_PRECISION)
        return self._apply_quantity_change(
            lot=lot,
            quantity_change=quantity_change,
            movement_type=InventoryMovementType.CONSUMPTION,
            reference_type=InventoryMovementReferenceType.CONSUMPTION_PROPOSAL,
            reference_id=reference_id,
            notes=notes,
            user_id=user_id,
        )

    def _apply_quantity_change(
        self,
        *,
        lot: InventoryLot,
        quantity_change: Decimal,
        movement_type: InventoryMovementType,
        reference_type: InventoryMovementReferenceType,
        reference_id: uuid.UUID | None,
        notes: str | None,
        user_id: uuid.UUID | None,
    ) -> InventoryMovement:
        new_balance = (lot.quantity_on_hand + quantity_change).quantize(QTY_PRECISION)
        if new_balance < 0:
            raise ValidationError("Insufficient quantity on this lot")

        lot.quantity_on_hand = new_balance
        if new_balance == 0:
            lot.is_active = False

        movement = InventoryMovement(
            lot_id=lot.id,
            movement_type=movement_type,
            quantity_change=quantity_change,
            unit=lot.unit,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            created_by_user_id=user_id,
        )
        self.movements.create(movement)
        self.db.add(lot)
        self.db.flush()
        return movement

    @staticmethod
    def _to_response(movement: InventoryMovement) -> InventoryMovementResponse:
        lot = movement.lot
        return InventoryMovementResponse(
            id=movement.id,
            lot_id=movement.lot_id,
            lot_code=lot.lot_code,
            product_item_id=lot.product_item_id,
            product_item_name=lot.product_item.name,
            movement_type=movement.movement_type,
            quantity_change=movement.quantity_change,
            unit=movement.unit,
            reference_type=movement.reference_type,
            reference_id=movement.reference_id,
            notes=movement.notes,
            created_by_user_id=movement.created_by_user_id,
            created_at=movement.created_at,
        )
