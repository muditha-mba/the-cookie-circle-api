"""Helpers for validating charge applicability on products and collections."""

from app.core.enums import ChargeApplicability
from app.core.exceptions import ValidationError

PRODUCT_APPLICABILITIES = frozenset(
    {ChargeApplicability.PRODUCT, ChargeApplicability.BOTH},
)
COLLECTION_APPLICABILITIES = frozenset(
    {ChargeApplicability.COLLECTION, ChargeApplicability.BOTH},
)


def validate_charges_for_target(
    charges: list,
    *,
    target_label: str,
    allowed: frozenset[ChargeApplicability],
) -> None:
    """Ensure each charge may attach to the given target (product or collection)."""
    for charge in charges:
        if charge.applicability not in allowed:
            raise ValidationError(
                f"Charge '{charge.name}' cannot be attached to a {target_label}",
            )
