"""Public client ordering routes (no authentication required)."""

import uuid
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.dependencies.client import (
    get_customer_catalog_service,
    get_customer_checkout_service,
)
from app.dependencies.client_account import get_optional_current_customer_id
from app.core.enums import PaymentMethod
from app.schemas.business_settings import BusinessSettingsResponse
from app.schemas.client_ordering import (
    CateringConstraintsResponse,
    ClientCatalogResponse,
    ClientCheckoutOptionsResponse,
    ClientCheckoutRequest,
    ClientCheckoutResponse,
    ClientCollectionQuoteRequest,
    ClientCollectionQuoteResponse,
    ClientDeliveryAreaOption,
    ClientOrderPreviewRequest,
    ClientOrderPreviewResponse,
    ClientPaymentMethodOption,
    EmailAvailabilityResponse,
    DeliveryScheduleCopyResponse,
    WeeklyDeliveryInfoResponse,
)
from app.services.customer_catalog_service import CustomerCatalogService
from app.services.customer_checkout_service import CustomerCheckoutService
from app.services.customer_delivery_date_service import (
    CATERING_MIN_COOKIE_QUANTITY,
    CATERING_MIN_DAYS_AHEAD,
    CustomerDeliveryDateService,
)
from app.services.delivery_schedule_copy_service import (
    delivery_schedule_copy_from_settings,
    get_delivery_schedule_config,
)
from app.database.session import get_db
from app.repositories.delivery_area_repository import DeliveryAreaRepository
from app.services.business_setting_service import BusinessSettingService
from app.services.delivery_fee_service import resolve_delivery_fee
from app.utils.captcha import verify_captcha_token
from app.utils.client_ip import get_client_ip
from sqlalchemy.orm import Session

router = APIRouter(prefix="/client", tags=["Client Ordering"])


def _client_payment_methods(settings: BusinessSettingsResponse) -> list[ClientPaymentMethodOption]:
    methods: list[ClientPaymentMethodOption] = []
    if settings.cod_enabled:
        methods.append(
            ClientPaymentMethodOption(
                code=PaymentMethod.CASH_ON_DELIVERY,
                label="Cash on delivery",
            ),
        )
    if settings.bank_transfer_enabled:
        methods.append(
            ClientPaymentMethodOption(
                code=PaymentMethod.BANK_TRANSFER,
                label="Bank transfer",
            ),
        )
    if settings.stripe_enabled:
        methods.append(
            ClientPaymentMethodOption(
                code=PaymentMethod.STRIPE,
                label="Card payment",
            ),
        )
    return methods


@router.get("/ordering/checkout-options", response_model=ClientCheckoutOptionsResponse)
def get_checkout_options(
    db: Annotated[Session, Depends(get_db)],
) -> ClientCheckoutOptionsResponse:
    settings = BusinessSettingService(db).get_settings()
    return ClientCheckoutOptionsResponse(
        use_fixed_delivery_fee=settings.use_fixed_delivery_fee,
        fixed_delivery_fee=str(settings.delivery_fee),
        payment_methods=_client_payment_methods(settings),
    )


@router.get("/catalog", response_model=ClientCatalogResponse)
def get_client_catalog(
    service: Annotated[CustomerCatalogService, Depends(get_customer_catalog_service)],
) -> ClientCatalogResponse:
    """Public collections and selectable products for Build Your Order."""
    return service.get_catalog()


@router.get("/delivery-areas", response_model=list[ClientDeliveryAreaOption])
def list_client_delivery_areas(
    db: Annotated[Session, Depends(get_db)],
) -> list[ClientDeliveryAreaOption]:
    settings = BusinessSettingService(db).get_settings()
    areas = DeliveryAreaRepository(db).list_active()
    return [
        ClientDeliveryAreaOption(
            id=area.id,
            name=area.name,
            delivery_fee=str(resolve_delivery_fee(settings, area)),
            pickup_only=area.pickup_only,
        )
        for area in areas
    ]


def _delivery_schedule_copy_response(
    settings: BusinessSettingsResponse,
) -> DeliveryScheduleCopyResponse:
    copy = delivery_schedule_copy_from_settings(
        order_cutoff_day=settings.order_cutoff_day,
        delivery_day=settings.delivery_day,
    )
    return DeliveryScheduleCopyResponse.model_validate(asdict(copy))


@router.get("/ordering/delivery-schedule", response_model=DeliveryScheduleCopyResponse)
def get_delivery_schedule(
    db: Annotated[Session, Depends(get_db)],
) -> DeliveryScheduleCopyResponse:
    settings = BusinessSettingService(db).get_settings()
    return _delivery_schedule_copy_response(settings)


@router.get("/ordering/weekly-delivery", response_model=WeeklyDeliveryInfoResponse)
def get_weekly_delivery_info(
    db: Annotated[Session, Depends(get_db)],
) -> WeeklyDeliveryInfoResponse:
    settings = BusinessSettingService(db).get_settings()
    schedule_config = get_delivery_schedule_config(db)
    scheduled = CustomerDeliveryDateService.calculate_weekly_delivery_date(
        config=schedule_config,
    )
    return WeeklyDeliveryInfoResponse(
        **_delivery_schedule_copy_response(settings).model_dump(),
        calculated_delivery_date=scheduled,
        is_before_cutoff=CustomerDeliveryDateService.is_before_weekly_cutoff(
            config=schedule_config,
        ),
    )


@router.get("/ordering/catering-constraints", response_model=CateringConstraintsResponse)
def get_catering_constraints() -> CateringConstraintsResponse:
    return CateringConstraintsResponse(
        minimum_cookie_quantity=CATERING_MIN_COOKIE_QUANTITY,
        minimum_days_ahead=CATERING_MIN_DAYS_AHEAD,
        earliest_delivery_date=CustomerDeliveryDateService.calculate_catering_earliest_date(),
    )


@router.post("/ordering/collection-quote", response_model=ClientCollectionQuoteResponse)
def quote_collection_price(
    payload: ClientCollectionQuoteRequest,
    service: Annotated[CustomerCheckoutService, Depends(get_customer_checkout_service)],
) -> ClientCollectionQuoteResponse:
    """Return server-calculated pack price for a completed collection selection."""
    return service.quote_collection(payload)


@router.post("/orders/preview", response_model=ClientOrderPreviewResponse)
def preview_client_order(
    payload: ClientOrderPreviewRequest,
    service: Annotated[CustomerCheckoutService, Depends(get_customer_checkout_service)],
    customer_id: Annotated[uuid.UUID | None, Depends(get_optional_current_customer_id)] = None,
) -> ClientOrderPreviewResponse:
    """Preview pricing and assigned delivery date before checkout."""
    return service.preview(payload, customer_id=customer_id)


@router.post(
    "/orders/checkout",
    response_model=ClientCheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
def checkout_client_order(
    payload: ClientCheckoutRequest,
    request: Request,
    service: Annotated[CustomerCheckoutService, Depends(get_customer_checkout_service)],
) -> ClientCheckoutResponse:
    """Place a website order and receive a WhatsApp handoff URL."""
    verify_captcha_token(payload.captcha_token, remote_ip=get_client_ip(request))
    return service.checkout(payload)


@router.get("/auth/check-email", response_model=EmailAvailabilityResponse)
def check_client_email(
    email: str,
    service: Annotated[CustomerCheckoutService, Depends(get_customer_checkout_service)],
) -> EmailAvailabilityResponse:
    """Check whether an email is already registered before optional account creation."""
    return service.check_email(email)
