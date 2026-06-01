"""Customer routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.admin import (
    get_current_admin_user,
    get_customer_communication_service,
    get_customer_insights_service,
    get_customer_note_service,
    get_customer_service,
)
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerDetailResponse, CustomerUpdate
from app.schemas.customer_crm import (
    CustomerCommunicationCreate,
    CustomerCommunicationResponse,
    CustomerInsightsResponse,
    CustomerListItemResponse,
    CustomerListParams,
    CustomerNoteCreate,
    CustomerNoteResponse,
    CustomerOrderHistoryItem,
)
from app.schemas.pagination import PaginatedResponse
from app.services.customer_communication_service import CustomerCommunicationService
from app.services.customer_insights_service import CustomerInsightsService
from app.services.customer_note_service import CustomerNoteService
from app.services.customer_service import CustomerService

router = APIRouter(
    prefix="/customers",
    tags=["Customers"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("", response_model=PaginatedResponse[CustomerListItemResponse])
def list_customers(
    params: Annotated[CustomerListParams, Depends()],
    service: Annotated[CustomerInsightsService, Depends(get_customer_insights_service)],
) -> PaginatedResponse[CustomerListItemResponse]:
    """List customers with CRM metrics, filters, and segments."""
    return service.list_customers(params)


@router.post("", response_model=CustomerDetailResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> CustomerDetailResponse:
    """Create a customer."""
    return service.create(payload)


@router.get("/{customer_id}", response_model=CustomerDetailResponse)
def get_customer(
    customer_id: uuid.UUID,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> CustomerDetailResponse:
    """Get customer detail."""
    return service.get(customer_id)


@router.patch("/{customer_id}", response_model=CustomerDetailResponse)
def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerUpdate,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> CustomerDetailResponse:
    """Update a customer."""
    return service.update(customer_id, payload)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: uuid.UUID,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> None:
    """Delete a customer."""
    service.delete(customer_id)


@router.get("/{customer_id}/insights", response_model=CustomerInsightsResponse)
def get_customer_insights(
    customer_id: uuid.UUID,
    service: Annotated[CustomerInsightsService, Depends(get_customer_insights_service)],
) -> CustomerInsightsResponse:
    """Calculated customer value and segment metrics."""
    return service.get_insights(customer_id)


@router.get("/{customer_id}/orders", response_model=list[CustomerOrderHistoryItem])
def get_customer_order_history(
    customer_id: uuid.UUID,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    service: Annotated[CustomerInsightsService, Depends(get_customer_insights_service)] = ...,
) -> list[CustomerOrderHistoryItem]:
    """Order history for a customer."""
    return service.get_order_history(customer_id, limit=limit)


@router.get("/{customer_id}/notes", response_model=list[CustomerNoteResponse])
def list_customer_notes(
    customer_id: uuid.UUID,
    service: Annotated[CustomerNoteService, Depends(get_customer_note_service)],
) -> list[CustomerNoteResponse]:
    """List internal notes for a customer."""
    return service.list_for_customer(customer_id)


@router.post(
    "/{customer_id}/notes",
    response_model=CustomerNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer_note(
    customer_id: uuid.UUID,
    payload: CustomerNoteCreate,
    admin_user: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[CustomerNoteService, Depends(get_customer_note_service)],
) -> CustomerNoteResponse:
    """Add an internal note to a customer."""
    return service.create(customer_id, payload, created_by=admin_user)


@router.delete("/{customer_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer_note(
    customer_id: uuid.UUID,
    note_id: uuid.UUID,
    service: Annotated[CustomerNoteService, Depends(get_customer_note_service)],
) -> None:
    """Delete an internal customer note."""
    service.delete(customer_id, note_id)


@router.get(
    "/{customer_id}/communications",
    response_model=list[CustomerCommunicationResponse],
)
def list_customer_communications(
    customer_id: uuid.UUID,
    service: Annotated[
        CustomerCommunicationService,
        Depends(get_customer_communication_service),
    ],
) -> list[CustomerCommunicationResponse]:
    """List communication log entries for a customer."""
    return service.list_for_customer(customer_id)


@router.post(
    "/{customer_id}/communications",
    response_model=CustomerCommunicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer_communication(
    customer_id: uuid.UUID,
    payload: CustomerCommunicationCreate,
    admin_user: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[
        CustomerCommunicationService,
        Depends(get_customer_communication_service),
    ],
) -> CustomerCommunicationResponse:
    """Log internal staff communication with a customer."""
    return service.create(customer_id, payload, created_by=admin_user)
