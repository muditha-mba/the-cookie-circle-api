"""Tests for inventory readiness calculations."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
import uuid
from datetime import date

from app.services.inventory_readiness_service import InventoryReadinessService


def test_readiness_marks_shortfall_when_on_hand_below_need():
    service = InventoryReadinessService(MagicMock())
    item_id = uuid.uuid4()
    demand = SimpleNamespace(
        product_item_id=item_id,
        product_item_name="Flour",
        quantity=Decimal("10"),
        unit="grams",
    )
    item = SimpleNamespace(track_inventory=True)

    service.production = MagicMock()
    service.production.get_ingredient_demand.return_value = [demand]
    service.production.get_packaging_demand.return_value = []
    service.items = MagicMock()
    service.items.get_by_id.return_value = item
    service.balances = MagicMock()
    service.balances.sum_on_hand.return_value = Decimal("4")

    result = service.get_readiness(date(2026, 6, 7))

    assert result.shortfall_count == 1
    assert result.lines[0].quantity_gap == Decimal("6.0000")
    assert result.lines[0].is_short is True


def test_readiness_merges_ingredient_and_packaging_for_same_item():
    service = InventoryReadinessService(MagicMock())
    item_id = uuid.uuid4()
    ingredient = SimpleNamespace(
        product_item_id=item_id,
        product_item_name="Box",
        quantity=Decimal("3"),
        unit="units",
    )
    packaging = SimpleNamespace(
        product_item_id=item_id,
        product_item_name="Box",
        quantity=Decimal("2"),
        unit="units",
    )
    item = SimpleNamespace(track_inventory=True)

    service.production = MagicMock()
    service.production.get_ingredient_demand.return_value = [ingredient]
    service.production.get_packaging_demand.return_value = [packaging]
    service.items = MagicMock()
    service.items.get_by_id.return_value = item
    service.balances = MagicMock()
    service.balances.sum_on_hand.return_value = Decimal("5")

    result = service.get_readiness(date(2026, 6, 7))

    assert len(result.lines) == 1
    assert result.lines[0].quantity_needed == Decimal("5.0000")
    assert result.lines[0].is_short is False
