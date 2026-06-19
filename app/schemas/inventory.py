"""Inventory Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import InventoryMovementReferenceType, InventoryMovementType
from app.schemas.product_item import ProductItemTypeSummary


class InventoryLotSummary(BaseModel):
    id: UUID
    lot_code: str
    quantity_on_hand: Decimal
    unit: str
    expires_at: date | None
    received_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class InventoryBalanceResponse(BaseModel):
    product_item_id: UUID
    product_item_name: str
    item_type: ProductItemTypeSummary
    unit: str
    quantity_on_hand: Decimal
    reorder_level: Decimal | None
    reorder_unit: str | None
    is_low_stock: bool
    nearest_expiry: date | None


class InventoryBalanceDetailResponse(InventoryBalanceResponse):
    lots: list[InventoryLotSummary]


class InventoryMovementResponse(BaseModel):
    id: UUID
    lot_id: UUID
    lot_code: str
    product_item_id: UUID
    product_item_name: str
    movement_type: InventoryMovementType
    quantity_change: Decimal
    unit: str
    reference_type: InventoryMovementReferenceType
    reference_id: UUID | None
    notes: str | None
    created_by_user_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InventoryAdjustmentCreate(BaseModel):
    lot_id: UUID
    quantity_change: Decimal = Field(description="Positive to add stock, negative to remove")
    notes: str | None = Field(default=None, max_length=2000)


class InventoryWasteCreate(BaseModel):
    lot_id: UUID
    quantity: Decimal = Field(gt=0)
    notes: str | None = Field(default=None, max_length=2000)


class InventoryAlertResponse(BaseModel):
    low_stock_count: int
    expiring_soon_count: int
    pending_consumption_count: int = 0
