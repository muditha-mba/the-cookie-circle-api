"""Shared global charge Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.enums import ChargeType


# ─── Overhead (Utility / Labour) ─────────────────────────────────────────────

class OverheadChargeBase(BaseModel):
    """Shared fields for utility and labour overhead definitions."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class OverheadChargeUpdate(BaseModel):
    """Update fields for utility and labour overhead definitions."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class OverheadChargeResponse(OverheadChargeBase):
    """Response for a utility or labour overhead definition."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Bill Entries ─────────────────────────────────────────────────────────────

class BillEntryCreate(BaseModel):
    """Record a monthly bill amount for an overhead category."""

    year: int = Field(ge=2020, le=2100)
    month: int = Field(ge=1, le=12)
    amount: Decimal = Field(ge=0)
    notes: str | None = Field(default=None, max_length=2000)


class BillEntryUpdate(BaseModel):
    """Update a monthly bill entry."""

    amount: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=2000)


class BillEntryResponse(BaseModel):
    """Monthly bill entry response."""

    id: UUID
    year: int
    month: int
    amount: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OverheadChargeDetailResponse(OverheadChargeResponse):
    """Overhead detail with all monthly bill entries."""

    bill_entries: list[BillEntryResponse] = Field(default_factory=list)


# ─── Tax Charges ─────────────────────────────────────────────────────────────

class TaxChargeBase(BaseModel):
    """Order-level tax or fee definition."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    charge_type: ChargeType
    amount: Decimal = Field(gt=0)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_amount_for_type(self) -> "TaxChargeBase":
        if self.charge_type == ChargeType.PERCENTAGE and self.amount > Decimal("100"):
            raise ValueError("Percentage amount cannot exceed 100")
        return self


class TaxChargeUpdate(BaseModel):
    """Update an order-level tax charge."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    charge_type: ChargeType | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @model_validator(mode="after")
    def validate_amount_for_type(self) -> "TaxChargeUpdate":
        if self.amount is None or self.charge_type is None:
            return self
        if self.charge_type == ChargeType.PERCENTAGE and self.amount > Decimal("100"):
            raise ValueError("Percentage amount cannot exceed 100")
        return self


class TaxChargeResponse(TaxChargeBase):
    """Tax charge response."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Typed aliases for backwards compat / OpenAPI clarity ────────────────────

class UtilityChargeCreate(OverheadChargeBase):
    """Create utility charge request."""


class UtilityChargeUpdate(OverheadChargeUpdate):
    """Update utility charge request."""


class UtilityChargeResponse(OverheadChargeResponse):
    """Utility charge response."""


class UtilityChargeDetailResponse(OverheadChargeDetailResponse):
    """Utility charge with bill entries."""


class LabourChargeCreate(OverheadChargeBase):
    """Create labour charge request."""


class LabourChargeUpdate(OverheadChargeUpdate):
    """Update labour charge request."""


class LabourChargeResponse(OverheadChargeResponse):
    """Labour charge response."""


class LabourChargeDetailResponse(OverheadChargeDetailResponse):
    """Labour charge with bill entries."""


class TaxChargeCreate(TaxChargeBase):
    """Create tax charge request."""


# Re-export TaxChargeUpdate and TaxChargeResponse as-is
__all__ = [
    "OverheadChargeBase",
    "OverheadChargeUpdate",
    "OverheadChargeResponse",
    "OverheadChargeDetailResponse",
    "BillEntryCreate",
    "BillEntryUpdate",
    "BillEntryResponse",
    "TaxChargeBase",
    "TaxChargeUpdate",
    "TaxChargeResponse",
    "TaxChargeCreate",
    "UtilityChargeCreate",
    "UtilityChargeUpdate",
    "UtilityChargeResponse",
    "UtilityChargeDetailResponse",
    "LabourChargeCreate",
    "LabourChargeUpdate",
    "LabourChargeResponse",
    "LabourChargeDetailResponse",
]
