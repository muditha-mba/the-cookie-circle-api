"""Analytics aggregation queries (snapshot-based)."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import (
    CustomerSegment,
    MarketingSource,
    OrderSource,
    OrderStatus,
    OrderType,
    PaymentStatus,
)
from app.models.customer import Customer
from app.models.collection import Collection
from app.models.collection_package import CollectionPackage
from app.models.delivery_area import DeliveryArea
from app.models.order import Order
from app.models.order_collection_line import OrderCollectionLine
from app.models.order_product_line import OrderProductLine
from app.repositories.customer_insights_repository import CustomerInsightsRepository
from app.services.customer_segmentation import (
    CustomerSegmentationConfig,
    calculate_customer_segment,
)
from app.utils.analytics_date_range import AnalyticsDateRange, TrendGranularity

MONEY = Decimal("0.01")
QTY = Decimal("0.0001")

ANALYTICS_EXCLUDED = [OrderStatus.DRAFT.value, OrderStatus.CANCELLED.value]
ORDER_ANALYTICS_EXCLUDED = [OrderStatus.DRAFT.value]

HIGH_VALUE_PENDING_REVENUE = Decimal("50000")

ONLINE_ORDER_SOURCES = (
    OrderSource.WEBSITE.value,
    OrderSource.WHATSAPP.value,
    OrderSource.INSTAGRAM.value,
    OrderSource.FACEBOOK.value,
)


@dataclass(frozen=True)
class KpiAggregate:
    total_revenue: Decimal
    total_profit: Decimal
    total_orders: int
    total_customers: int
    repeat_customers: int


@dataclass(frozen=True)
class CollectionKpiAggregate:
    total_revenue: Decimal
    total_profit: Decimal
    total_units: Decimal
    active_collections: int
    collection_order_count: int


@dataclass(frozen=True)
class OrderKpiAggregate:
    total_orders: int
    completed_orders: int
    total_revenue: Decimal
    total_profit: Decimal
    total_delivery_fees: Decimal
    total_package_fees: Decimal
    cancelled_orders: int


class AnalyticsRepository:
    """Read-only analytics queries over persisted snapshots."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self._insights = CustomerInsightsRepository(db)

    def _order_time_filter(self, date_range: AnalyticsDateRange):
        return and_(
            Order.created_at >= date_range.start_datetime,
            Order.created_at < date_range.end_datetime_exclusive,
            Order.status.notin_(ANALYTICS_EXCLUDED),
        )

    def _order_analytics_filter(self, date_range: AnalyticsDateRange):
        """Order analytics window — excludes draft only (includes cancelled)."""
        return and_(
            Order.created_at >= date_range.start_datetime,
            Order.created_at < date_range.end_datetime_exclusive,
            Order.status.notin_(ORDER_ANALYTICS_EXCLUDED),
        )

    def _delivery_date_filter(self, date_range: AnalyticsDateRange):
        return and_(
            Order.scheduled_delivery_date >= date_range.start_date,
            Order.scheduled_delivery_date <= date_range.end_date,
            Order.status.notin_(ANALYTICS_EXCLUDED),
        )

    def fetch_core_kpis(self, date_range: AnalyticsDateRange) -> KpiAggregate:
        filt = self._order_time_filter(date_range)
        stmt = select(
            func.coalesce(func.sum(Order.total_revenue_snapshot), 0),
            func.coalesce(func.sum(Order.total_profit_snapshot), 0),
            func.count(Order.id),
            func.count(func.distinct(Order.customer_id)),
        ).where(filt)
        row = self.db.execute(stmt).one()
        revenue = Decimal(row[0] or 0).quantize(MONEY)
        profit = Decimal(row[1] or 0).quantize(MONEY)
        total_orders = int(row[2] or 0)
        total_customers = int(row[3] or 0)

        repeat_stmt = (
            select(Order.customer_id)
            .where(filt)
            .group_by(Order.customer_id)
            .having(func.count(Order.id) >= 2)
        )
        repeat_customers = len(self.db.execute(repeat_stmt).all())

        return KpiAggregate(
            total_revenue=revenue,
            total_profit=profit,
            total_orders=total_orders,
            total_customers=total_customers,
            repeat_customers=repeat_customers,
        )

    def _period_column(self, granularity: TrendGranularity, column):
        if granularity == TrendGranularity.DAY:
            return func.date(column)
        if granularity == TrendGranularity.WEEK:
            return func.date_trunc("week", column)
        return func.date_trunc("month", column)

    def fetch_order_trends(
        self,
        date_range: AnalyticsDateRange,
        granularity: TrendGranularity,
    ) -> list[tuple[date, Decimal, Decimal, int]]:
        period = self._period_column(granularity, Order.created_at).label("period")
        filt = self._order_time_filter(date_range)
        stmt = (
            select(
                period,
                func.coalesce(func.sum(Order.total_revenue_snapshot), 0),
                func.coalesce(func.sum(Order.total_profit_snapshot), 0),
                func.count(Order.id),
            )
            .where(filt)
            .group_by(period)
            .order_by(period)
        )
        rows = self.db.execute(stmt).all()
        return [
            (
                row[0].date() if hasattr(row[0], "date") else row[0],
                Decimal(row[1] or 0).quantize(MONEY),
                Decimal(row[2] or 0).quantize(MONEY),
                int(row[3] or 0),
            )
            for row in rows
        ]

    def fetch_product_rankings(
        self,
        date_range: AnalyticsDateRange,
        *,
        limit: int,
        order_by: str = "units",
        ascending: bool = False,
    ) -> list[dict[str, object]]:
        revenue = func.sum(
            OrderProductLine.product_selling_price_snapshot * OrderProductLine.quantity,
        ).label("revenue_snapshot")
        cost = func.sum(
            OrderProductLine.product_cost_snapshot * OrderProductLine.quantity,
        ).label("cost_snapshot")
        profit = func.sum(
            OrderProductLine.product_profit_snapshot * OrderProductLine.quantity,
        ).label("profit_snapshot")
        units = func.sum(OrderProductLine.quantity).label("units_sold")
        last_sold = func.max(Order.created_at).label("last_sold_at")

        order_columns = {
            "units": units,
            "profit": profit,
            "revenue": revenue,
            "margin": profit / func.nullif(revenue, 0),
        }
        order_col = order_columns.get(order_by, units)
        order_expr = order_col.asc() if ascending else desc(order_col)

        stmt = (
            select(
                OrderProductLine.product_id,
                OrderProductLine.product_name_snapshot,
                units,
                revenue,
                cost,
                profit,
                last_sold,
            )
            .join(Order, OrderProductLine.order_id == Order.id)
            .where(self._order_time_filter(date_range))
            .group_by(
                OrderProductLine.product_id,
                OrderProductLine.product_name_snapshot,
            )
            .order_by(order_expr)
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "product_id": row.product_id,
                "product_name_snapshot": row.product_name_snapshot,
                "units_sold": row.units_sold,
                "revenue_snapshot": row.revenue_snapshot,
                "cost_snapshot": row.cost_snapshot,
                "profit_snapshot": row.profit_snapshot,
                "last_sold_at": row.last_sold_at,
            }
            for row in rows
        ]

    def fetch_total_product_units_sold(self, date_range: AnalyticsDateRange) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(OrderProductLine.quantity), 0))
            .select_from(OrderProductLine)
            .join(Order, OrderProductLine.order_id == Order.id)
            .where(self._order_time_filter(date_range))
        )
        total = self.db.scalar(stmt)
        return Decimal(total or 0).quantize(QTY)

    def fetch_collection_rankings(
        self,
        date_range: AnalyticsDateRange,
        *,
        limit: int,
        order_by: str = "units",
        ascending: bool = False,
    ) -> list[dict[str, object]]:
        revenue = func.sum(
            OrderCollectionLine.collection_selling_price_snapshot
            * OrderCollectionLine.quantity,
        ).label("revenue_snapshot")
        cost = func.sum(
            OrderCollectionLine.collection_cost_snapshot * OrderCollectionLine.quantity,
        ).label("cost_snapshot")
        profit = func.sum(
            OrderCollectionLine.collection_profit_snapshot * OrderCollectionLine.quantity,
        ).label("profit_snapshot")
        units = func.sum(OrderCollectionLine.quantity).label("units_sold")
        last_sold = func.max(Order.created_at).label("last_sold_at")

        order_columns = {
            "units": units,
            "profit": profit,
            "revenue": revenue,
            "margin": profit / func.nullif(revenue, 0),
        }
        order_col = order_columns.get(order_by, units)
        order_expr = order_col.asc() if ascending else desc(order_col)

        stmt = (
            select(
                OrderCollectionLine.collection_id,
                OrderCollectionLine.collection_name_snapshot,
                CollectionPackage.name.label("package_name"),
                units,
                revenue,
                cost,
                profit,
                last_sold,
            )
            .join(Order, OrderCollectionLine.order_id == Order.id)
            .join(Collection, Collection.id == OrderCollectionLine.collection_id)
            .outerjoin(CollectionPackage, CollectionPackage.id == Collection.package_id)
            .where(self._order_time_filter(date_range))
            .group_by(
                OrderCollectionLine.collection_id,
                OrderCollectionLine.collection_name_snapshot,
                CollectionPackage.name,
            )
            .order_by(order_expr)
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "collection_id": row.collection_id,
                "collection_name_snapshot": row.collection_name_snapshot,
                "package_name": row.package_name,
                "units_sold": row.units_sold,
                "revenue_snapshot": row.revenue_snapshot,
                "cost_snapshot": row.cost_snapshot,
                "profit_snapshot": row.profit_snapshot,
                "last_sold_at": row.last_sold_at,
            }
            for row in rows
        ]

    def fetch_total_collection_units_sold(self, date_range: AnalyticsDateRange) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(OrderCollectionLine.quantity), 0))
            .select_from(OrderCollectionLine)
            .join(Order, OrderCollectionLine.order_id == Order.id)
            .where(self._order_time_filter(date_range))
        )
        total = self.db.scalar(stmt)
        return Decimal(total or 0).quantize(QTY)

    def _collection_line_filter(self, date_range: AnalyticsDateRange):
        return self._order_time_filter(date_range)

    def fetch_collection_kpi_aggregate(
        self,
        date_range: AnalyticsDateRange,
    ) -> CollectionKpiAggregate:
        filt = self._collection_line_filter(date_range)
        revenue_expr = OrderCollectionLine.collection_selling_price_snapshot * OrderCollectionLine.quantity
        profit_expr = OrderCollectionLine.collection_profit_snapshot * OrderCollectionLine.quantity
        stmt = (
            select(
                func.coalesce(func.sum(revenue_expr), 0),
                func.coalesce(func.sum(profit_expr), 0),
                func.coalesce(func.sum(OrderCollectionLine.quantity), 0),
                func.count(func.distinct(OrderCollectionLine.collection_id)),
                func.count(func.distinct(Order.id)),
            )
            .select_from(OrderCollectionLine)
            .join(Order, OrderCollectionLine.order_id == Order.id)
            .where(filt)
        )
        row = self.db.execute(stmt).one()
        return CollectionKpiAggregate(
            total_revenue=Decimal(row[0] or 0).quantize(MONEY),
            total_profit=Decimal(row[1] or 0).quantize(MONEY),
            total_units=Decimal(row[2] or 0).quantize(QTY),
            active_collections=int(row[3] or 0),
            collection_order_count=int(row[4] or 0),
        )

    def fetch_collection_trends(
        self,
        date_range: AnalyticsDateRange,
        granularity: TrendGranularity,
    ) -> list[tuple[date, Decimal, Decimal, Decimal, int]]:
        period = self._period_column(granularity, Order.created_at).label("period")
        filt = self._collection_line_filter(date_range)
        revenue_expr = OrderCollectionLine.collection_selling_price_snapshot * OrderCollectionLine.quantity
        profit_expr = OrderCollectionLine.collection_profit_snapshot * OrderCollectionLine.quantity
        stmt = (
            select(
                period,
                func.coalesce(func.sum(revenue_expr), 0),
                func.coalesce(func.sum(profit_expr), 0),
                func.coalesce(func.sum(OrderCollectionLine.quantity), 0),
                func.count(func.distinct(Order.id)),
            )
            .select_from(OrderCollectionLine)
            .join(Order, OrderCollectionLine.order_id == Order.id)
            .where(filt)
            .group_by(period)
            .order_by(period)
        )
        rows = self.db.execute(stmt).all()
        return [
            (
                row[0].date() if hasattr(row[0], "date") else row[0],
                Decimal(row[1] or 0).quantize(MONEY),
                Decimal(row[2] or 0).quantize(MONEY),
                Decimal(row[3] or 0).quantize(QTY),
                int(row[4] or 0),
            )
            for row in rows
        ]

    def fetch_collection_units_by_collection(
        self,
        date_range: AnalyticsDateRange,
    ) -> list[dict[str, object]]:
        filt = self._collection_line_filter(date_range)
        units = func.coalesce(func.sum(OrderCollectionLine.quantity), 0).label("units_sold")
        stmt = (
            select(
                OrderCollectionLine.collection_id,
                OrderCollectionLine.collection_name_snapshot,
                units,
            )
            .join(Order, OrderCollectionLine.order_id == Order.id)
            .where(filt)
            .group_by(
                OrderCollectionLine.collection_id,
                OrderCollectionLine.collection_name_snapshot,
            )
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "collection_id": row.collection_id,
                "collection_name_snapshot": row.collection_name_snapshot,
                "units_sold": row.units_sold,
            }
            for row in rows
        ]

    def fetch_collection_package_performance(
        self,
        date_range: AnalyticsDateRange,
    ) -> list[dict[str, object]]:
        filt = self._collection_line_filter(date_range)
        package_name = func.coalesce(CollectionPackage.name, "Unassigned").label("package_name")
        package_code = func.coalesce(CollectionPackage.code, "UNASSIGNED").label("package_code")
        package_id = CollectionPackage.id.label("package_id")
        revenue = func.sum(
            OrderCollectionLine.collection_selling_price_snapshot * OrderCollectionLine.quantity,
        ).label("revenue_snapshot")
        cost = func.sum(
            OrderCollectionLine.collection_cost_snapshot * OrderCollectionLine.quantity,
        ).label("cost_snapshot")
        profit = func.sum(
            OrderCollectionLine.collection_profit_snapshot * OrderCollectionLine.quantity,
        ).label("profit_snapshot")
        units = func.sum(OrderCollectionLine.quantity).label("units_sold")
        order_count = func.count(func.distinct(Order.id)).label("order_count")
        stmt = (
            select(
                package_id,
                package_code,
                package_name,
                revenue,
                cost,
                profit,
                units,
                order_count,
            )
            .select_from(OrderCollectionLine)
            .join(Order, OrderCollectionLine.order_id == Order.id)
            .join(Collection, Collection.id == OrderCollectionLine.collection_id)
            .outerjoin(CollectionPackage, CollectionPackage.id == Collection.package_id)
            .where(filt)
            .group_by(package_id, package_code, package_name)
            .order_by(desc(revenue))
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "package_id": row.package_id,
                "package_code": row.package_code,
                "package_name": row.package_name,
                "revenue_snapshot": Decimal(row.revenue_snapshot or 0).quantize(MONEY),
                "cost_snapshot": Decimal(row.cost_snapshot or 0).quantize(MONEY),
                "profit_snapshot": Decimal(row.profit_snapshot or 0).quantize(MONEY),
                "units_sold": Decimal(row.units_sold or 0).quantize(QTY),
                "order_count": int(row.order_count or 0),
            }
            for row in rows
        ]

    def fetch_order_kpi_aggregate(self, date_range: AnalyticsDateRange) -> OrderKpiAggregate:
        filt = self._order_analytics_filter(date_range)
        stmt = select(
            func.count(Order.id),
            func.coalesce(
                func.sum(
                    case(
                        (Order.status == OrderStatus.DELIVERED, 1),
                        else_=0,
                    ),
                ),
                0,
            ),
            func.coalesce(func.sum(Order.total_revenue_snapshot), 0),
            func.coalesce(func.sum(Order.total_profit_snapshot), 0),
            func.coalesce(func.sum(Order.delivery_fee_snapshot), 0),
            func.coalesce(
                func.sum(
                    case(
                        (Order.status == OrderStatus.CANCELLED, 1),
                        else_=0,
                    ),
                ),
                0,
            ),
        ).where(filt)
        row = self.db.execute(stmt).one()

        package_fee_stmt = (
            select(
                func.coalesce(
                    func.sum(
                        OrderCollectionLine.package_fee_snapshot
                        * OrderCollectionLine.quantity,
                    ),
                    0,
                ),
            )
            .select_from(OrderCollectionLine)
            .join(Order, Order.id == OrderCollectionLine.order_id)
            .where(
                filt,
                OrderCollectionLine.package_fee_snapshot.isnot(None),
            )
        )
        package_fees = Decimal(self.db.scalar(package_fee_stmt) or 0).quantize(MONEY)

        return OrderKpiAggregate(
            total_orders=int(row[0] or 0),
            completed_orders=int(row[1] or 0),
            total_revenue=Decimal(row[2] or 0).quantize(MONEY),
            total_profit=Decimal(row[3] or 0).quantize(MONEY),
            total_delivery_fees=Decimal(row[4] or 0).quantize(MONEY),
            total_package_fees=package_fees,
            cancelled_orders=int(row[5] or 0),
        )

    def fetch_order_status_distribution(
        self,
        date_range: AnalyticsDateRange,
    ) -> list[tuple[str, int]]:
        filt = self._order_analytics_filter(date_range)
        stmt = (
            select(Order.status, func.count(Order.id))
            .where(filt)
            .group_by(Order.status)
            .order_by(desc(func.count(Order.id)))
        )
        rows = self.db.execute(stmt).all()
        return [(str(row[0]), int(row[1] or 0)) for row in rows]

    def fetch_order_payment_status_distribution(
        self,
        date_range: AnalyticsDateRange,
    ) -> list[tuple[str, int]]:
        filt = self._order_analytics_filter(date_range)
        stmt = (
            select(Order.payment_status, func.count(Order.id))
            .where(filt)
            .group_by(Order.payment_status)
            .order_by(desc(func.count(Order.id)))
        )
        rows = self.db.execute(stmt).all()
        return [(str(row[0]), int(row[1] or 0)) for row in rows]

    def fetch_order_payment_method_distribution(
        self,
        date_range: AnalyticsDateRange,
    ) -> list[tuple[str, int]]:
        filt = self._order_analytics_filter(date_range)
        stmt = (
            select(Order.payment_method, func.count(Order.id))
            .where(filt)
            .group_by(Order.payment_method)
            .order_by(desc(func.count(Order.id)))
        )
        rows = self.db.execute(stmt).all()
        return [(str(row[0]), int(row[1] or 0)) for row in rows]

    def fetch_order_source_distribution(
        self,
        date_range: AnalyticsDateRange,
    ) -> list[tuple[str, int]]:
        filt = self._order_analytics_filter(date_range)
        stmt = (
            select(Order.source, func.count(Order.id))
            .where(filt)
            .group_by(Order.source)
            .order_by(desc(func.count(Order.id)))
        )
        rows = self.db.execute(stmt).all()
        return [(str(row[0]), int(row[1] or 0)) for row in rows]

    def fetch_order_type_distribution(
        self,
        date_range: AnalyticsDateRange,
    ) -> list[tuple[str, int]]:
        filt = self._order_analytics_filter(date_range)
        stmt = (
            select(Order.order_type, func.count(Order.id))
            .where(filt)
            .group_by(Order.order_type)
            .order_by(desc(func.count(Order.id)))
        )
        rows = self.db.execute(stmt).all()
        return [(str(row[0].value if isinstance(row[0], OrderType) else row[0]), int(row[1] or 0)) for row in rows]

    def fetch_order_delivery_area_distribution(
        self,
        date_range: AnalyticsDateRange,
        *,
        limit: int,
    ) -> list[tuple[str, int]]:
        filt = self._order_analytics_filter(date_range)
        area_name = func.coalesce(DeliveryArea.name, "Unassigned")
        stmt = (
            select(area_name, func.count(Order.id))
            .outerjoin(DeliveryArea, Order.delivery_area_id == DeliveryArea.id)
            .where(filt)
            .group_by(area_name)
            .order_by(desc(func.count(Order.id)))
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        return [(str(row[0]), int(row[1] or 0)) for row in rows]

    def fetch_order_fulfillment_trends(
        self,
        date_range: AnalyticsDateRange,
        granularity: TrendGranularity,
    ) -> list[tuple[date, int]]:
        period = self._period_column(granularity, Order.delivered_at).label("period")
        filt = and_(
            self._order_analytics_filter(date_range),
            Order.status == OrderStatus.DELIVERED.value,
            Order.delivered_at.isnot(None),
        )
        stmt = (
            select(period, func.count(Order.id))
            .where(filt)
            .group_by(period)
            .order_by(period)
        )
        rows = self.db.execute(stmt).all()
        return [
            (
                row[0].date() if hasattr(row[0], "date") else row[0],
                int(row[1] or 0),
            )
            for row in rows
            if row[0] is not None
        ]

    def fetch_order_delivery_trends(
        self,
        date_range: AnalyticsDateRange,
        granularity: TrendGranularity,
    ) -> list[tuple[date, int]]:
        period = self._period_column(granularity, Order.scheduled_delivery_date).label(
            "period",
        )
        filt = and_(
            self._order_analytics_filter(date_range),
            Order.status == OrderStatus.DELIVERED.value,
        )
        stmt = (
            select(period, func.count(Order.id))
            .where(filt)
            .group_by(period)
            .order_by(period)
        )
        rows = self.db.execute(stmt).all()
        return [
            (
                row[0].date() if hasattr(row[0], "date") else row[0],
                int(row[1] or 0),
            )
            for row in rows
        ]

    def fetch_order_lifecycle_trends(
        self,
        date_range: AnalyticsDateRange,
        granularity: TrendGranularity,
    ) -> list[dict[str, object]]:
        period = self._period_column(granularity, Order.created_at).label("period")
        filt = self._order_analytics_filter(date_range)
        stmt = (
            select(
                period,
                func.coalesce(func.sum(case((Order.status == OrderStatus.DRAFT, 1), else_=0)), 0).label("draft"),
                func.coalesce(func.sum(case((Order.status == OrderStatus.CONFIRMED, 1), else_=0)), 0).label("confirmed"),
                func.coalesce(func.sum(case((Order.status == OrderStatus.PREPARING, 1), else_=0)), 0).label("preparing"),
                func.coalesce(func.sum(case((Order.status == OrderStatus.READY, 1), else_=0)), 0).label("ready"),
                func.coalesce(func.sum(case((Order.status == OrderStatus.DELIVERED, 1), else_=0)), 0).label("delivered"),
                func.coalesce(func.sum(case((Order.status == OrderStatus.CANCELLED, 1), else_=0)), 0).label("cancelled"),
            )
            .where(filt)
            .group_by(period)
            .order_by(period)
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "period_start": row.period.date() if hasattr(row.period, "date") else row.period,
                "draft": int(row.draft or 0),
                "confirmed": int(row.confirmed or 0),
                "preparing": int(row.preparing or 0),
                "ready": int(row.ready or 0),
                "delivered": int(row.delivered or 0),
                "cancelled": int(row.cancelled or 0),
            }
            for row in rows
        ]

    def fetch_delivery_area_performance(
        self,
        date_range: AnalyticsDateRange,
        *,
        limit: int,
    ) -> list[dict[str, object]]:
        filt = self._order_analytics_filter(date_range)
        area_name = func.coalesce(DeliveryArea.name, "Unassigned")
        stmt = (
            select(
                area_name.label("area_name"),
                func.count(Order.id).label("order_count"),
                func.coalesce(func.sum(Order.total_revenue_snapshot), 0).label("revenue_snapshot"),
                func.coalesce(func.sum(Order.delivery_fee_snapshot), 0).label("delivery_fee_revenue"),
            )
            .outerjoin(DeliveryArea, Order.delivery_area_id == DeliveryArea.id)
            .where(filt)
            .group_by(area_name)
            .order_by(desc(func.coalesce(func.sum(Order.total_revenue_snapshot), 0)))
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "area_name": str(row.area_name),
                "order_count": int(row.order_count or 0),
                "revenue_snapshot": Decimal(row.revenue_snapshot or 0).quantize(MONEY),
                "delivery_fee_revenue": Decimal(row.delivery_fee_revenue or 0).quantize(MONEY),
            }
            for row in rows
        ]

    def fetch_payment_method_performance(
        self,
        date_range: AnalyticsDateRange,
    ) -> list[dict[str, object]]:
        filt = self._order_analytics_filter(date_range)
        stmt = (
            select(
                Order.payment_method.label("payment_method"),
                func.count(Order.id).label("order_count"),
                func.coalesce(func.sum(Order.total_revenue_snapshot), 0).label("revenue_snapshot"),
            )
            .where(filt)
            .group_by(Order.payment_method)
            .order_by(desc(func.coalesce(func.sum(Order.total_revenue_snapshot), 0)))
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "payment_method": row.payment_method,
                "order_count": int(row.order_count or 0),
                "revenue_snapshot": Decimal(row.revenue_snapshot or 0).quantize(MONEY),
            }
            for row in rows
        ]

    def fetch_customer_order_behaviour(
        self,
        date_range: AnalyticsDateRange,
    ) -> dict[str, object]:
        in_range = (
            select(
                Order.customer_id.label("customer_id"),
                func.count(Order.id).label("order_count"),
            )
            .where(self._order_analytics_filter(date_range))
            .group_by(Order.customer_id)
            .subquery()
        )
        before_range = (
            select(Order.customer_id.label("customer_id"))
            .where(
                Order.created_at < date_range.start_datetime,
                Order.status.notin_(ORDER_ANALYTICS_EXCLUDED),
            )
            .distinct()
            .subquery()
        )
        stmt = select(
            func.coalesce(func.sum(case((before_range.c.customer_id.is_(None), 1), else_=0)), 0).label("first_time_customers"),
            func.coalesce(func.sum(case((before_range.c.customer_id.is_not(None), 1), else_=0)), 0).label("returning_customers"),
            func.coalesce(func.sum(in_range.c.order_count), 0).label("total_orders"),
            func.count(in_range.c.customer_id).label("total_customers"),
            func.coalesce(func.sum(case((in_range.c.order_count >= 2, 1), else_=0)), 0).label("repeat_customers"),
        ).select_from(in_range).outerjoin(
            before_range,
            before_range.c.customer_id == in_range.c.customer_id,
        )
        row = self.db.execute(stmt).one()
        return {
            "first_time_customers": int(row.first_time_customers or 0),
            "returning_customers": int(row.returning_customers or 0),
            "total_orders": int(row.total_orders or 0),
            "total_customers": int(row.total_customers or 0),
            "repeat_customers": int(row.repeat_customers or 0),
        }

    def fetch_order_performance(
        self,
        date_range: AnalyticsDateRange,
        *,
        limit: int,
    ) -> list[Order]:
        stmt = (
            select(Order)
            .options(
                joinedload(Order.customer),
                joinedload(Order.delivery_area),
                joinedload(Order.collection_lines)
                .joinedload(OrderCollectionLine.collection)
                .joinedload(Collection.package),
            )
            .where(self._order_analytics_filter(date_range))
            .order_by(desc(Order.created_at))
            .limit(limit)
        )
        return list(self.db.scalars(stmt).unique().all())

    def fetch_top_delivery_area(
        self,
        date_range: AnalyticsDateRange,
    ) -> tuple[str, int] | None:
        rows = self.fetch_order_delivery_area_distribution(date_range, limit=1)
        return (rows[0][0], rows[0][1]) if rows else None

    def fetch_top_payment_method(
        self,
        date_range: AnalyticsDateRange,
    ) -> tuple[str, int] | None:
        rows = self.fetch_order_payment_method_distribution(date_range)
        return (rows[0][0], rows[0][1]) if rows else None

    def fetch_top_order_source_raw(
        self,
        date_range: AnalyticsDateRange,
    ) -> tuple[str, int] | None:
        rows = self.fetch_order_source_distribution(date_range)
        return (rows[0][0], rows[0][1]) if rows else None

    def fetch_fastest_fulfilled_order(
        self,
        date_range: AnalyticsDateRange,
    ) -> Order | None:
        filt = and_(
            self._order_analytics_filter(date_range),
            Order.status == OrderStatus.DELIVERED.value,
            Order.delivered_at.isnot(None),
        )
        duration = Order.delivered_at - Order.created_at
        stmt = (
            select(Order)
            .options(joinedload(Order.customer))
            .where(filt)
            .order_by(duration.asc())
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def fetch_highest_value_order(
        self,
        date_range: AnalyticsDateRange,
    ) -> Order | None:
        filt = self._order_analytics_filter(date_range)
        stmt = (
            select(Order)
            .options(joinedload(Order.customer))
            .where(filt)
            .order_by(desc(Order.total_revenue_snapshot))
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def fetch_largest_delivery_batch(
        self,
        date_range: AnalyticsDateRange,
    ) -> tuple[date, int] | None:
        filt = self._order_analytics_filter(date_range)
        stmt = (
            select(Order.scheduled_delivery_date, func.count(Order.id))
            .where(filt)
            .group_by(Order.scheduled_delivery_date)
            .order_by(desc(func.count(Order.id)))
            .limit(1)
        )
        row = self.db.execute(stmt).first()
        if not row:
            return None
        return row[0], int(row[1] or 0)

    def count_orders_by_status(self, statuses: tuple[OrderStatus, ...]) -> int:
        if not statuses:
            return 0
        values = [status.value for status in statuses]
        stmt = select(func.count(Order.id)).where(Order.status.in_(values))
        return int(self.db.scalar(stmt) or 0)

    def count_upcoming_delivery_orders(self, on_or_after: date) -> int:
        stmt = select(func.count(Order.id)).where(
            Order.scheduled_delivery_date >= on_or_after,
            Order.status.notin_(ORDER_ANALYTICS_EXCLUDED),
        )
        return int(self.db.scalar(stmt) or 0)

    def fetch_upcoming_delivery_schedule(
        self,
        on_or_after: date,
        *,
        limit: int,
    ) -> list[tuple[date, int]]:
        stmt = (
            select(Order.scheduled_delivery_date, func.count(Order.id))
            .where(
                Order.scheduled_delivery_date >= on_or_after,
                Order.status.notin_(ORDER_ANALYTICS_EXCLUDED),
            )
            .group_by(Order.scheduled_delivery_date)
            .order_by(Order.scheduled_delivery_date)
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        return [(row[0], int(row[1] or 0)) for row in rows]

    def fetch_delivery_fee_revenue_by_area(
        self,
        date_range: AnalyticsDateRange,
        *,
        limit: int,
    ) -> list[tuple[str, int, Decimal]]:
        filt = self._order_analytics_filter(date_range)
        area_name = func.coalesce(DeliveryArea.name, "Unassigned")
        stmt = (
            select(
                area_name,
                func.count(Order.id),
                func.coalesce(func.sum(Order.delivery_fee_snapshot), 0),
            )
            .outerjoin(DeliveryArea, Order.delivery_area_id == DeliveryArea.id)
            .where(filt)
            .group_by(area_name)
            .order_by(desc(func.coalesce(func.sum(Order.delivery_fee_snapshot), 0)))
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        return [
            (str(row[0]), int(row[1] or 0), Decimal(row[2] or 0).quantize(MONEY))
            for row in rows
        ]

    def fetch_payment_revenue_split(
        self,
        date_range: AnalyticsDateRange,
    ) -> tuple[Decimal, Decimal, Decimal]:
        filt = self._order_analytics_filter(date_range)
        paid_case = case(
            (Order.payment_status == PaymentStatus.PAID, Order.total_revenue_snapshot),
            else_=0,
        )
        unpaid_case = case(
            (
                Order.payment_status.in_(
                    [PaymentStatus.PENDING, PaymentStatus.FAILED],
                ),
                Order.total_revenue_snapshot,
            ),
            else_=0,
        )
        stmt = select(
            func.coalesce(func.sum(paid_case), 0),
            func.coalesce(func.sum(unpaid_case), 0),
        ).where(filt)
        row = self.db.execute(stmt).one()
        paid = Decimal(row[0] or 0).quantize(MONEY)
        unpaid = Decimal(row[1] or 0).quantize(MONEY)
        return paid, unpaid, unpaid

    def fetch_revenue_contribution(
        self,
        date_range: AnalyticsDateRange,
    ) -> tuple[Decimal, Decimal, Decimal]:
        stmt = select(
            func.coalesce(func.sum(Order.products_subtotal_snapshot), 0),
            func.coalesce(func.sum(Order.collections_subtotal_snapshot), 0),
            func.coalesce(func.sum(Order.delivery_fee_snapshot), 0),
        ).where(self._order_time_filter(date_range))
        row = self.db.execute(stmt).one()
        return (
            Decimal(row[0] or 0).quantize(MONEY),
            Decimal(row[1] or 0).quantize(MONEY),
            Decimal(row[2] or 0).quantize(MONEY),
        )

    def count_high_value_pending_orders(
        self,
        *,
        minimum_revenue: Decimal = HIGH_VALUE_PENDING_REVENUE,
    ) -> int:
        stmt = select(func.count(Order.id)).where(
            Order.status.in_([OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value]),
            Order.total_revenue_snapshot >= minimum_revenue,
        )
        return int(self.db.scalar(stmt) or 0)

    def fetch_top_orders(
        self,
        date_range: AnalyticsDateRange,
        *,
        limit: int,
    ) -> list[Order]:
        stmt = (
            select(Order)
            .options(joinedload(Order.customer))
            .where(self._order_time_filter(date_range))
            .order_by(desc(Order.total_profit_snapshot))
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def fetch_customer_growth(
        self,
        date_range: AnalyticsDateRange,
        granularity: TrendGranularity,
    ) -> list[tuple[date, int]]:
        period = self._period_column(granularity, Customer.created_at).label("period")
        stmt = (
            select(period, func.count(Customer.id))
            .where(
                Customer.created_at >= date_range.start_datetime,
                Customer.created_at < date_range.end_datetime_exclusive,
            )
            .group_by(period)
            .order_by(period)
        )
        rows = self.db.execute(stmt).all()
        return [
            (
                row[0].date() if hasattr(row[0], "date") else row[0],
                int(row[1] or 0),
            )
            for row in rows
        ]

    def fetch_active_customer_ids(self, date_range: AnalyticsDateRange) -> list:
        stmt = (
            select(Order.customer_id)
            .where(self._order_time_filter(date_range))
            .distinct()
        )
        return list(self.db.scalars(stmt).all())

    def count_customers_by_segment(
        self,
        date_range: AnalyticsDateRange,
        config: CustomerSegmentationConfig,
    ) -> dict[CustomerSegment, int]:
        customer_ids = self.fetch_active_customer_ids(date_range)
        counts: dict[CustomerSegment, int] = {}
        for customer_id in customer_ids:
            customer = self.db.get(Customer, customer_id)
            if not customer:
                continue
            metrics = self._insights.get_metrics_for_customer(customer)
            segment = calculate_customer_segment(metrics, config=config)
            if segment:
                counts[segment] = counts.get(segment, 0) + 1
        return counts

    def count_total_customers_as_of(self, date_range: AnalyticsDateRange) -> int:
        stmt = select(func.count(Customer.id)).where(
            Customer.created_at < date_range.end_datetime_exclusive,
        )
        return int(self.db.scalar(stmt) or 0)

    def fetch_period_customer_revenue_stats(
        self,
        date_range: AnalyticsDateRange,
    ) -> tuple[int, Decimal]:
        """Distinct customers with orders in range and total snapshot revenue."""
        stmt = select(
            func.count(func.distinct(Order.customer_id)),
            func.coalesce(func.sum(Order.total_revenue_snapshot), 0),
        ).where(self._order_time_filter(date_range))
        row = self.db.execute(stmt).one()
        return int(row[0] or 0), Decimal(row[1] or 0).quantize(MONEY)

    def fetch_customers_performance_in_range(
        self,
        date_range: AnalyticsDateRange,
        *,
        limit: int,
        config: CustomerSegmentationConfig,
    ) -> list[dict[str, object]]:
        """Customers with orders in range, ranked by lifetime spend (snapshot)."""
        period_stats = (
            select(
                Order.customer_id.label("customer_id"),
                func.count(Order.id).label("period_orders"),
                func.coalesce(func.sum(Order.total_revenue_snapshot), 0).label(
                    "period_revenue",
                ),
                func.max(Order.scheduled_delivery_date).label("period_last_order"),
            )
            .where(self._order_time_filter(date_range))
            .group_by(Order.customer_id)
            .subquery()
        )
        stmt = (
            select(Customer, period_stats.c.period_orders, period_stats.c.period_last_order)
            .join(period_stats, Customer.id == period_stats.c.customer_id)
            .order_by(desc(period_stats.c.period_revenue))
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        results: list[dict[str, object]] = []
        for row in rows:
            customer = row[0]
            metrics = self._insights.get_metrics_for_customer(customer)
            segment = calculate_customer_segment(metrics, config=config)
            avg_order = Decimal("0.00")
            if metrics.total_orders > 0:
                avg_order = (metrics.lifetime_spend / metrics.total_orders).quantize(MONEY)
            results.append(
                {
                    "customer": customer,
                    "total_orders": metrics.total_orders,
                    "lifetime_spend": metrics.lifetime_spend,
                    "average_order_value": avg_order,
                    "last_order_date": metrics.last_order_date,
                    "segment": segment,
                    "marketing_source": customer.marketing_source,
                },
            )
        results.sort(
            key=lambda item: Decimal(item["lifetime_spend"]),  # type: ignore[arg-type]
            reverse=True,
        )
        return results

    def fetch_new_customers_by_marketing_source(
        self,
        date_range: AnalyticsDateRange,
    ) -> list[tuple[MarketingSource | None, int]]:
        stmt = (
            select(Customer.marketing_source, func.count(Customer.id))
            .where(
                Customer.created_at >= date_range.start_datetime,
                Customer.created_at < date_range.end_datetime_exclusive,
            )
            .group_by(Customer.marketing_source)
            .order_by(desc(func.count(Customer.id)))
        )
        rows = self.db.execute(stmt).all()
        return [(row[0], int(row[1] or 0)) for row in rows]

    def fetch_segment_lifetime_spend_totals(
        self,
        date_range: AnalyticsDateRange,
        config: CustomerSegmentationConfig,
    ) -> dict[CustomerSegment, Decimal]:
        """Sum of lifetime spend per segment among customers active in range."""
        totals: dict[CustomerSegment, Decimal] = {}
        for customer_id in self.fetch_active_customer_ids(date_range):
            customer = self.db.get(Customer, customer_id)
            if not customer:
                continue
            metrics = self._insights.get_metrics_for_customer(customer)
            segment = calculate_customer_segment(metrics, config=config)
            if segment:
                totals[segment] = totals.get(segment, Decimal("0")) + metrics.lifetime_spend
        return totals

    def fetch_marketing_source_performance(
        self,
        date_range: AnalyticsDateRange,
    ) -> list[dict[str, object]]:
        stmt = (
            select(
                Customer.marketing_source,
                func.count(func.distinct(Customer.id)),
                func.count(Order.id),
                func.coalesce(func.sum(Order.total_revenue_snapshot), 0),
                func.coalesce(func.sum(Order.total_profit_snapshot), 0),
            )
            .join(Order, Order.customer_id == Customer.id)
            .where(self._order_time_filter(date_range))
            .group_by(Customer.marketing_source)
            .order_by(desc(func.sum(Order.total_revenue_snapshot)))
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "marketing_source": row[0],
                "customer_count": int(row[1] or 0),
                "order_count": int(row[2] or 0),
                "revenue_snapshot": row[3],
                "profit_snapshot": row[4],
            }
            for row in rows
        ]

    def fetch_production_volume_by_delivery(
        self,
        date_range: AnalyticsDateRange,
        granularity: TrendGranularity,
    ) -> list[tuple[date, Decimal, Decimal, int]]:
        period = self._period_column(
            granularity,
            Order.scheduled_delivery_date,
        ).label("period")
        filt = self._delivery_date_filter(date_range)

        product_qty = (
            select(
                Order.id.label("order_id"),
                func.coalesce(func.sum(OrderProductLine.quantity), 0).label("pq"),
            )
            .outerjoin(OrderProductLine, OrderProductLine.order_id == Order.id)
            .group_by(Order.id)
            .subquery()
        )
        collection_qty = (
            select(
                Order.id.label("order_id"),
                func.coalesce(func.sum(OrderCollectionLine.quantity), 0).label("cq"),
            )
            .outerjoin(OrderCollectionLine, OrderCollectionLine.order_id == Order.id)
            .group_by(Order.id)
            .subquery()
        )

        stmt = (
            select(
                period,
                func.coalesce(func.sum(product_qty.c.pq), 0),
                func.coalesce(func.sum(collection_qty.c.cq), 0),
                func.count(Order.id),
            )
            .outerjoin(product_qty, product_qty.c.order_id == Order.id)
            .outerjoin(collection_qty, collection_qty.c.order_id == Order.id)
            .where(filt)
            .group_by(period)
            .order_by(period)
        )
        rows = self.db.execute(stmt).all()
        return [
            (
                row[0].date() if hasattr(row[0], "date") else row[0],
                Decimal(row[1] or 0).quantize(QTY),
                Decimal(row[2] or 0).quantize(QTY),
                int(row[3] or 0),
            )
            for row in rows
        ]

    def fetch_batch_volume(
        self,
        date_range: AnalyticsDateRange,
    ) -> list[tuple[date, int, Decimal]]:
        stmt = (
            select(
                Order.scheduled_delivery_date,
                func.count(Order.id),
                func.coalesce(func.sum(Order.total_revenue_snapshot), 0),
            )
            .where(self._delivery_date_filter(date_range))
            .group_by(Order.scheduled_delivery_date)
            .order_by(Order.scheduled_delivery_date)
        )
        rows = self.db.execute(stmt).all()
        return [
            (
                row[0],
                int(row[1] or 0),
                Decimal(row[2] or 0).quantize(MONEY),
            )
            for row in rows
        ]

    def list_distinct_delivery_dates(
        self,
        date_range: AnalyticsDateRange,
    ) -> list[date]:
        stmt = (
            select(Order.scheduled_delivery_date)
            .where(self._delivery_date_filter(date_range))
            .distinct()
            .order_by(Order.scheduled_delivery_date)
        )
        return list(self.db.scalars(stmt).all())

    def fetch_next_delivery_date_on_or_after(self, on_or_after: date) -> date | None:
        """Earliest scheduled delivery date on or after the given day."""
        stmt = (
            select(func.min(Order.scheduled_delivery_date))
            .where(
                Order.scheduled_delivery_date >= on_or_after,
                Order.status.notin_(ANALYTICS_EXCLUDED),
            )
        )
        return self.db.scalar(stmt)

    def fetch_next_delivery_date_after(self, after_date: date) -> date | None:
        """Earliest scheduled delivery date strictly after the given day."""
        stmt = (
            select(func.min(Order.scheduled_delivery_date))
            .where(
                Order.scheduled_delivery_date > after_date,
                Order.status.notin_(ANALYTICS_EXCLUDED),
            )
        )
        return self.db.scalar(stmt)
