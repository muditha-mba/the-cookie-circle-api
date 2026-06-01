"""Purchase planning Pydantic schemas."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import PurchasePlanningStatus
from app.schemas.production_batch import ProductionBatchResponse
from app.schemas.supplier import SupplierSummary


class PurchasePlanLine(BaseModel):
    """Single item to purchase for a production batch."""

    product_item_id: UUID
    product_item_name: str
    quantity: Decimal
    unit: str
    estimated_cost: Decimal
    supplier: SupplierSummary | None = None
    purchase_status: PurchasePlanningStatus


class PurchasePlanResponse(BaseModel):
    """Purchase plan for a delivery date."""

    delivery_date: date
    production_batch: ProductionBatchResponse
    items: list[PurchasePlanLine]


class PurchasePlanStatusUpdate(BaseModel):
    """Update purchase planning status for one item."""

    delivery_date: date
    product_item_id: UUID
    purchase_status: PurchasePlanningStatus


class PurchasePlanSupplierGroup(BaseModel):
    """Items grouped by supplier for display or export."""

    supplier: SupplierSummary | None
    items: list[PurchasePlanLine]
