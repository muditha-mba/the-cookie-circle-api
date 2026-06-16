"""Tests for delivery cost in order profitability snapshots."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.delivery_fee_service import is_pickup_delivery_area, resolve_delivery_cost
from app.services.order_profitability_service import OrderProfitabilityService


def test_resolve_delivery_cost_is_zero_for_pickup():
    assert resolve_delivery_cost(Decimal("350.00"), is_pickup=True) == Decimal("0.00")


def test_resolve_delivery_cost_matches_fee_for_delivery():
    assert resolve_delivery_cost(Decimal("350.00"), is_pickup=False) == Decimal("350.00")


def test_is_pickup_delivery_area():
    pickup_area = SimpleNamespace(pickup_only=True)
    delivery_area = SimpleNamespace(pickup_only=False)

    assert is_pickup_delivery_area(pickup_area) is True
    assert is_pickup_delivery_area(delivery_area) is False
    assert is_pickup_delivery_area(None) is False


def test_apply_delivery_fee_snapshot_recalculates_cost_and_profit():
    order = SimpleNamespace(
        products_subtotal_snapshot=Decimal("1000.00"),
        collections_subtotal_snapshot=Decimal("335.00"),
        delivery_fee_snapshot=Decimal("350.00"),
        delivery_cost_snapshot=Decimal("350.00"),
        package_fee_revenue_snapshot=Decimal("0.00"),
        packaging_cost_snapshot=Decimal("0.00"),
        total_cost_snapshot=Decimal("580.50") + Decimal("350.00"),
        total_revenue_snapshot=Decimal("1685.00"),
        total_profit_snapshot=Decimal("754.50"),
        margin_percentage_snapshot=Decimal("44.78"),
    )

    service = OrderProfitabilityService(MagicMock())
    service.apply_delivery_fee_snapshot(order, Decimal("0.00"), is_pickup=True)

    assert order.delivery_fee_snapshot == Decimal("0.00")
    assert order.delivery_cost_snapshot == Decimal("0.00")
    assert order.total_cost_snapshot == Decimal("580.50")
    assert order.total_revenue_snapshot == Decimal("1335.00")
    assert order.total_profit_snapshot == Decimal("754.50")
    assert order.margin_percentage_snapshot == Decimal("56.52")


def test_apply_delivery_fee_snapshot_adds_delivery_cost_for_delivery_area():
    order = SimpleNamespace(
        products_subtotal_snapshot=Decimal("1000.00"),
        collections_subtotal_snapshot=Decimal("335.00"),
        delivery_fee_snapshot=Decimal("0.00"),
        delivery_cost_snapshot=Decimal("0.00"),
        package_fee_revenue_snapshot=Decimal("0.00"),
        packaging_cost_snapshot=Decimal("0.00"),
        total_cost_snapshot=Decimal("580.50"),
        total_revenue_snapshot=Decimal("1335.00"),
        total_profit_snapshot=Decimal("754.50"),
        margin_percentage_snapshot=Decimal("56.52"),
    )

    service = OrderProfitabilityService(MagicMock())
    service.apply_delivery_fee_snapshot(order, Decimal("350.00"), is_pickup=False)

    assert order.delivery_fee_snapshot == Decimal("350.00")
    assert order.delivery_cost_snapshot == Decimal("350.00")
    assert order.total_cost_snapshot == Decimal("930.50")
    assert order.total_revenue_snapshot == Decimal("1685.00")
    assert order.total_profit_snapshot == Decimal("754.50")
    assert order.margin_percentage_snapshot == Decimal("44.78")
