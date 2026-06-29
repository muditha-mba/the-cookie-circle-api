"""Consumption proposal Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.enums import ConsumptionDemandType, ConsumptionProposalStatus


class ConsumptionProposalOrderSummary(BaseModel):
    id: UUID
    order_number: str
    customer_name: str
    delivered_at: datetime | None

    model_config = {"from_attributes": True}


class ConsumptionProposalLotAllocationResponse(BaseModel):
    id: UUID
    lot_id: UUID
    lot_code: str
    quantity: Decimal
    unit: str
    expires_at: date | None

    model_config = {"from_attributes": True}


class ConsumptionProposalLineResponse(BaseModel):
    id: UUID
    product_item_id: UUID
    product_item_name: str
    demand_type: ConsumptionDemandType
    quantity_proposed: Decimal
    quantity_approved: Decimal | None
    effective_quantity: Decimal
    unit: str
    quantity_on_hand_snapshot: Decimal
    quantity_after: Decimal
    track_inventory: bool
    has_shortfall: bool
    lot_allocations: list[ConsumptionProposalLotAllocationResponse]

    model_config = {"from_attributes": True}


class ConsumptionProposalSummary(BaseModel):
    id: UUID
    delivery_date: date
    status: ConsumptionProposalStatus
    order_count: int
    line_count: int
    has_shortfall: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConsumptionProposalResponse(BaseModel):
    id: UUID
    delivery_date: date
    status: ConsumptionProposalStatus
    notes: str | None
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    applied_at: datetime | None
    created_at: datetime
    updated_at: datetime
    orders: list[ConsumptionProposalOrderSummary]
    lines: list[ConsumptionProposalLineResponse]
    has_shortfall: bool


class ConsumptionProposalLineUpdate(BaseModel):
    id: UUID
    quantity_approved: Decimal | None = Field(default=None, ge=0)


class ConsumptionProposalUpdate(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)
    lines: list[ConsumptionProposalLineUpdate] | None = None


class ConsumptionProposalGenerateRequest(BaseModel):
    delivery_date: date | None = None
    order_ids: list[UUID] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def require_scope(self) -> "ConsumptionProposalGenerateRequest":
        if self.delivery_date is None and not self.order_ids:
            raise ValueError("Provide delivery_date or order_ids")
        return self


class ConsumptionProposalPendingCount(BaseModel):
    pending_count: int
