"""Dynamic package pricing from customer cookie selections."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.core.exceptions import ValidationError
from app.models.collection import Collection
from app.models.product import Product
from app.schemas.client_ordering import CollectionCookieSelectionInput
from app.services.product_cost_service import _money, calculate_breakdown_for_product
from app.utils.collection_packaging_fee import resolve_collection_packaging_fee


def unit_selling_price(product: Product) -> Decimal:
    if product.yield_quantity <= 0:
        raise ValidationError(f"Product '{product.name}' has invalid yield quantity.")
    return _money(product.selling_price / product.yield_quantity)


def unit_cost(product: Product) -> Decimal:
    breakdown = calculate_breakdown_for_product(product)
    return _money(breakdown.cost_per_unit)


def calculate_package_selling_price(
    collection: Collection,
    per_pack: dict[Product, Decimal],
) -> Decimal:
    """Cookie subtotal plus packaging fee (collection type fee, with legacy fallback)."""
    cookie_total = _money(
        sum(unit_selling_price(product) * qty for product, qty in per_pack.items()),
    )
    cookie_count = sum(per_pack.values(), Decimal("0"))
    packaging_fee = resolve_collection_packaging_fee(
        collection,
        cookie_count=cookie_count,
    )
    return _money(cookie_total + packaging_fee)


def calculate_package_cost(per_pack: dict[Product, Decimal]) -> Decimal:
    return _money(sum(unit_cost(product) * qty for product, qty in per_pack.items()))


def normalize_per_pack(
    selections: list[CollectionCookieSelectionInput],
    products_by_id: dict[UUID, Product],
) -> dict[Product, Decimal]:
    per_pack: dict[Product, Decimal] = {}
    for selection in selections:
        product = products_by_id[selection.product_id]
        per_pack[product] = per_pack.get(product, Decimal("0")) + selection.quantity
    return per_pack
