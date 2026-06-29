"""Admin user lookup schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class LinkableUserResponse(BaseModel):
    """Customer user option for linking to a customer profile."""

    id: UUID
    email: str
    first_name: str | None
    last_name: str | None
    display_name: str

    model_config = {"from_attributes": True}


class LinkableUserListResponse(BaseModel):
    """Search results for linkable users."""

    items: list[LinkableUserResponse]


class LinkableUserSearchParams(BaseModel):
    """Query parameters for linkable user search."""

    search: str | None = Field(default=None, max_length=200)
    limit: int = Field(default=25, ge=1, le=50)
