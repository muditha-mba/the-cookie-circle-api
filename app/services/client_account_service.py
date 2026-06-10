"""Authenticated customer profile and dashboard."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import OrderStatus, UserRole
from app.core.exceptions import AuthError, ValidationError
from app.core.security import hash_password, verify_password
from app.models.customer import Customer
from app.models.order import Order
from app.models.order_collection_line import OrderCollectionLine
from app.models.order_product_line import OrderProductLine
from app.models.order_review import OrderReview
from app.models.user import User
from app.repositories.customer_insights_repository import CustomerInsightsRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.user_repository import UserRepository
from app.schemas.client_account import (
    ChangePasswordRequest,
    ClientAccountDashboardResponse,
    ClientAccountProfileResponse,
    ClientAccountProfileUpdate,
)
from app.services.client_order_history_service import ClientOrderHistoryService


class ClientAccountService:
    """Customer self-service profile and dashboard."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.customers = CustomerRepository(db)
        self.users = UserRepository(db)
        self.orders = OrderRepository(db)
        self.insights = CustomerInsightsRepository(db)
        self.order_history = ClientOrderHistoryService(db)

    def get_profile(self, customer: Customer, user: User) -> ClientAccountProfileResponse:
        return ClientAccountProfileResponse(
            customer_id=customer.id,
            user_id=user.id,
            first_name=customer.first_name,
            last_name=customer.last_name,
            email=user.email,
            phone=customer.phone,
            phone_secondary=customer.phone_secondary,
            preferred_delivery_area=customer.city,
            member_since=user.created_at,
            email_verified=user.email_verified,
        )

    def update_profile(
        self,
        customer: Customer,
        user: User,
        payload: ClientAccountProfileUpdate,
    ) -> ClientAccountProfileResponse:
        customer.first_name = payload.first_name
        customer.last_name = payload.last_name
        customer.phone = payload.phone.strip()
        customer.phone_secondary = payload.phone_secondary
        if "preferred_delivery_area" in payload.model_fields_set:
            customer.city = payload.preferred_delivery_area
        user.first_name = payload.first_name
        user.last_name = payload.last_name
        self.db.commit()
        self.db.refresh(customer)
        self.db.refresh(user)
        return self.get_profile(customer, user)

    def change_password(self, user: User, payload: ChangePasswordRequest) -> None:
        if user.role != UserRole.CUSTOMER:
            raise AuthError("Invalid account type")
        if not verify_password(payload.current_password, user.password_hash):
            raise ValidationError("Current password is incorrect")
        user.password_hash = hash_password(payload.new_password)
        self.db.commit()

    def get_dashboard(self, customer: Customer, user: User) -> ClientAccountDashboardResponse:
        metrics = self.insights.get_metrics_for_customer(customer)

        status_counts = dict(
            self.db.execute(
                select(Order.status, func.count(Order.id))
                .where(Order.customer_id == customer.id)
                .group_by(Order.status),
            ).all(),
        )
        completed_orders = int(status_counts.get(OrderStatus.DELIVERED, 0))
        pending_statuses = {
            OrderStatus.PENDING,
            OrderStatus.CONFIRMED,
            OrderStatus.PREPARING,
            OrderStatus.READY,
        }
        pending_orders = sum(
            int(status_counts.get(status, 0)) for status in pending_statuses
        )

        cookie_count = int(
            self.db.scalar(
                select(func.coalesce(func.sum(OrderProductLine.quantity), 0))
                .join(Order, OrderProductLine.order_id == Order.id)
                .where(Order.customer_id == customer.id),
            )
            or 0,
        )
        from app.models.order_collection_line_selection import OrderCollectionLineSelection

        collection_count = int(
            self.db.scalar(
                select(func.count(OrderCollectionLine.id))
                .join(Order, OrderCollectionLine.order_id == Order.id)
                .where(Order.customer_id == customer.id),
            )
            or 0,
        )
        selection_cookie_count = int(
            self.db.scalar(
                select(func.coalesce(func.sum(OrderCollectionLineSelection.quantity), 0))
                .join(
                    OrderCollectionLine,
                    OrderCollectionLineSelection.order_collection_line_id == OrderCollectionLine.id,
                )
                .join(Order, OrderCollectionLine.order_id == Order.id)
                .where(Order.customer_id == customer.id),
            )
            or 0,
        )

        total_reviews = int(
            self.db.scalar(
                select(func.count(OrderReview.id)).where(
                    OrderReview.customer_id == customer.id,
                ),
            )
            or 0,
        )

        recent_orders, _ = self.order_history.list_orders(
            customer,
            page=1,
            page_size=5,
            search=None,
            status=None,
            order_type=None,
            sort_by="created_at",
            sort_order="desc",
        )

        return ClientAccountDashboardResponse(
            first_name=customer.first_name,
            member_since=user.created_at,
            email=user.email,
            preferred_delivery_area=customer.city,
            total_orders=metrics.total_orders,
            completed_orders=completed_orders,
            pending_orders=pending_orders,
            total_cookies_ordered=cookie_count + selection_cookie_count,
            total_collections_ordered=collection_count,
            total_reviews=total_reviews,
            favourite_cookie=self.insights.get_favourite_product_name(customer.id),
            favourite_package_type=self.insights.get_favourite_collection_name(customer.id),
            recent_orders=recent_orders,
        )
