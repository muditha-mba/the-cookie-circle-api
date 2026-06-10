"""Operational dashboard routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.admin_access import can_view_financials
from app.dependencies.admin import (
    get_current_admin_user,
    get_dashboard_service,
)
from app.models.user import User
from app.schemas.dashboard import DashboardOverviewResponse
from app.services.dashboard_service import DashboardService
from app.services.financial_redaction import redact_dashboard_overview

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("/overview", response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardOverviewResponse:
    """Operational overview focused on today's actions."""
    result = service.get_overview()
    if not can_view_financials(current_user):
        return redact_dashboard_overview(result)
    return result
