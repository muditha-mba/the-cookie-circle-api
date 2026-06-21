"""Admin activity log API schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import ActivityAction, ActivityResourceType, ClientDeviceType
from app.schemas.pagination import PaginationParams


class ActivityLogListParams(PaginationParams):
    """Activity log list filters."""

    action: ActivityAction | None = None
    resource_type: ActivityResourceType | None = None
    actor_user_id: UUID | None = None
    success: bool | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


class ActivityLogSummaryResponse(BaseModel):
    """Activity log list item."""

    id: UUID
    created_at: datetime
    actor_user_id: UUID | None
    actor_email: str | None
    actor_admin_role: str | None
    action: ActivityAction
    resource_type: ActivityResourceType
    resource_id: UUID | None
    resource_label: str | None
    http_method: str | None
    path: str | None
    ip_address: str | None
    browser_name: str | None
    browser_version: str | None
    os_name: str | None
    os_version: str | None
    device_type: ClientDeviceType
    status_code: int | None
    success: bool

    model_config = {"from_attributes": True}


class ActivityLogDetailResponse(ActivityLogSummaryResponse):
    """Activity log detail including raw client metadata."""

    user_agent: str | None
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias="metadata_json",
    )

    model_config = {"from_attributes": True, "populate_by_name": True}
