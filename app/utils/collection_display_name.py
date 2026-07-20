"""Display titles for collection size SKUs and collection types."""

_SIZE_NAME_TO_DISPLAY: dict[str, str] = {
    "the little circle": "Chocolate Chip Cookie Collection",
    "the family circle": "Chocolate Chip Cookie Collection",
    "the party circle": "Chocolate Chip Cookie Collection",
    "the tea circle": "The Butter Cookie Collection",
    "the warm circle": "The Butter Cookie Collection",
    "the gathering circle": "The Butter Cookie Collection",
}

_PACKAGE_CODE_TO_COLLECTION_DISPLAY: dict[str, str] = {
    "MIX_AND_MATCH": "Chocolate Chip Cookie Collection",
    "BUTTER_COLLECTION": "The Butter Cookie Collection",
}

_PACKAGE_CODE_TO_TYPE_DISPLAY: dict[str, str] = {
    "MIX_AND_MATCH": "Favourite Cookies",
    "BUTTER_COLLECTION": "Tea Time Cookies",
}

_PACKAGE_NAME_TO_TYPE_DISPLAY: dict[str, str] = {
    "mix and match": "Favourite Cookies",
    "butter collection": "Tea Time Cookies",
    "special edition": "Special Edition",
}


def format_collection_display_name(
    name: str,
    *,
    package_code: str | None = None,
) -> str:
    """Map internal size SKU names to customer-facing collection titles."""
    code = (package_code or "").strip().upper()
    if code in _PACKAGE_CODE_TO_COLLECTION_DISPLAY:
        return _PACKAGE_CODE_TO_COLLECTION_DISPLAY[code]

    mapped = _SIZE_NAME_TO_DISPLAY.get(name.strip().lower())
    if mapped:
        return mapped

    return name


def format_package_type_display_name(
    name: str,
    *,
    package_code: str | None = None,
) -> str:
    """Map collection type (collection_packages) names for analytics and ops UI."""
    code = (package_code or "").strip().upper()
    if code in _PACKAGE_CODE_TO_TYPE_DISPLAY:
        return _PACKAGE_CODE_TO_TYPE_DISPLAY[code]

    mapped = _PACKAGE_NAME_TO_TYPE_DISPLAY.get(name.strip().lower())
    if mapped:
        return mapped

    return name
