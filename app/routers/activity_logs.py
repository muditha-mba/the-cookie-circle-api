"""Admin activity log routes (super-admin only)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.admin import get_activity_log_service
from app.dependencies.permissions import require_super_admin
from app.schemas.activity_log import (
    ActivityLogDetailResponse,
    ActivityLogListParams,
    ActivityLogSummaryResponse,
)
from app.schemas.pagination import PaginatedResponse
from app.services.activity_log_service import ActivityLogService

router = APIRouter(
    prefix="/activity-logs",
    tags=["Activity Logs"],
    dependencies=[Depends(require_super_admin)],
)


@router.get("", response_model=PaginatedResponse[ActivityLogSummaryResponse])
def list_activity_logs(
    params: Annotated[ActivityLogListParams, Depends()],
    service: Annotated[ActivityLogService, Depends(get_activity_log_service)],
) -> PaginatedResponse[ActivityLogSummaryResponse]:
    """List admin activity logs with filters."""
    return service.list(params)


@router.get("/{log_id}", response_model=ActivityLogDetailResponse)
def get_activity_log(
    log_id: uuid.UUID,
    service: Annotated[ActivityLogService, Depends(get_activity_log_service)],
) -> ActivityLogDetailResponse:
    """Get a single activity log entry."""
    return service.get(log_id)
