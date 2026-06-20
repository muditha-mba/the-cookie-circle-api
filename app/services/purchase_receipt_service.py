"""Purchase receipt business logic."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import (
    ActivityAction,
    ActivityResourceType,
    PurchaseReceiptStatus,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.models.inventory_lot import InventoryLot
from app.models.purchase_receipt import PurchaseReceipt
from app.models.purchase_receipt_attachment import PurchaseReceiptAttachment
from app.models.purchase_receipt_line import PurchaseReceiptLine
from app.repositories.product_item_repository import ProductItemRepository
from app.repositories.purchase_receipt_repository import PurchaseReceiptRepository
from app.repositories.supplier_repository import SupplierRepository
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.purchase_receipt import (
    BillUploadUrlRequest,
    BillUploadUrlResponse,
    PurchaseReceiptAttachmentRegister,
    PurchaseReceiptAttachmentResponse,
    PurchaseReceiptCreate,
    PurchaseReceiptLineCreate,
    PurchaseReceiptLineResponse,
    PurchaseReceiptResponse,
    PurchaseReceiptSummary,
    PurchaseReceiptUpdate,
)
from app.services.activity_log_service import ActivityLogService
from app.services.inventory_movement_service import InventoryMovementService
from app.services.storage.purchase_receipt_storage_service import (
    PurchaseReceiptStorageService,
    get_purchase_receipt_storage_service,
)

MONEY_PRECISION = Decimal("0.01")
QTY_PRECISION = Decimal("0.0001")
UNIT_COST_PRECISION = Decimal("0.0001")
MAX_ATTACHMENTS_PER_RECEIPT = 10
_IMAGE_EXTENSIONS = frozenset({"jpg", "png", "webp"})


class PurchaseReceiptService:
    """CRUD and confirmation for purchase receipts."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.receipts = PurchaseReceiptRepository(db)
        self.suppliers = SupplierRepository(db)
        self.items = ProductItemRepository(db)
        self.movements = InventoryMovementService(db)
        self.activity = ActivityLogService(db)
        self.storage: PurchaseReceiptStorageService = get_purchase_receipt_storage_service()

    def create(
        self,
        payload: PurchaseReceiptCreate,
        *,
        user_id: uuid.UUID,
    ) -> PurchaseReceiptResponse:
        self._ensure_supplier(payload.supplier_id)
        lines = self._build_lines(payload.lines)
        total_amount = self._sum_line_totals(lines)

        receipt = PurchaseReceipt(
            supplier_id=payload.supplier_id,
            receipt_date=payload.receipt_date,
            reference_number=payload.reference_number,
            notes=payload.notes,
            total_amount=total_amount,
            status=PurchaseReceiptStatus.DRAFT,
            created_by_user_id=user_id,
            lines=lines,
        )
        self.receipts.create(receipt)
        self.db.commit()
        self.db.refresh(receipt)
        self.activity.record(
            action=ActivityAction.CREATED,
            resource_type=ActivityResourceType.PURCHASE_RECEIPT,
            actor_user_id=user_id,
            resource_id=receipt.id,
            resource_label=self._receipt_label(receipt),
            commit=True,
        )
        return self._to_response(self.receipts.get_by_id(receipt.id))

    def get(self, receipt_id: uuid.UUID) -> PurchaseReceiptResponse:
        receipt = self.receipts.get_by_id(receipt_id)
        if not receipt:
            raise NotFoundError("Purchase receipt not found")
        return self._to_response(receipt)

    def list(
        self,
        params: PaginationParams,
        *,
        status: PurchaseReceiptStatus | None = None,
        supplier_id: uuid.UUID | None = None,
    ) -> PaginatedResponse[PurchaseReceiptSummary]:
        rows, total = self.receipts.list_paginated(
            page=params.page,
            page_size=params.page_size,
            search=params.search,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
            status=status,
            supplier_id=supplier_id,
        )
        return PaginatedResponse(
            items=[self._to_summary(row) for row in rows],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=self.receipts.total_pages(total, params.page_size),
        )

    def update(
        self,
        receipt_id: uuid.UUID,
        payload: PurchaseReceiptUpdate,
        *,
        user_id: uuid.UUID,
    ) -> PurchaseReceiptResponse:
        receipt = self.receipts.get_by_id(receipt_id)
        if not receipt:
            raise NotFoundError("Purchase receipt not found")
        if receipt.status != PurchaseReceiptStatus.DRAFT:
            raise ValidationError("Only draft receipts can be edited")

        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields provided to update")

        if payload.supplier_id is not None:
            self._ensure_supplier(payload.supplier_id)
            receipt.supplier_id = payload.supplier_id
        if payload.receipt_date is not None:
            receipt.receipt_date = payload.receipt_date
        if "reference_number" in update_data:
            receipt.reference_number = payload.reference_number
        if "notes" in update_data:
            receipt.notes = payload.notes
        if payload.lines is not None:
            receipt.lines.clear()
            receipt.lines.extend(self._build_lines(payload.lines))
            receipt.total_amount = self._sum_line_totals(receipt.lines)
        if "bill_asset_id" in update_data:
            receipt.bill_asset_id = payload.bill_asset_id
            receipt.bill_content_type = payload.bill_content_type
            receipt.bill_extension = payload.bill_extension

        self.db.add(receipt)
        self.db.commit()
        self.db.refresh(receipt)
        self.activity.record(
            action=ActivityAction.UPDATED,
            resource_type=ActivityResourceType.PURCHASE_RECEIPT,
            actor_user_id=user_id,
            resource_id=receipt.id,
            resource_label=self._receipt_label(receipt),
            commit=True,
        )
        return self._to_response(self.receipts.get_by_id(receipt.id))

    def delete(self, receipt_id: uuid.UUID, *, user_id: uuid.UUID) -> None:
        receipt = self.receipts.get_by_id(receipt_id)
        if not receipt:
            raise NotFoundError("Purchase receipt not found")
        if receipt.status != PurchaseReceiptStatus.DRAFT:
            raise ValidationError("Only draft receipts can be deleted")
        if receipt.bill_asset_id and receipt.bill_extension:
            self.storage.delete_asset(receipt.bill_asset_id, receipt.bill_extension)
        for attachment in receipt.attachments:
            self.storage.delete_asset(attachment.asset_id, attachment.extension)
        label = self._receipt_label(receipt)
        self.receipts.delete(receipt)
        self.db.commit()
        self.activity.record(
            action=ActivityAction.DELETED,
            resource_type=ActivityResourceType.PURCHASE_RECEIPT,
            actor_user_id=user_id,
            resource_id=receipt_id,
            resource_label=label,
            commit=True,
        )

    def confirm(self, receipt_id: uuid.UUID, *, user_id: uuid.UUID) -> PurchaseReceiptResponse:
        receipt = self.receipts.get_by_id(receipt_id)
        if not receipt:
            raise NotFoundError("Purchase receipt not found")
        if receipt.status != PurchaseReceiptStatus.DRAFT:
            raise ValidationError("Receipt is already confirmed")
        if not receipt.lines:
            raise ValidationError("Receipt must have at least one line")

        now = datetime.now(UTC)
        for index, line in enumerate(receipt.lines, start=1):
            item = self.items.get_by_id(line.product_item_id)
            if not item:
                raise NotFoundError(f"Product item not found for line {index}")
            if not item.track_inventory:
                raise ValidationError(
                    f"Enable inventory tracking on '{item.name}' before receiving stock",
                )

            lot_code = f"PR-{receipt.id.hex[:8].upper()}-{index:02d}"
            lot = InventoryLot(
                product_item_id=line.product_item_id,
                lot_code=lot_code,
                quantity_on_hand=Decimal("0"),
                unit=line.unit,
                expires_at=line.expires_at,
                received_at=now,
                purchase_receipt_line_id=line.id,
                is_active=True,
            )
            self.db.add(lot)
            self.db.flush()
            self.movements.record_receipt_movement(
                lot=lot,
                quantity=line.quantity,
                reference_id=receipt.id,
                user_id=user_id,
                notes=f"Receipt {receipt.reference_number or receipt.id}",
            )

        receipt.status = PurchaseReceiptStatus.CONFIRMED
        receipt.confirmed_at = now
        receipt.confirmed_by_user_id = user_id
        self.db.add(receipt)
        self.db.commit()
        self.activity.record(
            action=ActivityAction.UPDATED,
            resource_type=ActivityResourceType.PURCHASE_RECEIPT,
            actor_user_id=user_id,
            resource_id=receipt.id,
            resource_label=f"Confirmed {self._receipt_label(receipt)}",
            commit=True,
        )
        return self._to_response(self.receipts.get_by_id(receipt.id))

    def create_bill_upload_url(
        self,
        receipt_id: uuid.UUID,
        payload: BillUploadUrlRequest,
    ) -> BillUploadUrlResponse:
        """Legacy single-bill upload URL — prefer attachment upload endpoints."""
        return self.create_attachment_upload_url(receipt_id, payload)

    def create_attachment_upload_url(
        self,
        receipt_id: uuid.UUID,
        payload: BillUploadUrlRequest,
    ) -> BillUploadUrlResponse:
        receipt = self._get_receipt(receipt_id)
        if len(receipt.attachments) >= MAX_ATTACHMENTS_PER_RECEIPT:
            raise ValidationError(
                f"A receipt can have at most {MAX_ATTACHMENTS_PER_RECEIPT} attachments.",
            )

        asset_id = uuid.uuid4()
        result = self.storage.create_presigned_upload(
            asset_id=asset_id,
            content_type=payload.content_type,
        )
        return BillUploadUrlResponse(
            asset_id=uuid.UUID(str(result["asset_id"])),
            upload_url=str(result["upload_url"]),
            extension=str(result["extension"]),
            expires_in=int(result["expires_in"]),
        )

    def upload_attachment(
        self,
        receipt_id: uuid.UUID,
        *,
        file_bytes: bytes,
        content_type: str,
        file_name: str | None,
        user_id: uuid.UUID,
    ) -> PurchaseReceiptAttachmentResponse:
        """Upload a receipt file through the API (avoids browser-to-S3 CORS)."""
        receipt = self._get_receipt(receipt_id)
        if len(receipt.attachments) >= MAX_ATTACHMENTS_PER_RECEIPT:
            raise ValidationError(
                f"A receipt can have at most {MAX_ATTACHMENTS_PER_RECEIPT} attachments.",
            )
        if not file_bytes:
            raise ValidationError("Uploaded file is empty.")

        normalized_type = content_type.split(";", 1)[0].strip().lower()
        extension = self.storage.extension_for_content_type(normalized_type)
        asset_id = uuid.uuid4()
        self.storage.upload_object(
            asset_id=asset_id,
            extension=extension,
            body=file_bytes,
            content_type=normalized_type,
        )
        return self.register_attachment(
            receipt_id,
            PurchaseReceiptAttachmentRegister(
                asset_id=asset_id,
                content_type=normalized_type,
                extension=extension,
                file_name=file_name,
            ),
            user_id=user_id,
        )

    def register_attachment(
        self,
        receipt_id: uuid.UUID,
        payload: PurchaseReceiptAttachmentRegister,
        *,
        user_id: uuid.UUID,
    ) -> PurchaseReceiptAttachmentResponse:
        receipt = self._get_receipt(receipt_id)
        if len(receipt.attachments) >= MAX_ATTACHMENTS_PER_RECEIPT:
            raise ValidationError(
                f"A receipt can have at most {MAX_ATTACHMENTS_PER_RECEIPT} attachments.",
            )

        extension = payload.extension.strip().lower().removeprefix(".")
        expected = self.storage.extension_for_content_type(payload.content_type)
        if extension != expected:
            raise ValidationError("Attachment extension does not match content type.")

        attachment = PurchaseReceiptAttachment(
            purchase_receipt_id=receipt.id,
            asset_id=payload.asset_id,
            content_type=payload.content_type.split(";", 1)[0].strip().lower(),
            extension=extension,
            file_name=payload.file_name,
            sort_order=len(receipt.attachments),
        )
        self.db.add(attachment)
        self.db.commit()
        self.db.refresh(attachment)
        self.activity.record(
            action=ActivityAction.UPDATED,
            resource_type=ActivityResourceType.PURCHASE_RECEIPT,
            actor_user_id=user_id,
            resource_id=receipt.id,
            resource_label=f"Attached file to {self._receipt_label(receipt)}",
            commit=True,
        )
        return self._to_attachment_response(attachment)

    def delete_attachment(
        self,
        receipt_id: uuid.UUID,
        attachment_id: uuid.UUID,
        *,
        user_id: uuid.UUID,
    ) -> None:
        receipt = self._get_draft_receipt(receipt_id)
        attachment = next((row for row in receipt.attachments if row.id == attachment_id), None)
        if not attachment:
            raise NotFoundError("Attachment not found")
        self.storage.delete_asset(attachment.asset_id, attachment.extension)
        self.db.delete(attachment)
        self.db.commit()
        self.activity.record(
            action=ActivityAction.UPDATED,
            resource_type=ActivityResourceType.PURCHASE_RECEIPT,
            actor_user_id=user_id,
            resource_id=receipt.id,
            resource_label=f"Removed attachment from {self._receipt_label(receipt)}",
            commit=True,
        )

    def get_attachment_bytes(
        self,
        receipt_id: uuid.UUID,
        attachment_id: uuid.UUID,
    ) -> tuple[bytes, str]:
        receipt = self.receipts.get_by_id(receipt_id)
        if not receipt:
            raise NotFoundError("Purchase receipt not found")
        attachment = next((row for row in receipt.attachments if row.id == attachment_id), None)
        if not attachment:
            raise NotFoundError("Attachment not found")
        return self.storage.get_object_bytes(attachment.asset_id, attachment.extension)

    def get_bill_bytes(self, receipt_id: uuid.UUID) -> tuple[bytes, str]:
        receipt = self.receipts.get_by_id(receipt_id)
        if not receipt:
            raise NotFoundError("Purchase receipt not found")
        if receipt.attachments:
            first = sorted(receipt.attachments, key=lambda row: row.sort_order)[0]
            return self.storage.get_object_bytes(first.asset_id, first.extension)
        if not receipt.bill_asset_id or not receipt.bill_extension:
            raise NotFoundError("No bill attached to this receipt")
        return self.storage.get_object_bytes(receipt.bill_asset_id, receipt.bill_extension)

    def _get_receipt(self, receipt_id: uuid.UUID) -> PurchaseReceipt:
        receipt = self.receipts.get_by_id(receipt_id)
        if not receipt:
            raise NotFoundError("Purchase receipt not found")
        return receipt

    def _get_draft_receipt(self, receipt_id: uuid.UUID) -> PurchaseReceipt:
        receipt = self._get_receipt(receipt_id)
        if receipt.status != PurchaseReceiptStatus.DRAFT:
            raise ValidationError("Only draft receipts can be changed")
        return receipt

    @staticmethod
    def _attachment_is_image(attachment: PurchaseReceiptAttachment) -> bool:
        if attachment.extension in _IMAGE_EXTENSIONS:
            return True
        return attachment.content_type.startswith("image/")

    def _to_attachment_response(
        self,
        attachment: PurchaseReceiptAttachment,
    ) -> PurchaseReceiptAttachmentResponse:
        return PurchaseReceiptAttachmentResponse(
            id=attachment.id,
            asset_id=attachment.asset_id,
            content_type=attachment.content_type,
            extension=attachment.extension,
            file_name=attachment.file_name,
            sort_order=attachment.sort_order,
            is_image=self._attachment_is_image(attachment),
            created_at=attachment.created_at,
        )

    def _build_lines(self, lines: list[PurchaseReceiptLineCreate]) -> list[PurchaseReceiptLine]:
        built: list[PurchaseReceiptLine] = []
        for line in lines:
            item = self.items.get_by_id(line.product_item_id)
            if not item:
                raise NotFoundError("Product item not found")
            line_total = line.line_total.quantize(MONEY_PRECISION)
            unit_cost = (line_total / line.quantity).quantize(UNIT_COST_PRECISION)
            built.append(
                PurchaseReceiptLine(
                    product_item_id=line.product_item_id,
                    quantity=line.quantity.quantize(QTY_PRECISION),
                    unit=line.unit,
                    unit_cost=unit_cost,
                    line_total=line_total,
                    expires_at=line.expires_at,
                ),
            )
        return built

    @staticmethod
    def _sum_line_totals(lines: list[PurchaseReceiptLine]) -> Decimal:
        return sum((line.line_total for line in lines), Decimal("0")).quantize(MONEY_PRECISION)

    def _ensure_supplier(self, supplier_id: uuid.UUID) -> None:
        if not self.suppliers.get_by_id(supplier_id):
            raise NotFoundError("Supplier not found")

    @staticmethod
    def _receipt_label(receipt: PurchaseReceipt) -> str:
        if receipt.reference_number:
            return f"Receipt {receipt.reference_number}"
        return f"Receipt {receipt.receipt_date.isoformat()}"

    def _to_summary(self, receipt: PurchaseReceipt) -> PurchaseReceiptSummary:
        from app.schemas.supplier import SupplierSummary

        return PurchaseReceiptSummary(
            id=receipt.id,
            supplier=SupplierSummary.model_validate(receipt.supplier),
            receipt_date=receipt.receipt_date,
            reference_number=receipt.reference_number,
            total_amount=receipt.total_amount,
            status=receipt.status,
            has_bill=bool(receipt.attachments) or bool(receipt.bill_asset_id),
            created_at=receipt.created_at,
            updated_at=receipt.updated_at,
        )

    def _to_response(self, receipt: PurchaseReceipt | None) -> PurchaseReceiptResponse:
        if receipt is None:
            raise NotFoundError("Purchase receipt not found")
        summary = self._to_summary(receipt)
        lines = [
            PurchaseReceiptLineResponse(
                id=line.id,
                product_item_id=line.product_item_id,
                product_item_name=line.product_item.name,
                quantity=line.quantity,
                unit=line.unit,
                unit_cost=line.unit_cost,
                line_total=line.line_total,
                expires_at=line.expires_at,
                created_at=line.created_at,
                updated_at=line.updated_at,
            )
            for line in receipt.lines
        ]
        return PurchaseReceiptResponse(
            **summary.model_dump(),
            notes=receipt.notes,
            bill_asset_id=receipt.bill_asset_id,
            bill_content_type=receipt.bill_content_type,
            bill_extension=receipt.bill_extension,
            attachments=[
                self._to_attachment_response(attachment)
                for attachment in sorted(receipt.attachments, key=lambda row: row.sort_order)
            ],
            lines=lines,
            confirmed_at=receipt.confirmed_at,
            created_by_user_id=receipt.created_by_user_id,
            confirmed_by_user_id=receipt.confirmed_by_user_id,
        )
