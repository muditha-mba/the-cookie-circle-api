"""Admin role helpers for financial vs operational access."""

from app.core.enums import AdminRole, UserRole
from app.core.exceptions import ForbiddenError
from app.models.user import User


def can_view_financials(user: User) -> bool:
    """Whether the user may view owner-level financial and analytics data."""
    return user.role == UserRole.ADMIN and user.admin_role == AdminRole.SUPER_ADMIN


def assert_financial_access(user: User) -> None:
    if not can_view_financials(user):
        raise ForbiddenError("Super admin access required for financial data")
