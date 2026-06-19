"""Purchase receipt routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response

from app.core.enums import PurchaseReceiptStatus
from app.dependencies.admin import (
    get_current_admin_user,
    get_purchase_receipt_service,
)
from app.dependencies.permissions import require_super_admin
from app.models.user import User
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.purchase_receipt import (
    BillUploadUrlRequest,
    BillUploadUrlResponse,
    PurchaseReceiptCreate,
    PurchaseReceiptResponse,
    PurchaseReceiptSummary,
    PurchaseReceiptUpdate,
)
from app.services.purchase_receipt_service import PurchaseReceiptService

router = APIRouter(
    prefix="/purchase-receipts",
    tags=["Purchase Receipts"],
    dependencies=[Depends(require_super_admin)],
)


@router.get("", response_model=PaginatedResponse[PurchaseReceiptSummary])
def list_purchase_receipts(
    params: Annotated[PaginationParams, Depends()],
    receipt_status: Annotated[PurchaseReceiptStatus | None, Query(alias="status")] = None,
    supplier_id: Annotated[uuid.UUID | None, Query()] = None,
    service: Annotated[PurchaseReceiptService, Depends(get_purchase_receipt_service)] = ...,
) -> PaginatedResponse[PurchaseReceiptSummary]:
    """List purchase receipts."""
    return service.list(params, status=receipt_status, supplier_id=supplier_id)


@router.post("", response_model=PurchaseReceiptResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_receipt(
    payload: PurchaseReceiptCreate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[PurchaseReceiptService, Depends(get_purchase_receipt_service)] = ...,
) -> PurchaseReceiptResponse:
    """Create a draft purchase receipt."""
    return service.create(payload, user_id=current_user.id)


@router.get("/{receipt_id}", response_model=PurchaseReceiptResponse)
def get_purchase_receipt(
    receipt_id: uuid.UUID,
    service: Annotated[PurchaseReceiptService, Depends(get_purchase_receipt_service)] = ...,
) -> PurchaseReceiptResponse:
    """Get purchase receipt detail."""
    return service.get(receipt_id)


@router.patch("/{receipt_id}", response_model=PurchaseReceiptResponse)
def update_purchase_receipt(
    receipt_id: uuid.UUID,
    payload: PurchaseReceiptUpdate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[PurchaseReceiptService, Depends(get_purchase_receipt_service)] = ...,
) -> PurchaseReceiptResponse:
    """Update a draft purchase receipt."""
    return service.update(receipt_id, payload, user_id=current_user.id)


@router.delete("/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase_receipt(
    receipt_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[PurchaseReceiptService, Depends(get_purchase_receipt_service)] = ...,
) -> None:
    """Delete a draft purchase receipt."""
    service.delete(receipt_id, user_id=current_user.id)


@router.post("/{receipt_id}/confirm", response_model=PurchaseReceiptResponse)
def confirm_purchase_receipt(
    receipt_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[PurchaseReceiptService, Depends(get_purchase_receipt_service)] = ...,
) -> PurchaseReceiptResponse:
    """Confirm receipt and post stock to inventory lots."""
    return service.confirm(receipt_id, user_id=current_user.id)


@router.post("/{receipt_id}/bill-upload-url", response_model=BillUploadUrlResponse)
def create_bill_upload_url(
    receipt_id: uuid.UUID,
    payload: BillUploadUrlRequest,
    service: Annotated[PurchaseReceiptService, Depends(get_purchase_receipt_service)] = ...,
) -> BillUploadUrlResponse:
    """Get a presigned URL to upload a supplier bill."""
    return service.create_bill_upload_url(receipt_id, payload)


@router.get("/{receipt_id}/bill")
def download_purchase_receipt_bill(
    receipt_id: uuid.UUID,
    service: Annotated[PurchaseReceiptService, Depends(get_purchase_receipt_service)] = ...,
) -> Response:
    """Download the supplier bill attachment."""
    body, content_type = service.get_bill_bytes(receipt_id)
    return Response(content=body, media_type=content_type)
