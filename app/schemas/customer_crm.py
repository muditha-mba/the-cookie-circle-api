"""Customer CRM schemas (insights, notes, communications)."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import CommunicationType, CustomerSegment, MarketingSource
from app.core.enums import CustomerSource


class CustomerListParams(BaseModel):
    """Query parameters for enriched customer list."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: str | None = Field(default=None, max_length=200)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    segment: CustomerSegment | None = None
    marketing_source: MarketingSource | None = None
    min_order_count: int | None = Field(default=None, ge=0)
    max_order_count: int | None = Field(default=None, ge=0)
    min_lifetime_spend: Decimal | None = Field(default=None, ge=0)
    max_lifetime_spend: Decimal | None = Field(default=None, ge=0)


class CustomerInsightsResponse(BaseModel):
    """Calculated customer value and preference metrics."""

    lifetime_spend: Decimal
    total_orders: int
    average_order_value: Decimal
    last_order_date: date | None
    first_order_date: date | None
    favourite_product: str | None
    favourite_collection: str | None
    segment: CustomerSegment | None
    marketing_source: MarketingSource | None


class CustomerListItemResponse(BaseModel):
    """Customer list row with CRM metrics."""

    id: UUID
    user_id: UUID | None
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    source: CustomerSource
    marketing_source: MarketingSource | None
    is_active: bool
    created_at: datetime
    total_orders: int
    lifetime_spend: Decimal
    last_order_date: date | None
    segment: CustomerSegment | None


class CreatedBySummary(BaseModel):
    """Staff user who created a CRM entry."""

    id: UUID
    email: str
    display_name: str

    @classmethod
    def from_user(cls, user: object) -> "CreatedBySummary":
        from app.models.user import User

        if not isinstance(user, User):
            raise TypeError("Expected User")
        name_parts = [user.first_name, user.last_name]
        display = " ".join(p for p in name_parts if p).strip() or user.email
        return cls(id=user.id, email=user.email, display_name=display)


class CustomerNoteCreate(BaseModel):
    note: str = Field(min_length=1, max_length=10000)


class CustomerNoteResponse(BaseModel):
    id: UUID
    customer_id: UUID
    note: str
    created_by: CreatedBySummary
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerCommunicationCreate(BaseModel):
    communication_type: CommunicationType
    note: str = Field(min_length=1, max_length=10000)


class CustomerCommunicationResponse(BaseModel):
    id: UUID
    customer_id: UUID
    communication_type: CommunicationType
    note: str
    created_by: CreatedBySummary
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerOrderHistoryItem(BaseModel):
    id: UUID
    order_number: str
    status: str
    scheduled_delivery_date: date
    total_revenue_snapshot: Decimal
    total_profit_snapshot: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}
