"""Authenticated customer account schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.enums import OrderStatus, OrderType, PaymentMethod, PaymentStatus
from app.schemas.client_ordering import ClientBankTransferInstructions
from app.schemas.fields import NormalizedEmail
from app.utils.password import validate_password_strength


class ClientAccountProfileResponse(BaseModel):
    """Customer profile for the authenticated account."""

    customer_id: UUID
    user_id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None
    phone_secondary: str | None
    preferred_delivery_area: str | None
    member_since: datetime
    email_verified: bool


class ClientAccountProfileUpdate(BaseModel):
    """Update customer profile."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=5, max_length=50)
    phone_secondary: str | None = Field(default=None, max_length=50)
    preferred_delivery_area: str | None = Field(default=None, max_length=100)

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_names(cls, value: str) -> str:
        return value.strip()

    @field_validator("phone_secondary", "preferred_delivery_area")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ChangePasswordRequest(BaseModel):
    """Change password for authenticated customer."""

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, value: str, info) -> str:
        new_password = info.data.get("new_password")
        if new_password and value != new_password:
            raise ValueError("Passwords do not match")
        return value


class ClientAccountDashboardResponse(BaseModel):
    """Account dashboard summary."""

    first_name: str
    member_since: datetime
    email: EmailStr
    preferred_delivery_area: str | None
    total_orders: int
    completed_orders: int
    pending_orders: int
    total_cookies_ordered: int
    total_collections_ordered: int
    total_reviews: int
    favourite_cookie: str | None
    favourite_package_type: str | None
    recent_orders: list["ClientAccountOrderSummary"]


class ClientAccountAddressBase(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    recipient_name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=5, max_length=50)
    address_line_1: str = Field(min_length=1, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    landmark: str | None = Field(default=None, max_length=255)
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    is_default: bool = False


class ClientAccountAddressCreate(ClientAccountAddressBase):
    pass


class ClientAccountAddressUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=100)
    recipient_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, min_length=5, max_length=50)
    address_line_1: str | None = Field(default=None, min_length=1, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    landmark: str | None = Field(default=None, max_length=255)
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    is_default: bool | None = None


class ClientAccountAddressResponse(ClientAccountAddressBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientAccountOrderListParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: str | None = Field(default=None, max_length=200)
    status: OrderStatus | None = None
    order_type: OrderType | None = None
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class ClientAccountOrderSummary(BaseModel):
    id: UUID
    order_number: str
    order_type: OrderType
    status: OrderStatus
    scheduled_delivery_date: date
    delivery_area_name: str | None
    total: Decimal
    created_at: datetime


class ClientAccountOrderCookieLine(BaseModel):
    product_id: UUID
    product_name: str
    quantity: Decimal


class ClientAccountOrderCollectionLine(BaseModel):
    collection_name: str
    quantity: Decimal
    cookies: list[ClientAccountOrderCookieLine]


class ClientAccountOrderProductLine(BaseModel):
    product_id: UUID
    product_name: str
    quantity: Decimal


class ClientAccountOrderDetailResponse(BaseModel):
    id: UUID
    order_number: str
    order_type: OrderType
    status: OrderStatus
    payment_status: PaymentStatus
    event_name: str | None
    payment_method: PaymentMethod
    delivery_area_name: str | None
    scheduled_delivery_date: date
    created_at: datetime
    products_subtotal: Decimal
    collections_subtotal: Decimal
    delivery_fee: Decimal
    total: Decimal
    delivery_address_line_1: str | None
    delivery_address_line_2: str | None
    delivery_city: str | None
    delivery_postal_code: str | None
    delivery_landmark: str | None
    delivery_latitude: Decimal | None
    delivery_longitude: Decimal | None
    collection_lines: list[ClientAccountOrderCollectionLine]
    product_lines: list[ClientAccountOrderProductLine]
    premium_packaging_notice: str | None = None
    bank_transfer_instructions: ClientBankTransferInstructions | None = None
    order_details_message: str | None = None
    whatsapp_open_url: str | None = None


ClientAccountDashboardResponse.model_rebuild()
