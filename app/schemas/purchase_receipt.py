"""Purchase receipt Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.enums import PurchaseReceiptStatus
from app.schemas.supplier import SupplierSummary


class PurchaseReceiptLineBase(BaseModel):
    product_item_id: UUID
    quantity: Decimal = Field(gt=0)
    unit: str = Field(min_length=1, max_length=50)
    expires_at: date | None = None

    @field_validator("unit")
    @classmethod
    def normalize_unit(cls, value: str) -> str:
        return value.strip().lower()


class PurchaseReceiptLineCreate(PurchaseReceiptLineBase):
    """Line input from a supplier receipt — total paid, not per-unit cost."""

    line_total: Decimal = Field(ge=0)


class PurchaseReceiptLineResponse(PurchaseReceiptLineBase):
    id: UUID
    unit_cost: Decimal
    line_total: Decimal
    product_item_name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PurchaseReceiptBase(BaseModel):
    supplier_id: UUID
    receipt_date: date
    reference_number: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)


class PurchaseReceiptCreate(PurchaseReceiptBase):
    lines: list[PurchaseReceiptLineCreate] = Field(min_length=1)


class PurchaseReceiptUpdate(BaseModel):
    supplier_id: UUID | None = None
    receipt_date: date | None = None
    reference_number: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)
    lines: list[PurchaseReceiptLineCreate] | None = Field(default=None, min_length=1)
    bill_asset_id: UUID | None = None
    bill_content_type: str | None = Field(default=None, max_length=100)
    bill_extension: str | None = Field(default=None, max_length=20)


class PurchaseReceiptSummary(BaseModel):
    id: UUID
    supplier: SupplierSummary
    receipt_date: date
    reference_number: str | None
    total_amount: Decimal
    status: PurchaseReceiptStatus
    has_bill: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PurchaseReceiptAttachmentResponse(BaseModel):
    id: UUID
    asset_id: UUID
    content_type: str
    extension: str
    file_name: str | None
    sort_order: int
    is_image: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PurchaseReceiptAttachmentRegister(BaseModel):
    asset_id: UUID
    content_type: str = Field(min_length=3, max_length=100)
    extension: str = Field(min_length=1, max_length=20)
    file_name: str | None = Field(default=None, max_length=255)


class PurchaseReceiptResponse(PurchaseReceiptSummary):
    notes: str | None
    bill_asset_id: UUID | None
    bill_content_type: str | None
    bill_extension: str | None
    attachments: list[PurchaseReceiptAttachmentResponse]
    lines: list[PurchaseReceiptLineResponse]
    confirmed_at: datetime | None
    created_by_user_id: UUID | None
    confirmed_by_user_id: UUID | None


class BillUploadUrlRequest(BaseModel):
    content_type: str = Field(min_length=3, max_length=100)


class BillUploadUrlResponse(BaseModel):
    asset_id: UUID
    upload_url: str
    extension: str
    expires_in: int
