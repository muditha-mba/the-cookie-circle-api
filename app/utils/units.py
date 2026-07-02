"""Canonical measurement unit helpers (mirrors admin MEASUREMENT_UNITS)."""

DISCRETE_UNIT_VALUES = frozenset(
    {
        "units",
        "pieces",
        "packs",
        "boxes",
        "bags",
        "bottles",
        "cans",
        "trays",
        "servings",
        "dozen",
        "pairs",
        "rolls",
        "sheets",
    }
)


def normalize_unit(value: str) -> str:
    return value.strip().lower()


def is_discrete_unit(value: str) -> bool:
    return normalize_unit(value) in DISCRETE_UNIT_VALUES
