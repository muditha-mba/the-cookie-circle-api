"""Tests for flexible collection packaging fee helpers."""

from decimal import Decimal
from types import SimpleNamespace

from app.utils.collection_packaging_fee import (
    collection_order_quantity_bounds,
    resolve_collection_packaging_fee,
    resolve_packaging_fee_amount,
    resolve_packaging_fee_from_settings,
)


def test_resolve_packaging_fee_from_settings_per_cookie() -> None:
    assert resolve_packaging_fee_from_settings(
        mode="per_cookie",
        amount=Decimal("8"),
        cookie_count=Decimal("30"),
    ) == Decimal("240.00")


def test_resolve_packaging_fee_from_settings_flat() -> None:
    assert resolve_packaging_fee_from_settings(
        mode="flat",
        amount=Decimal("500"),
        cookie_count=Decimal("30"),
    ) == Decimal("500.00")


def test_resolve_packaging_fee_flat() -> None:
    package = SimpleNamespace(
        packaging_fee_mode="flat",
        packaging_fee_amount=Decimal("350"),
    )
    assert resolve_packaging_fee_amount(package, cookie_count=Decimal("12")) == Decimal(
        "350.00",
    )


def test_resolve_packaging_fee_per_cookie() -> None:
    package = SimpleNamespace(
        packaging_fee_mode="per_cookie",
        packaging_fee_amount=Decimal("10"),
    )
    assert resolve_packaging_fee_amount(package, cookie_count=Decimal("8")) == Decimal(
        "80.00",
    )


def test_collection_falls_back_to_legacy_package_fee() -> None:
    collection = SimpleNamespace(
        package_fee=Decimal("200"),
        package=SimpleNamespace(
            packaging_fee_mode="flat",
            packaging_fee_amount=Decimal("0"),
            min_quantity=4,
            max_quantity=20,
        ),
        package_size=8,
    )
    assert resolve_collection_packaging_fee(
        collection,
        cookie_count=Decimal("8"),
    ) == Decimal("200.00")


def test_quantity_bounds_from_package() -> None:
    collection = SimpleNamespace(
        package_size=8,
        package=SimpleNamespace(min_quantity=4, max_quantity=30),
    )
    assert collection_order_quantity_bounds(collection) == (4, 30)


def test_package_selling_price_includes_type_packaging_fee() -> None:
    from app.services.package_pricing_service import calculate_package_selling_price

    class _Product:
        name = "Cookie"
        yield_quantity = Decimal("1")
        selling_price = Decimal("100.00")

        def __hash__(self) -> int:
            return id(self)

    product = _Product()
    collection = SimpleNamespace(
        package_fee=Decimal("0"),
        package=SimpleNamespace(
            packaging_fee_mode="per_cookie",
            packaging_fee_amount=Decimal("8"),
        ),
    )
    # 4 cookies × 100 + 4 × 8 packaging = 432
    assert calculate_package_selling_price(
        collection,
        {product: Decimal("4")},
    ) == Decimal("432.00")


def test_package_selling_price_falls_back_to_legacy_fee() -> None:
    from app.services.package_pricing_service import calculate_package_selling_price

    class _Product:
        name = "Cookie"
        yield_quantity = Decimal("1")
        selling_price = Decimal("50.00")

        def __hash__(self) -> int:
            return id(self)

    product = _Product()
    collection = SimpleNamespace(
        package_fee=Decimal("200"),
        package=SimpleNamespace(
            packaging_fee_mode="flat",
            packaging_fee_amount=Decimal("0"),
        ),
    )
    assert calculate_package_selling_price(
        collection,
        {product: Decimal("2")},
    ) == Decimal("300.00")
