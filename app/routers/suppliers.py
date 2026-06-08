"""Supplier routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.admin import get_current_admin_user, get_supplier_service
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.supplier import SupplierCreate, SupplierResponse, SupplierUpdate
from app.services.supplier_service import SupplierService

router = APIRouter(
    prefix="/suppliers",
    tags=["Suppliers"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("", response_model=PaginatedResponse[SupplierResponse])
def list_suppliers(
    params: Annotated[PaginationParams, Depends()],
    service: Annotated[SupplierService, Depends(get_supplier_service)],
) -> PaginatedResponse[SupplierResponse]:
    """List suppliers with pagination."""
    return service.list(params)


@router.get("/active", response_model=list[SupplierResponse])
def list_active_suppliers(
    service: Annotated[SupplierService, Depends(get_supplier_service)],
) -> list[SupplierResponse]:
    """List active suppliers for product item forms."""
    return service.list_active()


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate,
    service: Annotated[SupplierService, Depends(get_supplier_service)],
) -> SupplierResponse:
    """Create a supplier."""
    return service.create(payload)


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(
    supplier_id: uuid.UUID,
    service: Annotated[SupplierService, Depends(get_supplier_service)],
) -> SupplierResponse:
    """Get a supplier by ID."""
    return service.get(supplier_id)


@router.patch("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: uuid.UUID,
    payload: SupplierUpdate,
    service: Annotated[SupplierService, Depends(get_supplier_service)],
) -> SupplierResponse:
    """Update a supplier."""
    return service.update(supplier_id, payload)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(
    supplier_id: uuid.UUID,
    service: Annotated[SupplierService, Depends(get_supplier_service)],
) -> None:
    """Delete a supplier."""
    service.delete(supplier_id)
