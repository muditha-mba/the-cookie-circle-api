"""Purchase receipt routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
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
    PurchaseReceiptAttachmentRegister,
    PurchaseReceiptAttachmentResponse,
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


@router.post("/{receipt_id}/attachments/upload-url", response_model=BillUploadUrlResponse)
def create_attachment_upload_url(
    receipt_id: uuid.UUID,
    payload: BillUploadUrlRequest,
    service: Annotated[PurchaseReceiptService, Depends(get_purchase_receipt_service)] = ...,
) -> BillUploadUrlResponse:
    """Get a presigned URL to upload a receipt image or PDF."""
    return service.create_attachment_upload_url(receipt_id, payload)


@router.post(
    "/{receipt_id}/attachments/upload",
    response_model=PurchaseReceiptAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_purchase_receipt_attachment(
    receipt_id: uuid.UUID,
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[PurchaseReceiptService, Depends(get_purchase_receipt_service)] = ...,
) -> PurchaseReceiptAttachmentResponse:
    """Upload a receipt image or PDF through the API."""
    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"
    return service.upload_attachment(
        receipt_id,
        file_bytes=file_bytes,
        content_type=content_type,
        file_name=file.filename,
        user_id=current_user.id,
    )


@router.post(
    "/{receipt_id}/attachments",
    response_model=PurchaseReceiptAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_purchase_receipt_attachment(
    receipt_id: uuid.UUID,
    payload: PurchaseReceiptAttachmentRegister,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[PurchaseReceiptService, Depends(get_purchase_receipt_service)] = ...,
) -> PurchaseReceiptAttachmentResponse:
    """Register an uploaded receipt attachment (allowed on draft and confirmed receipts)."""
    return service.register_attachment(receipt_id, payload, user_id=current_user.id)


@router.delete("/{receipt_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase_receipt_attachment(
    receipt_id: uuid.UUID,
    attachment_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[PurchaseReceiptService, Depends(get_purchase_receipt_service)] = ...,
) -> None:
    """Remove an attachment from a draft receipt."""
    service.delete_attachment(receipt_id, attachment_id, user_id=current_user.id)


@router.get("/{receipt_id}/attachments/{attachment_id}")
def download_purchase_receipt_attachment(
    receipt_id: uuid.UUID,
    attachment_id: uuid.UUID,
    service: Annotated[PurchaseReceiptService, Depends(get_purchase_receipt_service)] = ...,
) -> Response:
    """Download a receipt attachment."""
    body, content_type = service.get_attachment_bytes(receipt_id, attachment_id)
    return Response(content=body, media_type=content_type)


@router.post("/{receipt_id}/bill-upload-url", response_model=BillUploadUrlResponse)
def create_bill_upload_url(
    receipt_id: uuid.UUID,
    payload: BillUploadUrlRequest,
    service: Annotated[PurchaseReceiptService, Depends(get_purchase_receipt_service)] = ...,
) -> BillUploadUrlResponse:
    """Get a presigned URL to upload a supplier bill (legacy alias)."""
    return service.create_bill_upload_url(receipt_id, payload)


@router.get("/{receipt_id}/bill")
def download_purchase_receipt_bill(
    receipt_id: uuid.UUID,
    service: Annotated[PurchaseReceiptService, Depends(get_purchase_receipt_service)] = ...,
) -> Response:
    """Download the supplier bill attachment."""
    body, content_type = service.get_bill_bytes(receipt_id)
    return Response(content=body, media_type=content_type)
