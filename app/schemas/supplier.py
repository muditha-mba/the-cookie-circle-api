"""Supplier Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class SupplierBase(BaseModel):
    """Shared supplier fields."""

    supplier_name: str = Field(min_length=1, max_length=200)
    contact_person: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=10000)
    is_active: bool = True

    @field_validator("supplier_name", "contact_person", "phone", "address")
    @classmethod
    def strip_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("supplier_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class SupplierCreate(SupplierBase):
    """Create supplier request."""


class SupplierUpdate(BaseModel):
    """Update supplier request."""

    supplier_name: str | None = Field(default=None, min_length=1, max_length=200)
    contact_person: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=10000)
    is_active: bool | None = None

    @field_validator("supplier_name", "contact_person", "phone", "address")
    @classmethod
    def strip_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class SupplierResponse(SupplierBase):
    """Supplier response."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplierSummary(BaseModel):
    """Minimal supplier for embedding."""

    id: UUID
    supplier_name: str

    model_config = {"from_attributes": True}
