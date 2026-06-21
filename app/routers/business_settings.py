"""Business settings routes."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies.admin import get_business_setting_service, get_current_admin_user
from app.dependencies.permissions import require_super_admin
from app.schemas.business_settings import (
    BusinessSettingsResponse,
    BusinessSettingsUpdate,
    SuggestedDeliveryDateResponse,
)
from app.schemas.faq import FaqsSectionSettingsResponse, FaqsSectionSettingsUpdate
from app.schemas.shared_memory import (
    SharedMemoriesSectionSettingsResponse,
    SharedMemoriesSectionSettingsUpdate,
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
    _: Annotated[object, Depends(require_super_admin)],
    service: Annotated[BusinessSettingService, Depends(get_business_setting_service)],
) -> BusinessSettingsResponse:
    """Get operational business settings."""
    return service.get_settings()


@router.patch("", response_model=BusinessSettingsResponse)
def update_business_settings(
    _: Annotated[object, Depends(require_super_admin)],
    payload: BusinessSettingsUpdate,
    service: Annotated[BusinessSettingService, Depends(get_business_setting_service)],
) -> BusinessSettingsResponse:
    """Update operational business settings."""
    return service.update_settings(payload)


@router.get("/social-media", response_model=SocialMediaSettingsResponse)
def get_social_media_settings(
    _: Annotated[object, Depends(require_super_admin)],
    service: Annotated[BusinessSettingService, Depends(get_business_setting_service)],
) -> SocialMediaSettingsResponse:
    """Get social media link settings."""
    return service.get_social_media_settings()


@router.patch("/social-media", response_model=SocialMediaSettingsResponse)
def update_social_media_settings(
    _: Annotated[object, Depends(require_super_admin)],
    payload: SocialMediaSettingsUpdate,
    service: Annotated[BusinessSettingService, Depends(get_business_setting_service)],
) -> SocialMediaSettingsResponse:
    """Update social media link settings."""
    return service.update_social_media_settings(payload)


@router.get("/shared-memories", response_model=SharedMemoriesSectionSettingsResponse)
def get_shared_memories_section_settings(
    _: Annotated[object, Depends(require_super_admin)],
    service: Annotated[BusinessSettingService, Depends(get_business_setting_service)],
) -> SharedMemoriesSectionSettingsResponse:
    """Get shared memories section visibility settings."""
    return service.get_shared_memories_section_settings()


@router.patch("/shared-memories", response_model=SharedMemoriesSectionSettingsResponse)
def update_shared_memories_section_settings(
    _: Annotated[object, Depends(require_super_admin)],
    payload: SharedMemoriesSectionSettingsUpdate,
    service: Annotated[BusinessSettingService, Depends(get_business_setting_service)],
) -> SharedMemoriesSectionSettingsResponse:
    """Update shared memories section visibility on the client website."""
    return service.update_shared_memories_section_settings(payload)


@router.get("/faqs", response_model=FaqsSectionSettingsResponse)
def get_faqs_section_settings(
    _: Annotated[object, Depends(require_super_admin)],
    service: Annotated[BusinessSettingService, Depends(get_business_setting_service)],
) -> FaqsSectionSettingsResponse:
    """Get FAQ section visibility settings."""
    return service.get_faqs_section_settings()


@router.patch("/faqs", response_model=FaqsSectionSettingsResponse)
def update_faqs_section_settings(
    _: Annotated[object, Depends(require_super_admin)],
    payload: FaqsSectionSettingsUpdate,
    service: Annotated[BusinessSettingService, Depends(get_business_setting_service)],
) -> FaqsSectionSettingsResponse:
    """Update FAQ section visibility on the client website."""
    return service.update_faqs_section_settings(payload)


@router.get("/suggested-delivery-date", response_model=SuggestedDeliveryDateResponse)
def suggest_delivery_date(
    service: Annotated[BusinessSettingService, Depends(get_business_setting_service)],
    reference_date: Annotated[date | None, Query()] = None,
) -> SuggestedDeliveryDateResponse:
    """Suggest a delivery date based on schedule settings."""
    return service.suggest_delivery_date(reference_date)
