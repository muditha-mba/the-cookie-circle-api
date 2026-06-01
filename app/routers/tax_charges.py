"""Tax charge routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.admin import get_current_admin_user, get_tax_charge_service
from app.schemas.charge import (
    TaxChargeCreate,
    TaxChargeResponse,
    TaxChargeUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.tax_charge_service import TaxChargeService

router = APIRouter(
    prefix="/tax-charges",
    tags=["Tax Charges"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("", response_model=PaginatedResponse[TaxChargeResponse])
def list_tax_charges(
    params: Annotated[PaginationParams, Depends()],
    service: Annotated[TaxChargeService, Depends(get_tax_charge_service)],
) -> PaginatedResponse[TaxChargeResponse]:
    """List tax charges with pagination."""
    return service.list(params)


@router.post("", response_model=TaxChargeResponse, status_code=status.HTTP_201_CREATED)
def create_tax_charge(
    payload: TaxChargeCreate,
    service: Annotated[TaxChargeService, Depends(get_tax_charge_service)],
) -> TaxChargeResponse:
    """Create a tax charge."""
    return service.create(payload)


@router.get("/{charge_id}", response_model=TaxChargeResponse)
def get_tax_charge(
    charge_id: uuid.UUID,
    service: Annotated[TaxChargeService, Depends(get_tax_charge_service)],
) -> TaxChargeResponse:
    """Get a tax charge by ID."""
    return service.get(charge_id)


@router.patch("/{charge_id}", response_model=TaxChargeResponse)
def update_tax_charge(
    charge_id: uuid.UUID,
    payload: TaxChargeUpdate,
    service: Annotated[TaxChargeService, Depends(get_tax_charge_service)],
) -> TaxChargeResponse:
    """Update a tax charge."""
    return service.update(charge_id, payload)


@router.delete("/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tax_charge(
    charge_id: uuid.UUID,
    service: Annotated[TaxChargeService, Depends(get_tax_charge_service)],
) -> None:
    """Delete a tax charge."""
    service.delete(charge_id)
