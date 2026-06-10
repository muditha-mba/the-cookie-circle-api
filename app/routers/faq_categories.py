"""FAQ category admin routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.admin import get_current_admin_user, get_faq_category_service
from app.schemas.faq_category import FaqCategoryCreate, FaqCategoryResponse, FaqCategoryUpdate
from app.services.faq_category_service import FaqCategoryService

router = APIRouter(
    prefix="/faq-categories",
    tags=["FAQ Categories"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("", response_model=list[FaqCategoryResponse])
def list_faq_categories(
    service: Annotated[FaqCategoryService, Depends(get_faq_category_service)],
) -> list[FaqCategoryResponse]:
    """List all FAQ categories."""
    return service.list_all()


@router.post("", response_model=FaqCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_faq_category(
    payload: FaqCategoryCreate,
    service: Annotated[FaqCategoryService, Depends(get_faq_category_service)],
) -> FaqCategoryResponse:
    """Create a FAQ category."""
    return service.create(payload)


@router.get("/{category_id}", response_model=FaqCategoryResponse)
def get_faq_category(
    category_id: uuid.UUID,
    service: Annotated[FaqCategoryService, Depends(get_faq_category_service)],
) -> FaqCategoryResponse:
    """Get a FAQ category by ID."""
    return service.get(category_id)


@router.patch("/{category_id}", response_model=FaqCategoryResponse)
def update_faq_category(
    category_id: uuid.UUID,
    payload: FaqCategoryUpdate,
    service: Annotated[FaqCategoryService, Depends(get_faq_category_service)],
) -> FaqCategoryResponse:
    """Update a FAQ category."""
    return service.update(category_id, payload)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faq_category(
    category_id: uuid.UUID,
    service: Annotated[FaqCategoryService, Depends(get_faq_category_service)],
) -> None:
    """Delete a FAQ category."""
    service.delete(category_id)
