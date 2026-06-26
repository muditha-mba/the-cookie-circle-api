"""Customer discount override service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import DiscountAuditEventType, DiscountGrantStatus
from app.models.customer_discount_grant import CustomerDiscountGrant
from app.models.customer_discount_override import CustomerDiscountOverride
from app.schemas.discount import (
    CustomerDiscountOverrideResponse,
    CustomerDiscountOverrideSet,
)
from app.services.discount_audit_service import DiscountAuditService


class CustomerDiscountOverrideService:
    """Manage per-customer discount eligibility overrides."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = DiscountAuditService(db)

    def set_override(
        self,
        customer_id: uuid.UUID,
        payload: CustomerDiscountOverrideSet,
        admin_user_id: uuid.UUID | None = None,
    ) -> CustomerDiscountOverrideResponse:
        now = datetime.now(tz=timezone.utc)

        override = self.db.scalar(
            select(CustomerDiscountOverride).where(
                CustomerDiscountOverride.customer_id == customer_id
            )
        )

        if override is None:
            override = CustomerDiscountOverride(
                id=uuid.uuid4(),
                customer_id=customer_id,
                discounts_enabled=payload.discounts_enabled,
                reason=payload.reason,
                admin_user_id=admin_user_id,
                created_at=now,
                updated_at=now,
            )
            self.db.add(override)
        else:
            override.discounts_enabled = payload.discounts_enabled
            override.reason = payload.reason
            override.admin_user_id = admin_user_id
            override.updated_at = now

        # When disabling, immediately revoke all active grants for this customer
        if not payload.discounts_enabled:
            active_grants = list(
                self.db.scalars(
                    select(CustomerDiscountGrant).where(
                        CustomerDiscountGrant.customer_id == customer_id,
                        CustomerDiscountGrant.status == DiscountGrantStatus.ACTIVE,
                    )
                ).all()
            )
            for grant in active_grants:
                grant.status = DiscountGrantStatus.REVOKED
                grant.revoked_at = now
                grant.revoked_by_user_id = admin_user_id
                grant.revoke_reason = "Override: discounts disabled for customer"
                self.audit.record(
                    DiscountAuditEventType.REVOKED,
                    customer_id=customer_id,
                    grant_id=grant.id,
                    admin_user_id=admin_user_id,
                    payload={"reason": "override_disabled"},
                )

        self.audit.record(
            DiscountAuditEventType.OVERRIDE_SET,
            customer_id=customer_id,
            admin_user_id=admin_user_id,
            payload={
                "discounts_enabled": payload.discounts_enabled,
                "reason": payload.reason,
            },
        )

        self.db.commit()
        self.db.refresh(override)
        return CustomerDiscountOverrideResponse.model_validate(override)

    def get_override(self, customer_id: uuid.UUID) -> CustomerDiscountOverrideResponse | None:
        record = self.db.scalar(
            select(CustomerDiscountOverride).where(
                CustomerDiscountOverride.customer_id == customer_id
            )
        )
        if record is None:
            return None
        return CustomerDiscountOverrideResponse.model_validate(record)

    def delete_override(self, customer_id: uuid.UUID) -> None:
        record = self.db.scalar(
            select(CustomerDiscountOverride).where(
                CustomerDiscountOverride.customer_id == customer_id
            )
        )
        if record:
            self.db.delete(record)
            self.db.commit()
