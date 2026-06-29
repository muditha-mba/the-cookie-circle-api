"""Tests for purchase receipt confirm stock posting."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

from app.core.enums import PurchaseReceiptStatus
from app.models.inventory_lot import InventoryLot
from app.services.purchase_receipt_service import PurchaseReceiptService


def test_confirm_creates_lot_at_zero_before_receipt_movement():
    """Lot balance must equal receipt quantity, not double it."""
    service = PurchaseReceiptService(MagicMock())
    service.receipts = MagicMock()
    service.items = MagicMock()
    service.movements = MagicMock()
    service.activity = MagicMock()
    service.activity.record.return_value = None

    receipt_id = UUID("08659f91-0000-4000-8000-000000000001")
    line = SimpleNamespace(
        id=UUID("08659f91-0000-4000-8000-000000000002"),
        product_item_id=UUID("08659f91-0000-4000-8000-000000000003"),
        quantity=Decimal("20000"),
        unit="grams",
        expires_at=None,
    )
    receipt = SimpleNamespace(
        id=receipt_id,
        status=PurchaseReceiptStatus.DRAFT,
        lines=[line],
        reference_number="87684446",
    )
    item = SimpleNamespace(id=line.product_item_id, name="Butter", track_inventory=True)

    service.receipts.get_by_id.return_value = receipt
    service.items.get_by_id.return_value = item

    created_lots: list[InventoryLot] = []

    def capture_add(entity):
        if isinstance(entity, InventoryLot):
            created_lots.append(entity)

    service.db.add.side_effect = capture_add
    service.db.flush.return_value = None
    service.db.commit.return_value = None
    service.db.refresh.return_value = None

    def record_receipt_movement(*, lot, quantity, **kwargs):
        lot.quantity_on_hand = (lot.quantity_on_hand + quantity).quantize(Decimal("0.0001"))
        return SimpleNamespace(id="movement-id")

    service.movements.record_receipt_movement.side_effect = record_receipt_movement
    service._to_response = MagicMock(return_value="response")

    service.confirm(receipt_id, user_id=UUID("08659f91-0000-4000-8000-000000000004"))

    assert len(created_lots) == 1
    lot = created_lots[0]
    assert lot.quantity_on_hand == Decimal("20000")
    service.movements.record_receipt_movement.assert_called_once()
