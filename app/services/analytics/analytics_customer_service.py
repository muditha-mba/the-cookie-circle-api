"""Customer analytics using insights and snapshot data."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import CustomerSegment, MarketingSource
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.customer_insights_repository import CustomerInsightsRepository
from app.schemas.analytics import (
    AnalyticsQueryParams,
    CustomerAnalyticsInsightItem,
    CustomerAnalyticsInsightsResponse,
    CustomerAnalyticsKpiResponse,
    CustomerAnalyticsListResponse,
    CustomerAnalyticsRow,
    CustomerGrowthPoint,
    CustomerGrowthResponse,
    CustomerSegmentCount,
    CustomerSegmentSummaryResponse,
    MarketingSourcePerformanceResponse,
    MarketingSourcePerformanceRow,
)
from app.services.analytics._common import (
    date_range_response,
    previous_period,
    safe_divide,
    trend_delta_percentage,
)
from app.services.customer_segmentation import CustomerSegmentationConfig
from app.utils.analytics_date_range import resolve_analytics_date_range

MARKETING_SOURCE_LABELS: dict[MarketingSource, str] = {
    MarketingSource.INSTAGRAM: "Instagram",
    MarketingSource.FACEBOOK: "Facebook",
    MarketingSource.WHATSAPP: "WhatsApp",
    MarketingSource.TIKTOK: "TikTok",
    MarketingSource.LINKEDIN: "LinkedIn",
    MarketingSource.YOUTUBE: "YouTube",
    MarketingSource.TWITTER: "X / Twitter",
    MarketingSource.PINTEREST: "Pinterest",
    MarketingSource.EMAIL: "Email",
    MarketingSource.GOOGLE: "Google",
    MarketingSource.REFERRAL: "Referral",
    MarketingSource.WALK_IN: "Walk In",
    MarketingSource.OTHER: "Other",
}


class AnalyticsCustomerService:
    """Customer growth, segments, marketing performance, and dashboard KPIs."""

    def __init__(
        self,
        db: Session,
        *,
        segmentation_config: CustomerSegmentationConfig | None = None,
    ) -> None:
        self.repo = AnalyticsRepository(db)
        self.insights = CustomerInsightsRepository(db)
        self.segmentation_config = segmentation_config or CustomerSegmentationConfig()

    def get_customer_growth(self, params: AnalyticsQueryParams) -> CustomerGrowthResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        rows = self.repo.fetch_customer_growth(date_range, params.granularity)
        points = [
            CustomerGrowthPoint(period_start=period, new_customers=count)
            for period, count in rows
        ]
        return CustomerGrowthResponse(
            date_range=date_range_response(date_range),
            granularity=params.granularity,
            total_new_customers=sum(point.new_customers for point in points),
            points=points,
        )

    def get_segment_summary(
        self,
        params: AnalyticsQueryParams,
    ) -> CustomerSegmentSummaryResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        active = len(self.repo.fetch_active_customer_ids(date_range))
        counts = self.repo.count_customers_by_segment(
            date_range,
            self.segmentation_config,
        )

        segments = [
            CustomerSegmentCount(segment=segment, count=count)
            for segment, count in sorted(counts.items(), key=lambda item: item[0].value)
        ]
        for segment in CustomerSegment:
            if segment not in counts:
                segments.append(CustomerSegmentCount(segment=segment, count=0))

        return CustomerSegmentSummaryResponse(
            date_range=date_range_response(date_range),
            active_customers=active,
            segments=sorted(segments, key=lambda s: s.segment.value),
        )

    def get_marketing_source_performance(
        self,
        params: AnalyticsQueryParams,
    ) -> MarketingSourcePerformanceResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        rows = self.repo.fetch_marketing_source_performance(date_range)
        by_source: dict[MarketingSource | None, dict[str, object]] = {
            row["marketing_source"]: row for row in rows  # type: ignore[misc]
        }

        items: list[MarketingSourcePerformanceRow] = []
        for source in MarketingSource:
            row = by_source.get(source)
            if row:
                items.append(self._marketing_row(source, row))
            else:
                items.append(
                    MarketingSourcePerformanceRow(
                        marketing_source=source,
                        label=MARKETING_SOURCE_LABELS[source],
                        customer_count=0,
                        order_count=0,
                        revenue_snapshot=Decimal("0.00"),
                        profit_snapshot=Decimal("0.00"),
                    ),
                )

        unspecified = by_source.get(None)
        if unspecified:
            items.append(self._marketing_row(None, unspecified))

        return MarketingSourcePerformanceResponse(
            date_range=date_range_response(date_range),
            items=items,
        )

    def get_kpis(self, params: AnalyticsQueryParams) -> CustomerAnalyticsKpiResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        prev_params = params.model_copy(
            update={
                "preset": None,
                "start_date": previous_period(date_range).start_date,
                "end_date": previous_period(date_range).end_date,
            },
        )
        growth = self.get_customer_growth(params)
        segment_summary = self.get_segment_summary(params)
        segment_map = {item.segment: item.count for item in segment_summary.segments}

        performance = self.repo.fetch_customers_performance_in_range(
            date_range,
            limit=min(params.limit, 500),
            config=self.segmentation_config,
        )
        if performance:
            spend_sum = sum(
                Decimal(row["lifetime_spend"])  # type: ignore[arg-type]
                for row in performance
            )
            avg_clv = safe_divide(spend_sum, len(performance))
        else:
            avg_clv = Decimal("0.00")

        prev_growth = self.get_customer_growth(prev_params)
        prev_segment_summary = self.get_segment_summary(prev_params)
        prev_segment_map = {item.segment: item.count for item in prev_segment_summary.segments}
        prev_performance = self.repo.fetch_customers_performance_in_range(
            previous_period(date_range),
            limit=min(params.limit, 500),
            config=self.segmentation_config,
        )
        if prev_performance:
            prev_spend_sum = sum(
                Decimal(row["lifetime_spend"])  # type: ignore[arg-type]
                for row in prev_performance
            )
            prev_avg_clv = safe_divide(prev_spend_sum, len(prev_performance))
        else:
            prev_avg_clv = Decimal("0.00")

        def metric(current: Decimal, previous: Decimal):
            trend_pct, trend_dir = trend_delta_percentage(current, previous)
            return {
                "value": current,
                "trend_percentage": trend_pct,
                "trend_direction": trend_dir,
            }

        current_total_customers = Decimal(self.repo.count_total_customers_as_of(date_range))
        prev_total_customers = Decimal(
            self.repo.count_total_customers_as_of(previous_period(date_range)),
        )

        return CustomerAnalyticsKpiResponse(
            date_range=date_range_response(date_range),
            total_customers=metric(current_total_customers, prev_total_customers),
            new_customers=metric(
                Decimal(growth.total_new_customers),
                Decimal(prev_growth.total_new_customers),
            ),
            returning_customers=metric(
                Decimal(segment_map.get(CustomerSegment.RETURNING, 0)),
                Decimal(prev_segment_map.get(CustomerSegment.RETURNING, 0)),
            ),
            vip_customers=metric(
                Decimal(segment_map.get(CustomerSegment.VIP, 0)),
                Decimal(prev_segment_map.get(CustomerSegment.VIP, 0)),
            ),
            inactive_customers=metric(
                Decimal(segment_map.get(CustomerSegment.INACTIVE, 0)),
                Decimal(prev_segment_map.get(CustomerSegment.INACTIVE, 0)),
            ),
            average_customer_lifetime_value=metric(avg_clv, prev_avg_clv),
        )

    def get_performance(self, params: AnalyticsQueryParams) -> CustomerAnalyticsListResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        rows = self.repo.fetch_customers_performance_in_range(
            date_range,
            limit=params.limit,
            config=self.segmentation_config,
        )
        return CustomerAnalyticsListResponse(
            date_range=date_range_response(date_range),
            items=[self._customer_row(row) for row in rows],
        )

    def get_insights(self, params: AnalyticsQueryParams) -> CustomerAnalyticsInsightsResponse:
        date_range = resolve_analytics_date_range(
            preset=params.preset,
            start_date=params.start_date,
            end_date=params.end_date,
        )

        source_growth = self.repo.fetch_new_customers_by_marketing_source(date_range)
        fastest_source = source_growth[0] if source_growth else None

        segment_totals = self.repo.fetch_segment_lifetime_spend_totals(
            date_range,
            self.segmentation_config,
        )
        highest_segment = (
            max(segment_totals.items(), key=lambda item: item[1])[0]
            if segment_totals
            else None
        )

        top_customers = self.repo.fetch_customers_performance_in_range(
            date_range,
            limit=1,
            config=self.segmentation_config,
        )
        top_customer = top_customers[0] if top_customers else None

        marketing = self.get_marketing_source_performance(params)
        best_channel = (
            max(marketing.items, key=lambda item: item.revenue_snapshot)
            if marketing.items
            else None
        )

        segment_summary = self.get_segment_summary(params)
        retention_segment = max(
            (
                item
                for item in segment_summary.segments
                if item.segment in (CustomerSegment.RETURNING, CustomerSegment.VIP)
            ),
            key=lambda item: item.count,
            default=None,
        )

        def segment_label(segment: CustomerSegment | None) -> str:
            if not segment:
                return "—"
            return segment.value.replace("_", " ").title()

        items = [
            CustomerAnalyticsInsightItem(
                id="fastest_growing_source",
                title="Fastest Growing Source",
                name=(
                    MARKETING_SOURCE_LABELS.get(
                        fastest_source[0],  # type: ignore[arg-type]
                        "Unspecified",
                    )
                    if fastest_source and fastest_source[0] is not None
                    else ("Unspecified" if fastest_source else None)
                ),
                metric_label="New customers",
                metric_value=str(fastest_source[1]) if fastest_source else "—",
            ),
            CustomerAnalyticsInsightItem(
                id="highest_value_segment",
                title="Highest Value Segment",
                name=segment_label(highest_segment),
                metric_label="Lifetime spend",
                metric_value=(
                    f"Rs {segment_totals[highest_segment]:,.2f}"
                    if highest_segment
                    else "—"
                ),
            ),
            CustomerAnalyticsInsightItem(
                id="most_valuable_customer",
                title="Most Valuable Customer",
                name=(
                    f"{top_customer['customer'].first_name} {top_customer['customer'].last_name}".strip()  # type: ignore[index]
                    if top_customer
                    else None
                ),
                metric_label="Lifetime spend",
                metric_value=(
                    f"Rs {Decimal(top_customer['lifetime_spend']):,.2f}"  # type: ignore[index]
                    if top_customer
                    else "—"
                ),
            ),
            CustomerAnalyticsInsightItem(
                id="best_acquisition_channel",
                title="Best Performing Acquisition Channel",
                name=best_channel.label if best_channel else None,
                metric_label="Revenue",
                metric_value=(
                    f"Rs {best_channel.revenue_snapshot:,.2f}" if best_channel else "—"
                ),
            ),
            CustomerAnalyticsInsightItem(
                id="highest_retention_segment",
                title="Highest Retention Segment",
                name=segment_label(retention_segment.segment if retention_segment else None),
                metric_label="Active customers",
                metric_value=str(retention_segment.count) if retention_segment else "—",
            ),
        ]
        return CustomerAnalyticsInsightsResponse(
            date_range=date_range_response(date_range),
            items=items,
        )

    @staticmethod
    def _marketing_row(
        source: MarketingSource | None,
        row: dict[str, object],
    ) -> MarketingSourcePerformanceRow:
        label = (
            MARKETING_SOURCE_LABELS.get(source, "Unspecified")
            if source is not None
            else "Unspecified"
        )
        return MarketingSourcePerformanceRow(
            marketing_source=source,
            label=label,
            customer_count=int(row["customer_count"]),  # type: ignore[arg-type]
            order_count=int(row["order_count"]),  # type: ignore[arg-type]
            revenue_snapshot=Decimal(row["revenue_snapshot"]).quantize(Decimal("0.01")),  # type: ignore[arg-type]
            profit_snapshot=Decimal(row["profit_snapshot"]).quantize(Decimal("0.01")),  # type: ignore[arg-type]
        )

    @staticmethod
    def _customer_row(row: dict[str, object]) -> CustomerAnalyticsRow:
        customer = row["customer"]
        from app.models.customer import Customer

        if not isinstance(customer, Customer):
            raise TypeError("Expected Customer")
        return CustomerAnalyticsRow(
            customer_id=customer.id,
            customer_name=f"{customer.first_name} {customer.last_name}".strip(),
            total_orders=int(row["total_orders"]),  # type: ignore[arg-type]
            lifetime_spend=Decimal(row["lifetime_spend"]).quantize(Decimal("0.01")),  # type: ignore[arg-type]
            average_order_value=Decimal(row["average_order_value"]).quantize(Decimal("0.01")),  # type: ignore[arg-type]
            last_order_date=row["last_order_date"],  # type: ignore[arg-type]
            segment=row["segment"],  # type: ignore[arg-type]
            marketing_source=row["marketing_source"],  # type: ignore[arg-type]
        )
