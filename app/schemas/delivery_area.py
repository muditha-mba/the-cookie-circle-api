"""Delivery area Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class DeliveryAreaBase(BaseModel):
    """Shared delivery area fields."""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    delivery_fee_override: Decimal | None = Field(default=None, ge=0)
    pickup_only: bool = False
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class DeliveryAreaCreate(DeliveryAreaBase):
    """Create delivery area request."""


class DeliveryAreaUpdate(BaseModel):
    """Update delivery area request."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    delivery_fee_override: Decimal | None = Field(default=None, ge=0)
    pickup_only: bool | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class DeliveryAreaResponse(DeliveryAreaBase):
    """Delivery area response."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeliveryAreaSummary(BaseModel):
    """Minimal delivery area for order embedding."""

    id: UUID
    name: str
    pickup_only: bool

    model_config = {"from_attributes": True}
