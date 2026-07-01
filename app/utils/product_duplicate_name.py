"""Generate unique names for duplicated products."""

from __future__ import annotations

from collections.abc import Callable

from app.core.exceptions import ConflictError, ValidationError

COPY_PREFIX = "Copy of "
MAX_PRODUCT_NAME_LENGTH = 200
_MAX_SUFFIX_ATTEMPTS = 9_999


def generate_duplicate_product_name(
    source_name: str,
    *,
    name_exists: Callable[[str], bool],
) -> str:
    """Return ``Copy of {source}`` or numbered variants when the name is taken."""
    trimmed = source_name.strip()
    if not trimmed:
        raise ValidationError("Cannot duplicate a product without a name")

    first = _build_copy_name(trimmed, suffix="")
    if not name_exists(first):
        return first

    for number in range(2, _MAX_SUFFIX_ATTEMPTS + 1):
        candidate = _build_copy_name(trimmed, suffix=f" ({number})")
        if not name_exists(candidate):
            return candidate

    raise ConflictError("Unable to generate a unique name for the duplicated product")


def _build_copy_name(source_name: str, *, suffix: str) -> str:
    reserved = len(COPY_PREFIX) + len(suffix)
    if reserved >= MAX_PRODUCT_NAME_LENGTH:
        raise ValidationError("Product name is too long to duplicate")

    max_source_chars = MAX_PRODUCT_NAME_LENGTH - reserved
    truncated_source = source_name[:max_source_chars].rstrip()
    if not truncated_source:
        raise ValidationError("Product name is too long to duplicate")

    return f"{COPY_PREFIX}{truncated_source}{suffix}"
