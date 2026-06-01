"""Collection and costing Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.product import (
    AdditionalChargesBreakdown,
    AttachedChargeSummary,
    ChargeBreakdownLine,
)


class CollectionProductLineInput(BaseModel):
    """Product line for create/update/preview."""

    product_id: UUID
    quantity: Decimal = Field(gt=0)


class CollectionItemLineInput(BaseModel):
    """Packaging product item line for create/update/preview."""

    product_item_id: UUID
    quantity: Decimal = Field(gt=0)


class CollectionBase(BaseModel):
    """Shared collection fields."""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    selling_price: Decimal = Field(ge=0)
    buffer_amount: Decimal = Field(default=Decimal("0"), ge=0)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class CollectionCreate(CollectionBase):
    """Create collection request."""

    product_lines: list[CollectionProductLineInput] = Field(default_factory=list)
    item_lines: list[CollectionItemLineInput] = Field(default_factory=list)
    utility_charge_ids: list[UUID] = Field(default_factory=list)
    labour_charge_ids: list[UUID] = Field(default_factory=list)
    tax_charge_ids: list[UUID] = Field(default_factory=list)


class CollectionUpdate(BaseModel):
    """Update collection request."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    selling_price: Decimal | None = Field(default=None, ge=0)
    buffer_amount: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None
    product_lines: list[CollectionProductLineInput] | None = None
    item_lines: list[CollectionItemLineInput] | None = None
    utility_charge_ids: list[UUID] | None = None
    labour_charge_ids: list[UUID] | None = None
    tax_charge_ids: list[UUID] | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class CollectionCostPreviewRequest(BaseModel):
    """Calculate collection cost breakdown without persisting."""

    selling_price: Decimal = Field(ge=0)
    buffer_amount: Decimal = Field(default=Decimal("0"), ge=0)
    product_lines: list[CollectionProductLineInput] = Field(default_factory=list)
    item_lines: list[CollectionItemLineInput] = Field(default_factory=list)
    utility_charge_ids: list[UUID] = Field(default_factory=list)
    labour_charge_ids: list[UUID] = Field(default_factory=list)
    tax_charge_ids: list[UUID] = Field(default_factory=list)


class CollectionSummaryResponse(CollectionBase):
    """Collection list item."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CollectionProductLineResponse(BaseModel):
    """Collection product line with cost contribution."""

    id: UUID
    product_id: UUID
    product_name: str
    quantity: Decimal
    unit_total_cost: Decimal
    cost_contribution: Decimal

    model_config = {"from_attributes": True}


class CollectionProductsBreakdown(BaseModel):
    """Product cost section of a collection breakdown."""

    lines: list[CollectionProductLineResponse]
    subtotal: Decimal


class CollectionItemLineResponse(BaseModel):
    """Packaging item line with applied cost."""

    id: UUID
    product_item_id: UUID
    product_item_name: str
    quantity: Decimal
    unit: str
    cost_per_unit: Decimal
    applied_cost: Decimal

    model_config = {"from_attributes": True}


class CollectionItemsBreakdown(BaseModel):
    """Packaging item cost section of a collection breakdown."""

    lines: list[CollectionItemLineResponse]
    subtotal: Decimal


class CollectionCostBreakdown(BaseModel):
    """Full collection cost and profitability breakdown."""

    products: CollectionProductsBreakdown
    collection_items: CollectionItemsBreakdown
    additional_charges: AdditionalChargesBreakdown
    buffer_amount: Decimal
    total_cost: Decimal
    selling_price: Decimal
    profit_amount: Decimal
    profit_margin_percent: Decimal


class CollectionDetailResponse(CollectionSummaryResponse):
    """Collection detail with products, charges, and breakdown."""

    product_lines: list[CollectionProductLineResponse]
    item_lines: list[CollectionItemLineResponse]
    utility_charges: list[AttachedChargeSummary]
    labour_charges: list[AttachedChargeSummary]
    tax_charges: list[AttachedChargeSummary]
    cost_breakdown: CollectionCostBreakdown
