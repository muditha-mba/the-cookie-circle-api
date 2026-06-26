"""Inventory readiness Pydantic schemas."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class InventoryReadinessLine(BaseModel):
    product_item_id: UUID
    product_item_name: str
    quantity_needed: Decimal
    unit: str
    quantity_on_hand: Decimal
    quantity_gap: Decimal
    track_inventory: bool
    is_short: bool


class InventoryReadinessResponse(BaseModel):
    delivery_date: date
    lines: list[InventoryReadinessLine]
    shortfall_count: int
    tracked_item_count: int


class InventoryExpenseSupplierRow(BaseModel):
    supplier_id: UUID
    supplier_name: str
    receipt_count: int
    total_amount: Decimal


class InventoryExpenseItemTypeRow(BaseModel):
    item_type_id: UUID
    item_type_name: str
    total_amount: Decimal


class InventoryExpenseSummaryResponse(BaseModel):
    from_date: date
    to_date: date
    total_amount: Decimal
    receipt_count: int
    by_supplier: list[InventoryExpenseSupplierRow]
    by_item_type: list[InventoryExpenseItemTypeRow]
