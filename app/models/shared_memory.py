"""Shared memory SQLAlchemy model."""

import uuid

from sqlalchemy import Boolean, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.base import TimestampMixin


class SharedMemory(Base, TimestampMixin):
    """Customer social media post featured on the client website."""

    __tablename__ = "shared_memories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="", server_default="")
    preview_image_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    post_url: Mapped[str] = mapped_column(String(500), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="true")
