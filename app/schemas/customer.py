"""Customer Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.enums import CustomerSource, MarketingSource


class CustomerBase(BaseModel):
    """Shared customer fields."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    address_line_1: str | None = Field(default=None, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    landmark: str | None = Field(default=None, max_length=255)
    source: CustomerSource
    marketing_source: MarketingSource | None = None
    notes: str | None = Field(default=None, max_length=5000)
    is_active: bool = True

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_names(cls, value: str) -> str:
        return value.strip()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        return value.strip().lower()

    @field_validator("phone")
    @classmethod
    def strip_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class CustomerCreate(CustomerBase):
    """Create customer request."""

    user_id: UUID | None = None

    @model_validator(mode="after")
    def validate_registered_user(self) -> "CustomerCreate":
        if self.source == CustomerSource.REGISTERED and self.user_id is None:
            raise ValueError("Registered customers must be linked to a user")
        if self.source != CustomerSource.REGISTERED and self.user_id is not None:
            raise ValueError("Only registered customers may be linked to a user")
        return self


class CustomerUpdate(BaseModel):
    """Update customer request."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    address_line_1: str | None = Field(default=None, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    landmark: str | None = Field(default=None, max_length=255)
    source: CustomerSource | None = None
    marketing_source: MarketingSource | None = None
    notes: str | None = Field(default=None, max_length=5000)
    is_active: bool | None = None
    user_id: UUID | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_names(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        return value.strip().lower()


class CustomerUserSummary(BaseModel):
    """Linked user summary for registered customers."""

    id: UUID
    email: str

    model_config = {"from_attributes": True}


class CustomerSummaryResponse(CustomerBase):
    """Customer list item."""

    id: UUID
    user_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerDetailResponse(CustomerSummaryResponse):
    """Customer detail."""

    user: CustomerUserSummary | None = None
