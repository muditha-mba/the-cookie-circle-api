"""Shared memory data access."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.shared_memory import SharedMemory


class SharedMemoryRepository:
    """Repository for shared memory records."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, memory: SharedMemory) -> SharedMemory:
        self.db.add(memory)
        return memory

    def get_by_id(self, memory_id: uuid.UUID) -> SharedMemory | None:
        stmt = select(SharedMemory).where(SharedMemory.id == memory_id)
        return self.db.scalar(stmt)

    def list_all(self) -> list[SharedMemory]:
        stmt = select(SharedMemory).order_by(
            SharedMemory.sort_order.asc(),
            SharedMemory.created_at.asc(),
        )
        return list(self.db.scalars(stmt).all())

    def list_active(self) -> list[SharedMemory]:
        stmt = (
            select(SharedMemory)
            .where(SharedMemory.is_active.is_(True))
            .order_by(SharedMemory.sort_order.asc(), SharedMemory.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def delete(self, memory: SharedMemory) -> None:
        self.db.delete(memory)

    def next_sort_order(self) -> int:
        stmt = select(func.coalesce(func.max(SharedMemory.sort_order), -1))
        current_max = self.db.scalar(stmt)
        return int(current_max or -1) + 1
