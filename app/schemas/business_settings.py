"""Business settings Pydantic schemas."""

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.core.enums import Weekday


class BusinessSettingsResponse(BaseModel):
    """Typed view of operational business settings."""

    delivery_fee: Decimal
    use_fixed_delivery_fee: bool
    order_cutoff_day: Weekday
    delivery_day: Weekday
    business_phone: str
    business_email: str
    stripe_enabled: bool
    bank_transfer_enabled: bool
    cod_enabled: bool


class BusinessSettingsUpdate(BaseModel):
    """Update business settings."""

    delivery_fee: Decimal | None = Field(default=None, ge=0)
    use_fixed_delivery_fee: bool | None = None
    order_cutoff_day: Weekday | None = None
    delivery_day: Weekday | None = None
    business_phone: str | None = Field(default=None, max_length=50)
    business_email: str | None = Field(default=None, max_length=320)
    stripe_enabled: bool | None = None
    bank_transfer_enabled: bool | None = None
    cod_enabled: bool | None = None

    @field_validator("business_email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("business_phone")
    @classmethod
    def strip_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class SuggestedDeliveryDateResponse(BaseModel):
    """Suggested delivery date from schedule engine."""

    reference_date: str
    suggested_delivery_date: str
    order_cutoff_day: Weekday
    delivery_day: Weekday
