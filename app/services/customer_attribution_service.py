"""Apply first-touch marketing attribution to customer records."""

from __future__ import annotations

from app.models.customer import Customer
from app.schemas.attribution import MarketingAttributionInput
from app.utils.marketing_attribution import resolve_marketing_attribution


class CustomerAttributionService:
    """Persist acquisition source without overwriting existing CRM data."""

    @staticmethod
    def apply_first_touch(
        customer: Customer,
        attribution: MarketingAttributionInput | None,
    ) -> bool:
        """
        Set marketing source on a customer when not already known.

        Returns True when attribution was applied.
        """
        if attribution is None or not attribution.has_signal():
            return False
        if customer.marketing_source is not None:
            return False

        resolved = resolve_marketing_attribution(attribution)
        if resolved.source is None:
            return False

        customer.marketing_source = resolved.source
        customer.marketing_attribution_json = resolved.payload
        return True
