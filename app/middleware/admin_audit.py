"""Audit logging for authenticated admin mutations."""

from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.enums import UserRole
from app.core.security import decode_access_token
from app.services.security_audit import log_admin_mutation
from app.utils.client_ip import get_client_ip

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

PUBLIC_PREFIXES = (
    "/health",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/verify-email",
    "/api/v1/auth/resend-verification",
    "/api/v1/client",
)


def _is_auditable_admin_path(path: str) -> bool:
    if not path.startswith("/api/v1/"):
        return False
    return not any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)


def _extract_admin_actor_id(request: Request) -> str | None:
    authorization = request.headers.get("authorization")
    if not authorization or not authorization.lower().startswith("bearer "):
        return None

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except Exception:
        return None

    if payload.get("type") != "access":
        return None
    if payload.get("role") != UserRole.ADMIN.value:
        return None
    return payload.get("sub")


class AdminAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        if request.method.upper() not in MUTATING_METHODS:
            return response
        if not _is_auditable_admin_path(request.url.path):
            return response

        actor_id = _extract_admin_actor_id(request)
        if actor_id is None:
            return response

        log_admin_mutation(
            actor_id=actor_id,
            method=request.method.upper(),
            path=request.url.path,
            ip_address=get_client_ip(request),
            status_code=response.status_code,
        )
        return response


def setup_admin_audit(app) -> None:
    app.add_middleware(AdminAuditMiddleware)
