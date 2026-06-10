"""Business settings business logic."""

from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.core import business_settings_keys as keys
from app.core.enums import Weekday
from app.core.exceptions import ValidationError
from app.core.social_platforms import SOCIAL_PLATFORM_LABELS, SOCIAL_PLATFORMS, SocialPlatform
from app.repositories.business_setting_repository import BusinessSettingRepository
from app.schemas.business_settings import (
    BusinessSettingsResponse,
    BusinessSettingsUpdate,
    SuggestedDeliveryDateResponse,
)
from app.schemas.client_site import ClientSiteProfileResponse, ClientSocialLink
from app.schemas.shared_memory import (
    SharedMemoriesSectionSettingsResponse,
    SharedMemoriesSectionSettingsUpdate,
)
from app.schemas.social_media import (
    SocialMediaLink,
    SocialMediaSettingsResponse,
    SocialMediaSettingsUpdate,
    default_social_media_links,
)
from app.services.delivery_schedule_service import DeliveryScheduleService
from app.utils.weekday import parse_weekday


class BusinessSettingService:
    """Manage operational business settings."""

    DEFAULTS: dict[str, str] = {
        keys.DELIVERY_FEE: "0.00",
        keys.USE_FIXED_DELIVERY_FEE: "false",
        keys.ORDER_CUTOFF_DAY: Weekday.THURSDAY.value,
        keys.DELIVERY_DAY: Weekday.SATURDAY.value,
        keys.BUSINESS_PHONE: "",
        keys.BUSINESS_EMAIL: "",
        keys.STRIPE_ENABLED: "false",
        keys.BANK_TRANSFER_ENABLED: "true",
        keys.COD_ENABLED: "true",
        keys.SHARED_MEMORIES_ENABLED: "false",
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
        if payload.use_fixed_delivery_fee is not None:
            current[keys.USE_FIXED_DELIVERY_FEE] = str(payload.use_fixed_delivery_fee).lower()
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

    def get_social_media_settings(self) -> SocialMediaSettingsResponse:
        data = self._load_map()
        return SocialMediaSettingsResponse(links=self._social_links_from_map(data))

    def update_social_media_settings(
        self,
        payload: SocialMediaSettingsUpdate,
    ) -> SocialMediaSettingsResponse:
        current = self._load_map()

        for link in payload.links:
            platform = link.platform
            url_key = keys.social_url_key(platform)
            enabled_key = keys.social_enabled_key(platform)

            if link.url is not None:
                normalized_url = link.url.strip()
                if link.is_enabled is True or (
                    link.is_enabled is None and current.get(enabled_key, "false").lower() == "true"
                ):
                    self._validate_social_url(normalized_url, platform)
                current[url_key] = normalized_url

            if link.is_enabled is not None:
                enabled = link.is_enabled
                url_value = current.get(url_key, "").strip()
                if enabled and not url_value:
                    raise ValidationError(
                        f"A URL is required to enable {SOCIAL_PLATFORM_LABELS[platform]}",
                    )
                if enabled:
                    self._validate_social_url(url_value, platform)
                current[enabled_key] = str(enabled).lower()

        for key, value in current.items():
            if key in keys.SOCIAL_KEYS:
                self.settings.upsert(key, value)

        self.db.commit()
        return SocialMediaSettingsResponse(links=self._social_links_from_map(self._load_map()))

    def get_shared_memories_section_enabled(self) -> bool:
        data = self._load_map()
        return data.get(keys.SHARED_MEMORIES_ENABLED, "false").lower() == "true"

    def get_shared_memories_section_settings(self) -> SharedMemoriesSectionSettingsResponse:
        return SharedMemoriesSectionSettingsResponse(
            section_enabled=self.get_shared_memories_section_enabled(),
        )

    def update_shared_memories_section_settings(
        self,
        payload: SharedMemoriesSectionSettingsUpdate,
    ) -> SharedMemoriesSectionSettingsResponse:
        self.settings.upsert(keys.SHARED_MEMORIES_ENABLED, str(payload.section_enabled).lower())
        self.db.commit()
        return SharedMemoriesSectionSettingsResponse(section_enabled=payload.section_enabled)

    def get_client_site_profile(self) -> ClientSiteProfileResponse:
        data = self._load_map()
        settings = self._to_response(data)
        social_links = [
            ClientSocialLink(
                platform=link.platform,
                label=SOCIAL_PLATFORM_LABELS[link.platform],
                url=link.url,
            )
            for link in self._social_links_from_map(data)
            if link.is_enabled and link.url
        ]
        return ClientSiteProfileResponse(
            business_phone=settings.business_phone,
            business_email=settings.business_email,
            social_links=social_links,
        )

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

    def _social_links_from_map(self, data: dict[str, str]) -> list[SocialMediaLink]:
        links: list[SocialMediaLink] = []
        for platform in SOCIAL_PLATFORMS:
            url = data.get(keys.social_url_key(platform), "").strip()
            enabled = data.get(keys.social_enabled_key(platform), "false").lower() == "true"
            links.append(SocialMediaLink(platform=platform, url=url, is_enabled=enabled))
        return links or default_social_media_links()

    @staticmethod
    def _validate_social_url(url: str, platform: SocialPlatform) -> None:
        if not url:
            raise ValidationError(f"A URL is required for {SOCIAL_PLATFORM_LABELS[platform]}")
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValidationError(
                f"{SOCIAL_PLATFORM_LABELS[platform]} URL must start with http:// or https://",
            )

    def _to_response(self, data: dict[str, str]) -> BusinessSettingsResponse:
        try:
            delivery_fee = Decimal(data[keys.DELIVERY_FEE])
        except InvalidOperation as exc:
            raise ValidationError("Invalid delivery_fee setting") from exc

        return BusinessSettingsResponse(
            delivery_fee=delivery_fee,
            use_fixed_delivery_fee=data[keys.USE_FIXED_DELIVERY_FEE].lower() == "true",
            order_cutoff_day=parse_weekday(data[keys.ORDER_CUTOFF_DAY]),
            delivery_day=parse_weekday(data[keys.DELIVERY_DAY]),
            business_phone=data[keys.BUSINESS_PHONE],
            business_email=data[keys.BUSINESS_EMAIL],
            stripe_enabled=data[keys.STRIPE_ENABLED].lower() == "true",
            bank_transfer_enabled=data[keys.BANK_TRANSFER_ENABLED].lower() == "true",
            cod_enabled=data[keys.COD_ENABLED].lower() == "true",
        )
