"""Security-related FastAPI dependencies."""

from fastapi import Request

from app.core.config import settings
from app.core.exceptions import ForbiddenError
from app.utils.client_ip import get_client_ip


def enforce_admin_ip_allowlist(request: Request) -> None:
    """Restrict admin API access to configured IP ranges when enabled."""
    allowed = settings.admin_allowed_ip_list
    if not allowed:
        return

    client_ip = get_client_ip(request)
    if client_ip not in allowed:
        raise ForbiddenError("Admin access is not permitted from this network")
