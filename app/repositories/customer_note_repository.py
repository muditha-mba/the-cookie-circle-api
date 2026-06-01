"""Customer note data access."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.customer_note import CustomerNote


class CustomerNoteRepository:
    """Repository for customer notes."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, note: CustomerNote) -> CustomerNote:
        self.db.add(note)
        self.db.flush()
        return self.get_by_id(note.id)  # type: ignore[return-value]

    def get_by_id(self, note_id: uuid.UUID) -> CustomerNote | None:
        stmt = (
            select(CustomerNote)
            .options(joinedload(CustomerNote.created_by))
            .where(CustomerNote.id == note_id)
        )
        return self.db.scalar(stmt)

    def list_for_customer(self, customer_id: uuid.UUID) -> list[CustomerNote]:
        stmt = (
            select(CustomerNote)
            .options(joinedload(CustomerNote.created_by))
            .where(CustomerNote.customer_id == customer_id)
            .order_by(CustomerNote.created_at.desc())
        )
        return list(self.db.scalars(stmt).unique().all())

    def delete(self, note: CustomerNote) -> None:
        self.db.delete(note)
