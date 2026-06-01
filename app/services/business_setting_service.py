"""Business settings business logic."""

from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.core import business_settings_keys as keys
from app.core.enums import Weekday
from app.core.exceptions import ValidationError
from app.repositories.business_setting_repository import BusinessSettingRepository
from app.schemas.business_settings import (
    BusinessSettingsResponse,
    BusinessSettingsUpdate,
    SuggestedDeliveryDateResponse,
)
from app.services.delivery_schedule_service import DeliveryScheduleService
from app.utils.weekday import parse_weekday


class BusinessSettingService:
    """Manage operational business settings."""

    DEFAULTS: dict[str, str] = {
        keys.DELIVERY_FEE: "0.00",
        keys.ORDER_CUTOFF_DAY: Weekday.THURSDAY.value,
        keys.DELIVERY_DAY: Weekday.SATURDAY.value,
        keys.BUSINESS_PHONE: "",
        keys.BUSINESS_EMAIL: "",
        keys.STRIPE_ENABLED: "false",
        keys.BANK_TRANSFER_ENABLED: "true",
        keys.COD_ENABLED: "true",
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = BusinessSettingRepository(db)

    def get_settings(self) -> BusinessSettingsResponse:
        return self._to_response(self._load_map())

    def update_settings(self, payload: BusinessSettingsUpdate) -> BusinessSettingsResponse:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            raise ValidationError("No fields provided to update")

        current = self._load_map()
        if payload.delivery_fee is not None:
            current[keys.DELIVERY_FEE] = str(payload.delivery_fee)
        if payload.order_cutoff_day is not None:
            current[keys.ORDER_CUTOFF_DAY] = payload.order_cutoff_day.value
        if payload.delivery_day is not None:
            current[keys.DELIVERY_DAY] = payload.delivery_day.value
        if payload.business_phone is not None:
            current[keys.BUSINESS_PHONE] = payload.business_phone
        if payload.business_email is not None:
            current[keys.BUSINESS_EMAIL] = payload.business_email
        if payload.stripe_enabled is not None:
            current[keys.STRIPE_ENABLED] = str(payload.stripe_enabled).lower()
        if payload.bank_transfer_enabled is not None:
            current[keys.BANK_TRANSFER_ENABLED] = str(payload.bank_transfer_enabled).lower()
        if payload.cod_enabled is not None:
            current[keys.COD_ENABLED] = str(payload.cod_enabled).lower()

        for key, value in current.items():
            if key in keys.ALL_KEYS:
                self.settings.upsert(key, value)

        self.db.commit()
        return self._to_response(self._load_map())

    def suggest_delivery_date(self, reference_date: date | None = None) -> SuggestedDeliveryDateResponse:
        settings = self.get_settings()
        ref = reference_date or date.today()
        suggested = DeliveryScheduleService.calculate_delivery_date(
            order_date=ref,
            cutoff_day=settings.order_cutoff_day,
            delivery_day=settings.delivery_day,
        )
        return SuggestedDeliveryDateResponse(
            reference_date=ref.isoformat(),
            suggested_delivery_date=suggested.isoformat(),
            order_cutoff_day=settings.order_cutoff_day,
            delivery_day=settings.delivery_day,
        )

    def _load_map(self) -> dict[str, str]:
        stored = self.settings.get_all()
        merged = dict(self.DEFAULTS)
        merged.update(stored)
        return merged

    def _to_response(self, data: dict[str, str]) -> BusinessSettingsResponse:
        try:
            delivery_fee = Decimal(data[keys.DELIVERY_FEE])
        except InvalidOperation as exc:
            raise ValidationError("Invalid delivery_fee setting") from exc

        return BusinessSettingsResponse(
            delivery_fee=delivery_fee,
            order_cutoff_day=parse_weekday(data[keys.ORDER_CUTOFF_DAY]),
            delivery_day=parse_weekday(data[keys.DELIVERY_DAY]),
            business_phone=data[keys.BUSINESS_PHONE],
            business_email=data[keys.BUSINESS_EMAIL],
            stripe_enabled=data[keys.STRIPE_ENABLED].lower() == "true",
            bank_transfer_enabled=data[keys.BANK_TRANSFER_ENABLED].lower() == "true",
            cod_enabled=data[keys.COD_ENABLED].lower() == "true",
        )
