"""Application enums."""

import enum


class UserRole(str, enum.Enum):
    """Supported user roles."""

    ADMIN = "ADMIN"
    CUSTOMER = "CUSTOMER"


class AppContext(str, enum.Enum):
    """Application context for login role enforcement."""

    ADMIN = "admin"
    CLIENT = "client"


class ChargeType(str, enum.Enum):
    """Global charge calculation type."""

    FIXED = "fixed"
    PERCENTAGE = "percentage"
