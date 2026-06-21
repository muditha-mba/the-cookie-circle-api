"""Customer-facing delivery date rules (Sri Lanka timezone)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.enums import OrderType, Weekday
from app.core.exceptions import ValidationError
from app.utils.delivery_schedule import DeliveryScheduleConfig, build_delivery_schedule_config
SRI_LANKA_TZ = ZoneInfo("Asia/Colombo")

CATERING_MIN_DAYS_AHEAD = 3
CATERING_MIN_COOKIE_QUANTITY = 30

DEFAULT_SCHEDULE_CONFIG = build_delivery_schedule_config(
    cutoff_day=Weekday.THURSDAY,
    delivery_day=Weekday.SATURDAY,
)


class CustomerDeliveryDateService:
    """Reusable delivery scheduling for website checkout."""

    @staticmethod
    def to_local(order_at: datetime) -> datetime:
        if order_at.tzinfo is None:
            order_at = order_at.replace(tzinfo=UTC)
        return order_at.astimezone(SRI_LANKA_TZ)

    @classmethod
    def is_before_weekly_cutoff(
        cls,
        order_at: datetime | None = None,
        *,
        config: DeliveryScheduleConfig = DEFAULT_SCHEDULE_CONFIG,
    ) -> bool:
        local = cls.to_local(order_at or datetime.now(UTC))
        cutoff_index = config.cutoff_weekday_index
        if local.weekday() < cutoff_index:
            return True
        if local.weekday() > cutoff_index:
            return False
        return local.time() <= config.cutoff_time

    @staticmethod
    def week_delivery_day(reference: date, delivery_weekday: int) -> date:
        monday = reference - timedelta(days=reference.weekday())
        return monday + timedelta(days=delivery_weekday)

    @classmethod
    def next_delivery_day(
        cls,
        reference: date,
        *,
        config: DeliveryScheduleConfig = DEFAULT_SCHEDULE_CONFIG,
    ) -> date:
        delivery_index = config.delivery_weekday_index
        days = (delivery_index - reference.weekday()) % 7
        if days == 0:
            days = 7
        return reference + timedelta(days=days)

    @classmethod
    def calculate_weekly_delivery_date(
        cls,
        order_at: datetime | None = None,
        *,
        config: DeliveryScheduleConfig = DEFAULT_SCHEDULE_CONFIG,
    ) -> date:
        """Assign the next applicable delivery batch for weekly cookie delivery."""
        local = cls.to_local(order_at or datetime.now(UTC))
        order_date = local.date()
        this_week_delivery = cls.week_delivery_day(
            order_date,
            config.delivery_weekday_index,
        )

        if cls.is_before_weekly_cutoff(order_at, config=config):
            if order_date <= this_week_delivery:
                return this_week_delivery
            return cls.week_delivery_day(
                order_date + timedelta(days=7),
                config.delivery_weekday_index,
            )

        return cls.week_delivery_day(
            order_date + timedelta(days=7),
            config.delivery_weekday_index,
        )

    @classmethod
    def calculate_catering_earliest_date(cls, from_date: date | None = None) -> date:
        base = from_date or cls.to_local(datetime.now(UTC)).date()
        return base + timedelta(days=CATERING_MIN_DAYS_AHEAD)

    @classmethod
    def validate_catering_delivery_date(
        cls,
        delivery_date: date,
        *,
        order_at: datetime | None = None,
    ) -> None:
        earliest = cls.calculate_catering_earliest_date(
            cls.to_local(order_at or datetime.now(UTC)).date(),
        )
        if delivery_date < earliest:
            raise ValidationError(
                f"Catering delivery must be at least {CATERING_MIN_DAYS_AHEAD} days from today. "
                f"Earliest available date is {earliest.isoformat()}.",
            )

    @classmethod
    def resolve_delivery_date(
        cls,
        *,
        order_type: OrderType,
        requested_date: date | None,
        order_at: datetime | None = None,
        config: DeliveryScheduleConfig = DEFAULT_SCHEDULE_CONFIG,
    ) -> date:
        if order_type == OrderType.WEEKLY_DELIVERY:
            return cls.calculate_weekly_delivery_date(order_at, config=config)

        if requested_date is None:
            raise ValidationError("Catering orders require a delivery date.")
        cls.validate_catering_delivery_date(requested_date, order_at=order_at)
        return requested_date
