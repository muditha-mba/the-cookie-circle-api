"""Package configuration Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.pagination import PaginationParams
from app.schemas.collection_package import CollectionPackageResponse
from app.schemas.product import AttachedChargeSummary


class ProductCategorySummary(BaseModel):
    id: UUID
    code: str
    name: str

    model_config = {"from_attributes": True}


class CollectionItemLineInput(BaseModel):
    """Packaging product item line for create/update."""

    product_item_id: UUID
    quantity: Decimal = Field(gt=0)


class CollectionItemLineResponse(BaseModel):
    id: UUID
    product_item_id: UUID
    product_item_name: str
    quantity: Decimal
    unit: str

    model_config = {"from_attributes": True}


class CollectionBase(BaseModel):
    """Shared package configuration fields."""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    package_id: UUID
    package_size: int = Field(gt=0)
    package_fee: Decimal = Field(ge=0)
    is_active: bool = True
    is_public: bool = True
    allowed_category_ids: list[UUID] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class CollectionCreate(CollectionBase):
    """Create package configuration."""

    item_lines: list[CollectionItemLineInput] = Field(default_factory=list)
    utility_charge_ids: list[UUID] = Field(default_factory=list)
    labour_charge_ids: list[UUID] = Field(default_factory=list)
    tax_charge_ids: list[UUID] = Field(default_factory=list)


class CollectionUpdate(BaseModel):
    """Update package configuration."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    package_id: UUID | None = None
    package_size: int | None = Field(default=None, gt=0)
    package_fee: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None
    is_public: bool | None = None
    allowed_category_ids: list[UUID] | None = Field(default=None, min_length=1)
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


class CollectionListParams(PaginationParams):
    """Collections list query parameters."""

    package_id: UUID | None = None


class CollectionSummaryResponse(CollectionBase):
    """Package configuration list item."""

    id: UUID
    package_name: str
    package_code: str
    created_at: datetime
    updated_at: datetime


class CollectionDetailResponse(CollectionSummaryResponse):
    """Package configuration detail."""

    allowed_categories: list[ProductCategorySummary]
    item_lines: list[CollectionItemLineResponse]
    utility_charges: list[AttachedChargeSummary]
    labour_charges: list[AttachedChargeSummary]
    tax_charges: list[AttachedChargeSummary]
    package: CollectionPackageResponse
