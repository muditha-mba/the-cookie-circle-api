"""Admin activity log data access."""

import uuid
from datetime import datetime
from math import ceil

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.enums import ActivityAction, ActivityResourceType
from app.models.admin_activity_log import AdminActivityLog
from app.utils.search import ilike_contains


class ActivityLogRepository:
    """Repository for admin activity log persistence and queries."""

    SORTABLE_COLUMNS = {
        "created_at": AdminActivityLog.created_at,
        "action": AdminActivityLog.action,
        "resource_type": AdminActivityLog.resource_type,
        "actor_email": AdminActivityLog.actor_email,
        "status_code": AdminActivityLog.status_code,
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, log_entry: AdminActivityLog) -> AdminActivityLog:
        self.db.add(log_entry)
        self.db.flush()
        return log_entry

    def get_by_id(self, log_id: uuid.UUID) -> AdminActivityLog | None:
        return self.db.get(AdminActivityLog, log_id)

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_order: str,
        action: ActivityAction | None,
        resource_type: ActivityResourceType | None,
        actor_user_id: uuid.UUID | None,
        success: bool | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> tuple[list[AdminActivityLog], int]:
        stmt = select(AdminActivityLog)
        count_stmt = select(func.count()).select_from(AdminActivityLog)

        filters = []
        if search:
            pattern, escape = ilike_contains(search)
            filters.append(
                or_(
                    AdminActivityLog.actor_email.ilike(pattern, escape=escape),
                    AdminActivityLog.resource_label.ilike(pattern, escape=escape),
                    AdminActivityLog.path.ilike(pattern, escape=escape),
                    AdminActivityLog.browser_name.ilike(pattern, escape=escape),
                    AdminActivityLog.os_name.ilike(pattern, escape=escape),
                    AdminActivityLog.ip_address.ilike(pattern, escape=escape),
                ),
            )
        if action is not None:
            filters.append(AdminActivityLog.action == action)
        if resource_type is not None:
            filters.append(AdminActivityLog.resource_type == resource_type)
        if actor_user_id is not None:
            filters.append(AdminActivityLog.actor_user_id == actor_user_id)
        if success is not None:
            filters.append(AdminActivityLog.success == success)
        if created_from is not None:
            filters.append(AdminActivityLog.created_at >= created_from)
        if created_to is not None:
            filters.append(AdminActivityLog.created_at <= created_to)

        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)

        total = int(self.db.scalar(count_stmt) or 0)
        sort_column = self.SORTABLE_COLUMNS.get(sort_by, AdminActivityLog.created_at)
        ordering = asc(sort_column) if sort_order == "asc" else desc(sort_column)

        rows = self.db.scalars(
            stmt.order_by(ordering).offset((page - 1) * page_size).limit(page_size),
        ).all()
        return list(rows), total
