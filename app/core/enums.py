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
