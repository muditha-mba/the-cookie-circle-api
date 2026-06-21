"""Load delivery schedule messaging from business settings."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import Weekday
from app.database.session import SessionLocal
from app.services.business_setting_service import BusinessSettingService
from app.utils.delivery_schedule import (
    DeliveryScheduleConfig,
    DeliveryScheduleCopy,
    build_delivery_schedule_config,
    build_delivery_schedule_copy,
)


def delivery_schedule_config_from_settings(
    *,
    order_cutoff_day: Weekday,
    delivery_day: Weekday,
) -> DeliveryScheduleConfig:
    return build_delivery_schedule_config(
        cutoff_day=order_cutoff_day,
        delivery_day=delivery_day,
    )


def delivery_schedule_copy_from_settings(
    *,
    order_cutoff_day: Weekday,
    delivery_day: Weekday,
) -> DeliveryScheduleCopy:
    return build_delivery_schedule_copy(
        cutoff_day=order_cutoff_day,
        delivery_day=delivery_day,
    )


def get_delivery_schedule_copy(db: Session) -> DeliveryScheduleCopy:
    settings = BusinessSettingService(db).get_settings()
    return delivery_schedule_copy_from_settings(
        order_cutoff_day=settings.order_cutoff_day,
        delivery_day=settings.delivery_day,
    )


def get_delivery_schedule_config(db: Session) -> DeliveryScheduleConfig:
    settings = BusinessSettingService(db).get_settings()
    return delivery_schedule_config_from_settings(
        order_cutoff_day=settings.order_cutoff_day,
        delivery_day=settings.delivery_day,
    )


def get_delivery_schedule_copy_standalone() -> DeliveryScheduleCopy:
    """Load schedule copy in an isolated session (email rendering, etc.)."""
    db = SessionLocal()
    try:
        return get_delivery_schedule_copy(db)
    finally:
        db.close()
