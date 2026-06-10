"""Permission dependencies for admin role tiers."""

from typing import Annotated

from fastapi import Depends

from app.core.admin_access import assert_financial_access
from app.dependencies.admin import get_current_admin_user
from app.models.user import User


def require_super_admin(
    current_user: Annotated[User, Depends(get_current_admin_user)],
) -> User:
    """Require an authenticated super admin."""
    assert_financial_access(current_user)
    return current_user
