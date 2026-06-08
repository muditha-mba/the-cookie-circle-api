"""Admin user lookup routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies.admin import get_current_admin_user, get_user_lookup_service
from app.schemas.user import LinkableUserListResponse, LinkableUserResponse
from app.services.user_lookup_service import UserLookupService

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("/linkable", response_model=LinkableUserListResponse)
def list_linkable_users(
    service: Annotated[UserLookupService, Depends(get_user_lookup_service)],
    search: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 25,
) -> LinkableUserListResponse:
    """Search customer users that can be linked to a customer profile."""
    return service.list_linkable_customers(search=search, limit=limit)


@router.get("/linkable/{user_id}", response_model=LinkableUserResponse)
def get_linkable_user(
    user_id: uuid.UUID,
    service: Annotated[UserLookupService, Depends(get_user_lookup_service)],
) -> LinkableUserResponse:
    """Get a single linkable customer user."""
    return service.get_linkable_customer(user_id)
