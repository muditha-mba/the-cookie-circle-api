"""Production analytics using planning services and order snapshots."""

import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsQueryParams,
    BatchVolumePoint,
    BatchVolumeTrendsResponse,
    DemandTrendPoint,
    IngredientDemandTrendsResponse,
    PackagingDemandTrendsResponse,
    ProductionAnalyticsInsightItem,
    ProductionAnalyticsInsightsResponse,
    ProductionAnalyticsKpiResponse,
    ProductionDemandItemRow,
    ProductionDemandListResponse,
    ProductionVolumePoint,
    ProductionVolumeResponse,
)
from app.services.analytics._common import (
    date_range_response,
    previous_period,
    safe_divide,
    trend_delta_percentage,
)
from app.services.production_planning_service import (
    IngredientDemand,
    PackagingDemand,
    ProductionPlanningService,
)
from app.services.analytics.analytics_production_date_range import (
    resolve_production_analytics_date_range,
)
from app.utils.analytics_date_range import AnalyticsDateRange, TrendGranularity

MONEY = Decimal("0.01")
QTY = Decimal("0.0001")


class AnalyticsProductionService:
    """Production volume and demand trend analytics."""

    def __init__(self, db: Session) -> None:
        self.repo = AnalyticsRepository(db)
        self.production = ProductionPlanningService(db)

    def get_production_volume(
        self,
        params: AnalyticsQueryParams,
    ) -> ProductionVolumeResponse:
        date_range = resolve_production_analytics_date_range(self.repo, params)
        rows = self.repo.fetch_production_volume_by_delivery(
            date_range,
            params.granularity,
        )
        return ProductionVolumeResponse(
            date_range=date_range_response(date_range),
            granularity=params.granularity,
            points=[
                ProductionVolumePoint(
                    period_start=period,
                    total_products=products,
                    total_collections=collections,
                    order_count=orders,
                )
                for period, products, collections, orders in rows
            ],
        )

    def get_batch_volume_trends(
        self,
        params: AnalyticsQueryParams,
    ) -> BatchVolumeTrendsResponse:
        date_range = resolve_production_analytics_date_range(self.repo, params)
        rows = self.repo.fetch_batch_volume(date_range)
        return BatchVolumeTrendsResponse(
            date_range=date_range_response(date_range),
            points=[
                BatchVolumePoint(
                    delivery_date=delivery_date,
                    order_count=count,
                    total_revenue_snapshot=revenue,
                )
                for delivery_date, count, revenue in rows
            ],
        )

    def get_ingredient_demand_trends(
        self,
        params: AnalyticsQueryParams,
    ) -> IngredientDemandTrendsResponse:
        return self._demand_trends(params, ingredient=True)

    def get_packaging_demand_trends(
        self,
        params: AnalyticsQueryParams,
    ) -> PackagingDemandTrendsResponse:
        response = self._demand_trends(params, ingredient=False)
        return PackagingDemandTrendsResponse(
            date_range=response.date_range,
            granularity=response.granularity,
            points=response.points,
        )

    def get_kpis(self, params: AnalyticsQueryParams) -> ProductionAnalyticsKpiResponse:
        date_range = resolve_production_analytics_date_range(self.repo, params)
        day_params = params.model_copy(update={"granularity": TrendGranularity.DAY})
        volume = self.get_production_volume(day_params)
        total_products = sum((point.total_products for point in volume.points), Decimal("0"))
        total_collections = sum(
            (point.total_collections for point in volume.points),
            Decimal("0"),
        )
        ingredients = self._aggregate_demand(date_range, ingredient=True)
        packaging = self._aggregate_demand(date_range, ingredient=False)
        ingredient_cost = sum((row.estimated_cost for row in ingredients), Decimal("0"))
        packaging_cost = sum((row.estimated_cost for row in packaging), Decimal("0"))

        batches = self.repo.fetch_batch_volume(date_range)
        batch_count = len(batches)
        total_orders = sum(count for _, count, _ in batches)
        avg_batch = safe_divide(Decimal(total_orders), batch_count) if batch_count else Decimal("0")

        prev_range = previous_period(date_range)
        prev_params = params.model_copy(
            update={
                "preset": None,
                "start_date": prev_range.start_date,
                "end_date": prev_range.end_date,
            },
        )
        prev_volume = self.get_production_volume(prev_params)
        prev_total_products = sum((point.total_products for point in prev_volume.points), Decimal("0"))
        prev_total_collections = sum(
            (point.total_collections for point in prev_volume.points),
            Decimal("0"),
        )
        prev_ingredients = self._aggregate_demand(prev_range, ingredient=True)
        prev_packaging = self._aggregate_demand(prev_range, ingredient=False)
        prev_ingredient_cost = sum((row.estimated_cost for row in prev_ingredients), Decimal("0"))
        prev_packaging_cost = sum((row.estimated_cost for row in prev_packaging), Decimal("0"))
        prev_batches = self.repo.fetch_batch_volume(prev_range)
        prev_batch_count = len(prev_batches)
        prev_total_orders = sum(count for _, count, _ in prev_batches)
        prev_avg_batch = (
            safe_divide(Decimal(prev_total_orders), prev_batch_count)
            if prev_batch_count
            else Decimal("0")
        )

        def metric(current: Decimal, previous: Decimal):
            trend_pct, trend_dir = trend_delta_percentage(current, previous)
            return {
                "value": current,
                "trend_percentage": trend_pct,
                "trend_direction": trend_dir,
            }

        return ProductionAnalyticsKpiResponse(
            date_range=date_range_response(date_range),
            total_products_produced=metric(
                total_products.quantize(QTY),
                prev_total_products.quantize(QTY),
            ),
            total_collections_produced=metric(
                total_collections.quantize(QTY),
                prev_total_collections.quantize(QTY),
            ),
            total_ingredient_consumption_cost=metric(
                ingredient_cost.quantize(MONEY),
                prev_ingredient_cost.quantize(MONEY),
            ),
            total_packaging_consumption_cost=metric(
                packaging_cost.quantize(MONEY),
                prev_packaging_cost.quantize(MONEY),
            ),
            total_production_batches=metric(
                Decimal(batch_count),
                Decimal(prev_batch_count),
            ),
            average_batch_size=metric(avg_batch, prev_avg_batch),
        )

    def get_ingredient_summary(self, params: AnalyticsQueryParams) -> ProductionDemandListResponse:
        return self._demand_summary(params, ingredient=True)

    def get_packaging_summary(self, params: AnalyticsQueryParams) -> ProductionDemandListResponse:
        return self._demand_summary(params, ingredient=False)

    def get_insights(self, params: AnalyticsQueryParams) -> ProductionAnalyticsInsightsResponse:
        date_range = resolve_production_analytics_date_range(self.repo, params)
        ingredients = self._aggregate_demand(date_range, ingredient=True)
        packaging = self._aggregate_demand(date_range, ingredient=False)
        batches = self.repo.fetch_batch_volume(date_range)

        top_ingredient = max(ingredients, key=lambda row: row.total_quantity, default=None)
        top_packaging = max(packaging, key=lambda row: row.total_quantity, default=None)
        largest_batch = max(batches, key=lambda item: item[1], default=None) if batches else None

        fastest_ingredient = self._fastest_growing_item(date_range, ingredient=True)
        fastest_packaging = self._fastest_growing_item(date_range, ingredient=False)

        items = [
            ProductionAnalyticsInsightItem(
                id="most_consumed_ingredient",
                title="Most Consumed Ingredient",
                name=top_ingredient.item_name if top_ingredient else None,
                metric_label="Quantity",
                metric_value=(
                    f"{top_ingredient.total_quantity.normalize()} {top_ingredient.unit}"
                    if top_ingredient
                    else "—"
                ),
            ),
            ProductionAnalyticsInsightItem(
                id="most_consumed_packaging",
                title="Most Consumed Packaging Item",
                name=top_packaging.item_name if top_packaging else None,
                metric_label="Quantity",
                metric_value=(
                    f"{top_packaging.total_quantity.normalize()} {top_packaging.unit}"
                    if top_packaging
                    else "—"
                ),
            ),
            ProductionAnalyticsInsightItem(
                id="largest_production_batch",
                title="Largest Production Batch",
                name=(
                    largest_batch[0].isoformat()
                    if largest_batch
                    else None
                ),
                metric_label="Orders",
                metric_value=str(largest_batch[1]) if largest_batch else "—",
            ),
            ProductionAnalyticsInsightItem(
                id="fastest_growing_ingredient",
                title="Fastest Growing Ingredient Demand",
                name=fastest_ingredient[0] if fastest_ingredient else None,
                metric_label="Growth",
                metric_value=fastest_ingredient[1] if fastest_ingredient else "—",
            ),
            ProductionAnalyticsInsightItem(
                id="fastest_growing_packaging",
                title="Fastest Growing Packaging Demand",
                name=fastest_packaging[0] if fastest_packaging else None,
                metric_label="Growth",
                metric_value=fastest_packaging[1] if fastest_packaging else "—",
            ),
        ]
        return ProductionAnalyticsInsightsResponse(
            date_range=date_range_response(date_range),
            items=items,
        )

    def _demand_summary(
        self,
        params: AnalyticsQueryParams,
        *,
        ingredient: bool,
    ) -> ProductionDemandListResponse:
        date_range = resolve_production_analytics_date_range(self.repo, params)
        items = self._aggregate_demand(date_range, ingredient=ingredient)
        items.sort(key=lambda row: row.total_quantity, reverse=True)
        return ProductionDemandListResponse(
            date_range=date_range_response(date_range),
            items=items[: params.limit],
        )

    def _aggregate_demand(
        self,
        date_range: AnalyticsDateRange,
        *,
        ingredient: bool,
    ) -> list[ProductionDemandItemRow]:
        aggregates: dict[uuid.UUID, dict[str, object]] = {}

        for delivery_date in self.repo.list_distinct_delivery_dates(date_range):
            try:
                if ingredient:
                    lines: list[IngredientDemand] | list[PackagingDemand] = (
                        self.production.get_ingredient_demand(delivery_date)
                    )
                else:
                    lines = self.production.get_packaging_demand(delivery_date)
            except ValidationError:
                continue

            for line in lines:
                key = line.product_item_id
                existing = aggregates.get(key)
                if not existing:
                    aggregates[key] = {
                        "item_name": line.product_item_name,
                        "total_quantity": line.quantity,
                        "unit": line.unit,
                        "estimated_cost": line.estimated_cost,
                        "last_used_date": delivery_date,
                    }
                    continue
                existing["total_quantity"] = (
                    Decimal(existing["total_quantity"]) + line.quantity  # type: ignore[operator]
                )
                existing["estimated_cost"] = (
                    Decimal(existing["estimated_cost"]) + line.estimated_cost  # type: ignore[operator]
                )
                last_used = existing["last_used_date"]
                if last_used is None or delivery_date > last_used:  # type: ignore[operator]
                    existing["last_used_date"] = delivery_date

        return [
            ProductionDemandItemRow(
                product_item_id=key,
                item_name=str(data["item_name"]),
                total_quantity=Decimal(data["total_quantity"]).quantize(QTY),  # type: ignore[arg-type]
                unit=str(data["unit"]),
                estimated_cost=Decimal(data["estimated_cost"]).quantize(MONEY),  # type: ignore[arg-type]
                last_used_date=data["last_used_date"],  # type: ignore[arg-type]
            )
            for key, data in aggregates.items()
        ]

    def _fastest_growing_item(
        self,
        date_range: AnalyticsDateRange,
        *,
        ingredient: bool,
    ) -> tuple[str, str] | None:
        dates = self.repo.list_distinct_delivery_dates(date_range)
        if len(dates) < 2:
            return None

        midpoint = len(dates) // 2
        first_dates = dates[:midpoint]
        second_dates = dates[midpoint:]

        first_totals = self._demand_totals_for_dates(first_dates, ingredient=ingredient)
        second_totals = self._demand_totals_for_dates(second_dates, ingredient=ingredient)

        best_name: str | None = None
        best_growth: Decimal | None = None
        for item_id, second_qty in second_totals.items():
            first_qty = first_totals.get(item_id, Decimal("0"))
            if first_qty <= 0:
                continue
            growth = ((second_qty - first_qty) / first_qty) * Decimal("100")
            if best_growth is None or growth > best_growth:
                best_growth = growth
                best_name = self._item_name_for_id(item_id, date_range, ingredient=ingredient)

        if best_name is None or best_growth is None:
            return None
        return best_name, f"+{best_growth.quantize(MONEY)}%"

    def _demand_totals_for_dates(
        self,
        dates: list[date],
        *,
        ingredient: bool,
    ) -> dict[uuid.UUID, Decimal]:
        totals: dict[uuid.UUID, Decimal] = defaultdict(lambda: Decimal("0"))
        for delivery_date in dates:
            try:
                lines = (
                    self.production.get_ingredient_demand(delivery_date)
                    if ingredient
                    else self.production.get_packaging_demand(delivery_date)
                )
            except ValidationError:
                continue
            for line in lines:
                totals[line.product_item_id] += line.quantity
        return totals

    def _item_name_for_id(
        self,
        item_id: uuid.UUID,
        date_range: AnalyticsDateRange,
        *,
        ingredient: bool,
    ) -> str:
        rows = self._aggregate_demand(date_range, ingredient=ingredient)
        for row in rows:
            if row.product_item_id == item_id:
                return row.item_name
        return "Unknown"

    def _demand_trends(
        self,
        params: AnalyticsQueryParams,
        *,
        ingredient: bool,
    ) -> IngredientDemandTrendsResponse:
        date_range = resolve_production_analytics_date_range(self.repo, params)
        delivery_dates = self.repo.list_distinct_delivery_dates(date_range)

        buckets: dict[date, dict[str, tuple[Decimal, str, Decimal, str]]] = defaultdict(dict)

        for delivery_date in delivery_dates:
            period = self._bucket_start(delivery_date, params.granularity)
            try:
                if ingredient:
                    lines = self.production.get_ingredient_demand(delivery_date)
                else:
                    lines = self.production.get_packaging_demand(delivery_date)
            except ValidationError:
                continue

            for line in lines:
                key = str(line.product_item_id)
                existing = buckets[period].get(key)
                qty = line.quantity
                cost = line.estimated_cost
                if existing:
                    qty = existing[0] + line.quantity
                    cost = existing[2] + line.estimated_cost
                buckets[period][key] = (qty, line.unit, cost, line.product_item_name)

        points: list[DemandTrendPoint] = []
        for period in sorted(buckets.keys()):
            for _, (qty, unit, cost, name) in buckets[period].items():
                points.append(
                    DemandTrendPoint(
                        period_start=period,
                        item_name=name,
                        quantity=qty.quantize(QTY),
                        unit=unit,
                        estimated_cost=cost.quantize(MONEY),
                    ),
                )

        return IngredientDemandTrendsResponse(
            date_range=date_range_response(date_range),
            granularity=params.granularity,
            points=points,
        )

    @staticmethod
    def _bucket_start(delivery_date: date, granularity: TrendGranularity) -> date:
        if granularity == TrendGranularity.DAY:
            return delivery_date
        if granularity == TrendGranularity.WEEK:
            return delivery_date - timedelta(days=delivery_date.weekday())
        return delivery_date.replace(day=1)
