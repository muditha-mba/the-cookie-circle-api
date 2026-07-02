"""Recipe calculator schemas."""

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class RecipeCalculatorProductOption(BaseModel):
    id: uuid.UUID
    name: str
    yield_quantity: Decimal


class RecipeCalculatorProductOptionsResponse(BaseModel):
    products: list[RecipeCalculatorProductOption]


class RecipeCalculatorCalculateRequest(BaseModel):
    product_id: uuid.UUID
    target_quantity: Decimal = Field(gt=0)

    @field_validator("target_quantity")
    @classmethod
    def validate_whole_cookie_count(cls, value: Decimal) -> Decimal:
        if value != value.to_integral_value():
            raise ValueError("Target quantity must be a whole number.")
        return value


class RecipeCalculatorIngredientLine(BaseModel):
    product_item_id: uuid.UUID
    product_item_name: str
    recipe_quantity: Decimal
    scaled_quantity: Decimal
    unit: str
    is_discrete: bool
    suggested_quantity: int | None = None
    cost_per_unit: Decimal | None = None
    scaled_line_cost: Decimal | None = None


class RecipeCalculatorCostSummary(BaseModel):
    ingredients_subtotal: Decimal
    buffer_amount: Decimal
    total_cost: Decimal
    cost_per_unit: Decimal


class RecipeCalculatorResponse(BaseModel):
    product_id: uuid.UUID
    product_name: str
    yield_quantity: Decimal
    target_quantity: Decimal
    scale_factor: Decimal
    production_notes: str | None
    ingredients: list[RecipeCalculatorIngredientLine]
    cost_summary: RecipeCalculatorCostSummary | None = None
