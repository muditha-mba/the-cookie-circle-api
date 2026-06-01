"""Product item Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.utils.costing import calculate_cost_per_unit


class ProductItemBase(BaseModel):
    """Shared product item fields."""

    item_type_id: UUID
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    purchase_price: Decimal = Field(ge=0)
    purchase_quantity: Decimal = Field(gt=0)
    purchase_unit: str = Field(min_length=1, max_length=50)
    is_active: bool = True

    @field_validator("name", "purchase_unit")
    @classmethod
    def strip_strings(cls, value: str) -> str:
        return value.strip()

    @field_validator("purchase_unit")
    @classmethod
    def normalize_unit(cls, value: str) -> str:
        return value.strip().lower()


class ProductItemCreate(ProductItemBase):
    """Create product item request."""


class ProductItemUpdate(BaseModel):
    """Update product item request."""

    item_type_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    purchase_price: Decimal | None = Field(default=None, ge=0)
    purchase_quantity: Decimal | None = Field(default=None, gt=0)
    purchase_unit: str | None = Field(default=None, min_length=1, max_length=50)
    is_active: bool | None = None

    @field_validator("name", "purchase_unit")
    @classmethod
    def strip_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("purchase_unit")
    @classmethod
    def normalize_unit(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()


class ProductItemTypeSummary(BaseModel):
    """Embedded item type summary."""

    id: UUID
    name: str

    model_config = {"from_attributes": True}


class ProductItemResponse(ProductItemBase):
    """Product item response with derived unit cost."""

    id: UUID
    cost_per_unit: Decimal
    item_type: ProductItemTypeSummary
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, item: object) -> "ProductItemResponse":
        """Build response including computed cost per unit."""
        from app.models.product_item import ProductItem

        if not isinstance(item, ProductItem):
            raise TypeError("Expected ProductItem model instance")

        cost_per_unit = calculate_cost_per_unit(
            item.purchase_price,
            item.purchase_quantity,
        )
        return cls(
            id=item.id,
            item_type_id=item.item_type_id,
            name=item.name,
            description=item.description,
            purchase_price=item.purchase_price,
            purchase_quantity=item.purchase_quantity,
            purchase_unit=item.purchase_unit,
            is_active=item.is_active,
            cost_per_unit=cost_per_unit,
            item_type=ProductItemTypeSummary.model_validate(item.item_type),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
