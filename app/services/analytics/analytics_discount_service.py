"""Discount analytics — granted, redeemed, revenue impact, rule performance."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import DiscountGrantStatus, DiscountSource
from app.models.customer_discount_grant import CustomerDiscountGrant
from app.models.discount_rule import DiscountRule
from app.models.order import Order
from app.schemas.analytics import AnalyticsQueryParams
from app.utils.analytics_date_range import AnalyticsDateRange, resolve_analytics_date_range

MONEY = Decimal("0.01")


@dataclass(frozen=True)
class DiscountKpiAggregate:
    total_granted: int
    total_used: int
    total_expired: int
    total_revoked: int
    total_discount_amount: Decimal
    avg_discount_amount: Decimal
    orders_with_discount: int


@dataclass(frozen=True)
class DiscountRulePerformanceRow:
    rule_id: str
    rule_name: str
    grants_issued: int
    grants_used: int
    grants_expired: int
    total_discount_given: Decimal


class DiscountAnalyticsService:
    """Aggregate discount KPIs from grants and order snapshots."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_kpis(self, params: AnalyticsQueryParams) -> dict:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        kpi = self._fetch_kpis(date_range)
        return {
            "date_range": {
                "start": date_range.start.isoformat(),
                "end": date_range.end.isoformat(),
            },
            "total_grants_issued": kpi.total_granted,
            "total_grants_used": kpi.total_used,
            "total_grants_expired": kpi.total_expired,
            "total_grants_revoked": kpi.total_revoked,
            "redemption_rate_pct": (
                float(
                    (Decimal(kpi.total_used) / Decimal(kpi.total_granted) * 100).quantize(MONEY)
                )
                if kpi.total_granted > 0
                else 0.0
            ),
            "total_discount_amount": str(kpi.total_discount_amount),
            "avg_discount_per_order": str(kpi.avg_discount_amount),
            "orders_with_discount": kpi.orders_with_discount,
        }

    def get_rule_performance(self) -> list[dict]:
        rows = self._fetch_rule_performance()
        return [
            {
                "rule_id": r.rule_id,
                "rule_name": r.rule_name,
                "grants_issued": r.grants_issued,
                "grants_used": r.grants_used,
                "grants_expired": r.grants_expired,
                "redemption_rate_pct": (
                    float(
                        (Decimal(r.grants_used) / Decimal(r.grants_issued) * 100).quantize(MONEY)
                    )
                    if r.grants_issued > 0
                    else 0.0
                ),
                "total_discount_given": str(r.total_discount_given),
            }
            for r in rows
        ]

    def get_monthly_trends(self) -> list[dict]:
        """Monthly discount totals for the past 12 months."""
        stmt = (
            select(
                func.date_trunc("month", Order.created_at).label("month"),
                func.count(Order.id).label("order_count"),
                func.coalesce(func.sum(Order.discount_amount_snapshot), 0).label("discount_total"),
            )
            .where(
                Order.discount_amount_snapshot > 0,
            )
            .group_by(func.date_trunc("month", Order.created_at))
            .order_by(func.date_trunc("month", Order.created_at))
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "month": row.month.strftime("%Y-%m"),
                "orders_with_discount": int(row.order_count),
                "total_discount_amount": str(Decimal(row.discount_total or 0).quantize(MONEY)),
            }
            for row in rows
        ]

    def _fetch_kpis(self, date_range: AnalyticsDateRange) -> DiscountKpiAggregate:
        grant_stmt = select(
            func.count(CustomerDiscountGrant.id).label("total"),
            func.sum(
                func.cast(
                    CustomerDiscountGrant.status == DiscountGrantStatus.ACTIVE,
                    func.Integer(),
                )
            ).label("active"),
            func.sum(
                func.cast(
                    CustomerDiscountGrant.status == DiscountGrantStatus.USED,
                    func.Integer(),
                )
            ).label("used"),
            func.sum(
                func.cast(
                    CustomerDiscountGrant.status == DiscountGrantStatus.EXPIRED,
                    func.Integer(),
                )
            ).label("expired"),
            func.sum(
                func.cast(
                    CustomerDiscountGrant.status == DiscountGrantStatus.REVOKED,
                    func.Integer(),
                )
            ).label("revoked"),
        ).where(
            CustomerDiscountGrant.earned_at >= date_range.start,
            CustomerDiscountGrant.earned_at <= date_range.end,
        )
        grant_row = self.db.execute(grant_stmt).one()

        order_stmt = select(
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.discount_amount_snapshot), 0).label("discount_sum"),
        ).where(
            Order.discount_amount_snapshot > 0,
            Order.created_at >= date_range.start,
            Order.created_at <= date_range.end,
        )
        order_row = self.db.execute(order_stmt).one()

        total_granted = int(grant_row.total or 0)
        total_used = int(grant_row.used or 0)
        total_expired = int(grant_row.expired or 0)
        total_revoked = int(grant_row.revoked or 0)

        orders_with_discount = int(order_row.order_count or 0)
        discount_sum = Decimal(order_row.discount_sum or 0).quantize(MONEY)
        avg_discount = (
            (discount_sum / orders_with_discount).quantize(MONEY)
            if orders_with_discount > 0
            else Decimal("0.00")
        )

        return DiscountKpiAggregate(
            total_granted=total_granted,
            total_used=total_used,
            total_expired=total_expired,
            total_revoked=total_revoked,
            total_discount_amount=discount_sum,
            avg_discount_amount=avg_discount,
            orders_with_discount=orders_with_discount,
        )

    def _fetch_rule_performance(self) -> list[DiscountRulePerformanceRow]:
        rules = list(self.db.scalars(select(DiscountRule)).all())
        results = []
        for rule in rules:
            stmt = select(
                func.count(CustomerDiscountGrant.id).label("total"),
                func.sum(
                    func.cast(
                        CustomerDiscountGrant.status == DiscountGrantStatus.USED,
                        func.Integer(),
                    )
                ).label("used"),
                func.sum(
                    func.cast(
                        CustomerDiscountGrant.status == DiscountGrantStatus.EXPIRED,
                        func.Integer(),
                    )
                ).label("expired"),
            ).where(CustomerDiscountGrant.discount_rule_id == rule.id)
            row = self.db.execute(stmt).one()

            order_stmt = select(
                func.coalesce(func.sum(Order.discount_amount_snapshot), 0)
            ).where(Order.discount_rule_id_snapshot == rule.id)
            discount_total = Decimal(
                self.db.scalar(order_stmt) or 0
            ).quantize(MONEY)

            results.append(
                DiscountRulePerformanceRow(
                    rule_id=str(rule.id),
                    rule_name=rule.name,
                    grants_issued=int(row.total or 0),
                    grants_used=int(row.used or 0),
                    grants_expired=int(row.expired or 0),
                    total_discount_given=discount_total,
                )
            )
        return results
