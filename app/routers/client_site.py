"""Public client site content routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.admin import (
    get_business_setting_service,
    get_faq_service,
    get_shared_memory_service,
)
from app.schemas.client_site import ClientSiteProfileResponse
from app.schemas.faq import ClientFaqsResponse
from app.schemas.shared_memory import ClientSharedMemoriesResponse
from app.services.business_setting_service import BusinessSettingService
from app.services.faq_service import FaqService
from app.services.shared_memory_service import SharedMemoryService

router = APIRouter(prefix="/client", tags=["Client Site"])


@router.get("/site-profile", response_model=ClientSiteProfileResponse)
def get_client_site_profile(
    service: Annotated[BusinessSettingService, Depends(get_business_setting_service)],
) -> ClientSiteProfileResponse:
    """Public contact details and active social links for the client website."""
    return service.get_client_site_profile()


@router.get("/faqs", response_model=ClientFaqsResponse)
def list_client_faqs(
    service: Annotated[FaqService, Depends(get_faq_service)],
) -> ClientFaqsResponse:
    """List active FAQs grouped by category for the client website."""
    return service.list_active_public()


@router.get("/shared-memories", response_model=ClientSharedMemoriesResponse)
def list_client_shared_memories(
    service: Annotated[SharedMemoryService, Depends(get_shared_memory_service)],
) -> ClientSharedMemoriesResponse:
    """List active shared memories for the client website home page."""
    return service.list_active_public()
