"""Admin activity log business logic."""

from __future__ import annotations

import logging
import uuid
from math import ceil
from typing import Any

from sqlalchemy.orm import Session

from app.core.enums import ActivityAction, ActivityResourceType, ClientDeviceType
from app.core.exceptions import NotFoundError
from app.database.session import SessionLocal
from app.models.admin_activity_log import AdminActivityLog
from app.models.user import User
from app.repositories.activity_log_repository import ActivityLogRepository
from app.repositories.user_repository import UserRepository
from app.schemas.activity_log import (
    ActivityLogDetailResponse,
    ActivityLogListParams,
    ActivityLogSummaryResponse,
)
from app.schemas.pagination import PaginatedResponse
from app.services.security_audit import log_security_event
from app.utils.activity_path import parse_activity_path
from app.utils.client_context import ClientContext

logger = logging.getLogger(__name__)


class ActivityLogService:
    """Record and query admin activity logs."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.logs = ActivityLogRepository(db)
        self.users = UserRepository(db)

    def list(self, params: ActivityLogListParams) -> PaginatedResponse[ActivityLogSummaryResponse]:
        rows, total = self.logs.list_paginated(
            page=params.page,
            page_size=params.page_size,
            search=params.search,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
            action=params.action,
            resource_type=params.resource_type,
            actor_user_id=params.actor_user_id,
            success=params.success,
            created_from=params.created_from,
            created_to=params.created_to,
        )
        return PaginatedResponse(
            items=[ActivityLogSummaryResponse.model_validate(row) for row in rows],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=max(1, ceil(total / params.page_size)) if total else 0,
        )

    def get(self, log_id: uuid.UUID) -> ActivityLogDetailResponse:
        row = self.logs.get_by_id(log_id)
        if row is None:
            raise NotFoundError("Activity log entry not found")
        return ActivityLogDetailResponse.model_validate(row)

    def record(
        self,
        *,
        action: ActivityAction,
        resource_type: ActivityResourceType,
        actor_user_id: uuid.UUID | str | None = None,
        actor_email: str | None = None,
        actor_admin_role: str | None = None,
        resource_id: uuid.UUID | None = None,
        resource_label: str | None = None,
        http_method: str | None = None,
        path: str | None = None,
        client: ClientContext | None = None,
        status_code: int | None = None,
        success: bool | None = None,
        metadata: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> AdminActivityLog:
        resolved_actor_id = None
        if actor_user_id is not None:
            resolved_actor_id = (
                actor_user_id if isinstance(actor_user_id, uuid.UUID) else uuid.UUID(str(actor_user_id))
            )

        if resolved_actor_id is not None and (actor_email is None or actor_admin_role is None):
            user = self.users.get_by_id(resolved_actor_id)
            if user is not None:
                actor_email = actor_email or user.email
                if actor_admin_role is None and user.admin_role is not None:
                    actor_admin_role = user.admin_role.value

        entry = AdminActivityLog(
            actor_user_id=resolved_actor_id,
            actor_email=actor_email,
            actor_admin_role=actor_admin_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_label=resource_label,
            http_method=http_method,
            path=path,
            ip_address=client.ip_address if client else None,
            user_agent=client.user_agent if client else None,
            browser_name=client.browser_name if client else None,
            browser_version=client.browser_version if client else None,
            os_name=client.os_name if client else None,
            os_version=client.os_version if client else None,
            device_type=client.device_type if client else ClientDeviceType.UNKNOWN,
            status_code=status_code,
            success=success if success is not None else (status_code is None or status_code < 400),
            metadata_json=metadata,
        )
        created = self.logs.create(entry)
        if commit:
            self.db.commit()
        return created


def record_admin_activity(
    *,
    action: ActivityAction,
    resource_type: ActivityResourceType,
    actor_user_id: uuid.UUID | str | None = None,
    actor_email: str | None = None,
    actor_admin_role: str | None = None,
    resource_id: uuid.UUID | None = None,
    resource_label: str | None = None,
    http_method: str | None = None,
    path: str | None = None,
    client: ClientContext | None = None,
    status_code: int | None = None,
    success: bool | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Persist an activity log in an isolated session — failures never break requests."""
    db = SessionLocal()
    try:
        ActivityLogService(db).record(
            action=action,
            resource_type=resource_type,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            actor_admin_role=actor_admin_role,
            resource_id=resource_id,
            resource_label=resource_label,
            http_method=http_method,
            path=path,
            client=client,
            status_code=status_code,
            success=success,
            metadata=metadata,
            commit=True,
        )
        log_security_event(
            "admin_activity_recorded",
            actor_id=actor_user_id,
            method=http_method,
            path=path,
            status_code=status_code,
            metadata={
                "action": action.value,
                "resource_type": resource_type.value,
                "resource_label": resource_label,
            },
        )
    except Exception:
        logger.exception("Failed to persist admin activity log for %s %s", http_method, path)
        db.rollback()
    finally:
        db.close()


def record_admin_http_activity(
    *,
    actor_user_id: uuid.UUID | str,
    method: str,
    path: str,
    client: ClientContext,
    status_code: int,
) -> None:
    """Record a structured log entry from middleware for an admin HTTP request."""
    if path.startswith("/api/v1/activity-logs"):
        return

    parsed = parse_activity_path(method, path)
    record_admin_activity(
        action=parsed.action,
        resource_type=parsed.resource_type,
        actor_user_id=actor_user_id,
        resource_id=parsed.resource_id,
        resource_label=parsed.resource_label,
        http_method=method.upper(),
        path=path,
        client=client,
        status_code=status_code,
        success=status_code < 400,
    )


def record_admin_auth_activity(
    *,
    action: ActivityAction,
    user: User | None,
    email: str | None,
    client: ClientContext,
    status_code: int = 200,
    success: bool = True,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Record authentication-related admin activity."""
    label = "Admin login"
    if action == ActivityAction.LOGIN_FAILED:
        label = "Failed admin login"
    elif action == ActivityAction.LOGOUT:
        label = "Admin logout"
    elif action == ActivityAction.LOGOUT_ALL:
        label = "Admin logout all sessions"

    record_admin_activity(
        action=action,
        resource_type=ActivityResourceType.AUTH,
        actor_user_id=user.id if user else None,
        actor_email=user.email if user else email,
        actor_admin_role=user.admin_role.value if user and user.admin_role else None,
        resource_label=label,
        http_method="POST",
        path="/api/v1/auth/login" if action in {ActivityAction.LOGIN, ActivityAction.LOGIN_FAILED} else "/api/v1/auth/logout",
        client=client,
        status_code=status_code,
        success=success,
        metadata=metadata,
    )
