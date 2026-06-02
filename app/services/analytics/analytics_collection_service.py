"""Collection analytics from order line snapshots."""

from datetime import timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsQueryParams,
    CollectionAnalyticsInsightItem,
    CollectionAnalyticsInsightsResponse,
    CollectionAnalyticsKpiResponse,
    CollectionAnalyticsRow,
    CollectionKpiMetric,
    CollectionTrendDataPoint,
    CollectionTrendSeriesResponse,
    RankedCollectionsResponse,
)
from app.services.analytics._common import (
    date_range_response,
    safe_divide,
    snapshot_margin_percentage,
    to_optional_date,
)
from app.utils.analytics_date_range import AnalyticsDateRange, resolve_analytics_date_range

MONEY = Decimal("0.01")
QTY = Decimal("0.0001")


def _kpi_metric(value: Decimal) -> CollectionKpiMetric:
    return CollectionKpiMetric(value=value)


class AnalyticsCollectionService:
    """Collection demand and profitability from immutable order snapshots."""

    def __init__(self, db: Session) -> None:
        self.repo = AnalyticsRepository(db)

    def get_kpis(self, params: AnalyticsQueryParams) -> CollectionAnalyticsKpiResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        agg = self.repo.fetch_collection_kpi_aggregate(date_range)
        avg_order_value = safe_divide(agg.total_revenue, agg.collection_order_count)
        avg_margin = snapshot_margin_percentage(agg.total_revenue, agg.total_profit)

        return CollectionAnalyticsKpiResponse(
            date_range=date_range_response(date_range),
            total_collection_revenue=_kpi_metric(agg.total_revenue),
            total_collection_profit=_kpi_metric(agg.total_profit),
            collections_sold=_kpi_metric(agg.total_units),
            average_collection_order_value=_kpi_metric(avg_order_value),
            average_collection_margin_percentage=_kpi_metric(avg_margin),
            active_collections_sold=_kpi_metric(Decimal(agg.active_collections)),
        )

    def get_insights(self, params: AnalyticsQueryParams) -> CollectionAnalyticsInsightsResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )

        def top_row(order_by: str, *, ascending: bool = False) -> dict[str, object] | None:
            rows = self.repo.fetch_collection_rankings(
                date_range,
                limit=1,
                order_by=order_by,
                ascending=ascending,
            )
            return rows[0] if rows else None

        def insight(
            insight_id: str,
            title: str,
            row: dict[str, object] | None,
            metric_label: str,
            formatter,
        ) -> CollectionAnalyticsInsightItem:
            name = str(row["collection_name_snapshot"]) if row else None
            return CollectionAnalyticsInsightItem(
                id=insight_id,
                title=title,
                name=name,
                metric_label=metric_label,
                metric_value=formatter(row) if row else "—",
            )

        fastest = self._fastest_growing_collection(date_range)

        items = [
            insight(
                "highest_revenue_collection",
                "Highest Revenue Collection",
                top_row("revenue"),
                "Revenue",
                lambda r: f"Rs {Decimal(r['revenue_snapshot']):,.2f}",  # type: ignore[index]
            ),
            insight(
                "highest_profit_collection",
                "Highest Profit Collection",
                top_row("profit"),
                "Profit",
                lambda r: f"Rs {Decimal(r['profit_snapshot']):,.2f}",  # type: ignore[index]
            ),
            insight(
                "highest_margin_collection",
                "Highest Margin Collection",
                top_row("margin"),
                "Margin",
                lambda r: self._format_margin_row(r),
            ),
            insight(
                "most_ordered_collection",
                "Most Ordered Collection",
                top_row("units"),
                "Units sold",
                lambda r: f"{Decimal(r['units_sold']).normalize():g}",  # type: ignore[index]
            ),
            CollectionAnalyticsInsightItem(
                id="fastest_growing_collection",
                title="Fastest Growing Collection",
                name=str(fastest["collection_name_snapshot"]) if fastest else None,
                metric_label="Growth",
                metric_value=str(fastest["growth_label"]) if fastest else "—",
            ),
            insight(
                "lowest_performing_collection",
                "Lowest Performing Collection",
                top_row("profit", ascending=True),
                "Profit",
                lambda r: f"Rs {Decimal(r['profit_snapshot']):,.2f}",  # type: ignore[index]
            ),
        ]
        return CollectionAnalyticsInsightsResponse(
            date_range=date_range_response(date_range),
            items=items,
        )

    def get_most_ordered(self, params: AnalyticsQueryParams) -> RankedCollectionsResponse:
        return self._ranked(params, order_by="units", ascending=False)

    def get_most_profitable(self, params: AnalyticsQueryParams) -> RankedCollectionsResponse:
        return self._ranked(params, order_by="profit", ascending=False)

    def get_top_revenue(self, params: AnalyticsQueryParams) -> RankedCollectionsResponse:
        return self._ranked(params, order_by="revenue", ascending=False)

    def get_top_profit(self, params: AnalyticsQueryParams) -> RankedCollectionsResponse:
        return self._ranked(params, order_by="profit", ascending=False)

    def get_top_margin(self, params: AnalyticsQueryParams) -> RankedCollectionsResponse:
        return self._ranked(params, order_by="margin", ascending=False)

    def get_top_volume(self, params: AnalyticsQueryParams) -> RankedCollectionsResponse:
        return self._ranked(params, order_by="units", ascending=False)

    def get_performance(self, params: AnalyticsQueryParams) -> RankedCollectionsResponse:
        return self._ranked(params, order_by="revenue", ascending=False)

    def get_revenue_trends(self, params: AnalyticsQueryParams) -> CollectionTrendSeriesResponse:
        return self._trends(params)

    def get_profit_trends(self, params: AnalyticsQueryParams) -> CollectionTrendSeriesResponse:
        return self._trends(params)

    def get_order_trends(self, params: AnalyticsQueryParams) -> CollectionTrendSeriesResponse:
        return self._trends(params)

    def _trends(self, params: AnalyticsQueryParams) -> CollectionTrendSeriesResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        rows = self.repo.fetch_collection_trends(date_range, params.granularity)
        return CollectionTrendSeriesResponse(
            date_range=date_range_response(date_range),
            granularity=params.granularity,
            points=[
                CollectionTrendDataPoint(
                    period_start=period,
                    revenue=revenue,
                    profit=profit,
                    units_sold=units,
                    order_count=order_count,
                )
                for period, revenue, profit, units, order_count in rows
            ],
        )

    def _ranked(
        self,
        params: AnalyticsQueryParams,
        *,
        order_by: str,
        ascending: bool,
    ) -> RankedCollectionsResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        rows = self.repo.fetch_collection_rankings(
            date_range,
            limit=params.limit,
            order_by=order_by,
            ascending=ascending,
        )
        return RankedCollectionsResponse(
            date_range=date_range_response(date_range),
            items=[self._row(row) for row in rows],
        )

    def _fastest_growing_collection(
        self,
        date_range: AnalyticsDateRange,
    ) -> dict[str, object] | None:
        span_days = (date_range.end_date - date_range.start_date).days
        if span_days < 1:
            return None

        midpoint = date_range.start_date + timedelta(days=span_days // 2)
        first_range = AnalyticsDateRange(
            date_range.start_date,
            midpoint,
            date_range.preset,
        )
        second_range = AnalyticsDateRange(
            midpoint + timedelta(days=1),
            date_range.end_date,
            date_range.preset,
        )

        first_totals = {
            row["collection_id"]: Decimal(row["units_sold"])  # type: ignore[index]
            for row in self.repo.fetch_collection_units_by_collection(first_range)
        }
        second_totals = {
            row["collection_id"]: Decimal(row["units_sold"])  # type: ignore[index]
            for row in self.repo.fetch_collection_units_by_collection(second_range)
        }

        best_id = None
        best_growth: Decimal | None = None
        best_name: str | None = None

        for collection_id, second_qty in second_totals.items():
            first_qty = first_totals.get(collection_id, Decimal("0"))
            if first_qty <= 0:
                continue
            growth = ((second_qty - first_qty) / first_qty) * Decimal("100")
            if best_growth is None or growth > best_growth:
                best_growth = growth
                best_id = collection_id
                for row in self.repo.fetch_collection_units_by_collection(second_range):
                    if row["collection_id"] == collection_id:  # type: ignore[operator]
                        best_name = str(row["collection_name_snapshot"])
                        break

        if best_id is None or best_growth is None or best_name is None:
            return None

        return {
            "collection_name_snapshot": best_name,
            "growth_label": f"+{best_growth.quantize(MONEY)}%",
        }

    @staticmethod
    def _format_margin_row(row: dict[str, object]) -> str:
        revenue = Decimal(row["revenue_snapshot"])  # type: ignore[index]
        profit = Decimal(row["profit_snapshot"])  # type: ignore[index]
        return f"{snapshot_margin_percentage(revenue, profit)}%"

    @staticmethod
    def _row(row: dict[str, object]) -> CollectionAnalyticsRow:
        revenue = Decimal(row["revenue_snapshot"]).quantize(MONEY)  # type: ignore[arg-type]
        profit = Decimal(row["profit_snapshot"]).quantize(MONEY)  # type: ignore[arg-type]
        units = Decimal(row["units_sold"])  # type: ignore[arg-type]
        avg_price = safe_divide(revenue, units) if units > 0 else Decimal("0.00")
        return CollectionAnalyticsRow(
            collection_id=row["collection_id"],  # type: ignore[arg-type]
            name=str(row["collection_name_snapshot"]),
            units_sold=units.quantize(QTY),
            revenue_snapshot=revenue,
            cost_snapshot=Decimal(row["cost_snapshot"]).quantize(MONEY),  # type: ignore[arg-type]
            profit_snapshot=profit,
            average_margin_percentage=snapshot_margin_percentage(revenue, profit),
            average_selling_price=avg_price,
            last_sold_date=to_optional_date(row.get("last_sold_at")),
        )
