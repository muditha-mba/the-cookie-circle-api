"""Customer-facing delivery date rules (Sri Lanka timezone)."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.enums import OrderType
from app.core.exceptions import ValidationError

SRI_LANKA_TZ = ZoneInfo("Asia/Colombo")
WEEKLY_CUTOFF_WEEKDAY = 2  # Wednesday
WEEKLY_CUTOFF_TIME = time(23, 59, 59)
DELIVERY_WEEKDAY = 5  # Saturday

CATERING_MIN_DAYS_AHEAD = 3
CATERING_MIN_COOKIE_QUANTITY = 30

WEEKLY_DELIVERY_EXPLANATION = (
    "Orders placed before Wednesday 11:59 PM are delivered on the upcoming Saturday. "
    "Orders placed after the cutoff are delivered on the following Saturday."
)


class CustomerDeliveryDateService:
    """Reusable delivery scheduling for website checkout."""

    @staticmethod
    def to_local(order_at: datetime) -> datetime:
        if order_at.tzinfo is None:
            order_at = order_at.replace(tzinfo=UTC)
        return order_at.astimezone(SRI_LANKA_TZ)

    @classmethod
    def is_before_weekly_cutoff(cls, order_at: datetime | None = None) -> bool:
        local = cls.to_local(order_at or datetime.now(UTC))
        if local.weekday() < WEEKLY_CUTOFF_WEEKDAY:
            return True
        if local.weekday() > WEEKLY_CUTOFF_WEEKDAY:
            return False
        return local.time() <= WEEKLY_CUTOFF_TIME

    @staticmethod
    def week_saturday(reference: date) -> date:
        monday = reference - timedelta(days=reference.weekday())
        return monday + timedelta(days=DELIVERY_WEEKDAY)

    @classmethod
    def next_saturday(cls, reference: date) -> date:
        days = (DELIVERY_WEEKDAY - reference.weekday()) % 7
        if days == 0:
            days = 7
        return reference + timedelta(days=days)

    @classmethod
    def calculate_weekly_delivery_date(cls, order_at: datetime | None = None) -> date:
        """Assign the next applicable Saturday batch for weekly cookie delivery."""
        local = cls.to_local(order_at or datetime.now(UTC))
        order_date = local.date()
        this_week_sat = cls.week_saturday(order_date)

        if cls.is_before_weekly_cutoff(order_at):
            if order_date <= this_week_sat:
                return this_week_sat
            return cls.week_saturday(order_date + timedelta(days=7))

        return cls.week_saturday(order_date + timedelta(days=7))

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
    ) -> date:
        if order_type == OrderType.WEEKLY_DELIVERY:
            return cls.calculate_weekly_delivery_date(order_at)

        if requested_date is None:
            raise ValidationError("Catering orders require a delivery date.")
        cls.validate_catering_delivery_date(requested_date, order_at=order_at)
        return requested_date
