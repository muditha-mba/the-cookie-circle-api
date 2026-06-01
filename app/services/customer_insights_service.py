"""Customer insights and enriched list (analytics-ready)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.repositories.customer_insights_repository import CustomerInsightsRepository
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer_crm import (
    CustomerInsightsResponse,
    CustomerListItemResponse,
    CustomerListParams,
    CustomerOrderHistoryItem,
)
from app.schemas.pagination import PaginatedResponse
from app.services.customer_segmentation import (
    CustomerSegmentationConfig,
    calculate_customer_segment,
)


class CustomerInsightsService:
    """Calculate customer segments, spend, and favourites."""

    def __init__(
        self,
        db: Session,
        *,
        segmentation_config: CustomerSegmentationConfig | None = None,
    ) -> None:
        self.db = db
        self.customers = CustomerRepository(db)
        self.insights = CustomerInsightsRepository(db)
        self.segmentation_config = segmentation_config or CustomerSegmentationConfig()

    def get_insights(self, customer_id: uuid.UUID) -> CustomerInsightsResponse:
        customer = self.customers.get_by_id(customer_id)
        if not customer:
            raise NotFoundError("Customer not found")

        metrics = self.insights.get_metrics_for_customer(customer)
        segment = calculate_customer_segment(metrics, config=self.segmentation_config)
        avg_order = Decimal("0.00")
        if metrics.total_orders > 0:
            avg_order = (metrics.lifetime_spend / metrics.total_orders).quantize(
                Decimal("0.01"),
            )

        return CustomerInsightsResponse(
            lifetime_spend=metrics.lifetime_spend,
            total_orders=metrics.total_orders,
            average_order_value=avg_order,
            last_order_date=metrics.last_order_date,
            first_order_date=metrics.first_order_date,
            favourite_product=self.insights.get_favourite_product_name(customer_id),
            favourite_collection=self.insights.get_favourite_collection_name(customer_id),
            segment=segment,
            marketing_source=customer.marketing_source,
        )

    def list_customers(
        self,
        params: CustomerListParams,
    ) -> PaginatedResponse[CustomerListItemResponse]:
        rows, total = self.insights.list_customers_with_metrics(
            page=params.page,
            page_size=params.page_size,
            search=params.search,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
            segment=params.segment,
            marketing_source=params.marketing_source,
            min_order_count=params.min_order_count,
            max_order_count=params.max_order_count,
            min_lifetime_spend=params.min_lifetime_spend,
            max_lifetime_spend=params.max_lifetime_spend,
            config=self.segmentation_config,
        )
        return PaginatedResponse(
            items=[
                CustomerListItemResponse(
                    id=row.customer.id,
                    user_id=row.customer.user_id,
                    first_name=row.customer.first_name,
                    last_name=row.customer.last_name,
                    email=row.customer.email,
                    phone=row.customer.phone,
                    source=row.customer.source,
                    marketing_source=row.customer.marketing_source,
                    is_active=row.customer.is_active,
                    created_at=row.customer.created_at,
                    total_orders=row.total_orders,
                    lifetime_spend=row.lifetime_spend,
                    last_order_date=row.last_order_date,
                    segment=row.segment,
                )
                for row in rows
            ],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=self.insights.total_pages(total, params.page_size),
        )

    def get_order_history(
        self,
        customer_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[CustomerOrderHistoryItem]:
        if not self.customers.get_by_id(customer_id):
            raise NotFoundError("Customer not found")
        orders = self.insights.list_orders_for_customer(customer_id, limit=limit)
        return [CustomerOrderHistoryItem.model_validate(order) for order in orders]

    def get_segmentation_config(self) -> CustomerSegmentationConfig:
        """Expose thresholds for future analytics or admin settings."""
        return self.segmentation_config
