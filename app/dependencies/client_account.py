"""Authenticated customer account dependencies."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.exceptions import ForbiddenError
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.customer import Customer
from app.models.user import User
from app.services.client_account_service import ClientAccountService
from app.services.customer_identity_service import CustomerIdentityService
from app.services.client_address_service import ClientAddressService
from app.services.client_order_history_service import ClientOrderHistoryService
from app.services.order_review_service import OrderReviewService


def get_current_customer_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role != UserRole.CUSTOMER:
        raise ForbiddenError("Customer access required")
    return current_user


def get_or_create_customer(
    current_user: Annotated[User, Depends(get_current_customer_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Customer:
    return CustomerIdentityService(db).ensure_customer_for_user(current_user)


def get_client_account_service(
    db: Annotated[Session, Depends(get_db)],
) -> ClientAccountService:
    return ClientAccountService(db)


def get_client_address_service(
    db: Annotated[Session, Depends(get_db)],
) -> ClientAddressService:
    return ClientAddressService(db)


def get_client_order_history_service(
    db: Annotated[Session, Depends(get_db)],
) -> ClientOrderHistoryService:
    return ClientOrderHistoryService(db)


def get_order_review_service(
    db: Annotated[Session, Depends(get_db)],
) -> OrderReviewService:
    return OrderReviewService(db)
