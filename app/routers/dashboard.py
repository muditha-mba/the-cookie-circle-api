"""Operational dashboard routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.admin import (
    get_current_admin_user,
    get_dashboard_service,
)
from app.schemas.dashboard import DashboardOverviewResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("/overview", response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardOverviewResponse:
    """Operational overview focused on today's actions."""
    return service.get_overview()
