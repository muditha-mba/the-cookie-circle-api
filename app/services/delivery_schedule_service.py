"""Delivery date calculation from business settings."""

from datetime import date, timedelta

from app.core.enums import Weekday
from app.utils.weekday import weekday_to_index


class DeliveryScheduleService:
    """Calculate suggested delivery dates based on cutoff and delivery weekdays."""

    @staticmethod
    def calculate_delivery_date(
        *,
        order_date: date,
        cutoff_day: Weekday,
        delivery_day: Weekday,
    ) -> date:
        """Return the next applicable delivery date for an order placed on order_date."""
        order_weekday = order_date.weekday()
        cutoff_index = weekday_to_index(cutoff_day)
        delivery_index = weekday_to_index(delivery_day)

        days_to_delivery = (delivery_index - order_weekday) % 7
        candidate = order_date + timedelta(days=days_to_delivery)

        if order_weekday >= cutoff_index:
            span = (delivery_index - cutoff_index) % 7
            if days_to_delivery == 0 or days_to_delivery <= span:
                candidate += timedelta(days=7)

        return candidate
