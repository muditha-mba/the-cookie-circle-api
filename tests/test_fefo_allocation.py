"""Tests for FEFO allocation service."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
import uuid

from app.services.fefo_allocation_service import FefoAllocationService


def test_fefo_allocate_uses_lots_in_order_until_quantity_met():
    service = FefoAllocationService(MagicMock())
    item_id = uuid.uuid4()
    lot_a = SimpleNamespace(
        id=uuid.uuid4(),
        lot_code="A",
        quantity_on_hand=Decimal("3"),
        unit="grams",
        expires_at=None,
        is_active=True,
    )
    lot_b = SimpleNamespace(
        id=uuid.uuid4(),
        lot_code="B",
        quantity_on_hand=Decimal("5"),
        unit="grams",
        expires_at=None,
        is_active=True,
    )
    service.lots = MagicMock()
    service.lots.list_fefo_for_item.return_value = [lot_a, lot_b]

    result = service.allocate(product_item_id=item_id, quantity=Decimal("6"), unit="grams")

    assert result.shortfall == Decimal("0")
    assert len(result.allocations) == 2
    assert result.allocations[0].quantity == Decimal("3")
    assert result.allocations[1].quantity == Decimal("3")


def test_fefo_allocate_reports_shortfall():
    service = FefoAllocationService(MagicMock())
    lot = SimpleNamespace(
        id=uuid.uuid4(),
        lot_code="A",
        quantity_on_hand=Decimal("2"),
        unit="grams",
        expires_at=None,
        is_active=True,
    )
    service.lots = MagicMock()
    service.lots.list_fefo_for_item.return_value = [lot]

    result = service.allocate(product_item_id=uuid.uuid4(), quantity=Decimal("5"), unit="grams")

    assert result.shortfall == Decimal("3")
    assert len(result.allocations) == 1
    assert result.allocations[0].quantity == Decimal("2")
