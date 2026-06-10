"""Structured security and admin audit logging."""

import json
import logging
from typing import Any
from uuid import UUID

security_logger = logging.getLogger("security.audit")


def log_security_event(
    event: str,
    *,
    actor_id: UUID | str | None = None,
    actor_role: str | None = None,
    ip_address: str | None = None,
    method: str | None = None,
    path: str | None = None,
    status_code: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Emit a structured security audit log entry."""
    payload = {
        "event": event,
        "actor_id": str(actor_id) if actor_id is not None else None,
        "actor_role": actor_role,
        "ip_address": ip_address,
        "method": method,
        "path": path,
        "status_code": status_code,
        "metadata": metadata or {},
    }
    security_logger.info(json.dumps(payload, default=str))


def log_admin_mutation(
    *,
    actor_id: UUID | str,
    method: str,
    path: str,
    ip_address: str | None,
    status_code: int,
) -> None:
    log_security_event(
        "admin_mutation",
        actor_id=actor_id,
        actor_role="ADMIN",
        ip_address=ip_address,
        method=method,
        path=path,
        status_code=status_code,
    )
