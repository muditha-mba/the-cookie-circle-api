"""Product analytics from order line snapshots."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsQueryParams,
    ProductAnalyticsInsightItem,
    ProductAnalyticsInsightsResponse,
    ProductAnalyticsKpiResponse,
    ProductAnalyticsRow,
    RankedProductsResponse,
)
from app.services.analytics._common import (
    date_range_response,
    snapshot_margin_percentage,
    to_optional_date,
)
from app.utils.analytics_date_range import resolve_analytics_date_range


class AnalyticsProductService:
    """Product demand and profitability rankings."""

    def __init__(self, db: Session) -> None:
        self.repo = AnalyticsRepository(db)

    def get_most_ordered(self, params: AnalyticsQueryParams) -> RankedProductsResponse:
        return self._ranked(params, order_by="units", ascending=False)

    def get_most_profitable(self, params: AnalyticsQueryParams) -> RankedProductsResponse:
        return self._ranked(params, order_by="profit", ascending=False)

    def get_least_ordered(self, params: AnalyticsQueryParams) -> RankedProductsResponse:
        return self._ranked(params, order_by="units", ascending=True)

    def get_performance(self, params: AnalyticsQueryParams) -> RankedProductsResponse:
        return self._ranked(params, order_by="units", ascending=False)

    def get_kpis(self, params: AnalyticsQueryParams) -> ProductAnalyticsKpiResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        most_ordered = self.repo.fetch_product_rankings(
            date_range, limit=1, order_by="units", ascending=False
        )
        most_profitable = self.repo.fetch_product_rankings(
            date_range, limit=1, order_by="profit", ascending=False
        )
        most_ordered_collection = self.repo.fetch_collection_rankings(
            date_range, limit=1, order_by="units", ascending=False
        )
        most_profitable_collection = self.repo.fetch_collection_rankings(
            date_range, limit=1, order_by="profit", ascending=False
        )
        return ProductAnalyticsKpiResponse(
            date_range=date_range_response(date_range),
            most_ordered_product_name=(
                str(most_ordered[0]["product_name_snapshot"]) if most_ordered else None
            ),
            most_profitable_product_name=(
                str(most_profitable[0]["product_name_snapshot"]) if most_profitable else None
            ),
            most_ordered_collection_name=(
                str(most_ordered_collection[0]["collection_name_snapshot"])
                if most_ordered_collection
                else None
            ),
            most_profitable_collection_name=(
                str(most_profitable_collection[0]["collection_name_snapshot"])
                if most_profitable_collection
                else None
            ),
            total_products_sold=self.repo.fetch_total_product_units_sold(date_range),
            total_collections_sold=self.repo.fetch_total_collection_units_sold(date_range),
        )

    def get_insights(self, params: AnalyticsQueryParams) -> ProductAnalyticsInsightsResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )

        def top_product(order_by: str) -> ProductAnalyticsRow | None:
            rows = self.repo.fetch_product_rankings(
                date_range, limit=1, order_by=order_by, ascending=False
            )
            return self._row(rows[0]) if rows else None

        def top_collection(order_by: str) -> dict[str, object] | None:
            rows = self.repo.fetch_collection_rankings(
                date_range, limit=1, order_by=order_by, ascending=False
            )
            return rows[0] if rows else None

        revenue_product = top_product("revenue")
        profit_product = top_product("profit")
        margin_product = top_product("margin")
        fastest_product = top_product("units")
        revenue_collection = top_collection("revenue")
        profit_collection = top_collection("profit")

        def product_insight(
            insight_id: str,
            title: str,
            row: ProductAnalyticsRow | None,
            metric_label: str,
            formatter,
        ) -> ProductAnalyticsInsightItem:
            return ProductAnalyticsInsightItem(
                id=insight_id,
                title=title,
                entity_type="product",
                name=row.name if row else None,
                metric_label=metric_label,
                metric_value=formatter(row) if row else "—",
            )

        def collection_insight(
            insight_id: str,
            title: str,
            row: dict[str, object] | None,
            metric_label: str,
            formatter,
        ) -> ProductAnalyticsInsightItem:
            name = str(row["collection_name_snapshot"]) if row else None
            return ProductAnalyticsInsightItem(
                id=insight_id,
                title=title,
                entity_type="collection",
                name=name,
                metric_label=metric_label,
                metric_value=formatter(row) if row else "—",
            )

        items = [
            product_insight(
                "highest_revenue_product",
                "Highest Revenue Product",
                revenue_product,
                "Revenue",
                lambda r: f"Rs {r.revenue_snapshot:,.2f}",
            ),
            product_insight(
                "highest_profit_product",
                "Highest Profit Product",
                profit_product,
                "Profit",
                lambda r: f"Rs {r.profit_snapshot:,.2f}",
            ),
            product_insight(
                "highest_margin_product",
                "Highest Margin Product",
                margin_product,
                "Margin",
                lambda r: f"{r.average_margin_percentage}%",
            ),
            product_insight(
                "fastest_moving_product",
                "Fastest Moving Product",
                fastest_product,
                "Units sold",
                lambda r: f"{r.units_sold.normalize():g}",
            ),
            collection_insight(
                "highest_revenue_collection",
                "Highest Revenue Collection",
                revenue_collection,
                "Revenue",
                lambda r: f"Rs {Decimal(r['revenue_snapshot']):,.2f}",  # type: ignore[index]
            ),
            collection_insight(
                "highest_profit_collection",
                "Highest Profit Collection",
                profit_collection,
                "Profit",
                lambda r: f"Rs {Decimal(r['profit_snapshot']):,.2f}",  # type: ignore[index]
            ),
        ]
        return ProductAnalyticsInsightsResponse(
            date_range=date_range_response(date_range),
            items=items,
        )

    def _ranked(
        self,
        params: AnalyticsQueryParams,
        *,
        order_by: str,
        ascending: bool,
    ) -> RankedProductsResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        rows = self.repo.fetch_product_rankings(
            date_range,
            limit=params.limit,
            order_by=order_by,
            ascending=ascending,
        )
        return RankedProductsResponse(
            date_range=date_range_response(date_range),
            items=[self._row(item) for item in rows],
        )

    @staticmethod
    def _row(item: dict[str, object]) -> ProductAnalyticsRow:
        revenue = Decimal(item["revenue_snapshot"]).quantize(Decimal("0.01"))  # type: ignore[arg-type]
        profit = Decimal(item["profit_snapshot"]).quantize(Decimal("0.01"))  # type: ignore[arg-type]
        return ProductAnalyticsRow(
            product_id=item["product_id"],  # type: ignore[arg-type]
            name=str(item["product_name_snapshot"]),
            units_sold=Decimal(item["units_sold"]),  # type: ignore[arg-type]
            revenue_snapshot=revenue,
            cost_snapshot=Decimal(item["cost_snapshot"]).quantize(Decimal("0.01")),  # type: ignore[arg-type]
            profit_snapshot=profit,
            average_margin_percentage=snapshot_margin_percentage(revenue, profit),
            last_sold_date=to_optional_date(item.get("last_sold_at")),
        )
