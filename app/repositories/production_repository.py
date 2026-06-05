"""Production planning data access."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order
from app.models.order_collection_line import OrderCollectionLine


class ProductionRepository:
    """Read-only queries for production planning."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_delivery_dates_with_counts(
        self,
        *,
        delivery_weekday: int | None = None,
    ) -> list[tuple[date, int]]:
        """Distinct scheduled delivery dates with order counts, newest first."""
        stmt = (
            select(Order.scheduled_delivery_date, func.count(Order.id))
            .group_by(Order.scheduled_delivery_date)
            .order_by(Order.scheduled_delivery_date.desc())
        )
        if delivery_weekday is not None:
            # PostgreSQL: EXTRACT(DOW FROM date) — Sunday=0; Python Monday=0
            # Use (EXTRACT(DOW) + 6) % 7 for Monday=0 alignment
            dow_expr = func.mod(func.extract("dow", Order.scheduled_delivery_date) + 6, 7)
            stmt = stmt.where(dow_expr == delivery_weekday)

        rows = self.db.execute(stmt).all()
        return [(row[0], int(row[1])) for row in rows]

    def get_orders_for_delivery_date(self, delivery_date: date) -> list[Order]:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.product_lines),
                selectinload(Order.collection_lines).selectinload(
                    OrderCollectionLine.selections,
                ),
            )
            .where(Order.scheduled_delivery_date == delivery_date)
            .order_by(Order.order_number.asc())
        )
        return list(self.db.scalars(stmt).all())
