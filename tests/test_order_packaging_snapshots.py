"""Tests for packaging fee revenue and materials cost in order snapshots."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models.order_collection_line import OrderCollectionLine
from app.services.order_profitability_service import OrderProfitabilityService
from app.services.packaging_cost_service import calculate_packaging_materials_cost_per_pack
from app.utils.order_package_fee import package_fee_revenue_from_collection_lines


def test_package_fee_revenue_sums_across_lines_and_quantities():
    lines = [
        OrderCollectionLine(package_fee_snapshot=Decimal("350.00"), quantity=Decimal("1")),
        OrderCollectionLine(package_fee_snapshot=Decimal("350.00"), quantity=Decimal("2")),
        OrderCollectionLine(package_fee_snapshot=Decimal("0.00"), quantity=Decimal("1")),
        OrderCollectionLine(package_fee_snapshot=None, quantity=Decimal("1")),
    ]

    assert package_fee_revenue_from_collection_lines(lines) == Decimal("1050.00")


def test_package_fee_revenue_is_zero_without_fee_lines():
    lines = [
        OrderCollectionLine(package_fee_snapshot=Decimal("0.00"), quantity=Decimal("2")),
        OrderCollectionLine(package_fee_snapshot=None, quantity=Decimal("1")),
    ]

    assert package_fee_revenue_from_collection_lines(lines) == Decimal("0.00")


def test_calculate_packaging_materials_cost_per_pack():
    collection = SimpleNamespace(
        package_fee=Decimal("350"),
        item_lines=[
            SimpleNamespace(
                quantity=Decimal("1"),
                product_item=SimpleNamespace(
                    purchase_price=Decimal("100.00"),
                    purchase_quantity=Decimal("10"),
                ),
            ),
            SimpleNamespace(
                quantity=Decimal("2"),
                product_item=SimpleNamespace(
                    purchase_price=Decimal("50.00"),
                    purchase_quantity=Decimal("5"),
                ),
            ),
        ],
    )

    assert calculate_packaging_materials_cost_per_pack(collection) == Decimal("30.00")


def test_packaging_materials_cost_is_zero_without_package_fee():
    collection = SimpleNamespace(
        package_fee=Decimal("0"),
        item_lines=[
            SimpleNamespace(
                quantity=Decimal("1"),
                product_item=SimpleNamespace(
                    purchase_price=Decimal("120.00"),
                    purchase_quantity=Decimal("1"),
                ),
            ),
        ],
    )

    assert calculate_packaging_materials_cost_per_pack(collection) == Decimal("0.00")


def test_apply_delivery_fee_snapshot_preserves_packaging_cost():
    order = SimpleNamespace(
        products_subtotal_snapshot=Decimal("0.00"),
        collections_subtotal_snapshot=Decimal("810.00"),
        delivery_fee_snapshot=Decimal("350.00"),
        delivery_cost_snapshot=Decimal("350.00"),
        package_fee_revenue_snapshot=Decimal("350.00"),
        packaging_cost_snapshot=Decimal("45.00"),
        total_cost_snapshot=Decimal("797.92"),
        total_revenue_snapshot=Decimal("1160.00"),
        total_profit_snapshot=Decimal("362.08"),
        margin_percentage_snapshot=Decimal("31.21"),
    )

    service = OrderProfitabilityService(MagicMock())
    service.apply_delivery_fee_snapshot(order, Decimal("0.00"), is_pickup=True)

    assert order.packaging_cost_snapshot == Decimal("45.00")
    assert order.total_cost_snapshot == Decimal("447.92")
    assert order.total_profit_snapshot == Decimal("362.08")
