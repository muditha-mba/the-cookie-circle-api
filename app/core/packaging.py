"""Packaging product item type rules for collection item lines."""

PACKAGING_ITEM_TYPE_NAME = "Packaging"


def is_packaging_item_type(type_name: str) -> bool:
    """Return True when the item type is the Packaging category."""
    return type_name.strip().lower() == PACKAGING_ITEM_TYPE_NAME.lower()
