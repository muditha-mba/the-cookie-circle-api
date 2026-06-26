"""Server-side discount resolution — never trust client-sent amounts."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import DiscountGrantStatus
from app.models.customer_discount_grant import CustomerDiscountGrant
from app.models.customer_discount_override import CustomerDiscountOverride
from app.services.business_setting_service import BusinessSettingService
from app.core.business_settings_keys import DISCOUNTS_ENABLED


class DiscountApplicationService:
    """
    Resolve the active discount grant for a customer at checkout time.
    All resolution is server-side; the client never sends discount amounts.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def resolve_grant_for_customer(
        self, customer_id: uuid.UUID
    ) -> CustomerDiscountGrant | None:
        """
        Return the current active, non-expired grant for this customer,
        or None if:
        - global discounts_enabled toggle is OFF
        - customer has a disable override
        - no active grant exists
        - the grant has expired (lazy expiry applied here)
        """
        settings_svc = BusinessSettingService(self.db)
        settings = settings_svc.get_settings()
        if not settings.discounts_enabled:
            return None

        override = self.db.scalar(
            select(CustomerDiscountOverride).where(
                CustomerDiscountOverride.customer_id == customer_id
            )
        )
        if override is not None and not override.discounts_enabled:
            return None

        grant = self.db.scalar(
            select(CustomerDiscountGrant)
            .where(
                CustomerDiscountGrant.customer_id == customer_id,
                CustomerDiscountGrant.status == DiscountGrantStatus.ACTIVE,
            )
            .with_for_update(skip_locked=True)
        )
        if grant is None:
            return None

        now = datetime.now(tz=timezone.utc)
        if grant.expires_at is not None and grant.expires_at < now:
            grant.status = DiscountGrantStatus.EXPIRED
            self.db.flush()
            return None

        return grant

    def mark_grant_used(
        self,
        grant: CustomerDiscountGrant,
        order_id: uuid.UUID,
    ) -> None:
        """Mark a grant as used — call within the same transaction as order creation."""
        now = datetime.now(tz=timezone.utc)
        grant.status = DiscountGrantStatus.USED
        grant.used_at = now
        grant.used_on_order_id = order_id
