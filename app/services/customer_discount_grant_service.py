"""Customer discount grant service — list eligible, history, grant, revoke."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from math import ceil

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.enums import (
    DiscountAuditEventType,
    DiscountGrantStatus,
    DiscountSource,
)
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.customer import Customer
from app.models.customer_discount_grant import CustomerDiscountGrant
from app.schemas.discount import (
    CustomerDiscountGrantManualCreate,
    CustomerDiscountGrantResponse,
    CustomerDiscountGrantRevokeRequest,
    DiscountHistoryItem,
    EligibleCustomerItem,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.discount_audit_service import DiscountAuditService


class CustomerDiscountGrantService:
    """Manage customer discount grants."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = DiscountAuditService(db)

    def list_eligible(
        self,
        params: PaginationParams,
    ) -> PaginatedResponse[EligibleCustomerItem]:
        """List customers with an active grant."""
        stmt = (
            select(CustomerDiscountGrant, Customer)
            .join(Customer, CustomerDiscountGrant.customer_id == Customer.id)
            .where(CustomerDiscountGrant.status == DiscountGrantStatus.ACTIVE)
        )
        count_stmt = (
            select(func.count())
            .select_from(CustomerDiscountGrant)
            .where(CustomerDiscountGrant.status == DiscountGrantStatus.ACTIVE)
        )

        total = int(self.db.scalar(count_stmt) or 0)
        stmt = (
            stmt.order_by(desc(CustomerDiscountGrant.earned_at))
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )
        rows = self.db.execute(stmt).all()
        total_pages = ceil(total / params.page_size) if total > 0 else 0

        items = [
            EligibleCustomerItem(
                customer_id=grant.customer_id,
                customer_name=f"{customer.first_name} {customer.last_name}",
                customer_email=customer.email,
                grant_id=grant.id,
                discount_type=grant.discount_type,
                discount_value=grant.discount_value,
                source=grant.source,
                earned_at=grant.earned_at,
                expires_at=grant.expires_at,
            )
            for grant, customer in rows
        ]
        return PaginatedResponse(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    def list_history(
        self,
        params: PaginationParams,
        customer_id: uuid.UUID | None = None,
    ) -> PaginatedResponse[DiscountHistoryItem]:
        """List all grants (all statuses), optionally filtered by customer."""
        stmt = (
            select(CustomerDiscountGrant, Customer)
            .join(Customer, CustomerDiscountGrant.customer_id == Customer.id)
        )
        count_stmt = select(func.count()).select_from(CustomerDiscountGrant)

        if customer_id is not None:
            stmt = stmt.where(CustomerDiscountGrant.customer_id == customer_id)
            count_stmt = count_stmt.where(CustomerDiscountGrant.customer_id == customer_id)

        total = int(self.db.scalar(count_stmt) or 0)
        stmt = (
            stmt.order_by(desc(CustomerDiscountGrant.earned_at))
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )
        rows = self.db.execute(stmt).all()
        total_pages = ceil(total / params.page_size) if total > 0 else 0

        items = [
            DiscountHistoryItem(
                grant_id=grant.id,
                customer_id=grant.customer_id,
                customer_name=f"{customer.first_name} {customer.last_name}",
                customer_email=customer.email,
                discount_type=grant.discount_type,
                discount_value=grant.discount_value,
                source=grant.source,
                status=grant.status,
                earned_at=grant.earned_at,
                expires_at=grant.expires_at,
                used_at=grant.used_at,
                used_on_order_id=grant.used_on_order_id,
                revoked_at=grant.revoked_at,
                revoke_reason=grant.revoke_reason,
            )
            for grant, customer in rows
        ]
        return PaginatedResponse(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    def manual_grant(
        self,
        customer_id: uuid.UUID,
        payload: CustomerDiscountGrantManualCreate,
        admin_user_id: uuid.UUID | None = None,
    ) -> CustomerDiscountGrantResponse:
        """Manually issue a discount grant — fails if customer already has an active grant."""
        self._ensure_customer_exists(customer_id)

        existing = self.db.scalar(
            select(CustomerDiscountGrant).where(
                CustomerDiscountGrant.customer_id == customer_id,
                CustomerDiscountGrant.status == DiscountGrantStatus.ACTIVE,
            )
        )
        if existing:
            raise ConflictError("Customer already has an active discount grant")

        now = datetime.now(tz=timezone.utc)
        expires_at = (
            now + timedelta(days=payload.grant_expires_days)
            if payload.grant_expires_days
            else None
        )
        grant = CustomerDiscountGrant(
            id=uuid.uuid4(),
            customer_id=customer_id,
            discount_rule_id=None,
            discount_type=payload.discount_type,
            discount_value=payload.discount_value,
            source=DiscountSource.MANUAL,
            status=DiscountGrantStatus.ACTIVE,
            eligibility_reason=payload.eligibility_reason,
            earned_at=now,
            expires_at=expires_at,
        )
        self.db.add(grant)

        self.audit.record(
            DiscountAuditEventType.GRANTED,
            customer_id=customer_id,
            grant_id=grant.id,
            admin_user_id=admin_user_id,
            payload={"source": "manual", "discount_type": payload.discount_type.value},
        )

        self.db.commit()
        self.db.refresh(grant)
        return CustomerDiscountGrantResponse.model_validate(grant)

    def revoke(
        self,
        customer_id: uuid.UUID,
        grant_id: uuid.UUID,
        payload: CustomerDiscountGrantRevokeRequest,
        admin_user_id: uuid.UUID | None = None,
    ) -> CustomerDiscountGrantResponse:
        """Revoke an active grant."""
        self._ensure_customer_exists(customer_id)
        grant = self.db.get(CustomerDiscountGrant, grant_id)

        if not grant or grant.customer_id != customer_id:
            raise NotFoundError("Discount grant not found for this customer")
        if grant.status != DiscountGrantStatus.ACTIVE:
            raise ValidationError(f"Grant is already {grant.status.value}")

        now = datetime.now(tz=timezone.utc)
        grant.status = DiscountGrantStatus.REVOKED
        grant.revoked_at = now
        grant.revoked_by_user_id = admin_user_id
        grant.revoke_reason = payload.reason

        self.audit.record(
            DiscountAuditEventType.REVOKED,
            customer_id=customer_id,
            grant_id=grant_id,
            admin_user_id=admin_user_id,
            payload={"reason": payload.reason},
        )

        self.db.commit()
        self.db.refresh(grant)
        return CustomerDiscountGrantResponse.model_validate(grant)

    def get_customer_grants(
        self, customer_id: uuid.UUID
    ) -> list[CustomerDiscountGrantResponse]:
        """Return all grants for a customer ordered by most recent."""
        grants = list(
            self.db.scalars(
                select(CustomerDiscountGrant)
                .where(CustomerDiscountGrant.customer_id == customer_id)
                .order_by(desc(CustomerDiscountGrant.earned_at))
            ).all()
        )
        return [CustomerDiscountGrantResponse.model_validate(g) for g in grants]

    def _ensure_customer_exists(self, customer_id: uuid.UUID) -> None:
        if not self.db.get(Customer, customer_id):
            raise NotFoundError("Customer not found")
