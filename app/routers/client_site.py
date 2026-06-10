"""Public client site content routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.admin import get_business_setting_service, get_faq_service
from app.schemas.client_site import ClientSiteProfileResponse
from app.schemas.faq import ClientFaqCategoryGroup
from app.services.business_setting_service import BusinessSettingService
from app.services.faq_service import FaqService

router = APIRouter(prefix="/client", tags=["Client Site"])


@router.get("/site-profile", response_model=ClientSiteProfileResponse)
def get_client_site_profile(
    service: Annotated[BusinessSettingService, Depends(get_business_setting_service)],
) -> ClientSiteProfileResponse:
    """Public contact details and active social links for the client website."""
    return service.get_client_site_profile()


@router.get("/faqs", response_model=list[ClientFaqCategoryGroup])
def list_client_faqs(
    service: Annotated[FaqService, Depends(get_faq_service)],
) -> list[ClientFaqCategoryGroup]:
    """List active FAQs grouped by category for the client website."""
    return service.list_active_public()
