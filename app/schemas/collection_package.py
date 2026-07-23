"""Collection package schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

PackagingFeeModeLiteral = Literal["flat", "per_cookie"]


class CollectionPackageBase(BaseModel):
    """Shared collection package fields."""

    code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    badge_tone: str = Field(min_length=2, max_length=32)
    is_active: bool = True
    min_quantity: int = Field(default=1, ge=1)
    max_quantity: int = Field(default=30, ge=1)
    packaging_fee_mode: PackagingFeeModeLiteral = "flat"
    packaging_fee_amount: Decimal = Field(default=Decimal("0"), ge=0)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name", "badge_tone")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_quantity_range(self) -> "CollectionPackageBase":
        if self.max_quantity < self.min_quantity:
            raise ValueError("max_quantity must be greater than or equal to min_quantity")
        return self


class CollectionPackageCreate(CollectionPackageBase):
    """Create collection package request."""


class CollectionPackageUpdate(BaseModel):
    """Update collection package request."""

    code: str | None = Field(default=None, min_length=2, max_length=64)
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    badge_tone: str | None = Field(default=None, min_length=2, max_length=32)
    is_active: bool | None = None
    min_quantity: int | None = Field(default=None, ge=1)
    max_quantity: int | None = Field(default=None, ge=1)
    packaging_fee_mode: PackagingFeeModeLiteral | None = None
    packaging_fee_amount: Decimal | None = Field(default=None, ge=0)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @field_validator("name", "badge_tone")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class CollectionPackageResponse(CollectionPackageBase):
    """Collection package response."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
