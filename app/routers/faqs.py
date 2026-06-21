"""FAQ admin routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.admin import get_current_admin_user, get_faq_service
from app.schemas.faq import FaqCreate, FaqResponse, FaqUpdate
from app.services.faq_service import FaqService

router = APIRouter(
    prefix="/faqs",
    tags=["FAQs"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("", response_model=list[FaqResponse])
def list_faqs(
    service: Annotated[FaqService, Depends(get_faq_service)],
) -> list[FaqResponse]:
    """List all FAQs for admin management."""
    return service.list_all()


@router.post("", response_model=FaqResponse, status_code=status.HTTP_201_CREATED)
def create_faq(
    payload: FaqCreate,
    service: Annotated[FaqService, Depends(get_faq_service)],
) -> FaqResponse:
    """Create a FAQ."""
    return service.create(payload)


@router.get("/{faq_id}", response_model=FaqResponse)
def get_faq(
    faq_id: uuid.UUID,
    service: Annotated[FaqService, Depends(get_faq_service)],
) -> FaqResponse:
    """Get a FAQ by ID."""
    return service.get(faq_id)


@router.patch("/{faq_id}", response_model=FaqResponse)
def update_faq(
    faq_id: uuid.UUID,
    payload: FaqUpdate,
    service: Annotated[FaqService, Depends(get_faq_service)],
) -> FaqResponse:
    """Update a FAQ."""
    return service.update(faq_id, payload)


@router.delete("/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faq(
    faq_id: uuid.UUID,
    service: Annotated[FaqService, Depends(get_faq_service)],
) -> None:
    """Delete a FAQ."""
    service.delete(faq_id)
