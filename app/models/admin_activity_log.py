"""Admin activity log SQLAlchemy model."""

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import ActivityAction, ActivityResourceType, ClientDeviceType
from app.database.base import Base
from app.models.base import TimestampMixin
from app.models.enum_columns import (
    activity_action_enum,
    activity_resource_type_enum,
    client_device_type_enum,
)


class AdminActivityLog(Base, TimestampMixin):
    """Immutable audit trail for admin panel actions."""

    __tablename__ = "admin_activity_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    actor_admin_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    action: Mapped[ActivityAction] = mapped_column(activity_action_enum, nullable=False, index=True)
    resource_type: Mapped[ActivityResourceType] = mapped_column(
        activity_resource_type_enum,
        nullable=False,
        index=True,
    )
    resource_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    resource_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    http_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    browser_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    browser_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    os_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    os_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    device_type: Mapped[ClientDeviceType] = mapped_column(
        client_device_type_enum,
        nullable=False,
        default=ClientDeviceType.UNKNOWN,
    )
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )
