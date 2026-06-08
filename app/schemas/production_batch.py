"""Production batch Pydantic schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import ProductionBatchStatus


class ProductionBatchBase(BaseModel):
    """Shared production batch fields."""

    delivery_date: date
    status: ProductionBatchStatus = ProductionBatchStatus.DRAFT
    notes: str | None = Field(default=None, max_length=10000)


class ProductionBatchCreate(BaseModel):
    """Create production batch."""

    delivery_date: date
    notes: str | None = Field(default=None, max_length=10000)


class ProductionBatchUpdate(BaseModel):
    """Update production batch planning metadata."""

    status: ProductionBatchStatus | None = None
    notes: str | None = Field(default=None, max_length=10000)


class ProductionBatchResponse(ProductionBatchBase):
    """Production batch response."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
