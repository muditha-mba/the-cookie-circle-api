"""Tests for consumption demand packaging fee rule."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
import uuid

from app.services.consumption_demand_service import ConsumptionDemandService


def test_packaging_demand_skips_lines_without_package_fee():
    service = ConsumptionDemandService(MagicMock())
    collection_id = uuid.uuid4()
    item_id = uuid.uuid4()

    order = SimpleNamespace(
        order_number="ORD-1",
        collection_lines=[
            SimpleNamespace(
                collection_id=collection_id,
                quantity=Decimal("2"),
                package_fee_snapshot=Decimal("0"),
            ),
            SimpleNamespace(
                collection_id=collection_id,
                quantity=Decimal("1"),
                package_fee_snapshot=Decimal("5"),
            ),
        ],
    )

    collection = SimpleNamespace(
        item_lines=[
            SimpleNamespace(
                quantity=Decimal("3"),
                product_item=SimpleNamespace(
                    id=item_id,
                    name="Box",
                    purchase_unit="units",
                    item_type=SimpleNamespace(name="Packaging"),
                ),
            ),
        ],
    )

    service.planning = MagicMock()
    service.planning._load_collections.return_value = {collection_id: collection}

    lines = service._build_packaging_requirements_for_consumption([order])

    assert len(lines) == 1
    assert lines[0].product_item_id == item_id
    assert lines[0].quantity == Decimal("3.0000")


def test_packaging_demand_empty_when_all_lines_have_zero_fee():
    service = ConsumptionDemandService(MagicMock())
    order = SimpleNamespace(
        order_number="ORD-2",
        collection_lines=[
            SimpleNamespace(
                collection_id=uuid.uuid4(),
                quantity=Decimal("2"),
                package_fee_snapshot=Decimal("0"),
            ),
        ],
    )

    lines = service._build_packaging_requirements_for_consumption([order])

    assert lines == []
