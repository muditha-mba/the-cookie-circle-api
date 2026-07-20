"""Packaging fee helpers for collection types and catering orders."""

from __future__ import annotations

from decimal import Decimal

from app.core.enums import PackagingFeeMode
from app.models.collection import Collection
from app.models.collection_package import CollectionPackage
from app.services.product_cost_service import _money


def resolve_packaging_fee_from_settings(
    *,
    mode: str,
    amount: Decimal,
    cookie_count: Decimal,
) -> Decimal:
    """Compute packaging fee from mode + amount for a cookie count."""
    fee_amount = amount or Decimal("0")
    if fee_amount <= 0:
        return Decimal("0.00")

    normalized_mode = (mode or PackagingFeeMode.FLAT.value).strip().lower()
    if normalized_mode == PackagingFeeMode.PER_COOKIE.value:
        return _money(fee_amount * cookie_count)
    return _money(fee_amount)


def resolve_packaging_fee_amount(
    package: CollectionPackage,
    *,
    cookie_count: Decimal,
) -> Decimal:
    """Compute packaging fee for a cookie count from package type settings."""
    return resolve_packaging_fee_from_settings(
        mode=package.packaging_fee_mode or PackagingFeeMode.FLAT.value,
        amount=package.packaging_fee_amount or Decimal("0"),
        cookie_count=cookie_count,
    )


def resolve_collection_packaging_fee(
    collection: Collection,
    *,
    cookie_count: Decimal,
) -> Decimal:
    """
    Packaging fee for a collection order line.

    Prefers collection_packages fee settings. Falls back to legacy
    collection.package_fee (flat) when package fee amount is zero.
    """
    package = collection.package
    if package is not None and (package.packaging_fee_amount or Decimal("0")) > 0:
        return resolve_packaging_fee_amount(package, cookie_count=cookie_count)

    fee = collection.package_fee or Decimal("0")
    return _money(fee) if fee > 0 else Decimal("0.00")


def collection_order_quantity_bounds(collection: Collection) -> tuple[int, int]:
    """Return (min_quantity, max_quantity) for cookie selections."""
    package = collection.package
    if package is not None:
        min_qty = int(package.min_quantity or 1)
        max_qty = int(package.max_quantity or collection.package_size)
        if max_qty < min_qty:
            max_qty = min_qty
        return min_qty, max_qty
    size = int(collection.package_size)
    return size, size
