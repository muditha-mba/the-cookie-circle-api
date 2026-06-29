"""Authenticated customer account routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.client_account import (
    get_client_account_service,
    get_client_address_service,
    get_client_order_history_service,
    get_current_customer_user,
    get_or_create_customer,
    get_order_review_service,
)
from app.models.customer import Customer
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.client_account import (
    ChangePasswordRequest,
    ClientAccountAddressCreate,
    ClientAccountAddressResponse,
    ClientAccountAddressUpdate,
    ClientAccountDashboardResponse,
    ClientAccountOrderDetailResponse,
    ClientAccountOrderListParams,
    ClientAccountOrderSummary,
    ClientAccountProfileResponse,
    ClientAccountProfileUpdate,
)
from app.schemas.pagination import PaginatedResponse
from app.services.client_account_service import ClientAccountService
from app.services.client_address_service import ClientAddressService
from app.services.client_order_history_service import ClientOrderHistoryService
from app.schemas.order_review import (
    OrderReviewCreate,
    OrderReviewResponse,
    OrderReviewUpdate,
    ReviewTagCatalogResponse,
    ReviewableOrderSummary,
)
from app.services.order_review_service import OrderReviewService

router = APIRouter(prefix="/client/account", tags=["Client Account"])


@router.get("/dashboard", response_model=ClientAccountDashboardResponse)
def get_dashboard(
    customer: Annotated[Customer, Depends(get_or_create_customer)],
    user: Annotated[User, Depends(get_current_customer_user)],
    service: Annotated[ClientAccountService, Depends(get_client_account_service)],
) -> ClientAccountDashboardResponse:
    return service.get_dashboard(customer, user)


@router.get("/profile", response_model=ClientAccountProfileResponse)
def get_profile(
    customer: Annotated[Customer, Depends(get_or_create_customer)],
    user: Annotated[User, Depends(get_current_customer_user)],
    service: Annotated[ClientAccountService, Depends(get_client_account_service)],
) -> ClientAccountProfileResponse:
    return service.get_profile(customer, user)


@router.patch("/profile", response_model=ClientAccountProfileResponse)
def update_profile(
    payload: ClientAccountProfileUpdate,
    customer: Annotated[Customer, Depends(get_or_create_customer)],
    user: Annotated[User, Depends(get_current_customer_user)],
    service: Annotated[ClientAccountService, Depends(get_client_account_service)],
) -> ClientAccountProfileResponse:
    return service.update_profile(customer, user, payload)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    user: Annotated[User, Depends(get_current_customer_user)],
    service: Annotated[ClientAccountService, Depends(get_client_account_service)],
) -> MessageResponse:
    service.change_password(user, payload)
    return MessageResponse(message="Password updated successfully.")


@router.get("/addresses", response_model=list[ClientAccountAddressResponse])
def list_addresses(
    customer: Annotated[Customer, Depends(get_or_create_customer)],
    service: Annotated[ClientAddressService, Depends(get_client_address_service)],
) -> list[ClientAccountAddressResponse]:
    return service.list_addresses(customer)


@router.post(
    "/addresses",
    response_model=ClientAccountAddressResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_address(
    payload: ClientAccountAddressCreate,
    customer: Annotated[Customer, Depends(get_or_create_customer)],
    service: Annotated[ClientAddressService, Depends(get_client_address_service)],
) -> ClientAccountAddressResponse:
    return service.create_address(customer, payload)


@router.patch("/addresses/{address_id}", response_model=ClientAccountAddressResponse)
def update_address(
    address_id: uuid.UUID,
    payload: ClientAccountAddressUpdate,
    customer: Annotated[Customer, Depends(get_or_create_customer)],
    service: Annotated[ClientAddressService, Depends(get_client_address_service)],
) -> ClientAccountAddressResponse:
    return service.update_address(customer, address_id, payload)


@router.delete("/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(
    address_id: uuid.UUID,
    customer: Annotated[Customer, Depends(get_or_create_customer)],
    service: Annotated[ClientAddressService, Depends(get_client_address_service)],
) -> None:
    service.delete_address(customer, address_id)


@router.post("/addresses/{address_id}/default", response_model=ClientAccountAddressResponse)
def set_default_address(
    address_id: uuid.UUID,
    customer: Annotated[Customer, Depends(get_or_create_customer)],
    service: Annotated[ClientAddressService, Depends(get_client_address_service)],
) -> ClientAccountAddressResponse:
    return service.set_default(customer, address_id)


@router.get("/orders", response_model=PaginatedResponse[ClientAccountOrderSummary])
def list_orders(
    customer: Annotated[Customer, Depends(get_or_create_customer)],
    service: Annotated[ClientOrderHistoryService, Depends(get_client_order_history_service)],
    params: Annotated[ClientAccountOrderListParams, Query()],
) -> PaginatedResponse[ClientAccountOrderSummary]:
    return service.list_orders_paginated(
        customer,
        page=params.page,
        page_size=params.page_size,
        search=params.search,
        status=params.status,
        order_type=params.order_type,
        sort_by=params.sort_by,
        sort_order=params.sort_order,
    )


@router.get("/orders/{order_id}", response_model=ClientAccountOrderDetailResponse)
def get_order_detail(
    order_id: uuid.UUID,
    customer: Annotated[Customer, Depends(get_or_create_customer)],
    service: Annotated[ClientOrderHistoryService, Depends(get_client_order_history_service)],
) -> ClientAccountOrderDetailResponse:
    return service.get_order_detail(customer, order_id)


@router.get("/reviews/tags", response_model=ReviewTagCatalogResponse)
def get_review_tags(
    _: Annotated[Customer, Depends(get_or_create_customer)],
    service: Annotated[OrderReviewService, Depends(get_order_review_service)],
) -> ReviewTagCatalogResponse:
    return service.get_tag_catalog()


@router.get("/reviews", response_model=list[OrderReviewResponse])
def list_reviews(
    customer: Annotated[Customer, Depends(get_or_create_customer)],
    service: Annotated[OrderReviewService, Depends(get_order_review_service)],
) -> list[OrderReviewResponse]:
    return service.list_reviews(customer)


@router.get("/reviews/reviewable", response_model=list[ReviewableOrderSummary])
def list_reviewable_orders(
    customer: Annotated[Customer, Depends(get_or_create_customer)],
    service: Annotated[OrderReviewService, Depends(get_order_review_service)],
) -> list[ReviewableOrderSummary]:
    return service.list_reviewable_orders(customer)


@router.get("/reviews/{review_id}", response_model=OrderReviewResponse)
def get_review(
    review_id: uuid.UUID,
    customer: Annotated[Customer, Depends(get_or_create_customer)],
    service: Annotated[OrderReviewService, Depends(get_order_review_service)],
) -> OrderReviewResponse:
    return service.get_review(customer, review_id)


@router.post(
    "/reviews",
    response_model=OrderReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_review(
    payload: OrderReviewCreate,
    customer: Annotated[Customer, Depends(get_or_create_customer)],
    service: Annotated[OrderReviewService, Depends(get_order_review_service)],
) -> OrderReviewResponse:
    return service.create_review(customer, payload)


@router.patch("/reviews/{review_id}", response_model=OrderReviewResponse)
def update_review(
    review_id: uuid.UUID,
    payload: OrderReviewUpdate,
    customer: Annotated[Customer, Depends(get_or_create_customer)],
    service: Annotated[OrderReviewService, Depends(get_order_review_service)],
) -> OrderReviewResponse:
    return service.update_review(customer, review_id, payload)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
    review_id: uuid.UUID,
    customer: Annotated[Customer, Depends(get_or_create_customer)],
    service: Annotated[OrderReviewService, Depends(get_order_review_service)],
) -> None:
    service.delete_review(customer, review_id)
