"""Flexible key-value business settings model."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.base import TimestampMixin


class BusinessSetting(Base, TimestampMixin):
    """Operational setting stored as key-value for extensibility."""

    __tablename__ = "business_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
