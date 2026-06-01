"""Product and costing Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RecipeLineInput(BaseModel):
    """Recipe line for create/update/preview."""

    product_item_id: UUID
    quantity: Decimal = Field(gt=0)


class ProductBase(BaseModel):
    """Shared product fields."""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    selling_price: Decimal = Field(ge=0)
    buffer_amount: Decimal = Field(default=Decimal("0"), ge=0)
    yield_quantity: Decimal = Field(gt=0)
    production_notes: str | None = Field(default=None, max_length=5000)
    is_active: bool = True
    is_public: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class ProductCreate(ProductBase):
    """Create product request."""

    recipe_lines: list[RecipeLineInput] = Field(default_factory=list)
    utility_charge_ids: list[UUID] = Field(default_factory=list)
    labour_charge_ids: list[UUID] = Field(default_factory=list)
    tax_charge_ids: list[UUID] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    """Update product request."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    selling_price: Decimal | None = Field(default=None, ge=0)
    buffer_amount: Decimal | None = Field(default=None, ge=0)
    yield_quantity: Decimal | None = Field(default=None, gt=0)
    production_notes: str | None = Field(default=None, max_length=5000)
    is_active: bool | None = None
    is_public: bool | None = None
    recipe_lines: list[RecipeLineInput] | None = None
    utility_charge_ids: list[UUID] | None = None
    labour_charge_ids: list[UUID] | None = None
    tax_charge_ids: list[UUID] | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class ProductCostPreviewRequest(BaseModel):
    """Calculate cost breakdown without persisting."""

    selling_price: Decimal = Field(ge=0)
    buffer_amount: Decimal = Field(default=Decimal("0"), ge=0)
    yield_quantity: Decimal = Field(gt=0)
    recipe_lines: list[RecipeLineInput] = Field(default_factory=list)
    utility_charge_ids: list[UUID] = Field(default_factory=list)
    labour_charge_ids: list[UUID] = Field(default_factory=list)
    tax_charge_ids: list[UUID] = Field(default_factory=list)


class ProductSummaryResponse(ProductBase):
    """Product list item."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecipeLineResponse(BaseModel):
    """Recipe line with costing details."""

    id: UUID
    product_item_id: UUID
    product_item_name: str
    quantity: Decimal
    unit: str
    cost_per_unit: Decimal
    line_cost: Decimal

    model_config = {"from_attributes": True}


class ChargeBreakdownLine(BaseModel):
    """Applied global charge in a product breakdown."""

    id: UUID
    name: str
    charge_type: str
    configured_amount: Decimal
    applied_cost: Decimal


class IngredientBreakdown(BaseModel):
    """Ingredient cost section."""

    lines: list[RecipeLineResponse]
    subtotal: Decimal


class AdditionalChargesBreakdown(BaseModel):
    """Additional charges grouped by category."""

    utility_charges: list[ChargeBreakdownLine]
    labour_charges: list[ChargeBreakdownLine]
    tax_charges: list[ChargeBreakdownLine]
    subtotal: Decimal


class ProductCostBreakdown(BaseModel):
    """Full product cost and profitability breakdown."""

    ingredients: IngredientBreakdown
    additional_charges: AdditionalChargesBreakdown
    buffer_amount: Decimal
    total_cost: Decimal
    selling_price: Decimal
    profit_amount: Decimal
    profit_margin_percent: Decimal
    cost_per_unit: Decimal
    profit_per_unit: Decimal


class AttachedChargeSummary(BaseModel):
    """Reference to an attached global charge."""

    id: UUID
    name: str
    charge_type: str
    amount: Decimal
    applicability: str
    is_active: bool


class ProductDetailResponse(ProductSummaryResponse):
    """Product detail with recipe, charges, and breakdown."""

    recipe_lines: list[RecipeLineResponse]
    utility_charges: list[AttachedChargeSummary]
    labour_charges: list[AttachedChargeSummary]
    tax_charges: list[AttachedChargeSummary]
    cost_breakdown: ProductCostBreakdown
