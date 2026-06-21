"""Discount management Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.enums import (
    DiscountAuditEventType,
    DiscountGrantStatus,
    DiscountRuleType,
    DiscountSource,
    DiscountType,
)


# ─── Discount Rule config ─────────────────────────────────────────────────────


class OrderFrequencyInWindowConfig(BaseModel):
    """Config for the order_frequency_in_window rule type."""

    required_order_count: int = Field(ge=2, description="Number of orders required in the window")
    window_days: int = Field(ge=1, le=365, description="Rolling window in days")
    discount_type: DiscountType
    discount_value: Decimal = Field(gt=0, description="Fixed amount (LKR) or percentage (0–100)")
    image_url: str = Field(
        min_length=1,
        max_length=2000,
        description="Banner image URL shown on the client promotions carousel",
    )
    grant_expires_days: int | None = Field(
        default=None,
        ge=1,
        le=365,
        description="Days until grant expires after issue; null = never expires",
    )

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str) -> str:
        value = value.strip()
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("image_url must start with http:// or https://")
        return value

    @model_validator(mode="after")
    def validate_percentage_cap(self) -> "OrderFrequencyInWindowConfig":
        if (
            self.discount_type == DiscountType.PERCENTAGE
            and self.discount_value > Decimal("100")
        ):
            raise ValueError("Percentage discount value cannot exceed 100")
        return self


# ─── Discount Rule ────────────────────────────────────────────────────────────


class DiscountRuleCreate(BaseModel):
    """Create a new discount rule."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    rule_type: DiscountRuleType
    config: dict[str, Any]
    priority: int = Field(default=100, ge=1, le=999)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_config(self) -> "DiscountRuleCreate":
        _validate_rule_config(self.rule_type, self.config)
        return self


class DiscountRuleUpdate(BaseModel):
    """Update a discount rule."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    config: dict[str, Any] | None = None
    priority: int | None = Field(default=None, ge=1, le=999)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class DiscountRuleResponse(BaseModel):
    """Discount rule response."""

    id: UUID
    name: str
    description: str | None
    rule_type: DiscountRuleType
    config: dict[str, Any]
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Customer Discount Grant ──────────────────────────────────────────────────


class CustomerDiscountGrantManualCreate(BaseModel):
    """Manually issue a discount grant to a customer."""

    discount_type: DiscountType
    discount_value: Decimal = Field(gt=0)
    eligibility_reason: str | None = Field(default=None, max_length=2000)
    grant_expires_days: int | None = Field(default=None, ge=1, le=365)

    @model_validator(mode="after")
    def validate_percentage_cap(self) -> "CustomerDiscountGrantManualCreate":
        if (
            self.discount_type == DiscountType.PERCENTAGE
            and self.discount_value > Decimal("100")
        ):
            raise ValueError("Percentage discount value cannot exceed 100")
        return self


class CustomerDiscountGrantResponse(BaseModel):
    """A customer discount grant."""

    id: UUID
    customer_id: UUID
    discount_rule_id: UUID | None
    discount_type: DiscountType
    discount_value: Decimal
    source: DiscountSource
    status: DiscountGrantStatus
    eligibility_reason: str | None
    earned_at: datetime
    expires_at: datetime | None
    used_at: datetime | None
    used_on_order_id: UUID | None
    revoked_at: datetime | None
    revoke_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerDiscountGrantRevokeRequest(BaseModel):
    """Revoke a customer discount grant."""

    reason: str | None = Field(default=None, max_length=2000)


# ─── Eligible customer summary ────────────────────────────────────────────────


class EligibleCustomerItem(BaseModel):
    """Eligible customer with their active grant summary."""

    customer_id: UUID
    customer_name: str
    customer_email: str
    grant_id: UUID
    discount_type: DiscountType
    discount_value: Decimal
    source: DiscountSource
    earned_at: datetime
    expires_at: datetime | None


# ─── Customer Discount Override ───────────────────────────────────────────────


class CustomerDiscountOverrideSet(BaseModel):
    """Set or clear a customer-level discount override."""

    discounts_enabled: bool
    reason: str | None = Field(default=None, max_length=2000)


class CustomerDiscountOverrideResponse(BaseModel):
    """Customer discount override response."""

    id: UUID
    customer_id: UUID
    discounts_enabled: bool
    reason: str | None
    admin_user_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Discount Audit Events ────────────────────────────────────────────────────


class DiscountAuditEventResponse(BaseModel):
    """Discount audit event response."""

    id: UUID
    event_type: DiscountAuditEventType
    customer_id: UUID | None
    customer_discount_grant_id: UUID | None
    discount_rule_id: UUID | None
    order_id: UUID | None
    admin_user_id: UUID | None
    payload: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── History item (denormalized for list view) ────────────────────────────────


class DiscountHistoryItem(BaseModel):
    """Discount grant history row (all statuses)."""

    grant_id: UUID
    customer_id: UUID
    customer_name: str
    customer_email: str
    discount_type: DiscountType
    discount_value: Decimal
    source: DiscountSource
    status: DiscountGrantStatus
    earned_at: datetime
    expires_at: datetime | None
    used_at: datetime | None
    used_on_order_id: UUID | None
    revoked_at: datetime | None
    revoke_reason: str | None


# ─── Config validation helper ─────────────────────────────────────────────────


def _validate_rule_config(rule_type: DiscountRuleType, config: dict[str, Any]) -> None:
    """Raise ValidationError if config does not match rule_type shape."""
    if rule_type == DiscountRuleType.ORDER_FREQUENCY_IN_WINDOW:
        OrderFrequencyInWindowConfig.model_validate(config)
