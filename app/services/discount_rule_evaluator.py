"""Rules engine — evaluate discount rules after order placement."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import (
    DiscountAuditEventType,
    DiscountGrantStatus,
    DiscountRuleType,
    DiscountSource,
    DiscountType,
    OrderStatus,
)
from app.models.customer_discount_grant import CustomerDiscountGrant
from app.models.customer_discount_override import CustomerDiscountOverride
from app.models.discount_rule import DiscountRule
from app.models.order import Order
from app.services.business_setting_service import BusinessSettingService
from app.services.discount_audit_service import DiscountAuditService

import logging

logger = logging.getLogger(__name__)

ORDER_STATUSES_COUNTING_TOWARD_DISCOUNT_RULES = frozenset({
    OrderStatus.CONFIRMED,
    OrderStatus.PREPARING,
    OrderStatus.READY,
    OrderStatus.DELIVERED,
})


class DiscountRuleEvaluator:
    """
    Evaluate active discount rules after an order is placed.
    Grants are issued for the NEXT order, never the current one.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = DiscountAuditService(db)

    def evaluate_after_order_placed(
        self,
        customer_id: uuid.UUID,
        order_id: uuid.UUID,
    ) -> None:
        """
        Run all active rules for this customer. Call after order commit.
        Any grant issued is for their next order.
        """
        settings = BusinessSettingService(self.db).get_settings()
        if not settings.discounts_enabled:
            return

        override = self.db.scalar(
            select(CustomerDiscountOverride).where(
                CustomerDiscountOverride.customer_id == customer_id
            )
        )
        if override is not None and not override.discounts_enabled:
            return

        existing_active = self.db.scalar(
            select(CustomerDiscountGrant).where(
                CustomerDiscountGrant.customer_id == customer_id,
                CustomerDiscountGrant.status == DiscountGrantStatus.ACTIVE,
            )
        )
        if existing_active is not None:
            return

        rules = list(
            self.db.scalars(
                select(DiscountRule)
                .where(DiscountRule.is_active == True)  # noqa: E712
                .order_by(DiscountRule.priority.asc())
            ).all()
        )

        for rule in rules:
            grant = self._evaluate_rule(rule, customer_id, order_id)
            if grant is not None:
                self.db.add(grant)
                self.audit.record(
                    DiscountAuditEventType.GRANTED,
                    customer_id=customer_id,
                    grant_id=grant.id,
                    rule_id=rule.id,
                    order_id=order_id,
                    payload={
                        "source": "rule",
                        "rule_type": rule.rule_type.value,
                        "discount_type": grant.discount_type.value,
                        "discount_value": str(grant.discount_value),
                    },
                )
                self.audit.record(
                    DiscountAuditEventType.RULE_EVALUATED,
                    customer_id=customer_id,
                    rule_id=rule.id,
                    order_id=order_id,
                    payload={"matched": True, "rule_name": rule.name},
                )
                self.db.flush()
                return

        self.audit.record(
            DiscountAuditEventType.RULE_EVALUATED,
            customer_id=customer_id,
            order_id=order_id,
            payload={"matched": False, "evaluated_rules": len(rules)},
        )

    def _evaluate_rule(
        self,
        rule: DiscountRule,
        customer_id: uuid.UUID,
        order_id: uuid.UUID,
    ) -> CustomerDiscountGrant | None:
        if rule.rule_type == DiscountRuleType.ORDER_FREQUENCY_IN_WINDOW:
            return self._eval_order_frequency(rule, customer_id)
        return None

    def _eval_order_frequency(
        self,
        rule: DiscountRule,
        customer_id: uuid.UUID,
    ) -> CustomerDiscountGrant | None:
        config = rule.config
        required_count: int = int(config["required_order_count"])
        window_days: int = int(config["window_days"])
        discount_type_str: str = str(config["discount_type"])
        import decimal
        discount_value = decimal.Decimal(str(config["discount_value"]))
        grant_expires_days: int | None = (
            int(config["grant_expires_days"])
            if config.get("grant_expires_days") is not None
            else None
        )

        since = datetime.now(tz=timezone.utc) - timedelta(days=window_days)
        order_count = self.db.scalar(
            select(func.count(Order.id)).where(
                Order.customer_id == customer_id,
                Order.status.in_(ORDER_STATUSES_COUNTING_TOWARD_DISCOUNT_RULES),
                Order.created_at >= since,
            )
        ) or 0

        if order_count < required_count:
            return None

        now = datetime.now(tz=timezone.utc)
        expires_at = (
            now + timedelta(days=grant_expires_days) if grant_expires_days else None
        )

        return CustomerDiscountGrant(
            id=uuid.uuid4(),
            customer_id=customer_id,
            discount_rule_id=rule.id,
            discount_type=DiscountType(discount_type_str),
            discount_value=discount_value,
            source=DiscountSource.RULE,
            status=DiscountGrantStatus.ACTIVE,
            eligibility_reason=f"Matched rule: {rule.name}",
            earned_at=now,
            expires_at=expires_at,
        )
