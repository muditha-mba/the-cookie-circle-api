"""Resolve delivery fee from business settings and delivery area."""

from decimal import Decimal

from app.models.delivery_area import DeliveryArea
from app.schemas.business_settings import BusinessSettingsResponse
from app.services.product_cost_service import _money


def resolve_delivery_fee(
    settings: BusinessSettingsResponse,
    delivery_area: DeliveryArea | None,
) -> Decimal:
    """Use area override when set; pickup-only areas default to zero; else business default."""
    if delivery_area is not None:
        if delivery_area.delivery_fee_override is not None:
            return _money(delivery_area.delivery_fee_override)
        if delivery_area.pickup_only:
            return Decimal("0.00")
    return _money(settings.delivery_fee)
