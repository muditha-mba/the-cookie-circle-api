"""Business settings routes."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies.admin import get_business_setting_service, get_current_admin_user
from app.schemas.business_settings import (
    BusinessSettingsResponse,
    BusinessSettingsUpdate,
    SuggestedDeliveryDateResponse,
)
from app.schemas.social_media import SocialMediaSettingsResponse, SocialMediaSettingsUpdate
from app.services.business_setting_service import BusinessSettingService

router = APIRouter(
    prefix="/business-settings",
    tags=["Business Settings"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("", response_model=BusinessSettingsResponse)
def get_business_settings(
    service: Annotated[BusinessSettingService, Depends(get_business_setting_service)],
) -> BusinessSettingsResponse:
    """Get operational business settings."""
    return service.get_settings()


@router.patch("", response_model=BusinessSettingsResponse)
def update_business_settings(
    payload: BusinessSettingsUpdate,
    service: Annotated[BusinessSettingService, Depends(get_business_setting_service)],
) -> BusinessSettingsResponse:
    """Update operational business settings."""
    return service.update_settings(payload)


@router.get("/social-media", response_model=SocialMediaSettingsResponse)
def get_social_media_settings(
    service: Annotated[BusinessSettingService, Depends(get_business_setting_service)],
) -> SocialMediaSettingsResponse:
    """Get social media link settings."""
    return service.get_social_media_settings()


@router.patch("/social-media", response_model=SocialMediaSettingsResponse)
def update_social_media_settings(
    payload: SocialMediaSettingsUpdate,
    service: Annotated[BusinessSettingService, Depends(get_business_setting_service)],
) -> SocialMediaSettingsResponse:
    """Update social media link settings."""
    return service.update_social_media_settings(payload)


@router.get("/suggested-delivery-date", response_model=SuggestedDeliveryDateResponse)
def suggest_delivery_date(
    service: Annotated[BusinessSettingService, Depends(get_business_setting_service)],
    reference_date: Annotated[date | None, Query()] = None,
) -> SuggestedDeliveryDateResponse:
    """Suggest a delivery date based on schedule settings."""
    return service.suggest_delivery_date(reference_date)
