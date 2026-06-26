"""Overhead analytics service — utility & labour bill aggregations."""

from __future__ import annotations

from decimal import Decimal
from typing import NamedTuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.labour_bill_entry import LabourBillEntry
from app.models.labour_charge import LabourCharge
from app.models.order import Order
from app.models.utility_bill_entry import UtilityBillEntry
from app.models.utility_charge import UtilityCharge


def _money(value: Decimal | float | int | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal("0.01"))


class MonthlyOverheadRow(NamedTuple):
    year: int
    month: int
    utility_total: Decimal
    labour_total: Decimal
    overhead_total: Decimal
    gross_profit: Decimal
    operating_profit: Decimal


class CategorySpendRow(NamedTuple):
    name: str
    category: str  # "utility" | "labour"
    total: Decimal
    entry_count: int


class OverheadAnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ─── KPIs ──────────────────────────────────────────────────────────────────

    def get_kpis(self, year: int) -> dict:
        """Aggregate KPIs for a given year."""
        prev_year = year - 1

        utility_this = self._sum_utility(year)
        labour_this = self._sum_labour(year)
        utility_prev = self._sum_utility(prev_year)
        labour_prev = self._sum_labour(prev_year)

        overhead_this = _money(utility_this + labour_this)
        overhead_prev = _money(utility_prev + labour_prev)

        months_with_data = self._months_with_entries(year)
        monthly_avg = _money(overhead_this / months_with_data) if months_with_data > 0 else Decimal("0.00")

        utility_count = self._count_entries(year, "utility")
        labour_count = self._count_entries(year, "labour")

        return {
            "year": year,
            "total_utility": utility_this,
            "total_labour": labour_this,
            "total_overhead": overhead_this,
            "monthly_average": monthly_avg,
            "months_recorded": months_with_data,
            "utility_entry_count": utility_count,
            "labour_entry_count": labour_count,
            "prior_year": prev_year,
            "prior_year_overhead": overhead_prev,
            "yoy_change": _money(overhead_this - overhead_prev),
        }

    # ─── Monthly breakdown ─────────────────────────────────────────────────────

    def get_monthly_breakdown(self, year: int) -> list[dict]:
        """Return month-by-month utility + labour + gross profit + operating profit."""
        utility_by_month = self._utility_by_month(year)
        labour_by_month = self._labour_by_month(year)
        profit_by_month = self._gross_profit_by_month(year)

        rows = []
        for month in range(1, 13):
            u = utility_by_month.get(month, Decimal("0.00"))
            l = labour_by_month.get(month, Decimal("0.00"))
            overhead = _money(u + l)
            gross = profit_by_month.get(month, Decimal("0.00"))
            operating = _money(gross - overhead)
            rows.append({
                "month": month,
                "year": year,
                "utility_total": u,
                "labour_total": l,
                "overhead_total": overhead,
                "gross_profit": gross,
                "operating_profit": operating,
            })
        return rows

    # ─── Category breakdown ────────────────────────────────────────────────────

    def get_category_breakdown(self, year: int) -> list[dict]:
        """Per-charge-type spend for the year, sorted by total descending."""
        rows: list[dict] = []

        # Utility charges
        stmt = (
            select(
                UtilityCharge.name,
                func.count(UtilityBillEntry.id).label("entry_count"),
                func.coalesce(func.sum(UtilityBillEntry.amount), 0).label("total"),
            )
            .join(UtilityBillEntry, UtilityBillEntry.utility_charge_id == UtilityCharge.id, isouter=True)
            .where(
                (UtilityBillEntry.year == year) | (UtilityBillEntry.id.is_(None))
            )
            .group_by(UtilityCharge.id, UtilityCharge.name)
        )
        for name, count, total in self.db.execute(stmt).all():
            rows.append({
                "name": name,
                "category": "utility",
                "total": _money(total),
                "entry_count": count,
            })

        # Labour charges
        stmt = (
            select(
                LabourCharge.name,
                func.count(LabourBillEntry.id).label("entry_count"),
                func.coalesce(func.sum(LabourBillEntry.amount), 0).label("total"),
            )
            .join(LabourBillEntry, LabourBillEntry.labour_charge_id == LabourCharge.id, isouter=True)
            .where(
                (LabourBillEntry.year == year) | (LabourBillEntry.id.is_(None))
            )
            .group_by(LabourCharge.id, LabourCharge.name)
        )
        for name, count, total in self.db.execute(stmt).all():
            rows.append({
                "name": name,
                "category": "labour",
                "total": _money(total),
                "entry_count": count,
            })

        rows.sort(key=lambda r: r["total"], reverse=True)
        return rows

    # ─── Private helpers ────────────────────────────────────────────────────────

    def _sum_utility(self, year: int) -> Decimal:
        result = self.db.scalar(
            select(func.coalesce(func.sum(UtilityBillEntry.amount), 0))
            .where(UtilityBillEntry.year == year)
        )
        return _money(result)

    def _sum_labour(self, year: int) -> Decimal:
        result = self.db.scalar(
            select(func.coalesce(func.sum(LabourBillEntry.amount), 0))
            .where(LabourBillEntry.year == year)
        )
        return _money(result)

    def _utility_by_month(self, year: int) -> dict[int, Decimal]:
        rows = self.db.execute(
            select(UtilityBillEntry.month, func.sum(UtilityBillEntry.amount))
            .where(UtilityBillEntry.year == year)
            .group_by(UtilityBillEntry.month)
        ).all()
        return {month: _money(total) for month, total in rows}

    def _labour_by_month(self, year: int) -> dict[int, Decimal]:
        rows = self.db.execute(
            select(LabourBillEntry.month, func.sum(LabourBillEntry.amount))
            .where(LabourBillEntry.year == year)
            .group_by(LabourBillEntry.month)
        ).all()
        return {month: _money(total) for month, total in rows}

    def _gross_profit_by_month(self, year: int) -> dict[int, Decimal]:
        """Sum total_profit_snapshot from non-cancelled orders, grouped by month."""
        rows = self.db.execute(
            select(
                func.extract("month", Order.scheduled_delivery_date).label("month"),
                func.sum(Order.total_profit_snapshot).label("profit"),
            )
            .where(
                func.extract("year", Order.scheduled_delivery_date) == year,
                Order.status.notin_(["cancelled", "draft"]),
            )
            .group_by(func.extract("month", Order.scheduled_delivery_date))
        ).all()
        return {int(month): _money(profit) for month, profit in rows}

    def _months_with_entries(self, year: int) -> int:
        """Count distinct months that have at least one bill entry."""
        u_months = set(
            self.db.scalars(
                select(UtilityBillEntry.month).where(UtilityBillEntry.year == year).distinct()
            ).all()
        )
        l_months = set(
            self.db.scalars(
                select(LabourBillEntry.month).where(LabourBillEntry.year == year).distinct()
            ).all()
        )
        return len(u_months | l_months)

    def _count_entries(self, year: int, kind: str) -> int:
        if kind == "utility":
            return self.db.scalar(
                select(func.count(UtilityBillEntry.id)).where(UtilityBillEntry.year == year)
            ) or 0
        return self.db.scalar(
            select(func.count(LabourBillEntry.id)).where(LabourBillEntry.year == year)
        ) or 0
