"""Discount audit event service — write and query audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from math import ceil
from typing import Any

from sqlalchemy import desc, select, func
from sqlalchemy.orm import Session

from app.core.enums import DiscountAuditEventType
from app.models.discount_audit_event import DiscountAuditEvent
from app.schemas.discount import DiscountAuditEventResponse
from app.schemas.pagination import PaginatedResponse, PaginationParams


class DiscountAuditService:
    """Write and read discount lifecycle audit events."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        event_type: DiscountAuditEventType,
        *,
        customer_id: uuid.UUID | None = None,
        grant_id: uuid.UUID | None = None,
        rule_id: uuid.UUID | None = None,
        order_id: uuid.UUID | None = None,
        admin_user_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Append a new audit event (fire-and-forget — caller must commit)."""
        now = datetime.now(tz=timezone.utc)
        event = DiscountAuditEvent(
            id=uuid.uuid4(),
            event_type=event_type,
            customer_id=customer_id,
            customer_discount_grant_id=grant_id,
            discount_rule_id=rule_id,
            order_id=order_id,
            admin_user_id=admin_user_id,
            payload=payload or {},
            created_at=now,
        )
        self.db.add(event)

    def list(
        self,
        params: PaginationParams,
        customer_id: uuid.UUID | None = None,
    ) -> PaginatedResponse[DiscountAuditEventResponse]:
        stmt = select(DiscountAuditEvent)
        count_stmt = select(func.count()).select_from(DiscountAuditEvent)

        if customer_id is not None:
            stmt = stmt.where(DiscountAuditEvent.customer_id == customer_id)
            count_stmt = count_stmt.where(DiscountAuditEvent.customer_id == customer_id)

        total = int(self.db.scalar(count_stmt) or 0)
        stmt = (
            stmt.order_by(desc(DiscountAuditEvent.created_at))
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )
        items = list(self.db.scalars(stmt).all())
        total_pages = ceil(total / params.page_size) if total > 0 else 0
        return PaginatedResponse(
            items=[DiscountAuditEventResponse.model_validate(e) for e in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )
