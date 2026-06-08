"""Product costing calculations."""

from decimal import Decimal


def calculate_cost_per_unit(
    purchase_price: Decimal,
    purchase_quantity: Decimal,
) -> Decimal:
    """Derive unit cost from purchase price and quantity."""
    if purchase_quantity <= 0:
        raise ValueError("Purchase quantity must be greater than zero")
    return (purchase_price / purchase_quantity).quantize(Decimal("0.0001"))
